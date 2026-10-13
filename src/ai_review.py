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

SYSTEM_PROMPT = """你是 Clash 免费节点审核员。输入是一批待审节点（序号|协议|名称|server）。

剔除以下情况（verdict=drop）：
1. 引流/广告/机场促销/导航站/群组引流/订阅地址本身
2. 占位符、示例、已失效提示（过期、剩余流量、官网、公告）
3. 伪装成海外出口的境内中转/落地（名称声称某国但 server 是明显境内/中转域名或 IP）
4. 同一出口的重复营销位

保留正常节点（verdict=keep）。判定存疑时选 keep —— 宁可放过垃圾，不可误杀好节点。

只输出 JSON：{"decisions":[{"n":序号,"verdict":"keep|drop","why":"不超过20字理由"}]}
不要输出任何其他文字，不要改写节点内容。"""

CHUNK = 120
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


def _call_http(nodes, soft_map, cfg):
    base = cfg["base_url"].rstrip("/")
    if "/v1" not in base:
        base += "/v1"
    body = {
        "model": cfg["model"],
        "temperature": 0,
        "max_tokens": 2000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _fmt_chunk(nodes, soft_map)},
        ],
    }
    data = json.dumps(body).encode("utf-8")
    import urllib.request
    req = urllib.request.Request(
        base + "/chat/completions", data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + cfg["api_key"]})
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
            out = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 400:  # 有的服务不认 response_format / max_tokens，重试一次精简请求
            body.pop("max_tokens", None)
            req = urllib.request.Request(
                base + "/chat/completions", data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + cfg["api_key"]})
            with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
                out = json.loads(r.read().decode("utf-8"))
        else:
            raise
    content = out["choices"][0]["message"]["content"]
    return _parse_json(content)


def _call_opencode(nodes, soft_map, cfg):
    prompt = SYSTEM_PROMPT + "\n\n待审节点：\n" + _fmt_chunk(nodes, soft_map)
    exe = cfg.get("opencode_exe") or "opencode"
    p = subprocess.run([exe, "run", prompt], capture_output=True, text=True,
                       timeout=cfg["timeout"])
    if p.returncode != 0:
        raise RuntimeError("opencode run 退出码 %d: %s" % (p.returncode, p.stderr[:200]))
    return _parse_json(p.stdout)


def _decisions_to_map(obj, offset, n_total):
    """把 chunk 内序号映射回节点索引；模型编号乱了就整块放弃。"""
    res = {}
    for d in (obj or {}).get("decisions") or []:
        try:
            n = int(d.get("n"))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= n_total:
            res[offset + n] = ("drop" if str(d.get("verdict", "")).lower() == "drop"
                               else "keep", str(d.get("why", ""))[:40])
    return res


def review_source(nodes, soft_map, mode, cfg, source_name, log):
    """返回 (drop_indices, 统计dict)。任何异常 -> 空 drop + 统计记 fail-soft。"""
    stats = {"mode": mode, "chunks": 0, "reviewed": 0, "dropped": 0,
             "rolled_back": False, "error": None}
    if mode == "off" or not nodes:
        return [], stats
    drops = {}
    reasons = []
    for off in range(0, len(nodes), CHUNK):
        chunk = nodes[off:off + CHUNK]
        stats["chunks"] += 1
        try:
            obj = _call_http(chunk, soft_map, cfg) if mode == "http" \
                else _call_opencode(chunk, soft_map, cfg)
        except Exception as e:
            stats["error"] = str(e)[:200]
            log("  [ai] %s chunk@%d 调用失败: %s" % (source_name, off, stats["error"]))
            return [], stats          # fail-soft：本源不剔除
        dm = _decisions_to_map(obj, off, len(chunk))
        stats["reviewed"] += len(dm)
        for idx, (verdict, why) in dm.items():
            if verdict == "drop":
                drops[idx] = why
                reasons.append(why)
    ratio = len(drops) / max(1, len(nodes))
    if ratio > DROP_RATIO_GUARD:
        stats["rolled_back"] = True
        stats["dropped"] = 0
        log("  [ai] %s 剔除比例 %.0f%% > 阈值 %.0f%%，疑似模型误读 -> 全部回滚"
            % (source_name, ratio * 100, DROP_RATIO_GUARD * 100))
        return [], stats
    stats["dropped"] = len(drops)
    stats["top_reasons"] = sorted(set(reasons), key=reasons.count, reverse=True)[:5]
    return sorted(drops.keys()), stats


def resolve_mode(arg_mode):
    """auto：有 base_url+key 就 http，否则关掉。"""
    if arg_mode in ("http", "opencode", "off"):
        return arg_mode
    if os.environ.get("AI_BASE_URL") and os.environ.get("AI_API_KEY"):
        return "http"
    return "off"


def config_from_env():
    return {
        "base_url": os.environ.get("AI_BASE_URL", ""),
        "api_key": os.environ.get("AI_API_KEY", ""),
        "model": os.environ.get("AI_MODEL", "gpt-4o-mini"),
        "timeout": int(os.environ.get("AI_TIMEOUT", "90")),
        "opencode_exe": os.environ.get("OPENCODE_EXE", "opencode"),
    }