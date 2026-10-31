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

## 五个用例（全部用真 git + 真裸仓，不碰网络；每例独立建仓）

  A 正常        -> 第 1 次就成功
  B 被 CI 插队  -> 第 1 次真被拒 -> rebase 自愈 -> 第 2 次成功；两个提交都在远端
  C 真冲突      -> 推不上去 + 自动救援也没成：返回非 0、无中间态、
                   工作区无冲突标记、**本地提交原封不动**（克隆式救援，
                   成功前不动真实工作区）
  D 救援成功    -> 三连败后自动「克隆-合并-补推」真成功：本机数据 + 桩写入的
                   健康档案都落到远端，真实工作区随后对齐远端（积压清零）
  E 救援失败    -> 桩 health 报错：真实工作区/积压提交纹丝不动，大声退出
                   （失败方向只能是「这轮没救成」，绝不是「仓库被拆」）

静默化静态扫描：local_probe.py / probe.py 的**每一个**子进程呼叫都必须带
creationflags=NOWIN —— pythonw 计划任务下少一处，推送/探针时段就多一路弹窗
（2026-10-24 用户反馈的根因）。
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


def remote_file(remote, cwd, rel):
    p = g(["--git-dir", remote, "show", "main:%s" % rel], cwd)
    return p.stdout if p.returncode == 0 else None


