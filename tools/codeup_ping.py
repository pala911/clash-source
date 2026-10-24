# -*- coding: utf-8 -*-
"""验证 Codeup 仓库可达性 + 令牌鉴权方式（不打印令牌本身）。"""
import base64
import os
import subprocess
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOKEN = open(os.path.join(ROOT, "codeup.token"), encoding="utf-8").read().strip()
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
URL = os.environ.get("REPO_URL", "https://myxk-cn-shenzhen.devops.aliyuncs.com/codeup/ci-probe-test.git")

host = URL.split("//", 1)[1].split("/")[0]
print("仓库: %s" % URL)
print("主机: %s" % host)

# 1) 主机可达性（不带鉴权，看是 401/404/403 还是根本不通）
for scheme in ("https",):
    try:
        req = urllib.request.Request("%s://%s/" % (scheme, host))
        with urllib.request.urlopen(req, timeout=20) as r:
            print("  HTTP %s （未鉴权竟能访问？）" % r.status)
    except urllib.error.HTTPError as e:
        print("  HTTP %s %s" % (e.code, "（说明主机活着，需要鉴权）"
                               if e.code in (401, 403, 404) else ""))
    except Exception as e:
        print("  连接失败: %s" % str(e)[:100])

# 2) git ls-remote，分别试三种鉴权写法
combos = [
    ("token as password, 固定用户名", "oauth2:%s" % TOKEN),
    ("token 直接当用户名+密码", "%s:%s" % (TOKEN, TOKEN)),
    ("用户名=token，密码空", "%s:" % TOKEN),
]
for label, cred in combos:
    enc = base64.b64encode(cred.encode()).decode()
    p = subprocess.run(
        [GIT, "-c", "http.proxy=http://127.0.0.1:7897",
         "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % host,
         "-c", "http.extraHeader=Authorization: Basic %s" % enc,
         "ls-remote", URL],
        capture_output=True, text=True, timeout=90)
    out = ((p.stdout or "") + (p.stderr or "")).strip().replace(TOKEN, "***")
    ok = p.returncode == 0
    print("\n  [%s] %s" % ("OK  " if ok else "FAIL", label))
    print("       exit=%d  %s" % (p.returncode, out[:200].replace("\n", " | ")))