# -*- coding: utf-8 -*-
"""验证 build_groups 按质量分桶，且不产出坏 profile。

五个场景，缺一不可：
  A 正常   -> AUTO 里应该是高质量源，ermaozi(本机2.9%) 必须被排除
  B 源太少 -> 达标源不足 3 个时**必须构建失败**（宁可不出也不给空自动组）
  C 有源被停用 -> 不能崩。原模板把 SRC-* 写死，停用任一源会让
     「模板引用了未提供的 provider」断言炸掉，整条流水线挂掉。
  D 档案损坏 -> **降级发布**（用户 2026-10-18 拍板）：不 assert 炸、AUTO 用
     上一轮 manifest 名单、warnings + ::warning:: 两处都要喊、损坏文件原样保留
  E 档案不存在且没有上一轮名单 -> 再退一步用启用源顺序，仍不许炸
     （D/E 的失败方向：手机拿到「次优但可用」的自动组，而不是 6 小时没有新订阅）

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

TOLERANCE_OK = True   # build_groups 输出的 url-test/fallback 参数形态是否合规

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
    fail_key = []
    for g in groups:
        # ⚠ 防抖断言（2026-10-29）：每个 url-test 组都必须带 tolerance，否则
        #   几十毫秒的延迟抖动就会换现役点（用户反馈「AUTO 组内使用频繁变化」）。
        #   fallback 没有该字段，不该有（塞了也是不详语义）。
        if g.get("type") == "url-test" and g.get("tolerance") != 200:
            fail_key.append(g["name"])
        elif g.get("type") == "fallback" and "tolerance" in g:
            fail_key.append("%s(不该有 tolerance)" % g["name"])
        if g["name"] in ("AUTO", "备用", "观察", "FAILOVER", "PROXY"):
            print("  %-9s %-6s %d 项" % (g["name"], g["type"],
                                        len(g.get("proxies") or g.get("use") or [])))
            for p in (g.get("proxies") or [])[:8]:
                n = p[4:] if p.startswith("SRC-") else p
                r = LOCAL.get(n)
                print("       %-16s 本机 %s" % (p, ("%.1f%%" % r) if r is not None else "-"))
            if len(g.get("proxies") or []) > 8:
                print("       ... 共 %d 项" % len(g["proxies"]))
    if fail_key:
        print("  ✗ url-test 组缺 tolerance / fallback 多了 tolerance: %s" % "、".join(fail_key))
        global TOLERANCE_OK
        TOLERANCE_OK = False
    else:
        print("  ✓ 所有 url-test 组都带 tolerance=200（防抖换点）,fallback 无该字段")
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
# 2026-11-04：manifest/report 的「备用」必须包含被 AUTO_MAX 挤出的达标源，
# 否则报告显示「备用 -」，和 profile 里真实的备用组不一致。
qualified = sorted([n for n in NAMES if LOCAL[n] >= build.GOOD_RATE],
                   key=lambda n: (-LOCAL[n], n))
expected_spare = [n for n in qualified if n not in auto]
actual_spare = rank.get("备用") or []
spare_missing = [n for n in expected_spare if n not in actual_spare]
spare_extra = [n for n in actual_spare if n not in expected_spare]
spare_overlap = sorted(set(auto) & set(actual_spare))
spare_group = [x[4:] for x in next(g for g in gs if g["name"] == "备用")["proxies"]
               if x.startswith("SRC-")]
group_missing = [n for n in actual_spare if n not in spare_group]
print("  ranking['备用'] = %s" % ("、".join(actual_spare) or "-"))
if spare_missing or spare_extra or spare_overlap or group_missing:
    print("  ✗ 备用口径不一致：缺 %s / 多 %s / 与 AUTO 重叠 %s / 未进备用组 %s"
          % (spare_missing or "无", spare_extra or "无", spare_overlap or "无",
             group_missing or "无"))
    ok = False
else:
    print("  ✓ 被 AUTO_MAX 挤出的达标源都在备用组（%d 个），且不与 AUTO 重叠"
          % len(actual_spare))
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
static = {x.get("name") for x in (p.get("proxies") or [])
          if isinstance(x, dict) and x.get("name")}
all_members = gp | static
print("  %s 每组引用的成员都存在" % ("✓" if all(
    x in all_members for g in p["proxy-groups"]
    for x in (g.get("proxies") or [])) else "✗"))
proxy_grp = next((g for g in p["proxy-groups"] if g["name"] == "PROXY"), {})
home_ok = ("家里路由" in static and
           "家里路由" in (proxy_grp.get("proxies") or []))
print("  %s PROXY 组含静态代理「家里路由」" % ("✓" if home_ok else "✗"))
ai_ok = all(
    "PROXY" in (next(g for g in p["proxy-groups"] if g["name"] == svc)
                .get("proxies") or [])
    for svc in ("Claude", "Gemini"))
print("  %s Claude/Gemini 默认跟随 PROXY" % ("✓" if ai_ok else "✗"))
ok = ok and home_ok and ai_ok
# provider 节点池必须走 gh-proxy 中转（2026-10-31 用户拍板替代 jsdelivr：
# gh-proxy 零缓存、CI 发完 ≤1h 到手机；jsdelivr@gh-pages 缓存 ~12h 太慢）
pv = p["proxy-providers"]
pv_ok = all(pv[n]["url"].startswith(
    "https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/nodes/")
    for n in pv) and not any(
    pv[n]["url"].startswith("https://raw.githubusercontent") for n in pv)
print("  %s 全部 provider URL 走 gh-proxy 中转@gh-pages（户数 %d）"
      % ("✓" if pv_ok else "✗", len(pv)))
ok = ok and pv_ok

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

# ---------- D 健康档案损坏 -> 降级发布（用户 2026-10-18 拍板）----------
# 口径：订阅照发（手机不能因为一个辅助档案坏掉就 6 小时不更新），
#       但降级必须喊出来（warnings + ::warning::），AUTO 用上一轮 manifest 的名单。
import contextlib                 # noqa: E402

print("")
print("=" * 68)
print("场景 D（健康档案损坏 -> 必须降级发布，不许 assert 炸）")
print("=" * 68)
_tmpd = tempfile.mkdtemp(prefix="bg_degrade_")
os.makedirs(os.path.join(_tmpd, "dist"), exist_ok=True)
with io.open(os.path.join(_tmpd, "dist", "manifest.json"), "w", encoding="utf-8") as f:
    json.dump({"ranking": {"auto": ["anaer", "ssrsub", "snakem982"]}}, f, ensure_ascii=False)
_bad = os.path.join(_tmpd, "broken_health.json")
with io.open(_bad, "w", encoding="utf-8") as f:
    f.write("{ 半截 JSON —— 磁盘满/写入中断的典型样貌")   # 不是合法 JSON
_old_root, _old_health, _old_env = build.ROOT, build.HEALTH, os.environ.get("GITHUB_ACTIONS")
build.HEALTH, build.ROOT = _bad, _tmpd
os.environ["GITHUB_ACTIONS"] = "true"          # 断言 CI 注解路径也真的打了
_buf = io.StringIO()
try:
    with contextlib.redirect_stdout(_buf):
        p3, _, rank3 = call(NAMES)
    out3 = _buf.getvalue()
    auto3 = [x[4:] for x in next(g for g in p3["proxy-groups"]
                                 if g["name"] == "AUTO")["proxies"]]
    print("  降级后 AUTO = %s" % "、".join(auto3))
    print("  ranking['degraded'] = %s" % (rank3.get("degraded") or "（空 —— 不该）"))
    d_ok = (len(auto3) >= build.AUTO_MIN                       # 有可用的自动组
            and auto3 == ["anaer", "ssrsub", "snakem982"]      # 用的是上一轮名单
            and not (set(rank3.get("auto") or []) &
                     set(rank3.get("备用") or []))             # 降级名单与备用不重叠
            and rank3.get("degraded")                          # 说明会进 warnings
            and "⚠ 降级" in out3                               # 本地日志
            and "::warning title=源健康档案降级::" in out3      # CI 注解
            and not os.path.exists(_bad + ".bak")              # 绝不改名/重建损坏档案
            and os.path.exists(_bad))                          # 原文件原样留着
    print("  %s 没炸、AUTO 用上一轮名单、两处告警都在、损坏文件原样保留" % ("✓" if d_ok else "✗"))
    if not d_ok:
        print("       AUTO=%s degraded=%r 有⚠=%s 有注解=%s"
              % (auto3, bool(rank3.get("degraded")), "⚠ 降级" in out3,
                 "::warning" in out3))
    ok = ok and d_ok
except AssertionError as e:
    print("  ✗ 降级路径仍然炸了：%s" % e)
    ok = False
finally:
    build.ROOT, build.HEALTH = _old_root, _old_health
    if _old_env is None:
        os.environ.pop("GITHUB_ACTIONS", None)
    else:
        os.environ["GITHUB_ACTIONS"] = _old_env

# ---------- E 连上一轮名单都没有 -> 再退一步，仍不许炸 ----------
print("")
print("=" * 68)
print("场景 E（档案不存在 + 没有上一轮 manifest -> 退到启用源顺序）")
print("=" * 68)
_empty = tempfile.mkdtemp(prefix="bg_degrade2_")      # 没有 dist/manifest.json
build.HEALTH, build.ROOT = os.path.join(_empty, "nope.json"), _empty
_buf2 = io.StringIO()
try:
    with contextlib.redirect_stdout(_buf2):
        p4, _, rank4 = call(NAMES)
    out4 = _buf2.getvalue()
    auto4 = [x[4:] for x in next(g for g in p4["proxy-groups"]
                                 if g["name"] == "AUTO")["proxies"]]
    e_ok = (auto4 == NAMES[:build.AUTO_MAX]
            and rank4.get("degraded") and "⚠ 降级" in out4)
    print("  降级后 AUTO = %s（前 %d 个启用源）" % ("、".join(auto4), build.AUTO_MAX))
    print("  %s 仍构建成功、AUTO 非空、说明带出" % ("✓" if e_ok else "✗"))
    ok = ok and e_ok
except AssertionError as e:
    print("  ✗ 连兜底都炸了：%s" % e)
    ok = False
finally:
    build.ROOT, build.HEALTH = _old_root, _old_health

# ---------- F 跨源内容指纹去重 ----------
print("")
print("=" * 68)
print("场景 F（跨源内容指纹去重：高质量源优先，不误删同端口不同凭据）")
print("=" * 68)


def check_f(name, cond):
    global ok
    print("  %s %s" % ("✓" if cond else "✗", name))
    if not cond:
        ok = False


n1 = {"name": "n1", "type": "ss", "server": "1.2.3.4", "port": 8388,
      "password": "p1"}
n1_copy = dict(n1, name="n1-copy")              # 只差 name：必须去重
n2 = dict(n1, name="n2", password="p2")         # 同端口不同凭据：必须保留
n3 = dict(n1, name="n3", server="5.6.7.8")      # 不同服务器：必须保留
n4 = dict(n1, name="n4", sni="other.example")   # 同凭据不同传输参数：必须保留
per = {"low": [n1_copy, n3], "high": [n1], "other": [n2]}

deduped, dup = build.dedupe_cross_source(per, ["high", "low", "other"])
check_f("高质量源保留共享节点（high 保留 n1）",
        [p["name"] for p in deduped["high"]] == ["n1"])
check_f("低质量源的只差 name 副本被剔除（low 只剩 n3）",
        [p["name"] for p in deduped["low"]] == ["n3"])
check_f("同端口不同凭据不被误删（other 保留 n2）",
        [p["name"] for p in deduped["other"]] == ["n2"])
check_f("dup_counts 按源记账（low=1）",
        dup.get("low") == 1 and dup.get("high") == 0 and dup.get("other") == 0)
check_f("返回 dict 保持原键顺序（provider/报告行顺序不变）",
        list(deduped) == list(per))

deduped2, dup2 = build.dedupe_cross_source(per, ["low", "high", "other"])
check_f("优先级反转后改由 low 保留（high 清空）",
        [p["name"] for p in deduped2["low"]] == ["n1-copy", "n3"]
        and deduped2["high"] == [] and dup2.get("high") == 1)

deduped3, _ = build.dedupe_cross_source(per)
check_f("不传 priority 时按 per_source 原顺序保留（low 先）",
        [p["name"] for p in deduped3["low"]] == ["n1-copy", "n3"]
        and deduped3["high"] == [])

per_dup = {"a": [n1], "b": [n1_copy]}
deduped4, dup4 = build.dedupe_cross_source(per_dup, ["a", "b"])
check_f("100% 重复源会被清空（调用方据此告警）",
        deduped4["a"] == [n1] and deduped4["b"] == [] and dup4.get("b") == 1)

per_meta = {"a": [n1], "b": [n4]}
deduped5, dup5 = build.dedupe_cross_source(per_meta, ["a", "b"])
check_f("同凭据但传输参数不同（sni）不被误删",
        len(deduped5["b"]) == 1 and dup5.get("b") == 0)

print("")
print("=" * 68)
print("结果：%s" % ("全部通过" if (ok and TOLERANCE_OK) else "有失败项"))
sys.exit(0 if (ok and TOLERANCE_OK) else 1)