# -*- coding: utf-8 -*-
"""验证 health.py 的双视角分级。

两个场景都必须验证，缺一不可：

  场景 A（真实当前状态）：云效只有 1 轮数据
      -> 分级应全部显示「数据不足」，且**不回收任何源**。
         这是安全默认值：阈值还没校准，不该让未校准的数据驱动决策。

  场景 B（模拟攒够 7 轮）：灌 7 轮合成数据
      -> 四格应正确分化。用的是 2026-10-15 两次实测的真实数值。

⚠ 全程备份并还原 state/ 和 src/sources.yaml，不留任何副作用。
"""
import json
import os
import shutil
import subprocess
import sys
import time

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# 2026-10-15 19:14 云效实测（抽样 30/源）与本机全量实测
CNCI_REAL = {"anaer": (27, 90.0), "autojiedian": (5, 16.7), "automerge": (16, 53.3),
             "ermaozi": (4, 13.3), "nomorewalls": (14, 46.7), "passcro": (10, 33.3),
             "ruk1ng001": (11, 36.7), "shaoyouvip": (24, 80.0), "snakem982": (0, 0.0),
             "ssrsub": (20, 66.7), "yypool": (5, 16.7), "zhuhaiuk": (7, 23.3),
             # ↓ 合成源，用来覆盖真实数据里**根本不存在**的第 4 格。
             #   12 个真实源没有一个是「两边都差」（要么本机行，要么云效行），
             #   所以 health.py 少实现的那个分支从来没被跑到过 —— 测试通过
             #   不代表逻辑对，只代表**没触发**。
             "demo_t4": (0, 0.0)}
LOCAL = {"anaer": 78.6, "autojiedian": 4.0, "automerge": 29.3, "ermaozi": 2.9,
         "nomorewalls": 13.2, "passcro": 25.9, "ruk1ng001": 10.3, "shaoyouvip": 24.4,
         "snakem982": 15.4, "ssrsub": 63.5, "yypool": 13.0, "zhuhaiuk": 46.7,
         "demo_t4": 3.0}

CNCI_PATH = os.path.join(ROOT, "state", "probe_cnci_latest.json")
PROBE_PATH = os.path.join(ROOT, "state", "probe_latest.json")
SRC_YAML = os.path.join(ROOT, "src", "sources.yaml")
ARCHIVE_YAML = os.path.join(ROOT, "archive", "sources.yaml")
HEALTH_PATH = os.path.join(ROOT, "state", "source_health.json")

BK = os.path.join(ROOT, ".tools", "_tier_test_backup")

# ⚠ 备份文件名必须**显式指定**，不能用 os.path.basename：
#   src/sources.yaml 和 archive/sources.yaml 的 basename 都是 sources.yaml，
#   撞在一起的结果是「用 archive 的内容盖掉了 src/sources.yaml」——
#   实测跑一次就把 12 源的清单换成了历史库，而 git status 上只显示「已修改」，
#   看起来像正常改动。（2026-10-16 踩到，靠 `git checkout -- src/sources.yaml` 救回。）
BK_FILES = {"src_sources.yaml": SRC_YAML,
            "archive_sources.yaml": ARCHIVE_YAML,
            "state_source_health.json": HEALTH_PATH,
            "state_probe_latest.json": PROBE_PATH,
            "state_probe_cnci_latest.json": CNCI_PATH}


def backup():
    """备份全部会被 health.py 改写的文件（备份前不存在就删掉，见 restore）。"""
    shutil.rmtree(BK, ignore_errors=True)
    os.makedirs(BK)
    for alias, path in BK_FILES.items():
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(BK, alias))


def restore():
    for alias, path in BK_FILES.items():
        src = os.path.join(BK, alias)
        if os.path.exists(src):
            shutil.copy2(src, path)
        elif os.path.exists(path):
            # 备份时**不存在**、跑测试时被造出来的（archive/sources.yaml 就属这种，
            # 它不在 git 里）—— 必须删掉，否则测试凭空给仓库留下一个历史库。
            os.remove(path)
    shutil.rmtree(BK, ignore_errors=True)


