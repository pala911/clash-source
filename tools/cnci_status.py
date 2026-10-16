# -*- coding: utf-8 -*-
"""看云效那层「回传主仓」到底通没通 —— 本地一条命令，不用翻流水线日志。

## 为什么需要这么个东西

`ci_push_main.py` 刻意永不失败（云效日志面板实测渲染不全，把流水线染红只会
掩盖真正的失败），所以「回传通没通」在云效那边**没有信号**。实测代价：
它从部署到被发现「一次都没真跑过」，中间隔了一天。

现在它每轮往 Codeup 仓的 `results/push_main_last.json` 落一份结果。
这个脚本 shallow-clone 一下就读出来，并和主仓的
`state/probe_cnci_latest.json` 对照，直接给结论：

    ✓ 回传正常        主仓的云效数据与 Codeup 最新一轮一致
    ⚠ 主仓落后了      这轮回传失败（看 status 里的原因）
    ⚠ 还没留痕过      云效那边还没跑过带留痕的版本

退出码：0 = 正常，1 = 回传不通/主仓落后，2 = 读不到（网络或凭据）。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = os.environ.get("GIT_BIN", "")
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"
RPATH = "codeup/ci-probe-test.git"
MAIN_LATEST = os.path.join(ROOT, "state", "probe_cnci_latest.json")

# 与 tools/ci_push_main.py 的 status_dir() 约定一致
STATUS_REL = "results/push_main_last.json"


def find_git():
    """本机没装系统 git，只有 portable-git（和 local_probe.py 的位置约定一致）。"""
    cand = [GIT, "git", r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"]
    for c in cand:
        if c and shutil.which(c):
            return shutil.which(c)
    return None


def load_creds():
    p = os.path.join(ROOT, "codeup.https")
    if not os.path.exists(p):
        return None
    lines = [ln.strip() for ln in open(p, encoding="utf-8").read().splitlines()
             if ln.strip()]
    if len(lines) < 2:
        return None
    return lines[0], lines[1]


def read_local_status():
    """读主仓里云效数据的时间戳（health.py 消费的那份）。"""
    try:
        with open(MAIN_LATEST, encoding="utf-8") as f:
            return (json.load(f) or {}).get("probed_at") or ""
    except Exception:
        return ""


def main():
    git = find_git()
    if not git:
        print("✗ 找不到 git（设 GIT_BIN=<git 绝对路径>）")
        return 2
    creds = load_creds()
    if not creds:
        print("✗ 缺 codeup.https（两行：登录账号 / 个人令牌）")
        print("  生成：python tools/codeup_auth.py")
        return 2
    u, p = creds
    url = "https://%s:%s@%s/%s" % (u, p, HOST, RPATH)

    tmp = tempfile.mkdtemp(prefix="cnci_status_")
    try:
        q = subprocess.run(
            [git, "-c", "credential.helper=", "-c", "core.askPass=",
             "clone", "--quiet", "--depth", "1", "--branch", "master", url,
             os.path.join(tmp, "r")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        if q.returncode != 0:
            out = (q.stdout or b"").decode("utf-8", "replace").replace(p, "***")
            print("✗ clone Codeup 失败：%s" % out.strip()[:200])
            print("  （云效 git 端点会间歇性 302 跳 SSO，稍后重试通常就好）")
            return 2
        repo = os.path.join(tmp, "r")

        st_path = os.path.join(repo, STATUS_REL.replace("/", os.sep))
        print("=" * 68)
        print("云效 -> 主仓 回传状态")
        print("=" * 68)
        if not os.path.exists(st_path):
            print("⚠ 还没有留痕（%s 不存在）" % STATUS_REL)
            print("  说明云效那边还没跑过「带留痕」的那版脚本。")
            print("  留痕是 2026-10-16 加的，第一轮应该是 10-17 04:23。")
            st = {}
        else:
            with open(st_path, encoding="utf-8") as f:
                st = json.load(f) or {}
            print("  跑的时刻   : %s" % st.get("at"))
            print("  这轮数据   : %s" % st.get("probe_cnci_at"))
            print("  结果       : %s" % ("✓ 成功" if st.get("ok") else "✗ 未成功"))
            print("  状态码     : %s" % st.get("status"))
            print("  通道       : %s" % (st.get("channel") or "（未走到任何通道）"))
            print("  说明       : %s" % st.get("detail"))
            print("  python     : %s" % st.get("py"))

        # Codeup 这边的结果文件
        res_dir = os.path.join(repo, "results")
        files = sorted(f for f in os.listdir(res_dir)
                       if f.startswith("probe_cnci_")) if os.path.isdir(res_dir) else []
        print("")
        print("  Codeup 里最新的探针存档: %s" % (files[-1] if files else "（无）"))
        print("  主仓里的云效数据时刻    : %s" % (read_local_status() or "（无）"))

        print("")
        verdict, rc = verdict_of(st, res_dir, files)
        print("  " + verdict)
        print("=" * 68)
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verdict_of(st, res_dir, files):
    newest = ""
    if files:
        try:
            with open(os.path.join(res_dir, files[-1]), encoding="utf-8") as f:
                newest = (json.load(f) or {}).get("probed_at") or ""
        except Exception:
            newest = ""
    local = read_local_status()
    if not st:
        return "⚠ 还没留痕过 —— 等云效跑一轮新版脚本再看", 1
    if not st.get("ok"):
        why = st.get("status") or "?"
        if why == "no-pat":
            return ("✗ 回传不通：云效流水线变量里没有 GH_PAT。\n"
                    "    去 云效 -> 流水线 -> 变量 加 GH_PAT（对 %s 有 Contents 写权限）"
                    % "pala911/clash-source"), 1
        return "✗ 回传不通（status=%s）：%s" % (why, st.get("detail")), 1
    if newest and local and newest > local:
        return ("⚠ 上一轮回传成功了，但主仓数据仍落后（Codeup %s > 主仓 %s）"
                % (newest, local)), 1
    return "✓ 回传正常：主仓的云效数据与 Codeup 最新一轮一致（%s）" % (local or "无"), 0


if __name__ == "__main__":
    sys.exit(main())
