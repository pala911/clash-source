#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国内 CI 能力判定（粘贴版）—— 5 分钟决定这条路走不走得通。
只用标准库，整段粘进 CI 的脚本任务直接跑即可。

⚠ 第一关是「能不能 clone GitHub」，国内平台多半过不了。
   过不了也不用硬来：把仓库镜像到 Gitee/Codeup 是一条路，但维护成本翻倍。
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = "https://github.com/pala911/clash-source"
R = []


def chk(name, ok, note, fatal=True):
    R.append((name, ok, note, fatal))
    print("[%-4s] %-26s %s" % ({True: "PASS", False: "FAIL", None: "INFO"}[ok], name, note),
          flush=True)


def go(fn, *a, **k):
    t0 = time.time()
    try:
        return fn(*a, **k), time.time() - t0, None
    except Exception as e:
        return None, time.time() - t0, e


d = tempfile.mkdtemp()

# 1. 环境（用 shutil.disk_usage 而非 os.statvfs：后者只有 Unix 有）
du = shutil.disk_usage(d)
print("环境: %d 核 / 可用 %.1f GB / python %s"
      % (os.cpu_count() or 0, du.free / 1024 ** 3, sys.version.split()[0]))

# 2. 出网到境外（探针要连节点服务器的 IP:端口）
for host, port in [("1.1.1.1", 443), ("208.67.222.222", 443)]:
    def tc(h=host, p=port):
        socket.create_connection((h, p), timeout=8).close()
        return True
    v, dt, e = go(tc)
    chk("出网 %s:%d" % (host, port), None if v else False,
        "%.1fs" % dt if v else type(e).__name__)

# 3. 本地端口（mihomo 要监听）
def bind():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.listen(1)
    s.close()
    return p
v, dt, e = go(bind)
chk("监听本地端口", bool(v), "端口 %s" % v if v else type(e).__name__)

# 4. GitHub API（决定结果能否免代理写回）
def api():
    with urllib.request.urlopen(urllib.request.Request(
            "https://api.github.com/rate_limit", headers={"User-Agent": "x"}),
            timeout=20) as r:
        return r.status
v, dt, e = go(api)
chk("api.github.com", None if v else False,
    "HTTP %s（通=回传可免代理）" % v if v else "%s（需经 Codeup/Gitee 中转）" % type(e).__name__)

# 5. raw.githubusercontent（国内必墙，参考项）
def raw():
    with urllib.request.urlopen(urllib.request.Request(
            "https://raw.githubusercontent.com/pala911/clash-source/main/README.md",
            headers={"User-Agent": "x"}), timeout=15) as r:
        return r.status
v, dt, e = go(raw)
chk("raw.githubusercontent", None if v else False,
    "HTTP %s" % v if v else "不通（国内预期如此，正常）")

# 6. 决定性的一关：clone GitHub
if shutil.which("git") is None:
    chk("git 命令", False, "环境里没有 git")
else:
    def clone():
        p = subprocess.run(["git", "clone", "--depth", "1", REPO,
                            os.path.join(d, "c")],
                           capture_output=True, text=True, timeout=150)
        return p.returncode, (p.stderr or p.stdout)[-160:]
    v, dt, e = go(clone)
    if v is None:
        chk("clone GitHub 仓库", False, "%s（%.0fs）" % (e, dt))
    else:
        rc, out = v
        ok = (rc == 0) and os.path.isdir(os.path.join(d, "c", "src"))
        chk("clone GitHub 仓库", ok, "%.0fs" % dt if ok else out.replace("\n", " "))

print("=" * 58)
bad = [r for r in R if r[1] is False and r[3]]
if bad:
    print("结论：不建议在此平台部署（致命项失败 %d 个）" % len(bad))
    for n, _, note, _f in bad:
        print("   x %s —— %s" % (n, note))
    if any("clone" in n for n, _, _, _ in bad):
        print("\n   出路：把仓库镜像到 Codeup/Gitee 再从那里拉。")
        print("   但 mihomo 二进制（GitHub Release）同样拉不到，得另想办法，")
        print("   整体维护成本翻倍 —— 除非你本来就常用该平台，否则建议到此为止。")
else:
    print("结论：技术上可行。下一步看构建集群给几核、任务超时上限是多少。")
print("=" * 58)
shutil.rmtree(d, ignore_errors=True)
sys.exit(1 if bad else 0)