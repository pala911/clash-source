# -*- coding: utf-8 -*-
"""验证 make_oneline.py 产出的单行命令真的能跑（别交付没验过的东西）。

本机是 Windows、没有 python3，所以把 python3 替换成 python 再执行 ——
解码/执行逻辑与 Linux 上完全一致，只是解释器名不同。
"""
import os
import subprocess
import sys

TEMP = os.environ.get("TEMP", ".")
src = os.path.join(TEMP, "check_oneline.txt")
lines = [l for l in open(src, encoding="ascii").read().splitlines() if l.strip()]

for name, line in zip(("写法1 exec(base64)", "写法2 base64 -d"), lines[:2]):
    cmd = line.replace("python3 ", "%s " % sys.executable + "", 1)
    cmd = cmd.replace("python3 ", "\"%s\" " % sys.executable)
    print("=" * 60)
    print(name, "| 命令长度", len(cmd))
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if l.strip()][-5:]
    for l in tail:
        print("   " + l)
    print("   -> exit=%d" % r.returncode)