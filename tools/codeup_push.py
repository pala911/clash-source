# -*- coding: utf-8 -*-
"""把 ci_check_paste.py 推进 Codeup 空仓。

鉴权用 http.extraHeader(Authorization: Basic ...) 而不是把令牌写进 URL ——
写进 URL 会被存进 .git/config，且容易出现在进程列表/日志里。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
URL = "https://myxk-cn-shenzhen.devops.aliyuncs.com/codeup/ci-probe-test.git"
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"

# ⚠ HTTPS 克隆的凭据不是「个人访问令牌」—— 阿里云要求在 Codeup 个人设置里
#   **单独生成**「HTTPS 克隆账号密码」（实测：用 PAT 当密码会得到
#   「Https克隆账号或密码错误」）。所以这里读 codeup.https，不是 codeup.token。
#   文件格式：第一行用户名，第二行密码。
CRED_FILE = os.path.join(ROOT, "codeup.https")
if not os.path.exists(CRED_FILE):
    print("缺少 %s" % CRED_FILE)
    print("请在云效 Codeup 个人设置里生成「HTTPS 克隆账号密码」，然后写成两行：")
    print("    <用户名>")
    print("    <密码>")
    sys.exit(2)
_lines = [l.strip() for l in open(CRED_FILE, encoding="utf-8").read().splitlines() if l.strip()]
if len(_lines) < 2:
    print("%s 需要两行（用户名 / 密码），实际只有 %d 行" % (CRED_FILE, len(_lines)))
    sys.exit(2)
USER, PASSWD = _lines[0], _lines[1]

PROXY = ["-c", "http.proxy=http://127.0.0.1:7897",
         "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % HOST]

# 鉴权：把密码嵌进一次性 URL。
# 为什么不用别的方案（都实测过）：
#   · http.extraHeader  —— 走代理时不生效，git 直接弹凭据框被取消
#   · credential store  —— 临时凭据文件根本没被读取，报 could not read Username
# 嵌入 URL 的代价是密码会短暂出现在进程命令行里。已把 credential.helper 置空，
# 所以 git **不会**把它写进 .git/config 或凭据存储。一次性操作，可接受。
AUTH = ["-c", "credential.helper=", "-c", "core.askPass="]
AUTH_URL = "https://%s:%s@%s/codeup/ci-probe-test.git" % (USER, PASSWD, HOST)
# 不弹交互式密码框
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")

FILES = ["ci_check_paste.py"]

README = """# ci-probe-test

云效流水线的能力探针仓库（临时用途）。

在云效流水线的「脚本」步骤里运行：

    python3 ci_check_paste.py

它会输出一张判定表，最后一行是结论：
  结论：技术上可行        -> 可以继续部署真正的探针
  结论：不建议在此平台部署  -> 某项致命能力缺失，放弃

脚本只用 Python 标准库，不依赖任何东西。
"""


def run(args, cwd=None, timeout=180):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=ENV)
    out = (((p.stdout or "") + (p.stderr or "")).replace(PASSWD, "***").strip())
    return p.returncode, out


def main():
    work = tempfile.mkdtemp(prefix="codeup_push_")
    try:
        # 1) 先只读确认能不能访问
        rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", AUTH_URL], timeout=120)
        print("[1] ls-remote  exit=%d" % rc)
        if out:
            print("    " + out[:300].replace("\n", "\n    "))
        if rc != 0:
            print("\n鉴权仍失败，停止（不猜更多组合）。")
            return 1

        # 2) 组装要推的内容
        for name in FILES:
            shutil.copy2(os.path.join(ROOT, "tools", name), os.path.join(work, name))
        with open(os.path.join(work, "README.md"), "w", encoding="utf-8") as f:
            f.write(README)

        # 3) 初始化并提交
        for args in (["init", "-q"],
                     ["symbolic-ref", "HEAD", "refs/heads/master"],
                     ["config", "user.name", "probe-bot"],
                     ["config", "user.email", "probe-bot@users.noreply.github.com"],
                     ["add", "-A"]):
            rc, out = run([GIT] + args, cwd=work)
            if rc != 0:
                print("[3] %s 失败: %s" % (args[0], out[:200]))
                return 1
        rc, out = run([GIT, "commit", "-q", "-m",
                       "ci: 能力判定脚本（云效探路用）"], cwd=work)
        print("[3] commit exit=%d" % rc)
        if rc != 0:
            print("    " + out[:300])
            return 1

        # 4) 推
        run([GIT, "remote", "remove", "origin"], cwd=work)
        run([GIT, "remote", "add", "origin", URL], cwd=work)
        rc, out = run([GIT] + PROXY + AUTH + ["push", "-u", "origin", AUTH_URL, "master"],
                      cwd=work, timeout=300)
        print("[4] push exit=%d" % rc)
        if out:
            print("    " + out[:500].replace("\n", "\n    "))
        if rc != 0:
            return 1

        rc, out = run([GIT] + AUTH + ["ls-remote", "--heads", AUTH_URL], cwd=work)
        print("[5] 远端分支: %s" % (out.replace("\n", " ") or "(无)"))
        print("\n✓ 推送完成。接下来在云效流水线脚本步骤里跑这一行：")
        print("    python3 ci_check_paste.py")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

