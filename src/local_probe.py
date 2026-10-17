# -*- coding: utf-8 -*-
"""本机（国内）真探针 —— 提供**可信口径**的质量数据，然后推回仓里。

为什么必须是「国内」（2026-10-14 实测校准；频率见第 3 点）：

  1) 国内口径不可替代。CI runner 在美国，同一批节点从美国看通过率系统性虚高
     1.8~13 倍，Spearman 秩相关只有 0.48，排名基本不可信：

         源            美国     国内     倍数    名次变化
         shaoyouvip   81.2%    6.2%    13.0x   #4  -> #11（垫底）
         yypool       84.3%   13.1%     6.4x   #2  -> #7
         anaer        78.6%   42.9%     1.8x   #5  -> #1（最好）

  2) 但国内口径**只能判优、不能判死**。从国内发起的 alive=0 是歧义的：
     节点真死了？或者它的 IP 被 GFW 阻断、我根本连不上？数据上一模一样。
     所以「降级」永远交给美国 CI（它能直连全球节点 IP）。
     —— 推论：**即使买台国内服务器，也只能把判优搬过去，判死仍得留在 CI。**

  3) 频率：计划任务是**每天 12:30**（2026-10-16 核对 schtasks）。
     早先（10-14）曾论证「每周一次足够」，理由是源质量是周/月尺度变量 ——
     但现在分级、AUTO 排序、节点稳定性档案全都吃本机口径的多轮均值，
     每天一轮才让这些数据保持新鲜；sni 修掉后全量一轮约 9 分钟，成本可忽略。

  4) **hc_timeout 一律保持 8000ms 默认值，别为了快调小**。
     它直接线性偏置 alive（shaoyouvip 实测：3s->0 活、8s->4 活、15s->6 活），
     调小等于批量制造假死亡。国内全量一轮约 9 分钟（2026-10-16 实测 8.7 分钟、
     12/12 源全测完）。真要省时间就用 `--sample 30`（实测 76 秒跑完 12 源且全部
     settle），那是「少测点」而不是「测得不实」。

用法：
    python src/local_probe.py                # 探针 + 健康档案 + 推回 GitHub
    （计划任务 \clash-source-local-probe 用 pythonw 直跑本脚本，无窗；
      run_local_probe.cmd 仅剩手动用途，效果相同）
    python src/local_probe.py --no-push      # 只探针，不推送
    python src/local_probe.py --scope-only   # 跳过探针，只把已有结果存档/推送

产出：state/probe_latest.json (scope=local) + state/source_health.json + reports/
"""
import argparse
import contextlib
import io
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"

# ⚠ pythonw（计划任务静默跑）下 sys.stdout/stderr 是 None，print 直接炸。
#   接到文件上：本脚本的 print 与子进程（probe.py 继承句柄）都落到这里。
if sys.stdout is None or sys.stderr is None:
    _d = os.path.join(ROOT, "logs")
    os.makedirs(_d, exist_ok=True)
    _f = open(os.path.join(_d, "local_probe_stdout.log"), "a",
         encoding="utf-8", buffering=1)   # 文本+行缓冲：print 写 str 才不炸
    sys.stdout = _f
    sys.stderr = _f
PROXY = "http://127.0.0.1:7897"          # github.com 直连被墙，push 必须走代理


def run_probe(args):
    """真探针。注意每次先清空装置目录 —— mihomo 的 -d 会残留上次文件。"""
    probe_dir = os.path.join(ROOT, ".probe")
    if os.path.isdir(probe_dir):
        shutil.rmtree(probe_dir, ignore_errors=True)
    env = dict(os.environ)
    env["PROBE_SCOPE"] = "local"
    # ⚠ 子进程 probe.py 没有守卫 —— 把父进程重定向后的句柄递给它，
    #   否则计划任务（pythonw）下子进程的 print 会直接炸掉整轮。
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "probe.py"),
         "--mihomo", args.mihomo, "--scope", "local",
         "--budget", str(args.budget),
         "--out", os.path.join(ROOT, "state", "probe_latest.json")],
        env=env, cwd=ROOT,
        stdout=sys.stdout, stderr=subprocess.STDOUT).returncode


def _nothing_to_commit(out):
    """git 的「无内容可提交」有两种措辞，漏挡一种就会把正常当失败。"""
    low = out.lower()
    return ("nothing to commit" in low
            or "no changes added to commit" in low
            or "working tree clean" in low)


