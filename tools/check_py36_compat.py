# -*- coding: utf-8 -*-
"""校验 ci_check_paste.py 只用了 Python 3.6 可用的特性。

云效公共构建集群实测是 Python 3.6.8，第一次提交就在这上面翻车：
`subprocess.run(capture_output=True)` 是 3.7+ 才有的，直接 TypeError，
看起来像"平台能力不足"其实是脚本自己的 bug —— 这种假阴性必须挡住。
"""
import ast
import sys

PATH = r"D:\work\agent\codebuddy\clash-source\tools\ci_check_paste.py"

# Python 3.7+ 的关键字参数（subprocess.run 等）
KW37 = {"capture_output", "text"}
# Python 3.6+ 支持（安全）
KW36_OK = {"encoding", "universal_newlines", "timeout", "stdout", "stderr",
           "stdin", "cwd", "env", "shell", "check", "input", "bufsize"}

src = open(PATH, encoding="utf-8").read()
tree = ast.parse(src)

bad = []
for n in ast.walk(tree):
    if isinstance(n, ast.keyword):
        if n.arg in KW37:
            bad.append("%s=  (3.7+)" % n.arg)
        elif n.arg and n.arg not in KW36_OK and not n.arg.isidentifier():
            bad.append("%s=  (未知关键字)" % n.arg)
    if hasattr(ast, "NamedExpr") and isinstance(n, ast.NamedExpr):
        bad.append("海象运算符 := (3.8+)")
    if isinstance(n, ast.JoinedStr):
        bad.append("f-string (3.6 可用，但本脚本统一用 %% 格式化)")

print("源码 %d 行，%d 字符" % (src.count("\n") + 1, len(src)))
if bad:
    print("⚠ 发现新版本特性: %s" % ", ".join(sorted(set(bad))))
    sys.exit(1)
print("✓ 未发现 Python 3.7+/3.8+ 特性，可在 3.6.8 上运行")

# 再确认没用到 subprocess.run 的新参数
import subprocess  # noqa: E402
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run":
        kws = {k.arg for k in n.keywords if k.arg}
        risky = kws & KW37
        if risky:
            print("  subprocess.run 使用了 3.7+ 参数: %s" % risky)
            sys.exit(1)
print("✓ subprocess.run 参数均在 3.6 兼容范围")