def _s(v):
    if v is None:
        return ""
    return v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)


def run_health():
    """跑一轮 health.py，返回 (退出码, stdout+stderr)。

    ⚠ 退出码必须一起返回：场景 D 守的正是「回收分支一进来就 NameError、exit=1」，
       只看输出文本会漏掉「进程整体崩掉」这一类失败。
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY, os.path.join(ROOT, "src", "health.py")],
                       capture_output=True, cwd=ROOT, env=env)
    return p.returncode, _s(p.stdout) + _s(p.stderr)


def cnci_doc(runs, tag):
    """构造一份 scope=cnci 的探针结果文档（runs 份，数值带微小抖动）。"""
    srcs = {}
    for i, (name, (alive, rate)) in enumerate(sorted(CNCI_REAL.items())):
        # 只在合成的第 2..n 轮加 ±2pp 抖动，模拟真实轮间噪声（实测 avg 5.5pp）
        jit = 0 if runs == 1 else ((i + runs) % 5 - 2) * 1.0
        r = max(0.0, rate + jit)
        srcs[name] = {"nodes": 30, "tested": 30, "alive": alive, "rate": round(r, 1),
                      "best_ms": 1000, "settled": True, "incomplete": False,
                      "is_sampled": True, "dom_pct": 10.0}
    return {"scope": "cnci", "probed_at": "2026-10-%02dT04:23:00Z#%s" % (10 + runs, tag),
            "hc_timeout_ms": 8000, "sampled": True, "sources": srcs}


def seed_local_probe(extra=None):
    """把本机全量结果写成 scope=local 的探针文档，供 health.py 读取。

    extra: {源名: 通过率} —— 额外塞进本轮的**合成源**（场景 D 回收要用）。
           合成源不在 src/sources.yaml 的 LOCAL 常量里，必须显式给。
    """
    srcs = {}
    rates = dict(LOCAL)
    rates.update(extra or {})
    for name, rate in sorted(rates.items()):
        n = 300
        srcs[name] = {"nodes": n, "tested": n, "alive": int(round(rate * n / 100.0)),
                      "rate": rate, "best_ms": 800, "settled": True,
                      "incomplete": False, "is_sampled": False}
    doc = {"scope": "local", "probed_at": "2026-10-15T12:07:00Z", "hc_timeout_ms": 8000,
           "sources": srcs}
    with open(PROBE_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def seed_health_empty(pre=None):
    """把健康档案重置成**零历史**（可选注入若干源的初始状态）。

    pre: {源名: {bad_streak, bad_since, state}} —— 场景 C 用它造「已经攒了几轮」的档案。

    ⚠ 为什么必须先重置：
      没有这一步，这个测试在结构上就是错的：
      · 测试用**硬编码常量** LOCAL[name] 算期望
      · 但 health.py 的 recent_mean() 是对 runs 里**所有**本机轮次求均值
      · 而 source_health.json 里躺着**真实累积的历史**（实测 snakem982
        有 4 轮，均值 5.5%，而测试期望的是注入那轮的 15.4%）

    拿「注入的单轮」去比「多轮均值」，两个数永远对不上。
    之前这个测试能过，只是因为数值恰好接近 —— 不是因为它对。

    这就是「验证环节自身的失败伪装成通过」：断言在跑，但它断言的是
    一个代码根本不会看到的数。
    """
    srcs = {}
    for name in LOCAL:
        srcs[name] = {"name": name, "state": "active", "bad_streak": 0,
                      "good_streak": 0, "bad_since": None, "runs": []}
    for name, e in (pre or {}).items():
        rec = srcs.setdefault(name, {"name": name, "state": "active",
                                     "good_streak": 0, "runs": []})
        rec.update({"bad_streak": e.get("bad_streak", 0),
                    "bad_since": e.get("bad_since"),
                    "state": e.get("state", "active")})
    doc = {"v": 1, "updated": "2026-01-01T00:00:00Z", "sources": srcs}
    with open(HEALTH_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def tier_of(name):
    h = json.load(open(HEALTH_PATH, encoding="utf-8"))
    return (h["sources"].get(name, {}) or {}).get("tier", "<无>")


FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                        ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


print("=" * 72)
print("场景 A：云效只有 1 轮（= 今天的真实状态）")
print("=" * 72)
backup()
try:
    seed_health_empty()
    seed_local_probe()
    with open(CNCI_PATH, "w", encoding="utf-8") as f:
        json.dump(cnci_doc(1, "A"), f, ensure_ascii=False, indent=2)
    rc, out = run_health()
    for ln in out.splitlines():
        if "分级" in ln or "暂不回收" in ln or "无云效" in ln:
            print("  " + ln.strip())
    print()
    hs = json.load(open(HEALTH_PATH, encoding="utf-8"))
    bad = [n for n in LOCAL if hs["sources"][n].get("tier") != "?"]
    print("  分级非「?」的源: %s" % (bad or "无（正确 —— 样本不足不该下结论）"))
    print("  cnci 轮次计数: %s" % hs["sources"]["anaer"].get("tier_rates", {}).get("cnci_runs"))
    check(not bad, "云效不足 7 轮时，没有任何源被判成 T1~T4", "；".join(bad))
finally:
    restore()

print()
print("=" * 72)
print("场景 B：模拟攒够 7 轮云效数据（验证四格是否正确分化）")
print("=" * 72)
backup()
try:
    seed_health_empty()
    seed_local_probe()
    for r in range(1, 8):
        with open(CNCI_PATH, "w", encoding="utf-8") as f:
            json.dump(cnci_doc(r, "B%d" % r), f, ensure_ascii=False, indent=2)
        run_health()
    rc, out = run_health()
    for ln in out.splitlines():
        if "分级" in ln or "===" in ln or "云效轮次" in ln:
            print("  " + ln.strip())

    print()
    print("  四格分类结果（对照两视角实测值）：")
    print("  %-14s %8s %8s  %s" % ("源", "本机%", "云效%", "分级"))
    print("  " + "-" * 46)
    exp = {}
    for name in sorted(LOCAL):
        l, c = LOCAL[name], CNCI_REAL[name][1]
        if l >= 8.0 and c >= 8.0:
            e = "T1"
        elif l >= 8.0:
            e = "T2"
        elif c >= 8.0:
            e = "T3"
        else:
            e = "T4"
        exp[name] = e
        got = tier_of(name)
        print("  %-14s %7.1f%% %7.1f%%  %-2s %s"
              % (name, l, c, got, "" if got == e else "<-- 预期 %s" % e))
    wrong = [n for n in exp if tier_of(n) != exp[n]]

    # ⚠ 光「全部与预期一致」不够 —— 如果测试数据本身没覆盖到某一格，
    #   那一格的代码就**从来没被执行过**，全绿也说明不了它对。
    #   上一版就是这样：12 个真实源里没有一个是「两边都差」，
    #   于是 health.py 少写的那个 T4 分支从未被跑到，测试照样通过。
    covered = sorted(set(exp.values()))
    missing = [t for t in ("T1", "T2", "T3", "T4") if t not in covered]
    print()
    print("  分级覆盖: %s" % "、".join(covered))
    if missing:
        print("  ✗ 四格未全覆盖，缺 %s —— 未覆盖的格子等于不存在" % missing)
        wrong = wrong + ["缺格:" + ",".join(missing)]
    else:
        print("  ✓ 四格全覆盖（每一格都有源真的踩到过）")

    print()
    print("  与预期不一致: %s" % (wrong or "无 —— 四格分类正确"))
    check(not wrong, "四格分类与实测值一致且全覆盖", "；".join(wrong))
    print()
    print("  关键校验：")
    print("    snakem982 本机 15.4%% / 云效 0.0%%  -> %s（位置敏感，绝不该自动回收）"
          % tier_of("snakem982"))
    print("    ermaozi    本机  2.9%% / 云效 13.3%% -> %s（机房友好，不该进主池）"
          % tier_of("ermaozi"))
finally:
    restore()

print()
print("已还原 state/ 与 src/sources.yaml，A/B 两个场景无副作用。")

print()
print("=" * 72)
print("场景 C：判死要「轮数够」**且**「跨度够」（cron 提速不该让判死提速）")
print("=" * 72)
print("""
  背景：L1 的 cron 从「每周一」提到「每 6 小时」后，只数轮数的话
        「连续 3 轮 0 活」= 18 小时就判死（原来是 3 周）。
        而回收要 2 轮本机 + 7 轮云效，误杀的代价是「好几天才可能收回来」。
        所以判死改成：轮数 >= 3 **且** 首末轮横跨 >= 48 小时。

  C1 3 轮 0 活、每轮隔 1 小时（跨度 2h）    -> 不判死（轮数够，跨度不够）
  C2 3 轮 0 活、每轮隔 25 小时（跨度 50h）  -> 判死   （轮数够，跨度也够）
  C3 老档案（没有 bad_since）且 bad_streak 已经是 3 -> 不判死（跨度从头起算）
