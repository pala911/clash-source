#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前置检查：能不能装上 mihomo + PyYAML？（判定脚本只测了网络，没测这两项）

mihomo 二进制是唯一可能翻盘的地方：
  GitHub Releases 在国内基本拉不到。如果镜像也拿不到，
  就只能把 22MB 的二进制塞进 Codeup 仓库（clone 时顺带带下来）。
所以这里把「镜像站」和「PyPI 镜像」一起测掉。

⚠ Python 3.6 兼容（云效集群实测 3.6.8）：
   不用 capture_output / f-string / 海象运算符。
"""
import subprocess
import sys
import time
import urllib.request

MIHOMO_VER = "v1.19.32"
MIRRORS = [
    ("官方 GitHub Releases",
     "https://github.com/MetaCubeX/mihomo/releases/download/%s/mihomo-linux-amd64-%s.gz"
     % (MIHOMO_VER, MIHOMO_VER)),
    ("gh-proxy 镜像",
     "https://gh-proxy.com/https://github.com/MetaCubeX/mihomo/releases/download/%s/mihomo-linux-amd64-%s.gz"
     % (MIHOMO_VER, MIHOMO_VER)),
    ("ghfast 镜像",
     "https://ghfast.top/https://github.com/MetaCubeX/mihomo/releases/download/%s/mihomo-linux-amd64-%s.gz"
     % (MIHOMO_VER, MIHOMO_VER)),
]

PYPI = [
    ("默认 PyPI", "https://pypi.org/simple/pyyaml/"),
    ("清华镜像", "https://pypi.tuna.tsinghua.edu.cn/simple/pyyaml/"),
]


def head(url, timeout=20, want_bytes=0):
    """抓前 want_bytes 字节并计时（HEAD 有些镜像不支持，用 GET 更可靠）。"""
    req = urllib.request.Request(url, headers={"User-Agent": "pre-check"})
    t0 = time.time()
    got = 0
    with urllib.request.urlopen(req, timeout=timeout) as r:
        code = r.status
        while got < (want_bytes or 1):
            b = r.read(65536)
            if not b:
                break
            got += len(b)
    return code, got, time.time() - t0


def run(cmd, timeout=180):
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - t0


def main():
    print("环境: python %s\n" % sys.version.split()[0])

    print("--- 1) mihomo 二进制（22MB）能不能拿到 ---")
    got_bin = False
    for name, url in MIRRORS:
        try:
            code, n, dt = head(url, timeout=40, want_bytes=3 * 1024 * 1024)
            print("  [OK  ] %-22s HTTP %s  已下 %.1f MB / %.1fs"
                  % (name, code, n / 1048576.0, dt))
            if n > 1024 * 1024:
                got_bin = True
        except Exception as e:
            print("  [FAIL] %-22s %s" % (name, e.__class__.__name__))
    if got_bin:
        print("  => 二进制可下载，无需把 22MB 塞进仓库")
    else:
        print("  => 二进制下载不通，必须把 mihomo 二进制提交进 Codeup 仓库")

    print("\n--- 2) PyYAML 能不能装 ---")
    good_pypi = None
    for name, url in PYPI:
        try:
            code, n, dt = head(url, timeout=25, want_bytes=2048)
            print("  [OK  ] %-12s HTTP %s  %.1fs" % (name, code, dt))
            good_pypi = name
        except Exception as e:
            print("  [FAIL] %-12s %s" % (name, e.__class__.__name__))

    print("\n--- 3) 实际 pip 安装测试 ---")
    idx = "-i https://pypi.tuna.tsinghua.edu.cn/simple" if good_piypi_ok(good_pypi) else ""
    rc, out, dt = run([sys.executable, "-m", "pip", "install", "-q", "--user",
                       "PyYAML"] + ([idx] if idx else []), timeout=240)
    print("  pip install PyYAML exit=%d  %.1fs" % (rc, dt))
    if rc != 0:
        print("  " + out.strip()[-300:])
    else:
        rc, out, dt = run([sys.executable, "-c",
                           "import yaml; print('yaml ok', yaml.__version__)"])
        print("  验证: %s" % out.strip()[-120:])

    print("\n--- 4) 子进程与内存（mihomo 带 400 节点要 300~600MB）---")
    try:
        rc, out, dt = run([sys.executable, "-c",
                           "import resource;print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)"])
        print("  进程内存: %s MB" % out.strip())
    except Exception as e:
        print("  读取失败: %s" % e)
    try:
        rc, out, dt = run(["free", "-m"], timeout=20)
        print("  " + (out or "").strip().replace("\n", " | ")[:160])
    except Exception:
        print("  free 命令不可用")

    print("\n" + "=" * 60)
    print("下一步取决于上面两行：")
    print("  二进制可下载 -> 直接部署，仓库不用改")
    print("  二进制不通   -> 需要我把 mihomo 二进制提交进 Codeup 仓库（+22MB）")
    return 0


def good_piypi_ok(name):
    return name is not None


if __name__ == "__main__":
    sys.exit(main())