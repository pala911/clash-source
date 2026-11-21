# -*- coding: utf-8 -*-
"""坏数据 / 写一半被杀：**不炸、不毁数据** 的 I/O 安全回归（§75 #10 / #11）。

## 为什么需要它

这两条都属于「低概率、后果不对称」的 I/O 缺陷：

  #10 `fetch.parse_proxies` 的列表分支原来只检查**首项**（`isinstance(cfg[0], dict)`）
      就把整个列表放行。上游给 `[{...}, "字符串", 42]` 时会一路流到 run.py 的
      `p.get("name")` -> AttributeError 把**整轮**炸掉 —— 一个源的问题
      变成所有源都没有产出。同类问题：`fetch_source` 的 docstring 写着
      「一个源坏掉只影响它自己」，但函数体里根本没有 try/except。

  #11 `probe.py` 的探针结果是**直写**（`json.dump(..., open(path, "w"))`）。
      写到一半被杀（预算到点 / 计划任务被结束 / 断电）会留下半截 JSON，
      而它正好覆盖掉上一轮的**好数据** —— 健康档案下一轮只能看到这个半截文件。

## 只看行为，不猜实现

  A 列表里混进非 dict     -> 只留 dict、不抛、错误文案说清首项类型
  B 列表里全是非 dict     -> 明确报错（不静默当空）
  C 畸形 src / 上游抛异常 -> fetch_source 兜住，返回 ([], meta.error)，绝不抛
  D 原子写正常路径        -> 内容正确、父目录自动创建、无 .tmp 残留
  E 写一半被杀（注入）    -> 旧文件**一个字节都没变**、.tmp 被清掉
"""
import io                         # noqa: E402
import json                       # noqa: E402
import os                         # noqa: E402
import sys                        # noqa: E402
import tempfile                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import fetch                      # noqa: E402
import probe                      # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                         ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


print("=" * 70)
print("A/B：上游给的列表里有非 dict（原来只查首项，会把整轮炸掉）")
print("=" * 70)
ok_a, err_a = fetch.parse_proxies(
    "- {name: a, server: 1.1.1.1}\n- 42\n- {name: b, server: 2.2.2.2}\n- null\n".encode("utf-8"))
check(ok_a is not None and [p.get("name") for p in ok_a] == ["a", "b"] and err_a is None,
      "混合列表 -> 只留 2 个 dict，不抛", "names=%s err=%r"
      % ([p.get("name") for p in (ok_a or [])], err_a))

ok_b, err_b = fetch.parse_proxies(b"- 42\n- [1, 2]\n")
check(ok_b is None and err_b and "首项类型 int" in err_b,
      "全非 dict -> 明确报错（说清首项类型）", "err=%r" % err_b)

ok_b2, err_b2 = fetch.parse_proxies(b"[]\n")
check(ok_b2 is None and err_b2 and "空列表" in err_b2,
      "空列表 -> 明确报错（不静默当空）", "err=%r" % err_b2)

print("")
print("=" * 70)
print("C：fetch_source 的兜底承诺（docstring 说过，代码里原来没有）")
print("=" * 70)
_orig = fetch.fetch


def _boom(*a, **k):
    raise RuntimeError("模拟上游给了一个畸形结构")


fetch.fetch = _boom
try:
    proxies, meta = fetch.fetch_source({"name": "x", "url": "https://example.invalid"}, timeout=1)
finally:
    fetch.fetch = _orig
check(proxies == [] and "兜住" in (meta.get("error") or ""),
      "上游抛异常 -> 返回 ([], error)，绝不往上抛", "error=%r" % (meta.get("error"),))

proxies2, meta2 = fetch.fetch_source("我是字符串不是 dict", timeout=1)
check(proxies2 == [] and meta2.get("error"),
      "src 本身不是 dict（配置手滑）-> 同样兜住", "error=%r" % (meta2.get("error"),))

print("")
print("=" * 70)
print("D/E：probe.save_json_atomic（写一半被杀不能毁掉上一轮的好数据）")
print("=" * 70)
_d = tempfile.mkdtemp(prefix="iosafe_")
_p = os.path.join(_d, "sub", "probe_latest.json")
probe.save_json_atomic(_p, {"a": 1, "中文": "✓", "sources": {"anaer": {"rate": 42.9}}})
check(json.load(open(_p, encoding="utf-8")) ==
      {"a": 1, "中文": "✓", "sources": {"anaer": {"rate": 42.9}}},
      "正常写入：内容正确（含中文/嵌套）+ 父目录自动创建")
check(not os.path.exists(_p + ".tmp"), "正常写入：没有 .tmp 残留")

_before = open(_p, "rb").read()
try:
    # "写一半" 的最真实模拟：先序列化出一部分，再在中间遇到不可序列化的对象
    probe.save_json_atomic(_p, {"a": 1, "long": "x" * 200, "boom": object()})
    check(False, "E 注入的失败必须真的抛出来（否则这个用例是假通过）")
except Exception as e:
    print("  （注入按预期失败：%s）" % type(e).__name__)
    _after = open(_p, "rb").read()
    check(_before == _after, "写一半被杀 -> 旧文件**一个字节都没变**",
          "%d bytes -> %d bytes" % (len(_before), len(_after)))
    check(not os.path.exists(_p + ".tmp"), "写一半被杀 -> .tmp 被清掉（不留垃圾）")

print("")
print("=" * 70)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（坏数据不炸 / 写一半不毁数据）")