""")

# 用**合成源**而不是真实源：这个场景会真的把源降级，
# 万一测试中途挂了，被禁用的也不能是线上真源。
FAKE = "demo_deadly"
SRC_BASE = os.path.join(ROOT, ".tools", "_tier_test_srcbase.yaml")


def ci_doc(ts, dead):
    """一份 scope=ci 的探针文档。dead 里的源 alive=0，其余 alive=10。"""
    srcs = {}
    for name in list(LOCAL) + [FAKE]:
        a = 0 if name in dead else 10
        srcs[name] = {"nodes": 100, "tested": 100, "alive": a, "rate": float(a),
                      "best_ms": 800, "settled": True, "incomplete": False,
                      "is_sampled": False}
    return {"scope": "ci", "probed_at": ts, "hc_timeout_ms": 8000,
            "sampled": False, "sources": srcs}


def enabled_of(name):
    cfg = yaml.safe_load(open(SRC_YAML, encoding="utf-8")) or {}
    for s in (cfg.get("sources") or []):
        if s.get("name") == name:
            return bool(s.get("enabled", True))
    return None


def add_fake_source():
    """把合成源**插进 `sources:` 段末尾**（保留原有注释，不做 yaml 往返重写）。

    ⚠ 不能"追加到文件末尾"：文件末尾是另一个顶层键 `excluded:`，
      追加进去会变成**候选排除清单**里的条目 —— 实测报
      `mapping values are not allowed here`（sources.yaml 第 99 行），
      而且 sources: 下面的条目是缩进 2 格的，不缩进的 `- name:` 也非法。
    """
    txt = open(SRC_YAML, encoding="utf-8").read()
    if FAKE in txt:
        return
    anchor = "\n# 已评估但未纳入（改 enabled: true 即恢复）\nexcluded:"
    if anchor not in txt:
        raise SystemExit("[tier-test] sources.yaml 结构变了：找不到 excluded 锚点，"
                         "无法安全插入合成源（宁可不测，也不能改坏源清单）")
    entry = ("\n  - name: %s\n"
             "    url: https://example/%s\n"
             "    note: 合成源，只用于 test_health_tiering 场景 C\n"
             "    enabled: true\n"
             "    exclude_filter: ''\n" % (FAKE, FAKE))
    txt = txt.replace(anchor, entry + anchor, 1)
    with open(SRC_YAML, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    shutil.copy2(SRC_YAML, SRC_BASE)


def run_ci_rounds(ts_list):
    """按给定时间戳逐轮跑 health.py，返回最后一轮的输出（用于抓提示语）。"""
    out = ""
    for t in ts_list:
        with open(PROBE_PATH, "w", encoding="utf-8") as f:
            json.dump(ci_doc(t, {FAKE}), f, ensure_ascii=False, indent=2)
        rc, out = run_health()
    return out


def archive_names():
    """历史库里的源名（archive/sources.yaml 不存在时返回空）。"""
    if not os.path.exists(ARCHIVE_YAML):
        return []
    arch = yaml.safe_load(open(ARCHIVE_YAML, encoding="utf-8")) or {}
    return [s.get("name") for s in (arch.get("sources") or [])]


def seeded_runs(scope, n, rate, alive, day0):
    """造 n 条**历史轮次**记录（字段与 health.py 写回的一模一样）。

    ⚠ hc_timeout_ms 必须和探针文档里的 8000 一致：health.py 见到同一口径的
      hc_timeout 变了就**清零 streak** —— 口径不一致这个用例永远攒不够回收条件，
      而症状会是「回收分支没进去」，看起来像另一个 bug。
    """
    return [{"ts": "2026-%02d-%02dT%02d:00:00Z"
                   % (9 if scope == "local" else 10, day0 + i,
                      12 if scope == "local" else 4),
             "scope": scope, "sampled": scope == "cnci", "hc_timeout_ms": 8000,
             "nodes": 300 if scope == "local" else 30,
             "tested": 300 if scope == "local" else 30,
             "alive": alive, "rate": rate, "best_ms": 500,
             "settled": True, "incomplete": False}
            for i in range(n)]


backup()
add_fake_source()
N_COMMENTS = sum(1 for ln in open(SRC_YAML, encoding="utf-8")
                 if ln.lstrip().startswith("#"))
try:
    # ---- C1：轮数够、跨度只有 2 小时 ----
    print("C1  3 轮 0 活，每轮隔 1 小时（跨度 2h）")
    shutil.copy2(SRC_BASE, SRC_YAML)
    seed_health_empty({FAKE: {"bad_streak": 0, "bad_since": None}})
    out = run_ci_rounds(["2026-10-10T00:00:00Z", "2026-10-10T01:00:00Z",
                         "2026-10-10T02:00:00Z"])
    h = json.load(open(HEALTH_PATH, encoding="utf-8"))["sources"][FAKE]
    check(h["bad_streak"] == 3, "bad_streak 攒到 3", "实际 %s" % h["bad_streak"])
    check(enabled_of(FAKE) is True, "源**没有**被判死（enabled 仍为 true）")
    check("判死不提速" in out, "日志明说了是「跨度不够」挡下的",
          "；".join(ln.strip()[:70] for ln in out.splitlines() if "判死" in ln)[:150])
    print()

    # ---- C2：同样 3 轮，但跨度 50 小时 ----
    print("C2  3 轮 0 活，每轮隔 25 小时（跨度 50h）")
    shutil.copy2(SRC_BASE, SRC_YAML)
    seed_health_empty({FAKE: {"bad_streak": 0, "bad_since": None}})
    run_ci_rounds(["2026-10-10T00:00:00Z", "2026-10-11T01:00:00Z",
                   "2026-10-12T02:00:00Z"])
    h = json.load(open(HEALTH_PATH, encoding="utf-8"))["sources"][FAKE]
    check(h["state"] == "quarantined", "状态变成 quarantined", "实际 %s" % h["state"])
    check(enabled_of(FAKE) is False, "源被判死（enabled: false）")
    arch = yaml.safe_load(open(ARCHIVE_YAML, encoding="utf-8")) or {}
    names = [s.get("name") for s in (arch.get("sources") or [])]
    check(FAKE in names, "已移入历史库 archive/sources.yaml", "；".join(names))
    # 真跑一遍 write_src_cfg（上面那次降级已经触发它）之后，注释必须一行不少。
    # 这是端到端的那一侧：单测 tools/test_src_cfg_write.py 测的是函数本身，
    # 这里测的是「health.py 真跑起来、真去改开关」时注释还在不在。
    now_comments = sum(1 for ln in open(SRC_YAML, encoding="utf-8")
                       if ln.lstrip().startswith("#"))
    check(now_comments == N_COMMENTS, "write_src_cfg 没有抹掉注释",
          "%d -> %d 行" % (N_COMMENTS, now_comments))
    print()

    # ---- C3：老档案（没有 bad_since）不该立刻判死 ----
    print("C3  老档案没有 bad_since，bad_streak 已经是 3")
    shutil.copy2(SRC_BASE, SRC_YAML)
    seed_health_empty({FAKE: {"bad_streak": 3, "bad_since": None}})
    out = run_ci_rounds(["2026-10-10T00:00:00Z"])
    check(enabled_of(FAKE) is True, "源**没有**被判死（跨度从本轮重新起算）")
    check("旧档案缺 bad_since" in out, "日志提示了这是老档案（不是静默降级）")
    print()
finally:
    restore()
    if os.path.exists(SRC_BASE):
        os.remove(SRC_BASE)

print()
print("=" * 72)
print("场景 D：被判死的源攒够条件后能否**自动回收**")
print("=" * 72)
print("""
  背景：回收分支（state=quarantined + good_streak>=2 + 云效 7 轮 + T1）自
        2026-10-15 分级抽成 compute_tier() 之后就是一条**死路径** ——
        cnci_ready/cn/why 是那个函数的局部变量，回收分支够不着，一进来就
        NameError，health.py 直接 exit=1。线上表现：判死历史库里的源
        从来没有一个被回收过（回收功能上线起 0 次生效）。
        这条用例走**真实路径**：先让 health.py 真判死，再喂 7 轮云效 +
        本机达标轮，看它能不能自己回来。
