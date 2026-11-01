# -*- coding: utf-8 -*-
"""league.py 门禁：末位淘汰决策纯函数 + sources.yaml 换位写入对账。"""
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import league  # noqa: E402
import refill  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    print("  %s %s%s" % ("✓" if cond else "✗", name, ("  " + detail) if detail else ""))
    if not cond:
        ok = False


def make_text(n, enabled_first=None):
    """造 n 个源的 sources.yaml；enabled_first 非 None 时只让前这几个 enabled。"""
    lines = ["sources:"]
    for i in range(n):
        en = "true" if (enabled_first is None or i < enabled_first) else "false"
        lines += [
            "  - name: src%02d" % i,
            "    url: https://example/src%02d.yaml" % i,
            "    enabled: %s" % en,
            "    note: test src %02d" % i,
        ]
    lines += ["excluded: []"]
    return "\n".join(lines)


print("=" * 68)
print("场景 A：decide —— 挑战者超末位 +5pp -> swap")
print("=" * 68)
en = {"a": (30.0, 10), "b": (25.0, 8), "c": (10.0, 4)}   # cap=3，末位 c
ch = {"ch1": (16.0, 5)}                                   # 超 c 6pp
act, out_n, in_n, why = league.decide(en, ch, 3)
check("swap 且对象正确", act == "swap" and out_n == "c" and in_n == "ch1", why)

print("")
print("场景 B：挑战者只超 3pp（< 5pp 防抖）-> hold")
ch2 = {"ch1": (12.0, 5)}
act, out_n, in_n, why = league.decide(en, ch2, 3)
check("hold", act == "hold", why)

print("")
print("场景 C：挑战者 alive < 3 -> 不配")
act, out_n, in_n, why = league.decide(en, {"ch1": (90.0, 2)}, 3)
check("hold（alive 门槛）", act == "hold", why)

print("")
print("场景 D：enabled 不满 cap -> 无条件补空位（promote）")
act, out_n, in_n, why = league.decide({"a": (30.0, 10), "b": (25.0, 8)},
                                      {"ch1": (5.0, 4)}, 3)
check("promote", act == "promote" and in_n == "ch1", why)

print("")
print("场景 E：无挑战者 -> hold")
act, _, _, why = league.decide(en, {}, 3)
check("hold（无挑战者）", act == "hold", why)

print("")
print("=" * 68)
print("场景 F：sources.yaml 换位写入（通道挑战者）—— 7 源真表格")
print("=" * 68)
tmp = tempfile.mkdtemp(prefix="league_")
src_path = os.path.join(tmp, "sources.yaml")
base = make_text(8, enabled_first=7)      # 8 源 7 enabled（1 个已 disabled）
io.open(src_path, "w", encoding="utf-8", newline="\n").write(base)
import yaml  # noqa: E402
doc = yaml.safe_load(base)

# 末位 = src06（enabled 的第 7 个）；挑战者从通道来
text2 = league._flip_to_relegated(base, "src06", "2026-11-02")
block = refill.render_block(
    "challenger", {"url": "https://example/challenger.yaml", "rate": 30.0,
                   "alive": 6, "best_ms": 300, "evaluated_at": "2026-11-02T00:00:00Z"},
    "2026-11-02T00:00:00Z")
text3 = refill.insert_block(text2, block)
try:
    league.verify_swap(doc, text3, "src06", "challenger", 7, 1, 0, True)
    check("swap 写入对账通过", True)
except SystemExit as e:
    check("swap 写入对账通过", False, str(e))
d2 = yaml.safe_load(text3)
w = next(s for s in d2["sources"] if s["name"] == "src06")
check("src06 已降级带 relegated 标", w["enabled"] is False and w["relegated"] == "2026-11-02")
check("enabled 数不变（-1+1）",
      sum(1 for s in d2["sources"] if s.get("enabled")) == 7)
check("challenger 已入册且 enabled",
      any(s["name"] == "challenger" and s.get("enabled") for s in d2["sources"]))

print("")
print("场景 G：relegated 回归（换位式回归：src05 降级换 src06 回场，源数/enabled 均不变）")
# 基线 = 换位后的当前文件（真实流程里回归发生在换位后的下一轮）
doc3 = yaml.safe_load(text3)
en3 = sum(1 for s in doc3["sources"] if s.get("enabled"))
# 真实流程：回归必须伴随在册末位降级（否则 enabled 超 cap，对账会正确拒绝）
text4 = league._flip_to_relegated(text3, "src05", "2026-11-03")
text5 = league._flip_enabled_back(text4, "src06")
text5 = league._drop_relegated_field(text5, "src06")
try:
    league.verify_swap(doc3, text5, "src05", "src06", en3, 0, 0, True)
    check("回归换位对账通过", True)
except SystemExit as e:
    check("回归换位对账通过", False, str(e))
d3 = yaml.safe_load(text5)
w = next(s for s in d3["sources"] if s["name"] == "src06")
check("src06 回归 enabled=true 且无 relegated 标",
      w["enabled"] is True and "relegated" not in w)
check("enabled 恒等于 7", sum(1 for s in d3["sources"] if s.get("enabled")) == 7)
d3 = yaml.safe_load(text5)
w = next(s for s in d3["sources"] if s["name"] == "src06")
check("src06 回归 enabled=true 且无 relegated 标",
      w["enabled"] is True and "relegated" not in w)

print("")
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)
