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
延迟几十分钟），本机是固定 12:30 —— 两个时间窗天然会撞。

## 这个测试守什么

静态检查（因为要防的是「有人改 workflow 时又把重试去掉」）：

  1. workflow YAML 能解析（别改出语法错误）
  2. workflow 里**不许再有非 force 的 `git push`** —— 全部走 tools/ci_git_push.sh
  3. 三个步骤都真的调了那个脚本（数一下调用次数）
  4. 脚本本身必须有：重试循环 / pull --rebase --autostash / 绝不 --force /
     失败时 ::warning:: 且 exit 0（红会连带 skip 下游，代价比晚一轮大）

⚠ 为什么失败必须是 warning 而不是红：红 = 后面 9 步 skip = 手机订阅不更新 +
判死不执行。而提交还留在 workspace 里，后面的步骤推的时候会把它一起带上，
下一轮也会重算 —— 失败方向是「晚一轮」，不是「丢一轮」。
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


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                        ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


print("=" * 72)
print("1) workflow 文件能否解析")
print("=" * 72)
wfs = sorted(f for f in os.listdir(WF_DIR) if f.endswith((".yml", ".yaml")))
check(bool(wfs), "找到 workflow 文件", "、".join(wfs))
docs = {}
for f in wfs:
    p = os.path.join(WF_DIR, f)
    try:
        docs[f] = yaml.safe_load(open(p, encoding="utf-8").read())
        check(True, "%s 解析通过" % f)
    except Exception as e:
        check(False, "%s 解析通过" % f, str(e)[:160])

print()
print("=" * 72)
print("2) 不许再有裸 `git push`（非 force 的都算违规）")
print("=" * 72)
bare = []
forced = []
for f in wfs:
    for i, ln in enumerate(open(os.path.join(WF_DIR, f), encoding="utf-8"), 1):
        s = ln.strip()
        if s.startswith("#") or "git push" not in s:
            continue
        if re.search(r"git\s+push\s+(-\S*\s+)*-(f|-[a-z]*force)\b", s) or " --force" in s:
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

print()
print("=" * 72)
print("3) 三个推送步骤都走 %s" % PUSH_REL)
print("=" * 72)
main_wf = os.path.join(WF_DIR, "update.yml")
text = open(main_wf, encoding="utf-8").read()
calls = re.findall(r"bash\s+%s\s+\"([^\"]+)\"" % re.escape(PUSH_REL), text)
print("  调用点: %s" % (len(calls) or "0"))
for c in calls:
    print("      %s" % c)
check(len(calls) == 3, "产物 / 健康档案 / 候选池 三处都调了",
      "实际 %d 处" % len(calls))
for kw in ("源更新", "源健康档案", "新源候选池"):
    check(any(kw in c for c in calls), "提交信息里保留了「%s」" % kw)

print()
print("=" * 72)
print("4) 脚本必须带重试，且失败不许把流水线染红")
print("=" * 72)
check(os.path.exists(PUSH_SH), "%s 存在" % PUSH_REL,
      "推送步骤会引用它，文件不存在就是整步 fatal")
sh = open(PUSH_SH, encoding="utf-8").read() if os.path.exists(PUSH_SH) else ""
checks = [
    ("有重试循环（for i in 1 2 3）", "for i in 1 2 3" in sh),
    ("被拒后 pull --rebase --autostash 再推", "pull --rebase --autostash" in sh),
    ("绝不 force（防抹掉本机探针的提交）",
     "push --force" not in sh and "-f origin" not in sh),
    ("报错用 ::warning:: 而不是 exit 1", "::warning::" in sh),
    ("push 失败后 exit 0（不染红，避免连带 skip）",
     bool(re.search(r"::warning::[^\n]*\n\s*exit 0\s*$", sh))),
    ("路径不存在时 add 不 fatal", "2>/dev/null || true" in sh),
]
for label, ok in checks:
    check(ok, label)

print()
print("=" * 72)
print("5) bash 语法检查（有 bash 才跑）")
print("=" * 72)
cands = [os.path.join(ROOT, "..", "portable-git", "usr", "bin", "bash.exe"),
         os.path.join(ROOT, "..", "portable-git", "bin", "bash.exe"),
         shutil.which("bash")]
bash = next((c for c in cands if c and os.path.exists(c)), None)
if not bash:
    print("  （跳过：本机没找到 bash。CI 跑在 ubuntu-latest 上，那里一定有）")
else:
    r = subprocess.run([bash, "-n", PUSH_SH], capture_output=True, timeout=60)
    check(r.returncode == 0, "bash -n 语法通过",
          (r.stderr or b"").decode("utf-8", "replace")[:200])

print()
print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（CI 推送带重试、失败保守降级；workflow 里没有裸 git push）")