""")
backup()
try:
    # ---- 1) 先走真实判死：3 轮 CI 0 活、跨度 50h ----
    # ⚠ SRC_BASE 在 C 段的 finally 里已删掉，这里必须重新造（add_fake_source 会把
    #   合成源插回 src/sources.yaml 并同步一份到 SRC_BASE）。
    add_fake_source()
    shutil.copy2(SRC_BASE, SRC_YAML)
    if os.path.exists(ARCHIVE_YAML):
        os.remove(ARCHIVE_YAML)          # 从空历史库起，下面的断言才不含混
    seed_health_empty({FAKE: {"bad_streak": 0, "bad_since": None}})
    run_ci_rounds(["2026-10-10T00:00:00Z", "2026-10-11T01:00:00Z",
                   "2026-10-12T02:00:00Z"])
    check(enabled_of(FAKE) is False, "前置：health.py 真把它判死了（enabled: false）")
    check(FAKE in archive_names(), "前置：进了历史库 archive/sources.yaml",
          "；".join(archive_names()))

    # ---- 2) 灌历史：本机 1 轮达标（本轮再达标 -> good_streak=2）、
    #          云效 7 轮达标（-> cnci_runs>=7 且 T1「两视角均达标」） ----
    h = json.load(open(HEALTH_PATH, encoding="utf-8"))
    rec = (h.get("sources") or {}).get(FAKE)
    if rec is None:
        raise SystemExit("[tier-test] 场景 D 前置失败：健康档案里没有 %s 的记录" % FAKE)
    rec["good_streak"] = 1
    rec["runs"] = (seeded_runs("cnci", 7, 66.0, 20, 1)
                   + seeded_runs("local", 1, 33.0, 99, 1)
                   + list(rec.get("runs") or []))
    with open(HEALTH_PATH, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

    # ---- 3) 本轮：本机全量达标（合成源也在里面），云效文档不含合成源 ----
    seed_local_probe({FAKE: 33.0})
    with open(CNCI_PATH, "w", encoding="utf-8") as f:
        json.dump(cnci_doc(1, "D"), f, ensure_ascii=False, indent=2)
    n_cmt = sum(1 for ln in open(SRC_YAML, encoding="utf-8")
                if ln.lstrip().startswith("#"))
    rc, out = run_health()
    for ln in out.splitlines():
        if FAKE in ln or "回收" in ln:
            print("  " + ln.strip())
    print()
    check(rc == 0 and "NameError" not in out, "health.py 正常退出（不再 NameError）",
          "exit=%s" % rc)
    check(enabled_of(FAKE) is True, "回收：enabled 回到 true")
    rec2 = (json.load(open(HEALTH_PATH, encoding="utf-8")).get("sources") or {}).get(FAKE) or {}
    check(rec2.get("state") == "active", "回收：状态回到 active",
          "实际 %s" % rec2.get("state"))
    check(FAKE not in archive_names(), "回收：已从历史库摘掉", "；".join(archive_names()))
    # 回收要写两处：src/sources.yaml（就地改 enabled）与 archive/sources.yaml。
    # 这一步同时守住那个反复发作的事故（写归档时把 src 的源清单覆盖成历史库内容）。
    n2 = sum(1 for ln in open(SRC_YAML, encoding="utf-8") if ln.lstrip().startswith("#"))
    check(n2 == n_cmt, "write_arch 写的是历史库，没盖到 src/sources.yaml",
          "%d -> %d 行注释" % (n_cmt, n2))
    print()
finally:
    restore()
    if os.path.exists(SRC_BASE):
        os.remove(SRC_BASE)

print()
print("=" * 72)
print("场景 E：auto_added 源的「自动补员退出」（2026-10-29 拍板）")
print("=" * 72)
print("""
  拍板：compute_tier T4 + 双口径均值 <2% + 云效 ≥7 轮 + 本机 ≥3 轮
        -> 自动降级（入历史库，翻盘走既有回收路线）。

  E1 云效 6 轮（<7）、本机 3 轮        -> 不退出（云效观察期未满）
  E2 云效 7 轮、本机 1+本轮=2（<3）    -> 不退出（本机观察期未满；本轮新轮次计入窗口）
  E3 双侧都够且均值 <2%（T4）         -> 退出（enabled=false + 入历史库 + 大声说明）
  E4 同等差但**没有** auto_added 标志 -> 绝不触发（此路只管自动补的，
      人工接入/老源只能走原判死路径 —— 别把 15 个现存源误伤）
