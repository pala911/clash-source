# -*- coding: utf-8 -*-
"""验证 build_groups 按质量分桶，且不产出坏 profile。

三个场景，缺一不可：
  A 正常   -> AUTO 里应该是高质量源，ermaozi(本机2.9%) 必须被排除
  B 源太少 -> 达标源不足 3 个时**必须构建失败**（宁可不出也不给空自动组）
  C 有源被停用 -> 不能崩。原模板把 SRC-* 写死，停用任一源会让
     「模板引用了未提供的 provider」断言炸掉，整条流水线挂掉。

⚠ 三个场景都跑在**自己种的合成健康档案**上（build.HEALTH 指到临时文件）。
   原来直接读线上档案，于是 2026-10-16 线上数据一变（autojiedian 修掉 sni 后
   本机测出 31.62%、均值 4.0% -> 17.8%），「场景 B 只剩 2 个达标源」的前提
   就碎了 —— 测试挂掉，但产品其实是在对的方向上变化。
   **测试的隐含前提依赖会漂移的线上状态，本身就是坏味道。**
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import io                       # noqa: E402
import json                      # noqa: E402
import tempfile                  # noqa: E402

import yaml                      # noqa: E402
import build                     # noqa: E402

NAMES = ["anaer", "autojiedian", "automerge", "ermaozi", "nomorewalls",
         "passcro", "ruk1ng001", "shaoyouvip", "snakem982", "ssrsub",
         "yypool", "zhuhaiuk"]

# 各源的本机实测通过率（2026-10-15，来自 state/probe_latest.json）
LOCAL = {"anaer": 78.57, "autojiedian": 4.0, "automerge": 29.3, "ermaozi": 2.9,
         "nomorewalls": 13.2, "passcro": 25.9, "ruk1ng001": 10.3,
         "shaoyouvip": 24.4, "snakem982": 15.4, "ssrsub": 63.5,
         "yypool": 13.0, "zhuhaiuk": 46.7}


# 把合成档案种好：build.rank_sources() 读的是 build.HEALTH 指向的文件，
# 不指过去的话它读的就是**线上真档案**（会随每天的探针结果漂移）。
_HEALTH_TMP = os.path.join(tempfile.gettempdir(), "bg_test_health.json")


def _seed(rates):
    doc = {"v": 1, "updated": "test-fixture", "sources": {}}
    for n, r in rates.items():
        doc["sources"][n] = {
            # cnci_runs 给 7：让分级处于「已生效」状态，与线上一致
            "tier_rates": {"local": r, "cnci": 0.0, "cnci_runs": 7},
            "tier": "T1" if r >= 8.0 else "T4",
            "tier_why": "test fixture",
            "runs": [], "state": "active",
            "bad_streak": 0, "good_streak": 0, "bad_since": None}
    with io.open(_HEALTH_TMP, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    build.HEALTH = _HEALTH_TMP


_seed(LOCAL)


def show(t, groups, names):
    print("")
    print("=" * 68)
    print("场景 %s" % t)
    print("=" * 68)
    for g in groups:
        if g["name"] in ("AUTO", "备用", "观察", "FAILOVER", "PROXY"):
            print("  %-9s %-6s %d 项" % (g["name"], g["type"],
                                        len(g.get("proxies") or g.get("use") or [])))
            for p in (g.get("proxies") or [])[:8]:
                n = p[4:] if p.startswith("SRC-") else p
                r = LOCAL.get(n)
                print("       %-16s 本机 %s" % (p, ("%.1f%%" % r) if r is not None else "-"))
            if len(g.get("proxies") or []) > 8:
                print("       ... 共 %d 项" % len(g["proxies"]))
    return groups


def call(names):
    enabled = [{"name": n, "url": "https://example/%s" % n} for n in names]
    return build.build_profile(enabled, {}, "pala911", "clash-source")


# ---------- A 正常 ----------
p, base, rank = call(NAMES)
gs = show("A（全部 12 源启用）", p["proxy-groups"], NAMES)
auto = [x[4:] for x in next(g for g in gs if g["name"] == "AUTO")["proxies"]]
print("")
print("  AUTO 实际入选: %s" % "、".join(auto))
ok = True
if "ermaozi" in auto:
    print("  ✗ ermaozi 本机 2.9% 却进了 AUTO —— 质量分桶没起作用")
    ok = False
else:
    print("  ✓ ermaozi（本机 2.9%，原模板里却手写在 AUTO）已被排除")
for must in ("anaer", "ssrsub", "zhuhaiuk"):
    if must not in auto:
        print("  ✗ %s 本机 %.1f%% 是好源却没进 AUTO" % (must, LOCAL[must]))
        ok = False
if len(auto) > build.AUTO_MAX:
    print("  ✗ AUTO 有 %d 项，超过上限 %d" % (len(auto), build.AUTO_MAX))
    ok = False
gp = {g["name"] for g in p["proxy-groups"]}
print("  %s 每组引用的成员都存在" % ("✓" if all(
    x in gp for g in p["proxy-groups"] for x in (g.get("proxies") or [])) else "✗"))

# ---------- B 达标源不足 ----------
print("")
print("=" * 68)
print("场景 B（只剩 2 个达标源）")
print("=" * 68)
weak = [n for n in NAMES if LOCAL[n] >= 8.0][:2] + ["ermaozi", "autojiedian"]
try:
    call(weak)
    print("  ✗ 构建成功了 —— 达标源不足时**必须**失败，否则 AUTO 是残缺的")
    ok = False
except AssertionError as e:
    print("  ✓ 按预期构建失败：")
    for ln in str(e).splitlines():
        print("       " + ln)

# ---------- C 停用一个源 ----------
print("")
print("=" * 68)
print("场景 C（停用 shaoyouvip 和 autojiedian）")
print("=" * 68)
left = [n for n in NAMES if n not in ("shaoyouvip", "autojiedian")]
try:
    p2, _, _ = call(left)
    gnames = {g["name"] for g in p2["proxy-groups"]}
    missing = [n for n in left if "SRC-%s" % n not in gnames]
    print("  ✓ 构建成功（不再因模板写死而炸）")
    print("  %s 每个启用源都有 SRC- 组（缺: %s）" % ("✓" if not missing else "✗", missing or "无"))
    leaked = [g for g in p2["proxy-groups"]
              for x in (g.get("proxies") or []) if x in ("SRC-shaoyouvip", "SRC-autojiedian")]
    print("  %s 已停用的源没有残留在任何组里" % ("✓" if not leaked else "✗ %s" % leaked))
    ok = ok and not missing and not leaked
except AssertionError as e:
    print("  ✗ 构建失败：%s" % e)
    ok = False

print("")
print("=" * 68)
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)