def spawn_blocks(path):
    """从源码文本里抠出每个 subprocess.run( / subprocess.Popen( 调用块（括号配平）。"""
    src = io.open(path, encoding="utf-8").read()
    out, i = [], 0
    while True:
        hit = None
        for kw in ("subprocess.run(", "subprocess.Popen("):
            k = src.find(kw, i)
            if k != -1 and (hit is None or k < hit[0]):
                hit = (k, len(kw))
        if hit is None:
            return out
        k, off = hit
        i = k + off
        depth = 1
        while i < len(src) and depth:
            ch = src[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1
        out.append(src[k:i])


orig_health = local_probe._run_health   # 各用例换桩，finally 里还原


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
print("用例 C：真冲突 -> 允许失败，必须把仓库留在干净状态（救援也救不成时）")
print("=" * 72)
dC, remoteC, workC, otherC = setup("c")
ci_rc, ci_out = ci_push(otherC, "state/probe_latest.json", '{"a": "CI 的版本"}\n',
                        "chore: 源健康档案（模拟 CI 抢改同一个文件）")
check(ci_rc == 0, "「CI」抢改同一个文件的提交真的推上去了（前提条件）",
      ci_out.splitlines()[-1][:80])
write(workC, "state/probe_latest.json", '{"a": "本机的版本"}')
local_probe._run_health = lambda cwd: (2, "stub: 克隆里的 health 失败")   # 救援必败
try:
    rc, out = run_push(workC)
    check(rc != 0, "冲突时明确返回非 0（不假装成功）", "rc=%s" % rc)
    check("已 rebase --abort" in out, "冲突后立刻 abort 并说出来了")
    check("第 3/3 次被拒" in out, "重试用满了（不是一次就放弃）",
          [l.strip() for l in out.splitlines() if "被拒" in l][-1:])
    check("自动救援" in out and "未成" in out, "救援被触发且大声说了没成",
          [l.strip() for l in out.splitlines() if "rescue" in l][:1])
    check(not mid_state(workC), "**没有** rebase-merge/rebase-apply 残留（§75 #9 的核心）")
    st = g(["status", "--porcelain"], workC).stdout
    check("UU" not in st and "<<<<<<<" not in st, "工作区没有冲突标记/未合并条目",
          st.strip()[:60])
    last = g(["log", "-1", "--format=%s"], workC).stdout.strip()
    check(last.startswith("chore: 本机探针"), "本地提交还在（克隆式救援不拆真实工作区）", last)
    subsC = remote_subjects(remoteC, dC)
    check(not any("补推" in s for s in subsC), "失败的救援没有把任何东西推上远端")
    probeC = remote_file(remoteC, dC, "state/probe_latest.json") or ""
    check("本机的版本" not in probeC,
          "冲突内容没有被硬推上去（绝不 --force）", probeC[:40])
    st2 = g(["status", "--porcelain"], workC)
    check(st2.returncode == 0 and not mid_state(workC),
          "abort 之后 git 仍能正常操作该仓库（人不用去手抠 .git）")
finally:
    local_probe._run_health = orig_health

# ---------------------------------------------------------------- D 救援成功
print("")
print("=" * 72)
print("用例 D：三连败 -> 自动救援真成功（克隆里合并并补推，工作区随后对齐）")
print("=" * 72)
dD, remoteD, workD, otherD = setup("d")
ci_rc, ci_out = ci_push(otherD, "state/probe_latest.json", '{"a": "CI 的版本"}\n',
                        "chore: 源健康档案（模拟 CI 抢改同一个文件）")
check(ci_rc == 0, "「CI」的插队提交真的推上去了（前提条件）", ci_out.splitlines()[-1][:80])


def fake_health_ok(cwd):
    """桩：在克隆里写一个真文件再返回成功 —— 若这文件最终出现在远端，
    说明「克隆合并 -> commit -> push -> 远端落地」整条镜头都是真的走过。"""
    with io.open(os.path.join(cwd, "state", "source_health.json"), "w",
                 encoding="utf-8") as f:
        f.write('{"marker": "rescued"}')
    return 0, "stub: ok"


local_probe._run_health = fake_health_ok
try:
    write(workD, "state/probe_latest.json", '{"a": "本机的版本"}')
    write(workD, "data/eval_verdicts.json", '{"verdicts": "本机评估结论 103 条"}')
    rc, out = run_push(workD)
    check(rc == 0, "三连败后救援链把推送救成了（exit=0）", "rc=%s" % rc)
    check(out.count("被拒") >= 2, "前 3 次推送真的被拒过（不走救援的假成功）")
    check("自动救援成功" in out, "救援成功被大声说出来了")
    subsD = remote_subjects(remoteD, dD)
    check(any("补推" in s for s in subsD) and any("模拟 CI" in s for s in subsD),
          "远端同时有 CI 的提交与本机的补推提交", subsD[:3])
    got = remote_file(remoteD, dD, "state/source_health.json")
    check(got is not None and "rescued" in got,
          "桩在克隆里写的健康档案真的落到了远端（整条链是真的）", (got or "")[:40])
    gotp = remote_file(remoteD, dD, "state/probe_latest.json") or ""
    check("本机的版本" in gotp, "本机积压数据真的并进了远端", gotp[:40])
    gotv = remote_file(remoteD, dD, "data/eval_verdicts.json") or ""
    check("本机评估结论" in gotv,
          "评估通道也被救援一并重放（2026-10-30 bb6d226 真 bug 后加的回归断言）",
          (gotv or "")[:40])
    stD = g(["status", "--porcelain"], workD).stdout
    nD = g(["rev-list", "--count", "origin/main..HEAD"], workD).stdout.strip()
    check(nD == "0" and stD.strip() == "" and not mid_state(workD),
          "真实工作区随后对齐远端（积压清零、无残留中间态）", "stuck=%s st=%s" % (nD, stD.strip()[:40]))
finally:
    local_probe._run_health = orig_health

# ---------------------------------------------------------------- E 救援失败
print("")
print("=" * 72)
print("用例 E：救援失败（桩 health 报错）-> 真实工作区与积压提交纹丝不动")
print("=" * 72)
dE, remoteE, workE, otherE = setup("e")
ci_rc, ci_out = ci_push(otherE, "state/probe_latest.json", '{"a": "CI 的版本"}\n',
                        "chore: 源健康档案（模拟 CI 抢改同一个文件）")
check(ci_rc == 0, "「CI」的插队提交真的推上去了（前提条件）", ci_out.splitlines()[-1][:80])
write(workE, "state/probe_latest.json", '{"a": "本机的版本"}')
local_probe._run_health = lambda cwd: (2, "stub: 克隆里的 health 失败")
try:
    rc, out = run_push(workE)
    check(rc != 0, "没救成就是没救成（明确非 0）", "rc=%s" % rc)
    check("自动救援" in out and ("未成" in out or "失败" in out), "救援失败被大声说了出来")
    stE = g(["status", "--porcelain"], workE).stdout
    lastE = g(["log", "-1", "--format=%s"], workE).stdout.strip()
    nE = g(["rev-list", "--count", "origin/main..HEAD"], workE).stdout.strip()
    check(lastE.startswith("chore: 本机探针") and nE == "1" and stE.strip() == "",
          "本地积压提交原封不动（下轮还能推/还能救）",
          "head=%s stuck=%s st=%s" % (lastE[:28], nE, stE.strip()[:30]))
    check(not mid_state(workE), "没有残留 rebase 中间态")
    check((remote_file(remoteE, dE, "state/probe_latest.json") or "").find("本机的版本") < 0,
          "失败路径没有把本机内容偷偷推上去（绝不 --force）")
finally:
    local_probe._run_health = orig_health

# ---------------------------------------------------------------- 静默化扫描
print("")
print("=" * 72)
print("静态扫描：L2 链（local_probe.py / probe.py）子进程必须全部静默（NOWIN）")
print("=" * 72)
pLP = os.path.join(ROOT, "src", "local_probe.py")
pPR = os.path.join(ROOT, "src", "probe.py")
bad = []
for path in (pLP, pPR):
    blocks = spawn_blocks(path)
    if not blocks:
        bad.append("%s: 一个子进程呼叫都没找到（文件被改坏？）" % os.path.basename(path))
    for b in blocks:
        if "creationflags" not in b:
            bad.append("%s: %s" % (os.path.basename(path), b.replace("\n", " ")[:90]))
nsites = len(spawn_blocks(pLP)) + len(spawn_blocks(pPR))
print("  呼叫点共 %d 个（local_probe %d + probe %d）"
      % (nsites, len(spawn_blocks(pLP)), len(spawn_blocks(pPR))))
check(not bad, "每个子进程呼叫都带 creationflags=NOWIN（pythonw 不弹窗）", "；".join(bad[:3]))

print("")
print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（正常 / 真竞态自愈 / 冲突干净 / 救援成功 / 救援失败不伤仓库 / 静默扫描）")
