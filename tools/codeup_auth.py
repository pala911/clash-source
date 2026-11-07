# -*- coding: utf-8 -*-
"""找出正确的 HTTPS 克隆凭据组合。

云效 Region 版(cn-shenzhen) 页面提示：「请使用登录账号 / 个人令牌进行克隆」。
=> 用户名 = **登录账号**（不是组织前缀 myxk），密码 = 个人令牌 或 登录密码。
"""
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"
PATH = "codeup/ci-probe-test.git"
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")
PROXY = ["-c", "http.proxy=http://127.0.0.1:7897",
         "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % HOST]
AUTH = ["-c", "credential.helper=", "-c", "core.askPass="]


def parse_kv(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*([^：:=]+)[：:=]\s*(\S+)\s*$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def mask(s):
    if len(s) <= 4:
        return s[0] + "*" * (len(s) - 1)
    if "@" in s:                      # 邮箱/账号：保留首尾
        a, b = s.split("@", 1)
        return (a[:2] + "*" * max(1, len(a) - 2)) + "@" + b[:2] + "*" * max(1, len(b) - 2)
    return s[:2] + "*" * (len(s) - 3) + s[-1]


kv = parse_kv(os.path.join(ROOT, "aliyun.token"))
login = kv.get("用户名") or kv.get("username") or kv.get("账号")
login_pw = kv.get("密码") or kv.get("password")
pat = open(os.path.join(ROOT, "codeup.token"), encoding="utf-8").read().strip()

print("登录账号(aliyun.key) : %s" % (mask(login) if login else "未找到"))
print("登录密码             : %s" % ("有 (%d 字符)" % len(login_pw) if login_pw else "无"))
print("个人令牌(codeup.token): %s (%d 字符)" % (pat[:3] + "***", len(pat)))
print()

combos = []
if login:
    combos.append(("登录账号 + 个人令牌", login, pat))
    if login_pw:
        combos.append(("登录账号 + 登录密码", login, login_pw))
combos.append(("组织前缀 myxk + 个人令牌", "myxk", pat))

ok = None
for label, u, p in combos:
    url = "https://%s:%s@%s/%s" % (u, p, HOST, PATH)
    r = subprocess.run([GIT] + PROXY + AUTH + ["ls-remote", url],
                       capture_output=True, text=True, timeout=120, env=ENV)
    out = ((r.stdout or "") + (r.stderr or "")).replace(p, "***").replace(login_pw or "\0", "***")
    good = r.returncode == 0
    print("[%s] %s" % ("OK  " if good else "FAIL", label))
    print("      exit=%d  %s" % (r.returncode, out[:180].replace("\n", " | ")))
    if good and ok is None:
        ok = (label, u, p)

if not ok:
    print("\n全部失败。若上面显示的是「令牌无效」，可能是令牌没勾选「代码仓库读」权限。")
    sys_exit = 1
else:
    label, u, p = ok
    cred = os.path.join(ROOT, "codeup.https")
    with open(cred, "w", encoding="utf-8", newline="\n") as f:
        f.write(u + "\n" + p + "\n")
    print("\n✓ 可用组合: %s" % label)
    print("已写入 %s（已在 .gitignore 的 *.https 规则内）" % cred)
    raise SystemExit(0)
raise SystemExit(1)
