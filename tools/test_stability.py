# -*- coding: utf-8 -*-
"""验证节点级稳定性加权，以及生成物能被真 mihomo 接受。

六个场景，缺一不可 —— 前三个对应三种「把池子砍空」的失败方式：
  A 无历史      -> 完全不加权（今天就是这种情况：档案是空的）
  B 历史充足    -> 不稳节点被移出 AUTO 竞速池，但仍能从「备用」组切到
  C 单源几乎全不稳 -> 触发地板保护，该源整体不砍（宁可漏加权，不可砍空）
  D 真内核校验  -> profile.yaml 能被 mihomo -t 接受
  E 档案损坏    -> 拒绝写入 + 改名留证，不许从零重建
  F 未知=保留   -> 样本不足（<5 轮）的新节点一律留在竞速池（2026-10-19 拍板）
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import yaml                              # noqa: E402
import build                             # noqa: E402
import node_stability as ns              # noqa: E402

MIHOMO = os.environ.get("MIHOMO_BIN", r"C:\Program Files\Clash Verge\verge-mihomo.exe")
STAB = os.path.join(ROOT, "state", "node_stability.json")
BACKUP = os.path.join(ROOT, ".tools", "_stab_test_backup")

NAMES = ["anaer", "autojiedian", "automerge", "ermaozi", "nomorewalls",
         "passcro", "ruk1ng001", "shaoyouvip", "snakem982", "ssrsub",
         "yypool", "zhuhaiuk"]
RATES = {"anaer": 60.7, "autojiedian": 4.0, "automerge": 25.8, "ermaozi": 4.7,
         "nomorewalls": 14.1, "passcro": 18.2, "ruk1ng001": 16.2,
         "shaoyouvip": 15.3, "snakem982": 11.0, "ssrsub": 49.2,
         "yypool": 13.1, "zhuhaiuk": 31.4}


def make_nodes(name, n):
    # ⚠ server 必须**随源变化**：指纹只取配置去掉 name 的哈希，
    #   若各源造出相同配置就会跨源撞成一个节点，档案里只剩 40 条，
    #   低于 STABILITY_MIN_KNOWN 就绪门槛，加权会被正确地（但错误地）跳过。
    sid = sum(ord(c) for c in name) % 200 + 1
    return [{"name": "%s-node-%03d" % (name, i), "type": "ss",
             "server": "10.%d.%d.%d" % (sid, i // 256 % 256, i % 256),
             "port": 1000 + i} for i in range(n)]


def seed_stability(per_source, flaky_rate):
    """造一份稳定性档案：每个节点 flaky_rate 概率被判为不稳。"""
    nodes = {}
    k = 0
    for name, pl in per_source.items():
        for i, p in enumerate(pl):
            bad = (k % 100) < int(flaky_rate * 100)
            rec = {"s": name, "n": 20, "up": (2 if bad else 19), "ms": [200], "t": "2026-10-16"}
            nodes[ns.fingerprint(p)] = rec
            k += 1
    ns.save({"version": 1, "nodes": nodes, "updated": "2026-10-16"})


def run_profile(per_source, flaky_sources=()):
    enabled = [{"name": n, "url": "https://example/%s" % n} for n in per_source]
    return build.build_profile(enabled, {}, "pala911", "clash-source",
                               flaky_sources=flaky_sources)


ok = True
shutil.rmtree(BACKUP, ignore_errors=True)
os.makedirs(BACKUP)
HAD_STAB = os.path.exists(STAB)
if HAD_STAB:
    shutil.copy2(STAB, os.path.join(BACKUP, "node_stability.json"))
else:
    # 明确记录「本来不存在」，否则 finally 只在备份存在时处理，
    # 结果测试造的假档案就留在 state/ 里了 —— 下一轮真实探针会把它当真数据读。
    # （和之前 probe_cnci_latest.json 那个「清理测试残留反而删了真数据」是同一类错误，
    #   方向相反：这次是残留了假的。）
    open(os.path.join(BACKUP, "__absent__"), "w").close()

try:
    # ---------- A 无历史 ----------
    print("=" * 66)
    print("场景 A：稳定性档案为空（今天的状态）")
    print("=" * 66)
    if os.path.exists(STAB):
        os.remove(STAB)
    per_source = {n: make_nodes(n, 40) for n in NAMES}
    stable, flaky, note = build.split_by_stability(per_source)
    print("  %s" % note)
    same = all(len(stable[n]) == len(per_source[n]) for n in NAMES) and not flaky
    print("  %s 完全不加权，全部保留" % ("✓" if same else "✗"))
    ok = ok and same

    # ---------- B 历史充足 ----------
    print("")
    print("=" * 66)
    print("场景 B：历史充足，40% 节点被判不稳")
    print("=" * 66)
    seed_stability(per_source, 0.4)
    stable, flaky, note = build.split_by_stability(per_source)
    print("  %s" % note)
    tot_s = sum(len(v) for v in stable.values())
    tot_f = sum(len(v) for v in flaky.values())
    print("  保留 %d / 移出 %d" % (tot_s, tot_f))
    okB = flaky and tot_f > 0
    print("  %s 不稳节点被移出" % ("✓" if okB else "✗"))
    p, base, rank = run_profile(per_source, flaky_sources=sorted(flaky))
    print("  AUTO        = %s" % "、".join(rank["auto"]))
    print("  不稳定组     = %s" % "、".join(rank["不稳定"]))
    gp = {g["name"] for g in p["proxy-groups"]}
    has_unstable_group = "不稳定" in gp
    spare = next(g for g in p["proxy-groups"] if g["name"] == "备用")
    # ⚠ 备用组里引用的是**组名**「不稳定」，不是 provider 名 SRCFL-*。
    #   proxies: 只能放组名；provider 必须用 use:。写成 SRCFL-* 内核直接拒绝加载。
    wired = "不稳定" in spare["proxies"]
    print("  %s 生成了「不稳定」组" % ("✓" if has_unstable_group else "✗"))
    print("  %s 备用组引用了「不稳定」组（仍可用，只是不自动竞速）"
          % ("✓" if wired else "✗ 实际=%s" % spare["proxies"][:4]))
    auto = next(g for g in p["proxy-groups"] if g["name"] == "AUTO")
    leaked = [x for x in auto["proxies"] if x.startswith("SRCFL-")]
    print("  %s AUTO 里没有不稳定源" % ("✓" if not leaked else "✗ %s" % leaked))
    ok = ok and okB and has_unstable_group and wired and not leaked

    # ---------- C 单源几乎全不稳 ----------
    print("")
    print("=" * 66)
    print("场景 C：某一个源 90% 节点不稳（地板保护）")
    print("=" * 66)
    per2 = {n: make_nodes(n, 40) for n in NAMES}
    nodes = {}
    for n, pl in per2.items():
        for i, p in enumerate(pl):
            # zhuhaiuk 几乎全不稳（触发地板保护）；ssrsub 四成不稳（正常加权）
            up = 1 if n == "zhuhaiuk" else (8 if (n == "ssrsub" and i % 10 < 4) else 20)
            nodes[ns.fingerprint(p)] = {"s": n, "n": 20, "up": up,
                                        "ms": [200], "t": "2026-10-16"}
    ns.save({"version": 1, "nodes": nodes, "updated": "2026-10-16"})
    stable2, flaky2, note2 = build.split_by_stability(per2)
    zh_stable = len(stable2.get("zhuhaiuk", []))
    zh_total = len(per2["zhuhaiuk"])
    print("  %s" % note2)
    print("  zhuhaiuk 保留 %d / 共 %d" % (zh_stable, zh_total))
    floor = max(build.STABILITY_MIN_PER_SRC, zh_total * build.STABILITY_MIN_RATIO)
    good = "zhuhaiuk" not in flaky2 and zh_stable == zh_total
    print("  %s 地板生效：该源整体不砍（需保留 ≥%d，实际保留 %d）"
          % ("✓" if good else "✗", floor, zh_stable))
    others = [n for n in flaky2 if n != "zhuhaiuk"]
    print("  %s 其他源照常加权（移出的: %s）"
          % ("✓" if others else "✗", "、".join(others) or "无"))
    ok = ok and good and bool(others)

    # ---------- D 真内核 ----------
    print("")
    print("=" * 66)
    print("场景 D：真 mihomo 校验")
    print("=" * 66)
    seed_stability(per_source, 0.4)
    stable4, flaky4, _ = build.split_by_stability(per_source)
    p4, _, _ = run_profile(per_source, flaky_sources=sorted(flaky4))
    out = os.path.join(tempfile.gettempdir(), "profile_stab_test.yaml")
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(p4, f, allow_unicode=True, sort_keys=False, width=4096)
    vfd = r"C:\Program Files\Clash Verge\resources"
    for fn, newname in (("Country.mmdb", "geoip.metadb"), ("geoip.dat", None),
                        ("geosite.dat", None)):
        src = os.path.join(vfd, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tempfile.gettempdir(), newname or fn))
    r = subprocess.run([MIHOMO, "-t", "-f", out], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    print("  exit=%d %s" % (r.returncode, "✓ 内核接受" if r.returncode == 0 else "✗ 内核拒绝"))
    if r.returncode != 0:
        for ln in (r.stdout or b"").decode("utf-8", "replace").splitlines()[-6:]:
            print("     " + ln)
    ok = ok and r.returncode == 0
    os.remove(out)

    # ---------- F 样本不足=保留（2026-10-19 拍板：未知不淘汰） ----------
    # 旧逻辑：新节点第一轮就被写档案，1~4 轮时 verdict=False -> 移出竞速池，
    # 与本函数「没有历史的节点不该因未知被淘汰」的保险互相矛盾 —— 实际效果是
    # 一切新节点要白等 5 天才回来考。现在 build 先看 n 再谈 verdict。
    print("")
    print("=" * 66)
    print("场景 F：攒够轮数才判不稳；样本不足（<5 轮）的新节点一律保留")
    print("=" * 66)
    per3 = {n: make_nodes(n, 40) for n in NAMES}
    nodes = {}
    for n, pl in per3.items():
        for i, p in enumerate(pl):
            if i < 5:
                # 前 5 个节点样本不足（1~4 轮）且可用率 0 —— 按拍板口径必须保留
                nodes[ns.fingerprint(p)] = {"s": n, "n": max(1, i), "up": 0,
                                            "ms": [200], "t": "2026-10-16"}
            else:
                nodes[ns.fingerprint(p)] = {"s": n, "n": 20, "up": 20,
                                            "ms": [200], "t": "2026-10-16"}
    # 攒够轮数的真不稳仍要照常移出（verdict 的本职工作不受影响）
    nodes[ns.fingerprint(per3["ssrsub"][6])] = {"s": "ssrsub", "n": 20, "up": 2,
                                                "ms": [200], "t": "2026-10-16"}
    ns.save({"version": 1, "nodes": nodes, "updated": "2026-10-16"})
    stable3, flaky3, note3 = build.split_by_stability(per3)
    print("  %s" % note3)
    partial_kept = all(all(p in stable3.get(n, []) for p in per3[n][:5])
                       for n in NAMES)
    print("  %s 1~4 轮样本不足节点全部保留（即使记录可用率 0）"
          % ("✓" if partial_kept else "✗"))
    mature_dropped = flaky3.get("ssrsub") == [per3["ssrsub"][6]]
    print("  %s 攒够轮数（20 轮）的可用率不足节点照常移出（ssrsub 第 7 个）"
          % ("✓" if mature_dropped
             else "✗ 实际 flaky=%r" % {k: len(v) for k, v in flaky3.items()}))
    ok = ok and partial_kept and mature_dropped
finally:
    if os.path.exists(os.path.join(BACKUP, "__absent__")):
        if os.path.exists(STAB):
            os.remove(STAB)
        print("（已清掉测试造的 node_stability.json：原本不存在）")
    elif os.path.exists(os.path.join(BACKUP, "node_stability.json")):
        shutil.copy2(os.path.join(BACKUP, "node_stability.json"), STAB)
    shutil.rmtree(BACKUP, ignore_errors=True)

# ---------- E 档案损坏：必须「拒绝写入 + 改名留证」，不许从零重建 ----------
# 这一段只用临时文件（不碰真的 state/node_stability.json），所以放在 try/finally 之外。
print("")
print("=" * 66)
print("场景 E：稳定性档案损坏时不许静默重建")
print("=" * 66)
print("""
  merge() 原来是 exists -> json.load -> 直接当空档案用：
  档案一坏，这一轮就拿**一份从零开始的档案**覆盖掉累积了几十轮的历史
  （线上有 3261 个节点），而且 save 不是原子的，写到一半崩溃还会留下半截文件
  —— 下次 load 又把它当损坏，再来一次「从零重建」。静默、且不可逆。

  现在的契约：
    load()  坏文件改名成 *.corrupt-<时间戳> 留证，然后抛 RuntimeError
    merge() 捕获后**本轮不写**（下一轮看到文件不存在会重建一份干净的）
    build   捕获后「不加权」（构建绝不能因为一个辅助档案坏掉而失败）
