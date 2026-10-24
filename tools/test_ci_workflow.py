# -*- coding: utf-8 -*-
"""验证 CI 的「提交并推送产物」不再是裸 `git push`（2026-10-18 那次红流水线的回归）。

## 事故经过（实测，不是理论风险）

    04:34:48  CI 检出 3da096e 开始跑（run #19）
    04:41:07  **L2 本机探针（每天 12:30 北京时间）推上 078d4e7**
    04:41:32  CI 拿 25 秒前的旧基点做 `git push` -> non-fast-forward -> 被拒
    04:41:32  step 6「提交产物到 main」失败 -> 后面 9 个步骤**全部 skip**

后果不是「红一个叉」，而是那一轮 **L1 层整层缺失**：

    · gh-pages 不发布        -> 手机订阅最多 6 小时不更新
    · 美国口径真探针不跑      -> **唯一有判死权的那层没执行**
    · 健康档案不算不提交      -> CI 口径少攒一轮（判死要攒轮数才能判）

而 workflow 里有**三处**裸 `git push`（产物 / 健康档案 / 候选池），每一处都能
单独造成同样的连带 skip。这不是「运气不好」：CI 是 `17 */6 * * *`（可能被排队
延迟几十分钟，实测 77 分钟），本机是固定 12:30 —— 两个时间窗天然会撞。

## 这个测试守什么

1~4 是静态检查（防「有人改 workflow 时又把重试去掉」）：

  1. workflow YAML 能解析（别改出语法错误）
  2. workflow 里**不许再有非 force 的 `git push`** —— 全部走 tools/ci_git_push.sh
  3. 三个步骤都真的调了那个脚本（数一下调用次数）
  4. 脚本本身必须有：重试循环 / pull --rebase --autostash / 绝不 --force /
     rebase 冲突后 --abort / 失败时 ::warning:: 且 exit 0

5~6 是**真跑**：用 portable-git 的 sh.exe 在临时 git 仓库上真执行那个脚本。
    ⚠ 静态检查看不出「重试循环写反了」或「rebase 冲突后卡死」——本仓的教训
    （README 坑表「断言全绿 ≠ 产出物没坏」）就是必须真跑那条路径。三个场景：

      a. 无变化 -> 跳过提交（且路径不存在也不能 fatal）
      b1. 基点已经旧了（事故当天的真实局面）-> pull --rebase 自愈，第 1 次就成功
      b2. **pull 与 push 之间被插队**（用 pre-push 钩子真造出来）-> 第 1 次被拒
          -> 第 2 次成功，两边的提交都在（谁都没被 force 掉）
      c. 远端不可达 -> 3 次都失败 -> ::warning:: + exit 0，提交不丢、不留 rebase 中间态

⚠ 本机没有 `bash`，用的是 portable-git 自带的 `sh.exe`；而且**必须带 `-e` 跑**
（GitHub 的 `run: |` 默认就是 `bash -e`），否则「sleep 失败」这类错误在本地看着
没事、到 CI 上会直接 abort 整步。本机也没有 `sleep.exe`，所以测试用 CI_PUSH_GAP=0。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_DIR = os.path.join(ROOT, ".github", "workflows")
PUSH_SH = os.path.join(ROOT, "tools", "ci_git_push.sh")
PUSH_REL = "tools/ci_git_push.sh"

sys.path.insert(0, os.path.join(ROOT, ".tools", "yaml_vendor"))
try:
    import yaml
except ImportError:                                   # 本机装了 PyYAML 也一样能用
    sys.path.pop(0)
    import yaml

FAILS = []
PORTABLE_GIT = os.path.join(os.path.dirname(ROOT), "portable-git")


def check(ok, label, detail=""):
    print("  %s %s%s" % ("\u2713" if ok else "\u2717", label,
                        ("  \u2014\u2014 %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def which(cands):
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None


GIT = which([os.path.join(PORTABLE_GIT, "bin", "cmd", "git.exe"),
             os.path.join(PORTABLE_GIT, "bin", "mingw64", "bin", "git.exe"),
             shutil.which("git")])
SHELL = which([shutil.which("bash"),
               os.path.join(PORTABLE_GIT, "bin", "usr", "bin", "sh.exe"),
               os.path.join(PORTABLE_GIT, "usr", "bin", "bash.exe"),
               os.path.join(PORTABLE_GIT, "bin", "bash.exe")])


def run(cmd, cwd, env=None, timeout=180):
    return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def git(args, cwd, check_rc=True):
    r = run([GIT] + args, cwd, env=GIT_ENV)
    if check_rc and r.returncode != 0:
        raise RuntimeError("git %s 失败: %s" % (" ".join(args), (r.stderr or r.stdout)[:300]))
    return r


GIT_ENV = os.environ.copy()
if GIT:
    GIT_ENV["PATH"] = os.path.dirname(GIT) + os.pathsep + GIT_ENV.get("PATH", "")

ID = ["-c", "user.name=ci-test", "-c", "user.email=ci-test@example.invalid"]


# ---------------------------------------------------------------- 1) 解析
print("=" * 72)
print("1) workflow 文件能否解析")
print("=" * 72)
wfs = sorted(f for f in os.listdir(WF_DIR) if f.endswith((".yml", ".yaml")))
check(bool(wfs), "找到 workflow 文件", "、".join(wfs))
for f in wfs:
    p = os.path.join(WF_DIR, f)
    try:
        yaml.safe_load(open(p, encoding="utf-8").read())
        check(True, "%s 解析通过" % f)
    except Exception as e:
        check(False, "%s 解析通过" % f, str(e)[:160])

# ---------------------------------------------------------------- 2) 裸 push
print()
print("=" * 72)
print("2) 不许再有裸 `git push`（非 force 的都算违规）")
print("=" * 72)
bare, forced = [], []
for f in wfs:
    for i, ln in enumerate(open(os.path.join(WF_DIR, f), encoding="utf-8"), 1):
        s = ln.strip()
        if s.startswith("#") or "git push" not in s:
            continue
        if " --force" in s or re.search(r"git\s+push\s+(-[^\s]+\s+)*-[a-z]*f", s):
            forced.append("%s:%d  %s" % (f, i, s))
        else:
            bare.append("%s:%d  %s" % (f, i, s))
print("  非 force 的 git push: %s" % (len(bare) or "0 处"))
for b in bare:
    print("      %s" % b)
print("  force 推送（gh-pages 孤儿分支，安全）: %s" % (len(forced) or "0 处"))
for x in forced:
    print("      %s" % x)
check(not bare, "workflow 里没有裸 git push",
      "；".join(bare)[:200] if bare else "")

# ---------------------------------------------------------------- 3) 三处调用
print()
print("=" * 72)
print("3) 三个推送步骤都走 %s" % PUSH_REL)
print("=" * 72)
text = open(os.path.join(WF_DIR, "update.yml"), encoding="utf-8").read()
calls = re.findall(r"bash\s+%s\s+\"([^\"]+)\"" % re.escape(PUSH_REL), text)
print("  调用点: %s" % (len(calls) or "0"))
for c in calls:
    print("      %s" % c)
check(len(calls) == 3, "产物 / 健康档案 / 候选池 三处都调了", "实际 %d 处" % len(calls))
for kw in ("源更新", "源健康档案", "新源候选池"):
    check(any(kw in c for c in calls), "提交信息里保留了「%s」" % kw)

# ---------------------------------------------------------------- 4) 脚本不变量
print()
print("=" * 72)
print("4) 脚本必须带重试，且失败不许把流水线染红")
print("=" * 72)
check(os.path.exists(PUSH_SH), "%s 存在" % PUSH_REL,
      "推送步骤会引用它，文件不存在就是整步 fatal")
script = open(PUSH_SH, encoding="utf-8").read() if os.path.exists(PUSH_SH) else ""
for label, ok in [
    ("有重试循环（次数可调，默认 3）",
     bool(re.search(r"tries=\"\$\{CI_PUSH_TRIES:-3\}\"", script))
     and bool(re.search(r"while\s+\[\s*\"\$n\"\s+-lt\s+\"\$tries\"\s*\]", script))),
    ("被拒后 pull --rebase --autostash 再推", "pull --rebase --autostash" in script),
    ("rebase 停在中间态时 --abort（§75 #9 同一个坑）",
     "rebase --abort" in script and "rebase-merge" in script),
    ("绝不 force（防抹掉本机探针的提交）",
     "push --force" not in script and "-f origin" not in script
     and "--force-with-lease" not in script),
    ("报错用 ::warning:: 而不是 exit 1", "::warning::" in script),
    ("push 失败后 exit 0（不染红，避免连带 skip）",
     bool(re.search(r"::warning::[^\n]*\n\s*exit 0\s*$", script))),
    ("路径不存在时 add 不 fatal", "2>/dev/null || true" in script),
    ("sleep 可关（CI_PUSH_GAP，便于真跑测试）", "CI_PUSH_GAP" in script),
]:
    check(ok, label)

# ---------------------------------------------------------------- 5) 语法
print()
print("=" * 72)
print("5) shell 语法检查")
print("=" * 72)
if not SHELL:
    print("  （跳过：本机没找到 bash/sh。CI 跑在 ubuntu-latest 上，那里一定有）")
else:
    print("  用: %s" % SHELL)
    r = run([SHELL, "-n", PUSH_SH], ROOT)
    check(r.returncode == 0, "语法通过（-n）", (r.stderr or "")[:200])

# ------------------------------------------------ 6) 真跑：重试路径必须真能自愈
print()
print("=" * 72)
print("6) 真跑：临时仓库上执行脚本（空跑 / 基点旧 / 被插队 / 远端不可达）")
print("=" * 72)
if not (GIT and SHELL):
    print("  （跳过：本机没找到 git 或 sh —— 但这条路径在 CI 上每 6 小时真跑一次）")
else:
    tmp = tempfile.mkdtemp(prefix="ci_push_test_")
    try:
        origin = os.path.join(tmp, "origin.git")
        a = os.path.join(tmp, "ci")          # 扮演 CI
        b = os.path.join(tmp, "local")       # 扮演本机探针
        env = GIT_ENV.copy()
        env.update({"GITHUB_REF_NAME": "main", "CI_PUSH_GAP": "0"})
        # sh.exe 自带的那批工具在 portable-git\bin\usr\bin 里（sleep 就没有，
        # 所以测试一律 CI_PUSH_GAP=0；PATH 还是给全，免得踩别的命令缺失）
        env["PATH"] = os.pathsep.join(
            [os.path.dirname(GIT), os.path.join(PORTABLE_GIT, "bin", "usr", "bin"),
             env.get("PATH", "")])

        git(["init", "--bare", "-q", "-b", "main", origin], tmp)
        os.makedirs(os.path.join(a, "dist"))
        git(["init", "-q", "-b", "main"], a)
        open(os.path.join(a, "dist", "base.txt"), "w").write("base\n")
        git(["add", "-A"], a)
        git(ID + ["commit", "-q", "-m", "base"], a)
        git(["remote", "add", "origin", origin], a)
        git(["push", "-q", "-u", "origin", "main"], a)

        # 本机探针先推一轮（制造「CI 的基点已经旧了」这个真实局面）
        git(["clone", "-q", origin, b], tmp)
        open(os.path.join(b, "local_only.txt"), "w").write("local\n")
        git(["add", "-A"], b)
        git(ID + ["commit", "-q", "-m", "chore: 本机探针先推"], b)
        git(["push", "-q", "origin", "main"], b)

        # a) 无变化 + 路径不存在 -> 跳过提交，且不能 fatal
        r = run([SHELL, "-e", PUSH_SH, "chore: 测试 空跑", "dist", "state"], a, env)
        check(r.returncode == 0, "a) 无变化时 exit 0", (r.stderr or "")[:200])
        check("本轮无变化" in (r.stdout or ""), "a) 明确说「本轮无变化」")
        check((git(["log", "-1", "--pretty=%s"], a).stdout or "").strip() == "base",
              "a) 不存在的路径没造出提交（add 不 fatal）")

        # b1) 事故当天的真实局面：CI 开始跑之后本机才推上来（基点已经旧了）
        #     -> 靠每轮尝试前的 pull --rebase 自愈，不该有任何红
        open(os.path.join(a, "dist", "ci_only.txt"), "w").write("ci\n")
        r = run([SHELL, "-e", PUSH_SH, "chore: 测试 源更新", "dist"], a, env)
        out = (r.stdout or "") + (r.stderr or "")
        check(r.returncode == 0, "b1) 基点旧了也不红（exit 0）", out[-300:])
        rl = git(["log", "--oneline", "main"], origin).stdout or ""
        check("chore: 测试 源更新" in rl, "b1) CI 的提交进了远端")
        check("chore: 本机探针先推" in rl, "b1) **本机探针的提交没被抹掉**")

        # b2) 真竞态：pull 与 push 之间被插队（pre-push 钩子里替「本机探针」推一把）
        #     -> 第 1 次必被拒 -> 重试第 2 次成功
        marker = os.path.join(tmp, "race-fired").replace(os.sep, "/")
        hook_log = os.path.join(tmp, "hook.log").replace(os.sep, "/")
        hook = os.path.join(a, ".git", "hooks", "pre-push")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        open(hook, "w", encoding="utf-8", newline="\n").write(
            "#!/bin/sh\n"
            "cat >/dev/null 2>&1 || true\n"
            "echo \"hook ran; marker=$( [ -f '%s' ] && echo yes || echo no )\" >> \"%s\"\n"
            "if [ ! -f \"%s\" ]; then\n"
            "  : > \"%s\"\n"
            "  # \u26a0 \u94a9\u5b50\u662f\u5728 `GIT_DIR=A/.git` \u7684\u73af\u5883\u91cc\u8dd1\u7684\uff1a\u4e0d unset \u7684\u8bdd\uff0c\n"
            "  #   `git -C B push` \u4e5f\u4f1a\u53bb\u63a8 A \u7684 ref\uff08\u5b9e\u6d4b\uff09\u2014\u2014 \u7ade\u6001\u5c31\u5047\u4e0d\u6210\u4e86\u3002\n"
            "  ( unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX; cd \"%s\" && git push -q origin main ) >> \"%s\" 2>&1\n"
            "  echo \"sneak rc=$?\" >> \"%s\"\n"
            "fi\n"
            "exit 0\n" % (marker, hook_log, marker, marker,
                          b.replace(os.sep, "/"), hook_log, hook_log))
        # ⚠ 插队那台机器的本地基点也必须先跟上当前 origin/main，
        #   否则它自己的推送先被拒（fetch first），竞态同样造不出来（实测）
        git(["pull", "-q", "--rebase", "origin", "main"], b)
        open(os.path.join(b, "race.txt"), "w").write("race\n")
        git(["add", "-A"], b)
        git(ID + ["commit", "-q", "-m", "chore: 本机探针插队"], b)
        open(os.path.join(a, "dist", "ci_race.txt"), "w").write("race\n")
        r = run([SHELL, "-e", PUSH_SH, "chore: 测试 撞车", "dist"], a, env)
        out = (r.stdout or "") + (r.stderr or "")
        hlog = ""
        if os.path.exists(hook_log):
            hlog = open(hook_log, encoding="utf-8", errors="replace").read()
        check(bool(hlog.strip()), "b2) pre-push 钩子真的跑了", hlog[-200:] or "没有 hook.log")
        check(r.returncode == 0, "b2) 撞车后仍然 exit 0", out[-400:])
        check("推送被拒（第 1 次" in out, "b2) 第 1 次真的被拒了（不是假竞态）",
              (out + " || 钩子日志: " + hlog)[-500:])
        check("第 2 次尝试" in out, "b2) 走了重试分支并成功",
              (out + " || 钩子日志: " + hlog)[-500:])
        rl = git(["log", "--oneline", "main"], origin).stdout or ""
        check("chore: 测试 撞车" in rl, "b2) CI 的提交进了远端")
        check("chore: 本机探针插队" in rl, "b2) **插队那台机器的提交也没被 force 掉**")
        n = len([x for x in rl.splitlines() if x.strip()])
        check(n == 5, "b2) 远端共 5 个提交（base+本机+CI+插队+CI）", "%d 个" % n)

        # c) 远端不可达 -> 3 次都失败 -> warning + exit 0，提交不丢、不留中间态
        git(["remote", "set-url", "origin", os.path.join(tmp, "nope.git")], a)
        open(os.path.join(a, "dist", "ci_fail.txt"), "w").write("fail\n")
        r = run([SHELL, "-e", PUSH_SH, "chore: 测试 失败路径", "dist"], a, env)
        out = (r.stdout or "") + (r.stderr or "")
        check(r.returncode == 0, "c) 三次都失败仍然 exit 0（不染红）", out[-300:])
        check("::warning::" in out, "c) 打了 ::warning:: 注解")
        check("第 3 次 / 共 3 次" in out, "c) 真的重试了 3 次", out[-300:])
        last = (git(["log", "-1", "--pretty=%s"], a).stdout or "").strip()
        check(last == "chore: 测试 失败路径", "c) 提交没丢（还在本地）", last)
        check(not os.path.isdir(os.path.join(a, ".git", "rebase-merge"))
              and not os.path.isdir(os.path.join(a, ".git", "rebase-apply")),
              "c) 没把仓库留在 rebase 中间态")
    except Exception as e:
        check(False, "6) 真跑过程没抛异常", "%s: %s" % (type(e).__name__, str(e)[:200]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 结果
print()
print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 \u2014\u2014 %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（CI 推送带重试、被拒能自愈、失败保守降级；workflow 里没有裸 git push）")
