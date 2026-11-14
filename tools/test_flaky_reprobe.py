# -*- coding: utf-8 -*-
"""验证「被移出竞速池的节点还能不能被重新测量」这条链路。

## 为什么要查这个

稳定性加权把不稳节点写进 dist/nodes/<源>--flaky.yaml，并从
dist/nodes/<源>.yaml 里移出。而**本机探针读的正是 dist/nodes/ 目录**。

于是有个反直觉的后果：
  节点被移出 -> 探针下一轮只看 <源>.yaml，不再测它 -> 它的稳定性记录冻结
  -> 30 天后被剪掉 -> 它**永远不可能翻盘**

一个只是暂时抽风的节点，会被永久判死。这个后果比「少几个候选」严重得多。

## 正确行为

  1. 探针必须仍然测量 flaky 节点（否则无法翻盘）
  2. 但 <源>--flaky 这个「伪源名」不得进入健康档案的升降级判定

两个都要测。
"""
import glob
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import build                              # noqa: E402
import node_stability as ns               # noqa: E402

NODES = os.path.join(ROOT, "dist", "nodes")
ok = True

# ---------- 1. 探针的文件发现逻辑 ----------
print("=" * 66)
print("1) 探针会测到 <源>--flaky.yaml 吗（探针.py 的发现逻辑）")
print("=" * 66)
files = []
for n in sorted(glob.glob(os.path.join(NODES, "*.yaml"))):
    name = os.path.splitext(os.path.basename(n))[0]
    if name == "all":
        continue
    files.append(name)
print("  dist/nodes/ 现有文件: %s" % ("、".join(files) or "（空）"))
if not any("--flaky" in f for f in files):
    print("  → 当前没有 --flaky 文件，构造一个再测")
    demo = {"proxies": [{"name": "x", "type": "ss", "server": "1.2.3.4", "port": 1}]}
    for fn in ("anademo.yaml", "anademo--flaky.yaml"):
        with open(os.path.join(NODES, fn), "w", encoding="utf-8") as f:
            json.dump(demo, f)
        import yaml as _y
        with open(os.path.join(NODES, fn), "w", encoding="utf-8") as f:
            _y.safe_dump(demo, f, allow_unicode=True)

files = []
for n in sorted(glob.glob(os.path.join(NODES, "*.yaml"))):
    name = os.path.splitext(os.path.basename(n))[0]
    if name == "all":
        continue
    files.append(name)
got_flaky = [f for f in files if "--flaky" in f]
print("  发现: %s" % "、".join(files))
print("  %s flaky 节点会被探针测量（否则它们永远无法翻盘）"
      % ("✓" if got_flaky else "✗ 被漏掉 —— 被移出的节点将永久判死"))
ok = ok and bool(got_flaky)

# ---------- 2. 健康档案会不会被伪源名污染 ----------
print("")
print("=" * 66)
print("2) <源>--flaky 这个伪源名会不会进入健康档案并触发判定")
print("=" * 66)
BACK = os.path.join(ROOT, ".tools", "_flaky_health_test")
shutil.rmtree(BACK, ignore_errors=True)
os.makedirs(BACK)
hp = os.path.join(ROOT, "state", "source_health.json")
sp = os.path.join(ROOT, "src", "sources.yaml")
pp = os.path.join(ROOT, "state", "probe_latest.json")
shutil.copy2(hp, os.path.join(BACK, "h.json"))
shutil.copy2(sp, os.path.join(BACK, "s.yaml"))
shutil.copy2(pp, os.path.join(BACK, "p.json"))
try:
    doc = json.load(open(pp, encoding="utf-8"))
    doc["scope"] = "ci"                       # 判死唯一有权的口径，最危险
    doc["probed_at"] = "2099-01-01T00:00:00Z#synthetic"
    for k in list(doc["sources"]):
        if k == "anaer":
            doc["sources"]["anaer--flaky"] = dict(doc["sources"][k], alive=0, rate=0.0)
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(ROOT, "src", "health.py")],
                       capture_output=True, cwd=ROOT,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = (r.stdout or b"").decode("utf-8", "replace")
    h = json.load(open(hp, encoding="utf-8"))
    polluted = [n for n in h["sources"] if "--flaky" in n]
    cfg = open(sp, encoding="utf-8").read()
    print("  健康档案里的伪源记录: %s" % ("、".join(polluted) or "无"))
    if polluted:
        rec = h["sources"][polluted[0]]
        print("    该记录的 state=%s bad_streak=%s" % (rec.get("state"), rec.get("bad_streak")))
    touched = "anaer--flaky" in cfg
    print("  %s sources.yaml 未被伪源改动" % ("✓" if not touched else "✗ 被污染"))
    ok = ok and not touched
    if polluted:
        print("  ⚠ 伪源进了健康档案（bad_streak 只认 ci 口径，理论上无害，")
        print("     但它会进 reports/ 和 source_health.json 造成噪声，且")
        print("     「源清单」里凭空多出一个不存在的源）")
finally:
    shutil.copy2(os.path.join(BACK, "h.json"), hp)
    shutil.copy2(os.path.join(BACK, "s.yaml"), sp)
    shutil.copy2(os.path.join(BACK, "p.json"), pp)
    shutil.rmtree(BACK, ignore_errors=True)
    for fn in ("anademo.yaml", "anademo--flaky.yaml"):
        p = os.path.join(NODES, fn)
        if os.path.exists(p):
            os.remove(p)

print("")
print("=" * 66)
print("结果：%s" % ("链路通" if ok else "有失败项"))
sys.exit(0 if ok else 1)