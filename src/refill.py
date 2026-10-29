# -*- coding: utf-8 -*-
"""自动补员 —— cap 内把评估通道里最强的 approved 候选补进 src/sources.yaml。

定位（2026-10-29 拍板：「两个待拍板项做吧，补员也自动化处理」）：
  评估（tools/eval_candidates.py，本机 12:30 链）只负责给 verdict，写进
  data/eval_verdicts.json（单写者通道：CI 从不写它）；discovered_pool.json 是
  CI discover 的专属写域 —— 两个文件各一个写者，零冲突（这是 source_health
  当年「低频方被高频方冲成死环节」教训的反向利用）。
  本脚本在 CI（每 6h 那轮的最后一步）消费评估通道：
      approved 候选 -> 空位且节流过 -> 选出最强的 1 个 -> 排重 -> append 插入。

铁规矩（每一条都有出处）：
  ① **只 append，不改任何既有行**。sources.yaml 里最值钱的是注释
     （为什么 exclude_filter 必须逐源之类，write_src_cfg 的教训是整份重写 =
     注释全灭）。本脚本插入一条新条目，其余逐字节不动；enabled 的翻转归
     health.py，历史库归档也归 health.py —— 各写各的字段，互不越界。
  ② **cap=TARGET_CAP**：enabled 数 >= 12 不再补员。现存 15 个不动（2026-10-29
     拍板），所以 cap 只管理未来：什么时候降到 12 以下，什么时候开始补。
     满员时 approved 候选在通道里**挂待用**（verdict 不是状态机的一部分，
     「待用」= approved 但尚未入组，refill 每轮再看）。
  ③ **每轮 <=1 + 节流 >=24h**：补员是慢系统。一次塞好几个新源，AUTO 分组 /
     AI 审核 / 降级机制都要一次性消化，观察期会变得毫无意义。
     state/refill_last.json 记录最后一次补员，间隔不足就跳过这一轮。
  ④ **已在清单里的 URL 一律跳过**：excluded 段是评估/人工的排除决定（自动
     补员绝不推翻）；sources 里 enabled=false 的（含隔离中）也不重复进。
     ——历史上被判死又留在 sources 里的 URL 在这里天然被挡住，不会死灰复燃。
  ⑤ 写入前用 yaml 全量解析**对账**：旧条目逐个都在且顺序不变 / 新条目 = 旧+1 /
     enabled 数不超 cap / excluded 段逐个未动。对不上一个字节都不写。

  退出规则（观察期）在 health.py：auto_added 源累计「双口径均值 < 2% 且
  云效 >= 7 轮、本机 >= 3 轮」→ 自动降级（沿用 quarantined 机制，真翻盘仍可
  走回收路径回来）。准入在这里，退出在那边，两把尺子互相独立。

用法：
    python src/refill.py            # CI 里真跑（决策+写入+state）
    python src/refill.py --dry-run  # 全程只打印，不写任何文件
    REFILL_DISABLE=1 环境变量     # 紧急停用开关（跳过，不写）
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import yaml                                     # noqa: E402
import health                                   # noqa: E402  （复用 _src_entries/_atomic_write/_hours_between）

SOURCES = os.path.join(HERE, "sources.yaml")
CHANNEL = os.path.join(ROOT, "data", "eval_verdicts.json")
STATE = os.path.join(ROOT, "state", "refill_last.json")

# cap（10-19 拍板 TARGET_SOURCES=12）与节流
TARGET_CAP = 12          # enabled 稳态上限；现存 15 个不动，cap 只管未来
MIN_GAP_HOURS = 24       # 两次补员的最小间隔（ISO 时间口径，坏时间戳=不补）
NAME_RE = re.compile(r"[^A-Za-z0-9_\-]")
NOTE_MAX = 240           # note 防御上限：评估结论可能异常长，别把清单撑爆


def fnum(v, default=0.0):
    """把通道里可能漂移类型的数值安全转 float（防御：eval 字段类型由 JSON 保证，
    但通道是跨推送的产物，宁可兜底也不让一次类型漂移炸掉整轮 CI）。
    bool 显式排除（isinstance(True, int) 是真，True 会混进排序）。
    """
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default
    return float(v)


def load_channel():
    """读评估通道。

    返回 (candidates, reason)。文件不存在是完全正常的早期状态（eval 还没跑过）；
    存在但坏了 -> 大声说明并按「没有数据」处理（本脚本是非关键消费者，
    报警交给 eval 侧修文件，绝不在这里红 CI 刷屏）。
    """
    try:
        with open(CHANNEL, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return [], "评估通道还不存在（eval_verdicts.json 由本机 12:30 链产出），本轮无事"
    except Exception as e:
        print("[refill] ✗ 评估通道存在但解析失败（不是本侧能修的，交给 eval 侧）：%s: %s"
              % (type(e).__name__, str(e)[:100]))
        return [], None
    if not isinstance(d, dict) or not isinstance(d.get("candidates"), list):
        print("[refill] ✗ 评估通道结构不对（缺 candidates 列表），按无数据处理")
        return [], None
    return [c for c in d["candidates"] if isinstance(c, dict)], None


def load_state():
    """读节流状态。损坏 -> None（跳过本轮：节流未知时「不补」永远是保守方向）。"""
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print("[refill] ⚠ 节流状态损坏（%s: %s），本轮按「刚补过」处理，不补"
              % (type(e).__name__, str(e)[:80]))
        return None


def enabled_count(cfg):
    return sum(1 for s in (cfg.get("sources") or [])
               if isinstance(s, dict) and s.get("enabled", True))


def known_urls(cfg):
    """sources + excluded 两段的所有 URL（补员排重用）。

    注意 archive 不在其中：隔离中的源留在 sources.yaml（enabled=false），
    已经由这里挡住；历史库里单独记的条目指望 discover.dead_urls 去拦发现侧。
    """
    out = set()
    for s in (cfg.get("sources") or []) + (cfg.get("excluded") or []):
        if isinstance(s, dict) and s.get("url"):
            out.add(s["url"])
    return out


def pick_best(cands):
    """排序：rate 降序 > alive 降序 > best_ms 升序，同分时 evaluated_at 新者优先。

    ⚠ 用两次稳定排序实现多键（先次要键、后主键），避免反向字符串比较的怪招。
    """
    def bm(c):
        v = c.get("best_ms")
        return fnum(v, 10 ** 9) if v is not None else 10 ** 9

    cands = sorted(cands, key=lambda c: str(c.get("evaluated_at") or ""), reverse=True)
    cands = sorted(cands, key=lambda c: (-fnum(c.get("rate")), -fnum(c.get("alive")), bm(c)))
    return cands[0]


def derive_name(c, taken):
    """给新条目起名，不许与既有源重名（撞了就 -2/-3 递增）。

    优先复用评估通道存的名字；没有就从 repo 的尾段、再从 URL 尾段猜——
    与人工接入时 ClashVerge 看到的名字风格保持同调（短、可读、去符号）。
    """
    base = (c.get("name") or "").strip()
    if not base:
        repo = (c.get("repo") or "").strip()
        if repo and "/" in repo:
            base = repo.rsplit("/", 1)[1]
    if not base:
        url = (c.get("url") or "").rstrip("/")
        base = os.path.basename(url.split("?")[0]).rsplit(".", 1)[0]
    base = NAME_RE.sub("", base).strip("-_") or "autorefill"
    nm, k = base, 2
    while nm in taken:
        nm = "%s-%d" % (base, k)
        k += 1
    return nm


def _plain(v):
    """note 一律组原子自己拼（不信通道里的自由文本）：全量 ASCII 字段对 +
    时间戳里没有「: 」（YAML plain scalar 的雷），超长裁断。"""
    return str(v or "").replace("\n", " ").replace("\r", " ")[:NOTE_MAX]


def render_block(name, c, now):
    """渲染待插入的文本块（缩进与文件里其他条目一致：条目 2 空格、字段 4 空格）。"""
    rate, alive = fnum(c.get("rate")), int(fnum(c.get("alive")))
    bm = c.get("best_ms")
    ev = _plain(c.get("evaluated_at"))
    note = ("补员(单轮结果,照常走降级机制) rate=%.1f%% alive=%d best=%sms @%s"
            % (rate, alive, ("%d" % int(bm)) if bm is not None else "-", ev))
    note = _plain(note)
    banner = "  # ── 自动补员 %s（src/refill.py cap 内补位；excluded 段不动）──" % now
    return [
        banner,
        "  - name: %s" % name,
        "    url: %s" % _plain(c.get("url")),
        "    enabled: true",
        "    max_nodes: 500",
        "    auto_added: true",
        "    note: %s" % note,
    ]


def insert_block(text, block):
    """在 sources: 段末尾（紧贴 excluded 段注释横幅之前）append 插入，其余不动。

    复用 health._src_entries —— 是同一套被 test_src_cfg_write 磨过的扫描逻辑，
    不自己再写一份「sources: 段在哪结束」，两处迟早分叉。
    """
    entries = health._src_entries(text)
    if not entries:
        raise SystemExit(
            "[refill] ✗ 拒绝写入：sources: 段里一个条目都扫不出来。\n"
            "         清单是 pipeline 的唯一事实来源，这种形状说明文件结构已经坏了，\n"
            "         宁可整轮不补，也不能盲插。先人工检查 src/sources.yaml。")
    lines = text.split("\n")
    idx = entries[-1][2]                        # 最后一个条目的结束行 = 首个顶层行
    if idx > 0 and lines[idx - 1].strip():
        block = [""] + block                    # 保证与上一条目之间有空行
    return "\n".join(lines[:idx] + block + [""] + lines[idx:])


def verify_text(before_doc, after_text, prev_enabled):
    """写入前的对账（返回 None=通过，否则 raise SystemExit）。

    这里的失败方向必须是「没写」，而不是「写了再发现」——所以先在**内存里**
    验证新文本，任何一条不满足都直接拒绝（调用方根本还没碰磁盘）。
    """
    after = yaml.safe_load(after_text)
    if not isinstance(after, dict) or not isinstance(after.get("sources"), list):
        raise SystemExit("[refill] ✗ 对账失败：新文本解析后没有 sources 列表")
    sb = [s for s in (before_doc.get("sources") or []) if isinstance(s, dict)]
    sa = after["sources"]
    if len(sa) != len(sb) + 1:
        raise SystemExit("[refill] ✗ 对账失败：源数 %d -> %d（应为 +1）"
                         % (len(sb), len(sa)))
    if sa[:len(sb)] != sb:
        raise SystemExit("[refill] ✗ 对账失败：旧条目被改动了（顺序/内容必须逐个不变）")
    new = sa[len(sb)]
    if not (new.get("auto_added") is True and new.get("enabled") is True
            and new.get("max_nodes") == 500):
        raise SystemExit("[refill] ✗ 对账失败：新条目缺 auto_added/enabled/max_nodes=500")
    if enabled_count(after) != prev_enabled + 1:
        raise SystemExit("[refill] ✗ 对账失败：enabled 数 %d -> %d（应为 +1）"
                         % (prev_enabled, enabled_count(after)))
    if enabled_count(after) > TARGET_CAP:
        raise SystemExit("[refill] ✗ 对账失败：enabled %d 超 cap %d" %
                         (enabled_count(after), TARGET_CAP))
    if [e for e in (after.get("excluded") or []) if isinstance(e, dict)] != \
       [e for e in (before_doc.get("excluded") or []) if isinstance(e, dict)]:
        raise SystemExit("[refill] ✗ 对账失败：excluded 段被动过了")
    return after


def save_state(prev, rec):
    st = prev if isinstance(prev, dict) else {}
    hist = list(st.get("history") or [])
    hist.append({k: rec[k] for k in rec if k != "history"})
    st["history"] = hist[-30:]
    st["last_refill_at"] = rec["at"]
    st["last_name"] = rec["name"]
    st["last_url"] = rec["url"]
    st["v"] = 1
    health._atomic_write(STATE, json.dumps(st, ensure_ascii=False, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description="自动补员：评估通道 -> cap 内补位（每轮 <=1）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写任何文件")
    args = ap.parse_args(argv)

    if os.environ.get("REFILL_DISABLE"):
        print("[refill] REFILL_DISABLE=1，紧急停用开关生效，本轮跳过")
        return 0

    try:
        text = open(SOURCES, encoding="utf-8").read()
        doc = yaml.safe_load(text)
    except Exception as e:
        print("[refill] 源清单读不了：%s: %s" % (type(e).__name__, str(e)[:120]))
        return 2
    if not isinstance(doc, dict) or not isinstance(doc.get("sources"), list) \
            or not any(isinstance(s, dict) for s in doc["sources"]):
        print("[refill] 源清单结构异常（sources 段为空/缺失）——这不正常，拒绝补员")
        return 2
    enabled_n = enabled_count(doc)

    cands, reason = load_channel()
    if reason:
        print("[refill] %s" % reason)
        return 0
    if not cands and reason is None and not os.path.isfile(CHANNEL):
        return 0                                    # load_channel 已打印过

    approved = [c for c in cands
                if c.get("verdict") == "approved" and c.get("url")]
    if not approved:
        print("[refill] 通道共 %d 条，无 approved 候选，本轮无事" % len(cands))
        return 0
    known = known_urls(doc)
    fresh = [c for c in approved if c["url"] not in known]
    if not fresh:
        print("[refill] approved %d 条全部已在 sources/excluded 里（无新候选），本轮无事"
              % len(approved))
        return 0
    held = len(fresh)
    if enabled_n >= TARGET_CAP:
        print("[refill] cap 满（enabled %d/%d）：%d 条 approved 候选挂待用"
              "（pending-cap，等降级腾位后自动补）" % (enabled_n, TARGET_CAP, held))
        return 0
    st = load_state()
    if st is None:
        return 0                                    # 节流状态坏了：保守不补（已大声）
    last = (st or {}).get("last_refill_at")
    if last:
        gap = health._hours_between(last, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        if gap is None:
            print("[refill] ⚠ 上次补员时间 %r 解析不了，按节流处理，本轮不补" % last)
            return 0
        if gap < MIN_GAP_HOURS:
            print("[refill] 距上次补员 %.1fh（< %dh），节流生效本轮不补"
                  "（候选照挂：%d 条）" % (gap, MIN_GAP_HOURS, held))
            return 0

    best = pick_best(fresh)
    name = derive_name(best, {s.get("name") for s in doc["sources"]
                              if isinstance(s, dict) and s.get("name")})
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    block = render_block(name, best, now)

    print("[refill] 入选 %s（rate=%.1f%% alive=%d evaluated_at=%s）"
          % (name, fnum(best.get("rate")), int(fnum(best.get("alive"))),
             (best.get("evaluated_at") or "?")))
    for ln in block:
        print("    | " + ln)
    if args.dry_run:
        print("[refill] --dry-run：未写入")
        return 0

    new_text = insert_block(text, block)
    try:
        verify_text(doc, new_text, enabled_n)
    except SystemExit as e:
        print(str(e))
        return 2

    health._atomic_write(SOURCES, new_text)
    rec = {"at": now, "name": name, "url": best.get("url"),
           "rate": fnum(best.get("rate")), "alive": int(fnum(best.get("alive")))}
    save_state(st or {}, rec)
    print("[refill] ✅ 已补员 %s（enabled %d/%d），state=%s"
          % (name, enabled_n + 1, TARGET_CAP, os.path.relpath(STATE, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
