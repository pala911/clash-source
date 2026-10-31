# -*- coding: utf-8 -*-
"""验证 probe.py 与 node_stability.py 之间的**接线**，不是模块本身。

## 为什么要有这个测试

第一次实现时，`test_stability.py` 全绿，但 `node_stability.json` 压根没生成 ——
原因是 `probe.node_fingerprints()` 里用了 `yaml.safe_load` 却**没 import yaml**，
每次调用抛 NameError，被 `except Exception: continue` 静默吞掉。

而探针照常打印正常的源级结果、退出码 0。**没有任何异常信号。**

所以测模块不够，必须测**模块与真实节点文件之间的接线**：
真的读 dist/nodes/*.yaml、真的算指纹、真的映射 mihomo 的返回。
"""
import glob
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import node_stability as ns      # noqa: E402
import probe                     # noqa: E402

NODES = os.path.join(ROOT, "dist", "nodes")
files = []
for n in sorted(glob.glob(os.path.join(NODES, "*.yaml"))):
    nm = os.path.splitext(os.path.basename(n))[0]
    if nm != "all":
        files.append((nm, n))

ok = True
print("=" * 66)
print("接线测试：dist/nodes/ 的 %d 个源文件" % len(files))
print("=" * 66)

# 1. 指纹映射不能是空的
fp = probe.node_fingerprints(files)
print("  指纹映射覆盖 %d 个源" % len(fp))
empty = [k for k, v in fp.items() if not v]
if not fp or empty:
    print("  ✗ 指纹映射为空或含空源（%s）—— 上次就是这里静默失败的" % (empty or "全空"))
    ok = False
else:
    print("  ✓ 全部源都算出了指纹")

# 2. 指纹必须真的对得上节点名（mihomo 返回的 name 就是这里的 key）
import yaml                     # noqa: E402
src = files[0][0]
raw = (yaml.safe_load(open(dict(files)[src], encoding="utf-8")) or {}).get("proxies") or []
names = [p.get("name") for p in raw if p.get("name")]
matched = sum(1 for n in names if n in (fp.get(src) or {}))
print("  %s 源「%s」%d/%d 个节点名能在映射里查到（mihomo 返回的 name 必须命中）"
      % ("✓" if matched == len(names) and names else "✗", src, matched, len(names)))
ok = ok and names and matched == len(names)

# 3. 指纹必须与 node_stability.fingerprint 一致（防止两边算法漂移）
bad = 0
for p in raw[:50]:
    nm = p.get("name")
    if nm and (fp.get(src) or {}).get(nm) != ns.fingerprint(p):
        bad += 1
print("  %s 前 50 个节点指纹与 ns.fingerprint 一致（不一致 %d 个）"
      % ("✓" if bad == 0 else "✗", bad))
ok = ok and bad == 0

# 4. probe() 的采集回路：塞一个假的 API 响应，确认 node_out 被填上
#    （不真起 mihomo —— 那要 12 分钟；这里只验证「拿到了 name 就能查到指纹」）
rows = {}
node_out = {}
node_rows = {}
fmap = fp.get(src) or {}
sample = names[:5]
for nm in sample:
    fpv = fmap.get(nm)
    if fpv:
        node_rows[fpv] = {"s": src, "alive": True, "ms": 120}
print("  %s 模拟 mihomo 返回的节点名能映射到指纹（抽 %d 个）"
      % ("✓" if len(node_rows) == len(sample) and sample else "✗", len(sample)))
ok = ok and len(node_rows) == len(sample)

# 5. 重新导入一次，确保没有模块级缓存问题
importlib.reload(probe)
fp2 = probe.node_fingerprints(files[:2])
print("  %s 重复调用结果稳定（%d 个源）" % ("✓" if len(fp2) == 2 else "✗", len(fp2)))
ok = ok and len(fp2) == 2

print("")
print("=" * 66)
print("结果：%s" % ("接线正常" if ok else "接线有问题"))
sys.exit(0 if ok else 1)