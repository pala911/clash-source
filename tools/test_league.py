# -*- coding: utf-8 -*-
"""league.py 门禁：末位淘汰决策纯函数 + sources.yaml 换位写入对账。"""
import io
import json
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
print("=" * 68)
print("场景 H：decide 的参赛键 -> 写入路径（2026-11-02 首跑真事故）")
print("=" * 68)
ch_map = {
    "channel:https://example/new.yaml": (42.9, 9, {
        "url": "https://example/new.yaml", "name": "new", "src": "channel",
        "cand": {"url": "https://example/new.yaml", "repo": "owner/new",
                 "rate": 42.9, "alive": 9, "nodes": 60,
                 "evaluated_at": "2026-11-02T00:00:00Z"}}),
    "relegated:src03": (30.0, 20, {
        "url": "https://example/src03.yaml", "name": "src03",
        "src": "relegated"}),
}
cm, cname, ret = league.resolve_challenger(
    ch_map, "channel:https://example/new.yaml", {"src00"})
check("通道候选解析出块名", cm is not None and cname == "new" and ret is None,
      "cand=%s name=%s ret=%s" % (cm is not None, cname, ret))
cm, cname, ret = league.resolve_challenger(ch_map, "relegated:src03", {"src00"})
check("回归源解析出原名", cm is None and cname is None and ret == "src03",
      "name=%s ret=%s" % (cname, ret))
cm, cname, ret = league.resolve_challenger(
    ch_map, "channel:https://example/missing.yaml", set())
check("未知键拒绝写入", cm is None and cname is None and ret is None)
cm, cname, ret = league.resolve_challenger(
    ch_map, "channel:https://example/new.yaml", {"new"})
check("块名撞车自动 -2", cname == "new-2", str(cname))

print("")
print("=" * 68)
print("场景 I：通道候选三道筛 —— 样本 ≥20 / 镜像判重 / 同仓库判重")
print("=" * 68)
vtmp = tempfile.mkdtemp(prefix="league_v_")
vpath = os.path.join(vtmp, "eval_verdicts.json")
with io.open(vpath, "w", encoding="utf-8") as f:
    json.dump({"candidates": [
        {"url": "https://example/tiny.yaml", "verdict": "approved",
         "rate": 42.9, "alive": 3, "nodes": 7},
        {"url": "https://example/big.yaml", "verdict": "approved",
         "rate": 40.0, "alive": 24, "nodes": 60},
        # 已入册源的镜像写法（同一个文件，只是换了镜像域名）
        {"url": "https://ghproxy.net/https://raw.githubusercontent.com/"
                "owner/known/refs/heads/main/x.yaml",
         "verdict": "approved", "rate": 50.0, "alive": 50, "nodes": 60},
        # 同一仓库的另一个文件（同一运营方，不许重复入册）
        {"url": "https://raw.githubusercontent.com/owner/known/main/other.yaml",
         "verdict": "approved", "rate": 60.0, "alive": 50, "nodes": 60},
        # 新仓库：raw + jsdelivr 是同一文件的两条结论，只留高的那条
        {"url": "https://raw.githubusercontent.com/other/fresh/main/y.yaml",
         "verdict": "approved", "rate": 30.0, "alive": 20, "nodes": 60},
        {"url": "https://cdn.jsdelivr.net/gh/other/fresh@main/y.yaml",
         "verdict": "approved", "rate": 10.0, "alive": 6, "nodes": 60},
    ]}, f)
old_verdicts = league.VERDICTS
league.VERDICTS = vpath
try:
    got = league.load_challengers_from_channel({
        "https://raw.githubusercontent.com/owner/known/main/x.yaml"})
finally:
    league.VERDICTS = old_verdicts
check("小样本被挡", "channel:https://example/tiny.yaml" not in got, str(list(got)))
check("足样本保留", "channel:https://example/big.yaml" in got, str(list(got)))
check("镜像写法被挡",
      not any("owner/known" in k for k in got), str(list(got)))
check("同仓库另一文件被挡",
      not any("owner/known" in k for k in got), str(list(got)))
fresh = [k for k in got if "other/fresh" in k]
check("同一文件两条结论只留一条", len(fresh) == 1, str(fresh))
check("留的是高 rate 那条", fresh and "raw.githubusercontent.com" in fresh[0],
      str(fresh))
check("ghproxy.net/github.com 镜像归一",
      league.source_identity(
          "https://ghproxy.net/github.com/o/r/raw/main/x.yaml")
      == league.source_identity(
          "https://raw.githubusercontent.com/o/r/refs/heads/main/x.yaml"))
