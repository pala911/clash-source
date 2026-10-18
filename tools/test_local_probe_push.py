# -*- coding: utf-8 -*-
"""验证本机探针的推送重试，以及「推失败也绝不能把仓库留在中间态」。

## 为什么必须真跑（不能只做静态断言）

`local_probe.push_to_github()` 的重试分支**只在真被插队的时候才走**；
「代码里有 for 循环」不等于「这条路真的能自愈」。2026-10-18 一天之内，
CI 侧的 tools/ci_git_push.sh 就是这么栽的：静态断言全绿，真跑抓出三处坑
（pre-push 钩子的 GIT_DIR、「插队方」的基点、rebase 中间态）。教训见
memory/feedback_race_test_must_prove_it_happened.md —— 所以下面每一处竞态
都**先断言「竞态真的发生了」**（CI 方推成功、本机第 1 次真被拒），
否则用例必须红，而不是绿着骗人。

## 三个用例（全部用真 git + 真裸仓，不碰网络；每例独立建仓）

  A 正常        -> 第 1 次就成功
  B 被 CI 插队  -> 第 1 次真被拒 -> rebase 自愈 -> 第 2 次成功；两个提交都在远端
  C 真冲突      -> 推不上去，但**仓库必须是干净的**：返回非 0、
                   .git/rebase-merge 不存在、工作区无冲突标记、本地提交还在
                   （§75 #9：失败方向只能是「这轮推不上去」，绝不能是「仓库卡死」）
"""
import contextlib                 # noqa: E402
import io                         # noqa: E402
import os                         # noqa: E402
import shutil                     # noqa: E402
import subprocess                 # noqa: E402
import sys                        # noqa: E402
import tempfile                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import local_probe                # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                         ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


GIT = local_probe.GIT if os.path.exists(local_probe.GIT) else (shutil.which("git") or "")
if not GIT:
    print("✗ 找不到 git（既不在 %s，也不在 PATH）—— 这门测试没有降级余地" % local_probe.GIT)
    sys.exit(1)


def g(args, cwd):
    return subprocess.run([GIT] + args, cwd=cwd, capture_output=True,
                          text=True, timeout=60)


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(text)


def commit(repo, msg):
    g(["-c", "user.name=test", "-c", "user.email=t@example.com", "add", "-A"], repo)
    return g(["-c", "user.name=test", "-c", "user.email=t@example.com",
              "commit", "-m", msg], repo)


def setup(tag):
    """建 裸仓 + work 克隆（main 分支）+ other 克隆（扮演 CI）。每例一个，互不干扰。"""
    d = tempfile.mkdtemp(prefix="lpush_%s_" % tag)
    remote = os.path.join(d, "remote.git")
    work, other = os.path.join(d, "work"), os.path.join(d, "other")
    g(["init", "--bare", remote], d)
    g(["symbolic-ref", "HEAD", "refs/heads/main"], remote)
    g(["clone", remote, work], d)
    # 本机脚本只会 add 这四个路径（路径不存在时 git add 会报错，所以先备好）
    for sub in ("state", "archive", "src", "reports"):
        os.makedirs(os.path.join(work, sub), exist_ok=True)
    write(work, "state/probe_latest.json", '{"a": 0}')
    write(work, "archive/a.txt", "a")
    write(work, "src/sources.yaml", "sources: []")
    write(work, "reports/latest.md", "# r")
    commit(work, "init")
    g(["push", "-u", "origin", "main"], work)
    # ⚠ 「插队方」必须在**首次推送之后**克隆：从空仓克隆出来的 other 没有 main 基点，
    #   它会提交成另一个根提交、推的时候自己先被 fetch first 顶掉 —— 竞态根本造不出来
    #   （2026-10-18 CI 侧也是同一个坑，见 feedback_race_test_must_prove_it_happened.md）
    g(["clone", remote, other], d)
    return d, remote, work, other


def ci_push(other, rel, text, msg):
    """扮演 CI：先跟上 origin/main（基点旧了它自己会被拒），再改文件、提交、推送。

    返回 push 的 (returncode, 输出) —— 调用方**必须断言 rc==0**：
    插队没成功 = 竞态没造出来 = 后面的「自愈」用例是假通过。
    """
    g(["-c", "user.name=ci", "-c", "user.email=ci@example.com",
       "pull", "--rebase", "origin", "main"], other)
    write(other, rel, text)
    commit(other, msg)
    p = g(["push", "origin", "main"], other)
    return p.returncode, (p.stdout + p.stderr).strip()


