# -*- coding: utf-8 -*-
"""AI 审核阶段 —— 只做裁决，绝不改写节点字段。

为什么这样设计：
- LLM 适合判断「这是不是引流/伪装/占位」这类语义问题（坑 §6 §27）；
- LLM 一旦幻觉改写 server/port/uuid，产出的就是坏节点 + 坏配置，比不过滤更糟。
  所以 AI 只输出 {序号: keep/drop + 理由}，实际剔除由 build.py 按节点名精确执行。
- 任何失败都 fail-soft：AI 挂了/没配 key -> 全部保留，只在报告里记警告，绝不清空池子。

两种后端：
  http     : 任意 OpenAI 兼容接口（OpenAI / DeepSeek / 通义 / Moonshot ...）
  opencode : 本地/CI 里调 `opencode run`（非交互 agent，会话更慢，适合低频）
"""
import json
import os
import re
import subprocess
import time

SYSTEM_PROMPT = """你是 Clash 免费节点审核员。输入是一批待审节点，每行格式：序号|协议|名称|server（可能带[软标记:...]）。

只需挑出**必须剔除**的节点，剔除标准：
1. 引流/广告/机场促销/导航站/群组引流/订阅地址本身
2. 占位符、示例、失效提示（过期、剩余流量、官网、公告、维护中）
3. 明显伪装：名称声称某国，但 server 看起来像境内中转/落地/同类出口批量克隆的营销位
4. 同一条目重复出现（同名同 server）中的冗余位

注意：**免费机场的正常节点常常带「机场/推荐/订阅」等字样（如「🇮🇩 机场推荐:dafei.de 印尼 01」），这类是可用节点，必须保留**。
拿不准的一律保留 —— 宁可放过垃圾，不可误杀好节点。

只输出 JSON，不要任何其他文字：
{"drop":[{"n":序号,"why":"不超过12字理由"}]}
没有需要剔除的就输出 {"drop":[]}。绝对不要改写节点内容。"""

CHUNK = 60
# 单源 AI 剔除比例超过这个值 -> 判定为模型误读，回滚该源全部剔除
DROP_RATIO_GUARD = 0.6


def _fmt_chunk(nodes, soft_map):
    lines = []
    for i, n in enumerate(nodes, 1):
        flag = soft_map.get(n["name"]) if soft_map else None
        lines.append("%d|%s|%s|%s%s" % (i, n.get("type", "?"), n.get("name", ""),
                                       n.get("server", ""),
                                       ("  [软标记:%s]" % ",".join(flag)) if flag else ""))
    return "\n".join(lines)


def _parse_json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _norm_base(base):
    """OpenAI 兼容端点的 base_url 归一化。

    各家路径形态不一样：
      DeepSeek    https://api.deepseek.com                  -> 补 /v1
      SiliconFlow https://api.siliconflow.cn/v1              -> 原样
      智谱GLM     https://open.bigmodel.cn/api/paas/v4       -> 原样（别补 v1）
      通义千问    https://dashscope.aliyuncs.com/compatible-mode/v1 -> 原样
      Gemini      https://generativelanguage.googleapis.com/v1beta/openai -> 原样
    规则：整条路径里已经出现 /v数字 才不补。
    """
    base = base.rstrip("/")
    if not re.search(r"/v\d+", base):
        base += "/v1"
    return base