check("jsdelivr 与 raw 归一",
      league.source_identity("https://cdn.jsdelivr.net/gh/o/r@main/x.yaml")
      == league.source_identity("https://raw.githubusercontent.com/o/r/main/x.yaml"))

print("")
print("=" * 68)
print("场景 J：main() 端到端 —— 通道挑战者真正写进 sources.yaml + 24h 节流")
print("=" * 68)
jtmp = tempfile.mkdtemp(prefix="league_j_")
jsrc = os.path.join(jtmp, "sources.yaml")
jstate = os.path.join(jtmp, "league_last.json")
jverdicts = os.path.join(jtmp, "eval_verdicts.json")
jprobe = os.path.join(jtmp, "probe_latest.json")
with io.open(jsrc, "w", encoding="utf-8", newline="\n") as f:
    f.write(make_text(7))
with io.open(jverdicts, "w", encoding="utf-8") as f:
    json.dump({"candidates": [{
        "url": "https://raw.githubusercontent.com/owner/new/main/x.yaml",
        "verdict": "approved", "repo": "owner/new", "rate": 40.0,
        "alive": 24, "nodes": 60,
        "evaluated_at": "2026-11-02T00:00:00Z"}, {
        # 第二轮仍在通道里的次强候选：用来验证 24h 节流，而不是「无挑战者」
        "url": "https://raw.githubusercontent.com/owner/other/main/y.yaml",
        "verdict": "approved", "repo": "owner/other", "rate": 35.0,
        "alive": 20, "nodes": 60,
        "evaluated_at": "2026-11-02T00:00:00Z"}]}, f)
with io.open(jprobe, "w", encoding="utf-8") as f:
    json.dump({"scope": "local", "sources": {
        "src%02d" % i: {"rate": 30.0 - i * 3, "alive": 10, "settled": True}
        for i in range(7)}}, f)
_old = (league.SOURCES, league.STATE, league.VERDICTS, league.PROBE_LATEST)
league.SOURCES, league.STATE = jsrc, jstate
league.VERDICTS, league.PROBE_LATEST = jverdicts, jprobe
try:
    rc = league.main(["--skip-reprobe"])
    jd = yaml.safe_load(io.open(jsrc, encoding="utf-8"))
    john = [s for s in jd["sources"] if s.get("enabled")]
    jworst = next(s for s in jd["sources"] if s["name"] == "src06")
    jnew = next((s for s in jd["sources"] if s["name"] == "new"), None)
    check("返回 0（已换位）", rc == 0, str(rc))
    check("源数 +1（append 新块）", len(jd["sources"]) == 8,
          str(len(jd["sources"])))
    check("enabled 仍 7", len(john) == 7, str(len(john)))
    check("末位 src06 降级带日期",
          jworst.get("enabled") is False and bool(jworst.get("relegated")))
    check("通道挑战者入册且 enabled",
          jnew is not None and jnew.get("enabled") is True)
    check("state/league_last.json 落盘", os.path.exists(jstate))
    # 下一轮本机探针没测到新源：缺速率必须 hold（不能按 0 分误杀）
    with io.open(jprobe, "w", encoding="utf-8") as f:
        json.dump({"scope": "local", "sources": {
            "src%02d" % i: {"rate": 30.0 - i * 3, "alive": 10, "settled": True}
            for i in range(6)}}, f)
    before_missing = io.open(jsrc, encoding="utf-8").read()
    rc_missing = league.main(["--skip-reprobe"])
    check("在册源缺速率 -> 返回 3 且不写（不按 0 分误杀）",
          rc_missing == 3
          and io.open(jsrc, encoding="utf-8").read() == before_missing,
          str(rc_missing))
    # 补齐新源速率后再跑：应命中 24h 节流
    rates2 = {"src%02d" % i: {"rate": 30.0 - i * 3, "alive": 10,
                              "settled": True} for i in range(6)}
    rates2["new"] = {"rate": 20.0, "alive": 10, "settled": True}
    with io.open(jprobe, "w", encoding="utf-8") as f:
        json.dump({"scope": "local", "sources": rates2}, f)
    before2 = io.open(jsrc, encoding="utf-8").read()
    rc2 = league.main(["--skip-reprobe"])
    after2 = io.open(jsrc, encoding="utf-8").read()
    check("第二次 24h 节流返回 3（无换位）", rc2 == 3, str(rc2))
    check("节流后文件逐字节不变", before2 == after2)
finally:
    (league.SOURCES, league.STATE,
     league.VERDICTS, league.PROBE_LATEST) = _old

print("")
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)