""")
bad = os.path.join(tempfile.gettempdir(), "ns_corrupt_case.json")
for p in glob.glob(bad + ".corrupt-*"):
    os.remove(p)
if os.path.exists(bad):
    os.remove(bad)
with open(bad, "w", encoding="utf-8") as f:
    f.write("not json at all")
rec1 = {"fp%d" % i: {"s": "anaer", "alive": True, "ms": 100} for i in range(3)}
n1, why1 = ns.merge(rec1, scope="local", path=bad)
corrupt = glob.glob(bad + ".corrupt-*")
print("  merge(坏档案) -> 写入 %d 个 / why=%s" % (n1, why1))
print("  留证文件: %s" % ([os.path.basename(p) for p in corrupt] or "无"))
e1 = (n1 == 0)
e2 = ("损坏" in (why1 or ""))
e3 = (not os.path.exists(bad))          # 没有被「从零重建」的档案覆盖
e4 = (len(corrupt) == 1)                # 坏内容留了证
for lab, good in (("损坏时拒绝写入（不让空档案覆盖历史）", e1),
                  ("原因里明说是损坏，不是静默跳过", e2),
                  ("坏档案没被覆盖，而是改名留证了", e3 and e4)):
    print("  %s %s" % ("✓" if good else "✗", lab))
    ok = ok and good
# 下一轮：坏文件已被改名，load 看到「不存在」-> 正常重建（能自愈）
n2, why2 = ns.merge({"fp0": {"s": "anaer", "alive": True, "ms": 100}},
                    scope="local", path=bad)
print("  下一轮 merge -> 写入 %d 个（应 1）" % n2)
ok = ok and (n2 == 1)
for p in corrupt:
    os.remove(p)
if os.path.exists(bad):
    os.remove(bad)

print("")
print("=" * 66)
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)