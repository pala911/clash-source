# -*- coding: utf-8 -*-
"""所有会跑到云效集群的文件，按 Python 3.6 规则做静态门禁。

为什么需要这道门禁（同一个坑踩了三次）：
  云效公共构建集群是 **Python 3.6.8**。三次栽在版本不兼容上：
    1) ci_check_paste.py 用了 capture_output=（3.7+）—— 报「unexpected keyword
       argument」，看起来像"平台能力不足"，其实是脚本自己的锅
    2) ci_preflight.py 一行末尾漏了右双引号 —— 报「EOL while scanning string
       literal」，同样是本机 3.11 完全正常、只有真机才炸
    3) **probe.py 也用了 capture_output=** —— 而第一版的门禁只扫 tools/ci_*.py，
       根本没扫从主仓拷过去的 probe.py，于是第三次漏网
       ⚠ 教训：门禁的**覆盖范围**本身就是 bug 源。改了文件清单要一起改门禁。

覆盖范围（= 会被推送到 Codeup 并在集群上执行的每一个 .py）：
    tools/ci_*.py    自带脚本
    src/probe.py     真探针主程序
    src/health.py    健康档案（虽然 cnci 口径不触发变更，但它随仓库一起推）
    src/node_stability.py   节点级稳定性档案
    tools/yaml_vendor/yaml/*.py    vendor 的第三方 PyYAML

⚠ 被 import 的模块同样要扫：probe.py 会 import node_stability，
  所以它在云效集群上也会被执行。只扫「直接跑」的入口会漏掉这类依赖
  （这和第一版漏掉 probe.py 是同一类错误）。
"""
import ast
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KW37 = {"capture_output", "text"}
PY36_TARGET = (3, 6)


def targets():
    out = sorted(glob.glob(os.path.join(HERE, "ci_*.py")))
    for n in ("probe.py", "health.py", "node_stability.py",
              "fetch.py", "filters.py"):
        p = os.path.join(ROOT, "src", n)
        if os.path.exists(p):
            out.append(p)
    # vendor 的第三方 PyYAML 在 .tools/yaml_vendor/（不在 tools/ 下）——
    # 这个路径一开始写错、导致门禁漏扫，等于没有这道门禁。
    out += sorted(glob.glob(os.path.join(ROOT, ".tools", "yaml_vendor", "yaml", "*.py")))
    return out


def check(path):
    src = open(path, encoding="utf-8").read()
    problems = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        line = src.splitlines()[e.lineno - 1] if e.lineno <= len(src.splitlines()) else ""
        return ["语法错误 L%d %s | 该行双引号 %d 个(应为偶数): %s"
                % (e.lineno, e.msg, line.count('"'), line.strip()[:70])]
    for n in ast.walk(tree):
        if isinstance(n, ast.keyword) and n.arg in KW37:
            problems.append("Python 3.7+ 参数 %s=（集群是 3.6，会 TypeError）" % n.arg)
        if hasattr(ast, "NamedExpr") and isinstance(n, ast.NamedExpr):
            problems.append("海象运算符 :=（3.8+）")
        if isinstance(n, ast.JoinedStr):
            problems.append("f-string（3.6 可用，但与本项目 %% 格式化风格不一致）")
    return problems


def main():
    ts = targets()
    print("按 Python %d.%d 规则检查 %d 个文件"
          % (PY36_TARGET[0], PY36_TARGET[1], len(ts)))
    bad = 0
    for p in ts:
        probs = check(p)
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if probs:
            bad += 1
            print("\n  [FAIL] %s" % rel)
            for x in probs:
                print("         x %s" % x)
        else:
            print("  [OK  ] %-34s %d 行"
                  % (rel, len(open(p, encoding="utf-8").read().splitlines())))
    print()
    print("结果：%s" % ("全部通过" if not bad else "%d 个文件有问题" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())