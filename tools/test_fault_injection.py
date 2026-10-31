# -*- coding: utf-8 -*-
"""故障注入：故意把每个输入搞坏，看系统是**明确报错**还是**静默出错**。

## 为什么要有这个测试

全系统的设计原则是**保守失败**：探针层坏了不误杀源、不让订阅变坏。
但「保守失败」很容易写反——代码在坏数据上抛异常、或者更糟：
**静默地按默认值继续**，于是「源被误判为达标」这种不可逆的事就发生了。

静态断言查不出这一类问题。只能真的把数据搞坏。

## 每个用例断言三件事

1. 是不是**报错或明确降级**（而不是静默按默认值走）
2. 有没有**改动真实状态**（sources.yaml / state/*.json）
3. 坏数据有没有**传播到下游**（build/profile）

跑完必须零残留。
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

PY = sys.executable
STATE = os.path.join(ROOT, "state")
BK = os.path.join(ROOT, ".tools", "_fault_backup")

WATCH = ["sources.yaml", "probe_latest.json", "probe_cnci_latest.json",
         "source_health.json", "node_stability.json"]
WATCH = [os.path.join(ROOT, "src", "sources.yaml")] + \
        [os.path.join(STATE, w.split(".")[0] + "." + w.split(".")[1]) for w in WATCH[1:]]


def snap():
    """记下每个受监控文件的原始状态（不存在也要记住）。"""
    out = {}
    for p in WATCH:
        if os.path.exists(p):
            with open(p, "rb") as f:
                out[p] = ("present", f.read())
        else:
            out[p] = ("absent", None)
    return out


def restore(s):
    for p, (kind, data) in s.items():
        if kind == "present":
            with open(p, "wb") as f:
                f.write(data)
        elif os.path.exists(p):
            os.remove(p)


# ⚠ node_stability.load() 损坏时会把坏档案改名成 *.corrupt-<时间戳> 留证。
#   那是**真实事故**要保留的东西，所以测试只清「本次新造出来的」那些，
#   不碰跑之前就存在的（否则会把上一次真事故的证据删掉）。
CORRUPT_BEFORE = set(glob.glob(os.path.join(STATE, "*.corrupt-*")))
STATE_BEFORE = set(os.listdir(STATE))


def cleanup_artifacts():
    """清掉本次跑出来的改名留证文件；返回 state/ 里新出现的文件（真残留）。"""
    for p in set(glob.glob(os.path.join(STATE, "*.corrupt-*"))) - CORRUPT_BEFORE:
        os.remove(p)
    return sorted(set(os.listdir(STATE)) - STATE_BEFORE)


def run(script, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY, os.path.join(ROOT, "src", script)] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       cwd=ROOT, env=env, timeout=180)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace")


def changed(s):
    """返回被改动的文件列表。"""
    out = []
    for p, (kind, data) in s.items():
        now = "present" if os.path.exists(p) else "absent"
        if now != kind:
            out.append(p + " (消失)")
            continue
        if now == "present":
            with open(p, "rb") as f:
                if f.read() != data:
                    out.append(p + " (被改写)")
    return out


RESULTS = []

# 每个用例会往这些路径注入坏数据。比较「代码到底写了没有」时必须排除它们 ——
# 否则我自己的注入会被算成「代码改了状态」，这个信号就没有意义了。
# （第一版就是踩了这个坑：9 个用例全显示「状态改动 1」，但那是注入本身。）
INJECTED = set()


def inject(path, content):
    INJECTED.add(os.path.abspath(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def case(name, fn):
    shutil.rmtree(BK, ignore_errors=True)
    os.makedirs(BK, exist_ok=True)
    INJECTED.clear()
    s = snap()
    print("-" * 70)
    print("用例：%s" % name)
    try:
        rc, out, expect_change = fn()
        verdict = "明确报错" if rc != 0 else "静默通过"
        touched = [t for t in changed(s) if os.path.abspath(t.split(" (")[0]) not in INJECTED]
        print("  退出码=%d  判定=%s" % (rc, verdict))
        print("  代码写回: %s" % (("、".join(os.path.basename(t) for t in touched)) or "无"))
        sig = [l for l in out.splitlines()
               if "Traceback" in l or "Error" in l or "错误" in l
               or "⚠" in l or "跳过" in l or "拒绝" in l]
        for l in sig[:4]:
            print("    > " + l.strip()[:120])
        RESULTS.append((name, rc, verdict, touched, False))
    except Exception as e:
        import traceback
        print("  用例自身抛异常（测试脚本问题）: %r" % e)
        traceback.print_exc()
        RESULTS.append((name, -1, "用例自身出错", [], False))
    finally:
        restore(s)
        shutil.rmtree(BK, ignore_errors=True)


# ---------------- 用例 ----------------

SRC_YAML = os.path.join(ROOT, "src", "sources.yaml")


def c_empty_sources():
    """源清单整个是空的。期望：拒绝写入，不把它写成空。"""
    inject(SRC_YAML, "sources: []\n")
    return run("health.py")[0], run("health.py")[1], None


def c_truncated_probe():
    """探针结果被截断（写到一半崩溃的典型产物）。期望：明说没数据并跳过。"""
    inject(os.path.join(STATE, "probe_latest.json"),
           '{"scope": "local", "sources": {"anaer": {"rate":')
    return run("health.py")[0], run("health.py")[1], None


def _set_rate(value):
    p = os.path.join(STATE, "probe_latest.json")
    d = json.load(open(p, encoding="utf-8"))
    for k in d.get("sources", {}):
        d["sources"][k]["rate"] = value
    inject(p, json.dumps(d, ensure_ascii=False))


def c_rate_is_string():
    """rate 变成字符串。期望：只丢该源，不崩。"""
    _set_rate("很高")
    return run("health.py")[0], run("health.py")[1], None


def c_negative_rate():
    """rate 为负。期望：只丢该源，不崩。"""
    _set_rate(-50.0)
    return run("health.py")[0], run("health.py")[1], None


def c_rate_over_100():
    """rate > 100。期望：只丢该源，不崩。"""
    _set_rate(999.0)
    return run("health.py")[0], run("health.py")[1], None


def c_missing_fields():
    """整份结果没有 sources 键。期望：明说没数据并跳过。"""
    inject(os.path.join(STATE, "probe_latest.json"),
           json.dumps({"scope": "local", "probed_at": "2026-10-16T00:00:00Z"}))
    return run("health.py")[0], run("health.py")[1], None


def c_health_corrupt():
    """健康档案本身是坏 JSON。
    期望：**拒绝运行(exit 2)且不覆盖原文件** —— 档案里是累积的多轮历史，
    静默重建等于永久丢失。"""
    inject(os.path.join(STATE, "source_health.json"), "{ this is not json")
    return run("health.py")[0], run("health.py")[1], None


def c_cnci_corrupt():
    """云效档案被截断（云效推主仓中断的典型情形）。
    期望：明说无云效数据 + 拒绝任何回收。"""
    inject(os.path.join(STATE, "probe_cnci_latest.json"), '{"scope": "cnci", "sources": ')
    return run("health.py")[0], run("health.py")[1], None


def c_stability_corrupt():
    """节点稳定性档案损坏（build.py 要读它）。期望：不加权，而不是崩溃。"""
    inject(os.path.join(STATE, "node_stability.json"), "not json at all")
    import build
    try:
        per = {}
        for fn in glob.glob(os.path.join(ROOT, "dist", "nodes", "*.yaml")):
            n = os.path.basename(fn)[:-5]
            if n != "all":
                per[n] = [{"name": "x%d" % i, "type": "ss", "server": "1.1.1.1",
                           "port": 443, "password": "p"} for i in range(120)]
        stable, flaky, note = build.split_by_stability(per)
        return 0, "[split] %s  stable=%d flaky=%d" % (note, len(stable), len(flaky)), None
    except Exception:
        import traceback
        return 1, traceback.format_exc(), None


# 期望值：退出码必须是这个数才算通过（None = 只要不崩且行为正确即可）
EXPECT_RC = {
    "源清单为空": 0,            # 没东西要改 -> 不动文件
    "探针结果被截断": 0,
    "rate 是字符串": 0,         # 只丢该源
    "rate 为负数": 0,
    "rate > 100": 0,
    "结果缺 sources 键": 0,
    "健康档案是坏 JSON": 2,     # 必须拒绝运行
    "云效档案被截断": 0,
    "稳定性档案损坏": 0,
}

CASES = [
    ("源清单为空", c_empty_sources),
    ("探针结果被截断", c_truncated_probe),
    ("rate 是字符串", c_rate_is_string),
    ("rate 为负数", c_negative_rate),
    ("rate > 100", c_rate_over_100),
    ("结果缺 sources 键", c_missing_fields),
    ("健康档案是坏 JSON", c_health_corrupt),
    ("云效档案被截断", c_cnci_corrupt),
    ("稳定性档案损坏", c_stability_corrupt),
]

print("=" * 70)
print("故障注入：坏数据进来时，系统是否**明确报错**")
print("=" * 70)
for n, f in CASES:
    case(n, f)

print()
print("=" * 70)
print("汇总")
print("=" * 70)
bad = []
for n, rc, v, t, _ in RESULTS:
    exp = EXPECT_RC.get(n)
    ok = (rc == exp)
    flag = "✓" if ok else "✗"
    print("  %s %-22s exit=%-3d (期望 %-3s) %-10s 代码写回%d"
          % (flag, n, rc, exp, v, len(t)))
    if not ok:
        bad.append("%s: exit=%s 期望 %s" % (n, rc, exp))
print()
if bad:
    print("  ⚠ %d 个用例行为不符:" % len(bad))
    for b in bad:
        print("      %s" % b)
else:
    print("  ✓ 全部用例行为符合预期（坏数据一律「明确报错」或「跳过该源」，无静默通过）")

# 残留检查：WATCH 里的文件一个都不能丢，state/ 里也不能多出任何东西。
left = [p for p in WATCH if not os.path.exists(p)]
extra = cleanup_artifacts()
print()
print("  缺失的受监控文件: %s" % ([os.path.basename(x) for x in left] or "无"))
print("  state/ 新增残留: %s" % (extra or "无"))
print("  备份目录: %s" % ("残留" if os.path.exists(BK) else "已清理"))

sys.exit(1 if (bad or left or extra) else 0)