def run_push(work):
    """跑被测函数（只替换 ROOT/GAP；GIT/PROXY 保持模块原样）。"""
    old_root, old_gap = local_probe.ROOT, local_probe.PUSH_GAP
    local_probe.ROOT, local_probe.PUSH_GAP = work, 0
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = local_probe.push_to_github()
    finally:
        local_probe.ROOT, local_probe.PUSH_GAP = old_root, old_gap
    return rc, buf.getvalue()


def mid_state(repo):
    gd = os.path.join(repo, ".git")
    return (os.path.exists(os.path.join(gd, "rebase-merge"))
            or os.path.exists(os.path.join(gd, "rebase-apply")))


def remote_subjects(remote, cwd):
    p = g(["--git-dir", remote, "log", "--format=%s", "main"], cwd)
    return p.stdout.splitlines()


# ---------------------------------------------------------------- A 正常
print("=" * 72)
print("用例 A：正常推送 -> 第 1 次就成功")
print("=" * 72)
dA, remoteA, workA, otherA = setup("a")
write(workA, "state/probe_latest.json", '{"a": 1}')
rc, out = run_push(workA)
check(rc == 0 and "push: OK" in out, "正常路径 exit=0 且没走重试", "rc=%s" % rc)
check("被拒" not in out, "没有被拒过（这才是「正常」的意思）")
check(not mid_state(workA), "没有残留 rebase 中间态")

# ---------------------------------------------------------------- B 真竞态
print("")
print("=" * 72)
print("用例 B：被 CI 插队（真竞态）-> 必须自愈，且竞态真的发生过")
print("=" * 72)
dB, remoteB, workB, otherB = setup("b")
ci_rc, ci_out = ci_push(otherB, "reports/latest.md", "# CI 刚推的产物\n",
                        "chore: 源更新（模拟 CI）")
check(ci_rc == 0, "「CI」的插队提交真的推上去了（前提条件）", ci_out.splitlines()[-1][:80])
write(workB, "state/probe_latest.json", '{"a": 2}')
rc, out = run_push(workB)
check(rc == 0, "重试后推送成功", "rc=%s" % rc)
check("第 1/3 次被拒" in out, "第 1 次 push **真的**被拒了（防假通过）",
      [l.strip() for l in out.splitlines() if "被拒" in l][:1])
check("重试生效" in out, "走的确实是重试分支（第 2 次尝试）")
subsB = remote_subjects(remoteB, dB)
check(any("模拟 CI" in s for s in subsB) and any("本机探针" in s for s in subsB),
      "两边的提交都在远端（rebase 没有丢东西）", subsB[:3])
check(not mid_state(workB), "没有残留 rebase 中间态")

# ---------------------------------------------------------------- C 真冲突
print("")
print("=" * 72)
print("用例 C：真冲突 -> 允许失败，但必须把仓库留在干净状态")
print("=" * 72)
dC, remoteC, workC, otherC = setup("c")
ci_rc, ci_out = ci_push(otherC, "state/probe_latest.json", '{"a": "CI 的版本"}\n',
                        "chore: 源健康档案（模拟 CI 抢改同一个文件）")
check(ci_rc == 0, "「CI」抢改同一个文件的提交真的推上去了（前提条件）",
      ci_out.splitlines()[-1][:80])
write(workC, "state/probe_latest.json", '{"a": "本机的版本"}')
rc, out = run_push(workC)
check(rc != 0, "冲突时明确返回非 0（不假装成功）", "rc=%s" % rc)
check("已 rebase --abort" in out, "冲突后立刻 abort 并说出来了")
check("第 3/3 次被拒" in out, "重试用满了（不是一次就放弃）",
      [l.strip() for l in out.splitlines() if "被拒" in l][-1:])
check(not mid_state(workC), "**没有** rebase-merge/rebase-apply 残留（§75 #9 的核心）")
st = g(["status", "--porcelain"], workC).stdout
check("UU" not in st and "<<<<<<<" not in st, "工作区没有冲突标记/未合并条目",
      st.strip()[:60])
last = g(["log", "-1", "--format=%s"], workC).stdout.strip()
check(last.startswith("chore: 本机探针"), "本地提交还在（数据没丢，下一轮还能推）", last)
subsC = remote_subjects(remoteC, dC)
check(not any("本机的版本" in s for s in subsC), "冲突内容没有被硬推上去（绝不 --force）")
st2 = g(["status", "--porcelain"], workC)
check(st2.returncode == 0 and not mid_state(workC),
      "abort 之后 git 仍能正常操作该仓库（人不用去手抠 .git）")

print("")
print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（正常 / 真竞态自愈 / 冲突不留中间态）")
