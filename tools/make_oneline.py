# -*- coding: utf-8 -*-
"""把 ci_check_paste.py 打成一条可直接粘贴的单行命令（绕开云效 UI 的多行粘贴问题）。"""
import base64
import os

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_check_paste.py")
raw = open(RAW, "rb").read()
b = base64.b64encode(raw).decode()

# 两种写法，任选其一
v1 = "python3 -c \"import base64;exec(base64.b64decode('%s'))\"" % b
v2 = ("echo %s | base64 -d > /tmp/check.py && python3 /tmp/check.py" % b)

out = os.path.join(os.environ.get("TEMP", "."), "check_oneline.txt")
with open(out, "w", encoding="ascii") as f:
    f.write(v1 + "\n\n" + v2 + "\n")

print("源脚本      : %d 字节" % len(raw))
print("base64      : %d 字符" % len(b))
print("写法1 长度  : %d 字符" % len(v1))
print("写法2 长度  : %d 字符" % len(v2))
print("已写入      : %s" % out)
print()
print("=== 写法1 前 90 字符 ===")
print(v1[:90] + " ...")
print()
print("=== 写法2 前 90 字符 ===")
print(v2[:90] + " ...")