""")

AUTO_SRC = "demo_auto"


def add_auto_source():
    """插入带 auto_added: true 的合成源（同 add_fake_source 的手法）。"""
    txt = open(SRC_YAML, encoding="utf-8").read()
    if AUTO_SRC not in txt:
        anchor = "\n# 已评估但未纳入（改 enabled: true 即恢复）\nexcluded:"
        if anchor not in txt:
            raise SystemExit("[tier-test] sources.yaml 结构变了：找不到 excluded 锚点")
        entry = ("\n  - name: %s\n"
                 "    url: https://example/%s\n"
                 "    enabled: true\n"
                 "    auto_added: true\n"
                 "    note: 合成源（场景 E）：模拟 src/refill.py 补进来的自动源\n"
                 % (AUTO_SRC, AUTO_SRC))
        txt = txt.replace(anchor, entry + anchor, 1)
        with open(SRC_YAML, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
    shutil.copy2(SRC_YAML, SRC_BASE)


def seed_auto_runs(n_cnci, n_local, rate=1.0):
    """把 auto_added 源的历史轮次直接写进档案（cnci/local 各 n 轮，均 rate）。"""
    h = json.load(open(HEALTH_PATH, encoding="utf-8"))
    runs = seeded_runs("cnci", n_cnci, rate, 0, 1) + \
        seeded_runs("local", n_local, rate, 3, 1)
    rec = (h.get("sources") or {}).setdefault(AUTO_SRC, {
        "name": AUTO_SRC, "state": "active", "bad_streak": 0,
        "good_streak": 0, "bad_since": None, "runs": []})
    rec["runs"] = runs + list(rec.get("runs") or [])
    rec["state"] = "active"
    with open(HEALTH_PATH, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)


def run_local_round():
    """以本机（scope=local）口径跑一轮 health.py。"""
    seed_local_probe({AUTO_SRC: 1.0})
    return run_health()


backup()
try:
    # ---- E1：云效 6 轮（< 7）、本机 3 轮 ----
    print("E1  云效 6 轮 < 7，本机 3 轮")
    add_auto_source()
    shutil.copy2(SRC_BASE, SRC_YAML)
    seed_health_empty()
    seed_auto_runs(n_cnci=6, n_local=3)
    rc, out = run_local_round()
    check(AUTO_SRC not in archive_names(), "云效观察期未满，没有退出",
          "；".join(archive_names()) or "（历史库为空）")
    check(enabled_of(AUTO_SRC) is True, "src 里 enabled 仍为 true")
    check("自动补员退出" not in out, "退出横幅没出现")
    print()

    # ---- E2：云效 7 轮、本机 1 + 本轮 = 2（< 3；本轮新轮次也计入窗口）----
    print("E2  云效 7 轮、本机 1+本轮=2（< 3）")
    shutil.copy2(SRC_BASE, SRC_YAML)
    seed_health_empty()
    seed_auto_runs(n_cnci=7, n_local=1)
    rc, out = run_local_round()
    check(enabled_of(AUTO_SRC) is True, "本机轮数不够，没有退出")
    check("自动补员退出" not in out, "退出横幅没出现")
    print()

    # ---- E3：双侧都够（云效 7 + 本机 3），均值 1%（< 2），T4 -> 退出 ----
    print("E3  云效 7 轮 + 本机 3 轮 + 双均值 1%（T4）")
    if os.path.exists(ARCHIVE_YAML):
        os.remove(ARCHIVE_YAML)          # 从空历史库起，入档断言才不含混
    shutil.copy2(SRC_BASE, SRC_YAML)
    seed_health_empty()
    seed_auto_runs(n_cnci=7, n_local=3)
    rc, out = run_health()
    for ln in out.splitlines():
        if "自动补员" in ln and AUTO_SRC in ln:
            print("  " + ln.strip())
    check(enabled_of(AUTO_SRC) is False, "退出：enabled 翻成 false")
    check(AUTO_SRC in archive_names(), "退出：已入历史库 archive/sources.yaml")
    rec3 = json.load(open(HEALTH_PATH, encoding="utf-8"))["sources"].get(AUTO_SRC) or {}
    check(rec3.get("state") == "quarantined", "退出：状态 = quarantined（复用降级机制，"
          "翻盘走既有回收路线）", "实际 %s" % rec3.get("state"))
    check("自动补员退出" in out, "大声说明（不是静默消失）")
    arch3 = yaml.safe_load(open(ARCHIVE_YAML, encoding="utf-8")) or {}
    why3 = [s.get("quarantine_reason") for s in (arch3.get("sources") or [])
            if s.get("name") == AUTO_SRC]
    check(why3 and "双口径均值" in (why3[0] or ""),
          "历史库里的退出原因写明双口径均值", (why3 or ["?"])[0][:80])
    print()

    # ---- E4：同样差的数据，但没有 auto_added 标志 -> 绝不触发 ----
    print("E4  同等差但无 auto_added 标志（人工接入的老源不受此路管辖）")
    shutil.copy2(SRC_BASE, SRC_YAML)
    txt_no = open(SRC_YAML, encoding="utf-8").read().replace(
        "    auto_added: true\n", "")
    with open(SRC_YAML, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt_no)
    seed_health_empty()
    seed_auto_runs(n_cnci=7, n_local=3)
    rc, out = run_health()
    check(enabled_of(AUTO_SRC) is True, "无 auto_added 标志 -> 退出规则不碰它")
    check("自动补员退出" not in out, "退出横幅没出现")
    print()
finally:
    restore()
    if os.path.exists(SRC_BASE):
        os.remove(SRC_BASE)

print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（A 数据不足不判定 / B 四格全覆盖 / C 判死双闸门 + 注释零丢失 "
      "/ D 判死后可回收 / E 自动补员退出双观察期闸门 + auto_added 旗标限定）")
