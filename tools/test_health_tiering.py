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

BK = os.path.join(ROOT, ".tools", "_tier_test_backup")


def backup():
    shutil.rmtree(BK, ignore_errors=True)
    os.makedirs(BK)
    for p in (PROBE_PATH, SRC_YAML, os.path.join(ROOT, "state", "source_health.json")):
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(BK, os.path.basename(p)))
    # ⚠ probe_cnci_latest.json 也必须一起备份。
    #   原来 restore() 里有个 `os.remove(CNCI_PATH)`，本意是清掉测试造的假数据，
    #   但它在**真实文件存在时也照删** —— 于是跑一次测试就把线上真数据删掉了。
    #   这类「清理测试残留」的动作如果不先判断文件是不是自己造的，就会毁真数据。
    shutil.copy2(CNCI_PATH, os.path.join(BK, "probe_cnci_latest.json")) \
        if os.path.exists(CNCI_PATH) else None


def restore():
    for fn in os.listdir(BK):
        dst = {"probe_latest.json": PROBE_PATH, "sources.yaml": SRC_YAML,
               "source_health.json": os.path.join(ROOT, "state", "source_health.json"),
               "probe_cnci_latest.json": CNCI_PATH}[fn]
        shutil.copy2(os.path.join(BK, fn), dst)
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


def seed_health_empty():
    """⚠ 把健康档案重置成**零历史**，再注入本轮探针数据。

    没有这一步，这个测试在结构上就是错的：
      · 测试第 152 行用**硬编码常量** LOCAL[name] 算期望
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
                      "good_streak": 0, "runs": []}
    doc = {"v": 1, "updated": "2026-01-01T00:00:00Z", "sources": srcs}
    with open(os.path.join(ROOT, "state", "source_health.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def tier_of(name):
    h = json.load(open(os.path.join(ROOT, "state", "source_health.json"), encoding="utf-8"))
    return (h["sources"].get(name, {}) or {}).get("tier", "<无>")


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
    hs = json.load(open(os.path.join(ROOT, "state", "source_health.json"), encoding="utf-8"))
    bad = [n for n in LOCAL if hs["sources"][n].get("tier") != "?"]
    print("  分级非「?」的源: %s" % (bad or "无（正确 —— 样本不足不该下结论）"))
    print("  cnci 轮次计数: %s" % hs["sources"]["anaer"].get("tier_rates", {}).get("cnci_runs"))
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
    print()
    print("  关键校验：")
    print("    snakem982 本机 15.4%% / 云效 0.0%%  -> %s（位置敏感，绝不该自动回收）"
          % tier_of("snakem982"))
    print("    ermaozi    本机  2.9%% / 云效 13.3%% -> %s（机房友好，不该进主池）"
          % tier_of("ermaozi"))
finally:
    restore()

print()
print("已还原 state/ 与 src/sources.yaml，测试无副作用。")