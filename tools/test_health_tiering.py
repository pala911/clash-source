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
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY, os.path.join(ROOT, "src", "health.py")],
                       capture_output=True, cwd=ROOT, env=env)
    return _s(p.stdout) + _s(p.stderr)


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


def seed_local_probe():
    """把本机全量结果写成 scope=local 的探针文档，供 health.py 读取。"""
    srcs = {}
    for name, rate in sorted(LOCAL.items()):
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
    out = run_health()
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
    out = run_health()
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
        out = run_health()
    return out


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

print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（A 数据不足不判定 / B 四格全覆盖 / C 判死双闸门 + 注释零丢失）")