def push_to_github():
    """把健康数据推回 main。CI 也会推 dist，两边并发时 push 会失败 -> rebase 重试。"""
    if not os.path.exists(GIT):
        print("[local] 未找到 portable-git，跳过推送: %s" % GIT)
        return 0
    stamp = time.strftime("%Y%m%d-%H%M")
    add = [GIT, "add", "-A", "state", "archive", "src/sources.yaml", "reports"]
    commit = [GIT, "-c", "user.name=local-probe-bot",
              "-c", "user.email=local-probe-bot@users.noreply.github.com",
              "commit", "-m", "chore: 本机探针(国内口径) %s" % stamp]
    push = [GIT, "-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
            "push", "origin", "main"]
    # ⚠ --autostash 是必需的（2026-10-15 实踩）：
    #   工作区只要有**未暂存**改动，`git pull --rebase` 就会直接拒绝
    #   （cannot pull with rebase: You have unstaged changes），
    #   于是「push 被拒 -> rebase -> 重试」的重试链必然二次失败，
    #   结果本地健康数据永远传不上去，而且日志里看不出真正原因。
    pull = [GIT, "-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
            "pull", "--rebase", "--autostash", "origin", "main"]
    for c in (add, commit):
        p = subprocess.run(c, cwd=ROOT, capture_output=True, text=True, timeout=180)
        out = (p.stdout + p.stderr).strip()
        if out:
            print("  " + out.splitlines()[-1][:150])
        # ⚠ git 说「没东西可提交」有两种措辞，少挡一种就会把正常情况当失败：
        #    nothing to commit, working tree clean          （连改动都没有）
        #    no changes added to commit (use "git add" ...) （有改动但没 add）
        # 2026-10-15 实踩：只挡了前一种，计划任务每轮都误报 exit=1。
        if p.returncode != 0 and not _nothing_to_commit(out):
            print("[local] 步骤失败: %s" % " ".join(c[:3]))
            return p.returncode
    p = subprocess.run(push, cwd=ROOT, capture_output=True, text=True, timeout=180)
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        # 最常见原因：CI 刚推过，远端领先 -> rebase 后重试一次
        pr = subprocess.run(pull, cwd=ROOT, capture_output=True, text=True, timeout=180)
        pout = (pr.stdout + pr.stderr).strip()
        if pr.returncode != 0:
            print("  rebase 失败: %s" % (pout.splitlines()[-1][:150] if pout else "?"))
        p = subprocess.run(push, cwd=ROOT, capture_output=True, text=True, timeout=180)
        out = (p.stdout + p.stderr).strip()
    print("  push: %s" % (out.splitlines()[-1][:150] if out else "OK"))
    if p.returncode != 0:
        print("[local] ⚠ 推送失败：本地数据仍在 state/，但远端不会更新。"
              "多半是代理(%s)没开或 PAT 过期。" % PROXY)
    return p.returncode


def main():
    ap = argparse.ArgumentParser(description="本机（国内口径）真探针，计划任务每天 12:30 跑")
    ap.add_argument("--no-push", action="store_true", help="只探针，不推回 GitHub")
    ap.add_argument("--scope-only", action="store_true",
                    help="跳过探针，只跑健康档案并推送（用已有的 probe_latest.json）")
    ap.add_argument("--mihomo", default=r"C:\Program Files\Clash Verge\verge-mihomo.exe")
    ap.add_argument("--budget", type=int, default=3600, help="探针墙钟预算（秒）")
    # ⚠ 3600 的由来：2026-10-17 中午轮实测，3549 节点在中午网络下
    #   1800 秒不够（autojiedian 744/868、yypool 741/900 未测完），
    #   而机器中午闲着 —— 宁可多给一小时，也别让大源掉出当日判定。
    args = ap.parse_args()

    oplog = os.path.join(ROOT, "logs", "local_probe.log")
    os.makedirs(os.path.dirname(oplog), exist_ok=True)

    def _oplog(msg):
        # 原 run_local_probe.cmd 的职责：往 local_probe.log 记 start/done。
        # 任务改 pythonw 直跑后 .cmd 不再参与，这里接手（格式保持一致）。
        with io.open(oplog, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y/%m/%d %H:%M:%S] ") + msg + "\n")

    _oplog("start local probe (scope=local)%s"
           % ((" " + " ".join(sys.argv[1:])) if sys.argv[1:] else ""))
    if not args.scope_only:
        print("[local] 本机真探针（scope=local，国内口径）…")
        if run_probe(args) != 0:
            print("[local] 探针失败，退出（不改动健康档案）")
            return 1
    else:
        print("[local] --scope-only：复用现有 state/probe_latest.json")

    print("[local] 健康档案（国内口径只判优/回收，判死留给 CI）…")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        subprocess.run([sys.executable, os.path.join(HERE, "health.py")], cwd=ROOT)
    for line in buf.getvalue().splitlines():
        print("  " + line)

    rc = 0
    if args.no_push:
        print("[local] --no-push，跳过推送")
    else:
        rc = push_to_github()
    _oplog("done, exit=%d" % rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())