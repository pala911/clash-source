# -*- coding: utf-8 -*-
"""验证本机探针（pythonw / 计划任务）下 health.py 的输出**可观测**、失败**不被吞掉**。

## 为什么要有这个测试

local_probe.py 由计划任务用 **pythonw** 静默跑。pythonw.exe 是 GUI 子系统程序，
没有控制台，`sys.stdout` / `sys.stderr` 都是 None（实测：从 PowerShell 直接起
pythonw，`sys.stdout is None` 照样是 True —— 它不继承控制台句柄）。

脚本自己有一道守卫把两者接到 `logs/local_probe_stdout.log`，`run_probe()` 也
**显式**把句柄递给 probe.py：

    subprocess.run([PY, probe.py, ...], stdout=sys.stdout, stderr=STDOUT)

但 health.py 那一处原来没有：

    subprocess.run([PY, health.py], cwd=ROOT)     # ← 子进程继承 pythonw 的无效句柄

实测后果（2026-10-18 12:41 那轮）：`logs/local_probe_stdout.log` 里有 [probe] 行，
**一个 [health] 行都没有** —— 健康档案那一步有没有跑、是不是崩了，全程不可观测。
而回收分支的 NameError 就是靠这个「不可观测」藏了很久（判死历史库 0 源被回收）。
删掉 contextlib.redirect_stdout(buf) 只解决了一半：那段转发是死代码，
真正让输出消失的是**没有递句柄**；退出码也从来没人看。

## 怎么测

把仓库复制到**临时目录**，用真 pythonw 跑 `--scope-only --no-push`：

  用例 1  正常的 health.py    -> 日志里必须有 [health] 行（输出确实递到了）
  用例 2  health.py 退出 3    -> 日志必须留痕，且进程退出码必须变成 3（不再静默）

⚠ 必须在隔离副本里跑：真跑一轮 health.py 会往 state/source_health.json 追加
  轮次、改写 src/sources.yaml —— 那是真实的判定历史，不能被测试污染。
  health.py 的 ROOT 由 __file__ 推出，所以副本天然自成一体。
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
STATE = os.path.join(ROOT, "state")
ARCHIVE = os.path.join(ROOT, "archive", "sources.yaml")

# ⚠ 必须用 pythonw.exe（不是 python.exe）：只有 GUI 子系统解释器才会
#   把 sys.stdout 置为 None，那个守卫和这个缺陷都只在 pythonw 下存在。
PYW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                        ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def make_tree(tag, health_body=None):
    """复制出跑 local_probe 必需的最小文件集，返回临时仓库根。"""
    t = tempfile.mkdtemp(prefix="lpobs_%s_" % tag)
    for d in ("src", "state", "archive", "logs"):
        os.makedirs(os.path.join(t, d), exist_ok=True)
    for p in glob.glob(os.path.join(SRC, "*.py")) + [os.path.join(SRC, "sources.yaml")]:
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(t, "src", os.path.basename(p)))
    for p in glob.glob(os.path.join(STATE, "*.json")):
        shutil.copy2(p, os.path.join(t, "state", os.path.basename(p)))
    if os.path.exists(ARCHIVE):
        shutil.copy2(ARCHIVE, os.path.join(t, "archive", "sources.yaml"))
    if health_body is not None:
        with open(os.path.join(t, "src", "health.py"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(health_body)
    return t


def run_scope_only(t):
    """按计划任务的真实方式跑一轮：pythonw + --scope-only + --no-push。"""
    p = subprocess.run([PYW, os.path.join(t, "src", "local_probe.py"),
                        "--scope-only", "--no-push"], cwd=t, timeout=600)
    return p.returncode


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def count_lines(text, prefix):
    return len([ln for ln in text.splitlines() if ln.strip().startswith(prefix)])


print("=" * 72)
print("前置检查")
print("=" * 72)
if not os.path.exists(PYW):
    print("  ✗ 找不到 pythonw.exe：%s" % PYW)
    print("    这个测试必须在有 GUI 解释器的机器上跑（就是跑计划任务的那台）。")
    sys.exit(1)
print("  ✓ pythonw.exe: %s" % PYW)

print()
print("=" * 72)
print("用例 1：正常的 health.py —— 输出必须落到 logs/local_probe_stdout.log")
print("=" * 72)
t1 = make_tree("ok")
try:
    rc = run_scope_only(t1)
    log = read(os.path.join(t1, "logs", "local_probe_stdout.log"))
    oplog = read(os.path.join(t1, "logs", "local_probe.log"))
    n_local = count_lines(log, "[local]")
    n_health = count_lines(log, "[health]")
    print("  pythonw 退出码: %s" % rc)
    print("  local_probe_stdout.log: %d 字节 / [local] %d 行 / [health] %d 行"
          % (len(log), n_local, n_health))
    for ln in log.splitlines()[:5]:
        print("    %s" % ln[:118])
    print("    …")
    check(len(log) > 0, "日志文件被创建（pythonw 守卫生效）")
    check(n_local > 0, "[local] 自己的输出落盘了")
    check(n_health > 0, "health.py 的输出也落盘了（本次修复的核心）",
          "" if n_health else "0 行 —— 子进程继承的是 pythonw 的无效句柄，输出被丢弃")
    check("done, exit=0" in oplog, "oplog 记了 done, exit=0",
          "；".join(oplog.splitlines()[-2:])[:140])
finally:
    shutil.rmtree(t1, ignore_errors=True)

print()
print("=" * 72)
print("用例 2：health.py 失败 —— 必须留痕，且退出码必须反映出来")
print("=" * 72)
# 3 是刻意选的：和 NameError 的 exit=1 不同，能证明「退出码被原样传递」，
# 而不是碰巧匹配了某个固定值。
STUB = ("# -*- coding: utf-8 -*-\n"
        "\"\"\"桩：模拟回收分支的未捕获异常（health.py 真崩了就是这个效果）。\"\"\"\n"
        "import sys\n"
        "sys.exit(3)\n")
t2 = make_tree("bad", health_body=STUB)
try:
    rc = run_scope_only(t2)
    log = read(os.path.join(t2, "logs", "local_probe_stdout.log"))
    oplog = read(os.path.join(t2, "logs", "local_probe.log"))
    print("  pythonw 退出码: %s" % rc)
    for ln in log.splitlines():
        if "health" in ln:
            print("    %s" % ln[:118])
    check(rc == 3, "退出码原样传到计划任务（原来是恒 0）", "实际 %s" % rc)
    check("health.py 失败" in log and "exit=3" in log,
          "日志明说了 health.py 失败并给出退出码",
          "；".join(ln.strip()[:80] for ln in log.splitlines()
                   if "health" in ln)[:160])
    check("done, exit=3" in oplog, "oplog 也记下真实退出码（计划任务里能直接查）",
          "；".join(oplog.splitlines()[-2:])[:140])
finally:
    shutil.rmtree(t2, ignore_errors=True)

print()
print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（pythonw 下 health.py 的输出可观测、失败可观测）")
