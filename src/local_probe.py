# -*- coding: utf-8 -*-
"""本机（国内）真探针 —— 提供**可信口径**的质量数据，然后推回仓里。

为什么必须是「国内」而且为什么**只能每周一次**（2026-10-14 实测校准）：

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

  3) 为什么每周而不是每天。国内口径只服务两件事：回收判定 + 质量排名，
     而源的质量是**周/月尺度**变化的（今天 13% 活的源，下周不会自己变 40%，
     除非上游整体轮换）。真正的日频刚需是「节点新鲜度」，那是 CI 抓取在解决，
     与探针无关。所以每天探一遍是浪费，一周一次足够。

用法：
    python src/local_probe.py                # 探针 + 健康档案 + 推回 GitHub
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
PROXY = "http://127.0.0.1:7897"          # github.com 直连被墙，push 必须走代理


def run_probe(args):
    """真探针。注意每次先清空装置目录 —— mihomo 的 -d 会残留上次文件。"""
    probe_dir = os.path.join(ROOT, ".probe")
    if os.path.isdir(probe_dir):
        shutil.rmtree(probe_dir, ignore_errors=True)
    env = dict(os.environ)
    env["PROBE_SCOPE"] = "local"
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "probe.py"),
         "--mihomo", args.mihomo, "--scope", "local",
         "--budget", str(args.budget),
         "--out", os.path.join(ROOT, "state", "probe_latest.json")],
        env=env, cwd=ROOT).returncode


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
    pull = [GIT, "-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
            "pull", "--rebase", "origin", "main"]
    for c in (add, commit):
        p = subprocess.run(c, cwd=ROOT, capture_output=True, text=True, timeout=180)
        out = (p.stdout + p.stderr).strip()
        if out:
            print("  " + out.splitlines()[-1][:150])
        if p.returncode != 0 and "nothing to commit" not in out:
            print("[local] 步骤失败: %s" % " ".join(c[:3]))
            return p.returncode
    p = subprocess.run(push, cwd=ROOT, capture_output=True, text=True, timeout=180)
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        # 最常见原因：CI 刚推过，远端领先 -> rebase 后重试一次
        subprocess.run(pull, cwd=ROOT, capture_output=True, text=True, timeout=180)
        p = subprocess.run(push, cwd=ROOT, capture_output=True, text=True, timeout=180)
        out = (p.stdout + p.stderr).strip()
    print("  push: %s" % (out.splitlines()[-1][:150] if out else "OK"))
    return p.returncode


def main():
    ap = argparse.ArgumentParser(description="本机（国内口径）真探针，建议每周一次")
    ap.add_argument("--no-push", action="store_true", help="只探针，不推回 GitHub")
    ap.add_argument("--scope-only", action="store_true",
                    help="跳过探针，只跑健康档案并推送（用已有的 probe_latest.json）")
    ap.add_argument("--mihomo", default=r"C:\Program Files\Clash Verge\verge-mihomo.exe")
    ap.add_argument("--budget", type=int, default=1800, help="探针墙钟预算（秒）")
    args = ap.parse_args()

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

    if args.no_push:
        print("[local] --no-push，跳过推送")
        return 0
    return push_to_github()


if __name__ == "__main__":
    raise SystemExit(main())