#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 PyYAML 到底为什么装不上（上次把 pip 的真实报错截掉了，只看到 tail）。

⚠ Python 3.6。不用 capture_output / f-string / 海象运算符。
"""
import os
import subprocess
import sys
import time


def run(cmd, timeout=300):
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=timeout)
    return p.returncode, (p.stdout or ""), time.time() - t0


def show(tag, rc, out, dt, keep=1200):
    print("\n--- %s  exit=%d  %.1fs ---" % (tag, rc, dt))
    o = out.strip()
    if len(o) > keep:
        o = o[:keep // 2] + "\n   ...(中略)...\n" + o[-keep // 2:]
    print(o)


def main():
    print("python: %s" % sys.version.replace("\n", " "))
    print("pip: ")
    rc, out, dt = run([sys.executable, "-m", "pip", "--version"], 60)
    print("  %s" % out.strip())

    print("\n--- 当前 sys.path ---")
    for p in sys.path:
        print("  %s" % p)

    # 1) 三个镜像的可达性
    print("\n=== 镜像可达性 ===")
    for name, url in [("默认 PyPI", "https://pypi.org/simple/pyyaml/"),
                      ("清华", "https://pypi.tuna.tsinghua.edu.cn/simple/pyyaml/"),
                      ("阿里云", "https://mirrors.aliyun.com/pypi/simple/pyyaml/")]:
        import urllib.request
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pip"})
            with urllib.request.urlopen(req, timeout=25) as r:
                r.read(512)
            print("  [OK  ] %-10s %s  %.1fs" % (name, r.status, time.time() - t0))
        except Exception as e:
            print("  [FAIL] %-10s %s" % (name, str(e)[:70]))

    # 2) pip 安装（完整输出，不截断）
    print("\n=== pip install PyYAML（清华，完整输出）===")
    rc, out, dt = run([sys.executable, "-m", "pip", "install", "--user",
                       "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                       "PyYAML"], 420)
    show("pip --user 清华", rc, out, dt)

    # 3) 不带 --user
    print("\n=== pip install PyYAML（清华，不带 --user）===")
    rc, out, dt = run([sys.executable, "-m", "pip", "install",
                       "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                       "PyYAML"], 420)
    show("pip 清华", rc, out, dt, keep=800)

    # 4) 阿里云镜像
    if rc != 0:
        print("\n=== pip install PyYAML（阿里云镜像）===")
        rc, out, dt = run([sys.executable, "-m", "pip", "install", "--user",
                           "-i", "https://mirrors.aliyun.com/pypi/simple",
                           "PyYAML"], 420)
        show("pip --user 阿里云", rc, out, dt, keep=800)

    # 5) 最终验证 + --user 路径问题
    rc, out, dt = run([sys.executable, "-c", "import yaml; print('yaml', yaml.__version__)"], 60)
    print("\n=== 直接 import yaml ===")
    print("  exit=%d %s" % (rc, out.strip()[:200]))

    if rc != 0:
        print("\n=== 排查 --user 路径未进 sys.path ===")
        rc2, out2, _ = run([sys.executable, "-c",
                            "import site,sys;print(site.getusersitepackages());"
                            "print('ENABLE_USER_SITE=',site.ENABLE_USER_SITE)"], 60)
        print("  %s" % out2.strip().replace("\n", "\n  "))

    return 0


if __name__ == "__main__":
    sys.exit(main())