def _call_http(nodes, soft_map, cfg, max_tokens=None):
    """一次调用。返回 (obj, finish_reason)。

    推理模型（Xing4.0 / 带 reasoning_content 的）会把 token 花在思维链上，
    可能 finish_reason=length 导致 JSON 被截断 -> 上层负责放大 max_tokens 重试。
    """
    import urllib.error
    import urllib.request

    base = _norm_base(cfg["base_url"])
    body = {
        "model": cfg["model"],
        "temperature": 0,
        "max_tokens": max_tokens or cfg.get("max_tokens", 1500),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _fmt_chunk(nodes, soft_map)},
        ],
    }
    data = json.dumps(body).encode("utf-8")
    last = None
    for a in range(max(1, cfg.get("retries", 3))):
        try:
            req = urllib.request.Request(
                base + "/chat/completions", data=data,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + cfg["api_key"]})
            with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
                out = json.loads(r.read().decode("utf-8"))
            ch = (out.get("choices") or [{}])[0]
            content = (ch.get("message") or {}).get("content") or ""
            finish = ch.get("finish_reason")
            obj = _parse_json(content)
            if obj is None:
                last = "非JSON(finish=%s): %s" % (finish, content[:120])
                if finish == "length" and (max_tokens or 0) < 8000:
                    last += " (疑似被截断，放大 max_tokens 重试)"
                    time.sleep(2)
                    continue
                raise RuntimeError(last)
            return obj, finish
        except urllib.error.HTTPError as e:
            last = "HTTP %d %s" % (e.code, e.read()[:200].decode("utf-8", "replace"))
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(60, 5 * (a + 1) ** 2))   # 429/5xx 指数退避
                continue
            raise RuntimeError(last)
        except RuntimeError:
            raise
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, str(e)[:160])
            time.sleep(min(30, 3 * (a + 1)))            # 超时等瞬时错误也退避重试
    raise RuntimeError(last or "未知错误")


def _call_opencode(nodes, soft_map, cfg):
    prompt = SYSTEM_PROMPT + "\n\n待审节点：\n" + _fmt_chunk(nodes, soft_map)
    exe = cfg.get("opencode_exe") or "opencode"
    p = subprocess.run([exe, "run", prompt], capture_output=True, text=True,
                       timeout=cfg["timeout"])
    if p.returncode != 0:
        raise RuntimeError("opencode run 退出码 %d: %s" % (p.returncode, p.stderr[:200]))
    return _parse_json(p.stdout)


def _drop_map(obj, offset, n_total):
    """把 chunk 内序号映射回全局下标。兼容两种协议：
       新：{"drop":[{"n":3,"why":"引流"}]}
       旧：{"decisions":[{"n":3,"verdict":"drop","why":"..."}]}
    """
    res = {}
    items = obj.get("drop") or obj.get("decisions") or []
    if isinstance(items, dict):
        items = [items]
    for d in items:
        if not isinstance(d, dict):
            # 也容忍 ["3","17"] 这种纯数组
            try:
                n = int(str(d).strip())
                res[offset + n] = ("", "")
                continue
            except (TypeError, ValueError):
                continue
        try:
            n = int(d.get("n", d.get("i", d.get("idx"))))
        except (TypeError, ValueError):
            continue
        if not (1 <= n <= n_total):
            continue
        verdict = str(d.get("verdict", "drop")).lower()
        if "drop" in obj and d.get("verdict") is None:
            verdict = "drop"
        if verdict == "drop":
            res[offset + n] = (str(d.get("why", ""))[:40], str(d.get("name", ""))[:60])
    return res


