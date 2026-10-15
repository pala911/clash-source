# -*- coding: utf-8 -*-
"""把 ci_check_paste.py 推进云效 Codeup 空仓。

之后流水线的脚本框里只需粘 `python3 ci_check_paste.py`（22 字符），
而不是 5.6KB 的 base64 单行。

鉴权（三种写法都实测过，这是唯一能通的）：
  · http.extraHeader=Authorization: Basic  -> 走代理时不生效，git 弹凭据框被取消
  · credential.helper=store --file=临时文件 -> 文件根本没被读取
                                              报 could not read Username
  · 凭据嵌进一次性 URL                        -> ✅ 可用
    代价是密码短暂出现在进程命令行。已把 credential.helper 置空，
    git 不会把它写进 .git/config 或凭据存储；并设 GIT_TERMINAL_PROMPT=0
    避免弹交互框卡死。

凭据来源：codeup.https（两行 = 登录账号 / 个人令牌）。
注意云效 Region 版页面提示「请使用登录账号 / 个人令牌进行克隆」——
用户名是**登录账号**，不是组织前缀 myxk（用 myxk 会得到
「Https克隆账号或密码错误」）。codeup_auth.py 负责自动试出可用组合。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"
RPATH = "codeup/ci-probe-test.git"
FILES = ["ci_check_paste.py"]

CRED_FILE = os.path.join(ROOT, "codeup.https")
if not os.path.exists(CRED_FILE):
    print("缺少 %s —— 先跑 python tools/codeup_auth.py 自动试出凭据组合" % CRED_FILE)
    sys.exit(2)
_lines = [l.strip() for l in open(CRED_FILE, encoding="utf-8").read().splitlines() if l.strip()]
if len(_lines) < 2:
    print("%s 需要两行（登录账号 / 个人令牌），实际 %d 行" % (CRED_FILE, len(_lines)))
    sys.exit(2)
USER, PASSWD = _lines[0], _lines[1]
AUTH_URL = "https://%s:%s@%s/%s" % (USER, PASSWD, HOST, RPATH)

PROXY = ["-c", "http.proxy=http://127.0.0.1:7897",
         "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % HOST]
AUTH = ["-c", "credential.helper=", "-c", "core.askPass="]
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")

README = """# ci-probe-test

云效流水线的能力探针仓库。

在云效流水线的「脚本」步骤里运行：

    python3 ci_check_paste.py

输出最后一行是结论：
  结论：技术上可行          -> 可以继续部署真正的探针
  结论：不建议在此平台部署  -> 某项致命能力缺失，放弃

脚本只用 Python 标准库。
"""


def run(args, cwd=None, timeout=180):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=ENV)
    out = (((p.stdout or "") + (p.stderr or "")).replace(PASSWD, "***").strip())
    return p.returncode, out


def show(tag, rc, out):
    print("[%s] %s exit=%d" % (tag, "OK  " if rc == 0 else "FAIL", rc))
    if out:
        print("    " + out[:400].replace("\n", "\n    "))


def main():
    work = os.path.join(tempfile.gettempdir(), "codeup_work")
    shutil.rmtree(work, ignore_errors=True)

    rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", AUTH_URL], timeout=120)
    show("1 ls-remote", rc, out)
    if rc != 0:
        return 1

    # clone 下来在其上提交：目标仓已有一个初始化提交，
    # 直接 git init 再推会撞 non-fast-forward。
    rc, out = run([GIT] + PROXY + AUTH + ["clone", AUTH_URL, work], timeout=300)
    show("2 clone", rc, out)
    if rc != 0:
        return 1

    for name in FILES:
        shutil.copy2(os.path.join(ROOT, "tools", name), os.path.join(work, name))
    with open(os.path.join(work, "README.md"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(README)

    for args in (["config", "user.name", "probe-bot"],
                 ["config", "user.email", "probe-bot@users.noreply.github.com"],
                 ["add", "-A"]):
        rc, out = run([GIT] + args, cwd=work)
        if rc != 0:
            show("3 %s" % args[0], rc, out)
            return 1

    rc, out = run([GIT, "commit", "-q", "-m", "ci: 能力判定脚本（云效探路用）"],
                  cwd=work)
    changed = "nothing to commit" not in out
    print("[3 commit] exit=%d %s" % (rc, "已提交" if changed else "无变化（已是最新）"))
    if rc != 0 and changed:
        print("    " + out[:300])
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["push", "origin", "HEAD:master"],
                  cwd=work, timeout=300)
    show("4 push", rc, out)
    if rc != 0:
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", "--heads", AUTH_URL])
    print("[5 远端分支] %s" % (out.replace("\n", " ") or "(无)"))
    print()
    print("✓ 推送完成。云效流水线的「脚本」步骤里跑这一行：")
    print("    python3 ci_check_paste.py")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())