def review_source(nodes, soft_map, mode, cfg, source_name, log):
    """返回 (drop_indices, 统计dict)。

    多后端故障转移：按 backends 顺序试，某后端耗尽重试仍失败就换下一个。
    fail-soft 粒度 = **单个 chunk**：某批全后端都失败只影响那一批；
    只有整源所有批都失败才算「AI 不可用」。
    """
    stats = {"mode": mode, "chunks": 0, "chunks_failed": 0, "reviewed": 0,
             "dropped": 0, "rolled_back": False, "error": None,
             "backends": cfg.get("_names"), "served": {}}
    if mode == "off" or not nodes:
        return [], stats
    drops, reasons = {}, []
    for off in range(0, len(nodes), CHUNK):
        chunk = nodes[off:off + CHUNK]
        stats["chunks"] += 1
        obj, used_backend = None, None
        for bi, b in enumerate(cfg.get("backends") or [cfg]):
            mt = cfg.get("max_tokens", 1500)
            for grow in (0, 1):        # 第二次：放大 max_tokens（应对推理模型截断）
                if obj is not None:
                    break
                try:
                    if mode == "opencode":
                        obj = _call_opencode(chunk, soft_map, b)
                        used_backend = "opencode"
                        break
                    obj, _finish = _call_http(chunk, soft_map, b, max_tokens=(mt * 4 if grow else mt))
                    used_backend = b.get("_name", "backend%d" % bi)
                    break
                except Exception as e:
                    log("  [ai] %s chunk@%d %s 失败: %s"
                        % (source_name, off, b.get("_name", "?"), str(e)[:110]))
        if obj is None:
            stats["chunks_failed"] += 1
            if stats["error"] is None:
                stats["error"] = "全部后端失败（chunk@%d）" % off
            continue
        stats["served"][used_backend] = stats["served"].get(used_backend, 0) + 1
        dm = _drop_map(obj, off, len(chunk))
        stats["reviewed"] += len(dm)
        for idx, (why, _nm) in dm.items():
            drops[idx] = why
            reasons.append(why)

    if stats["chunks_failed"] and stats["chunks_failed"] == stats["chunks"]:
        stats["error"] = stats["error"] or "全部批次失败"
        log("  [ai] %s 全部 %d 批失败 -> 本源不剔除" % (source_name, stats["chunks"]))
        return [], stats

    ratio = len(drops) / max(1, len(nodes))
    if ratio > DROP_RATIO_GUARD:
        stats["rolled_back"] = True
        stats["dropped"] = 0
        log("  [ai] %s 剔除比例 %.0f%% > 阈值 %.0f%%，疑似模型误读 -> 全部回滚"
            % (source_name, ratio * 100, DROP_RATIO_GUARD * 100))
        return [], stats
    stats["dropped"] = len(drops)
    stats["top_reasons"] = sorted(set(reasons), key=reasons.count, reverse=True)[:5]
    # 逐条留痕：AI 删了哪个节点、理由是什么（给人看，也便于事后调 prompt）
    stats["drop_detail"] = [{"name": nodes[i].get("name"), "type": nodes[i].get("type"),
                             "server": nodes[i].get("server"), "why": w}
                            for i, w in sorted(drops.items())][:200]
    return sorted(drops.keys()), stats


def resolve_mode(arg_mode):
    """auto：有任意可用后端就 http，否则关掉。"""
    if arg_mode in ("http", "opencode", "off"):
        return arg_mode
    if config_from_env()["backends"]:
        return "http"
    return "off"


def load_backends():
    """后端清单：src/ai_backends.yaml，key 从同名环境变量读（不落文件、不进 git）。

    例：
      - name: siliconflow_xing
        base_url: https://api.siliconflow.cn/v1
        model: XingChenAGI/Xing4.0-29B
        env_key: AI_KEY_SILICONFLOW
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_backends.yaml")
    out = []
    if os.path.exists(path):
        try:
            import yaml
            for b in (yaml.safe_load(open(path, encoding="utf-8")) or {}).get("backends") or []:
                key = os.environ.get(b.get("env_key", ""), "")
                if not key:
                    continue
                cfg = dict(b)
                cfg["api_key"] = key
                cfg["_name"] = b.get("name", "backend")
                cfg["timeout"] = int(os.environ.get("AI_TIMEOUT", b.get("timeout", 300)))
                cfg["retries"] = int(os.environ.get("AI_RETRIES", b.get("retries", 3)))
                out.append(cfg)
        except Exception:
            pass
    return out


def config_from_env():
    """单后端（AI_BASE_URL/AI_API_KEY）与多后端（ai_backends.yaml）统一出口。"""
    base = {
        "base_url": os.environ.get("AI_BASE_URL", ""),
        "api_key": os.environ.get("AI_API_KEY", ""),
        "model": os.environ.get("AI_MODEL", "gpt-4o-mini"),
        "timeout": int(os.environ.get("AI_TIMEOUT", "300")),
        # OpenRouter 免费模型是共享池，429 很常见；2026-10-14 实测上游限流 -> 必须退避重试
        "retries": int(os.environ.get("AI_RETRIES", "4")),
        "max_tokens": int(os.environ.get("AI_MAX_TOKENS", "1500")),
        "opencode_exe": os.environ.get("OPENCODE_EXE", "opencode"),
    }
    backends = load_backends()
    if backends:
        base["backends"] = backends
        base["_names"] = [b["_name"] for b in backends]
    elif base["base_url"] and base["api_key"]:
        base["backends"] = [dict(base, _name="env-single")]
        base["_names"] = ["env-single"]
    else:
        base["backends"] = []
        base["_names"] = []
    return base