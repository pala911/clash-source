# -*- coding: utf-8 -*-
"""硬化回归门禁：2026-10-19 §75 收尾剩余项 + 微项修复的守门员。

  1. run._prune_dist_stale —— 源消失后 dist/nodes、dist/raw 旧文件清理（微③）
  2. raw 快照 = 逐节点 dict(p) —— hard_filter 就地 clear/update 不得污染原貌（#5）
  3. ai_review._tpm_wait    —— need 超限额时放行并计数，绝不死循环（微②）
  4. ai_review.review_source —— 源级口径合同 + 墙钟预算闸门（#7 node 模式接线的
     依赖：run.py 阶段二将来把 node 模式整源一批交给它；键不齐/下标错位就会
     重演「报告审 0 剔 0」或误删越界）
"""
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import ai_review                        # noqa: E402
import filters                          # noqa: E402
import run as run_mod                   # noqa: E402

failures = []


def check(cond, msg):
    print("  %s %s" % ("✓" if cond else "✗", msg))
    if not cond:
        failures.append(msg)


# ---------- 1. dist 残留清理 ----------
print("1) _prune_dist_stale：删本轮不存在的源的旧快照")
d = tempfile.mkdtemp(prefix="prune_")
try:
    nodes_dir = os.path.join(d, "nodes")
    raw_dir = os.path.join(d, "raw")
    os.makedirs(nodes_dir)
    os.makedirs(raw_dir)
    for fn in ("a.yaml", "b.yaml", "a--flaky.yaml", "all.yaml", "notes.txt"):
        open(os.path.join(nodes_dir, fn), "w").close()
    for fn in ("a.yaml", "ghost.yaml"):
        open(os.path.join(raw_dir, fn), "w").close()
    run_mod._prune_dist_stale(d, {"a"})
    check(sorted(os.listdir(nodes_dir)) == ["a--flaky.yaml", "a.yaml", "all.yaml", "notes.txt"],
          "nodes 只认本轮源名（b 被删，all/--flaky(a)/非 yaml 保留）")
    check(sorted(os.listdir(raw_dir)) == ["a.yaml"],
          "raw 里 ghost（已消失的源）被删、a 保留")
    run_mod._prune_dist_stale(os.path.join(d, "no-such-dir"), {"a"})   # 缺目录不炸
    check(True, "dist 子目录不存在时静默跳过")
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---------- 2. raw 快照不得被就地清洗污染 ----------
print("2) raw 快照：hard_filter 就地清洗后，快照仍是原貌（#5）")
node = {"name": "hk-01", "type": "ss", "server": "1.2.3.4", "port": 443,
        "cipher": "aes-256-gcm", "password": "pw", "udp": "not a bool"}
snapshot = [dict(node)]                 # run.py 修复后的写法：逐节点浅拷贝
shared = [node]                         # 修复前的写法（共享引用）作对照
ok_f, why_f = filters.hard_filter(node, "")
check(ok_f and why_f == "", "带脏字段的节点应被清洗而非丢弃（str 塞 bool 字段 -> 丢字段）")
check("udp" not in node, "就地清洗生效（node 原 dict 已不含 udp）")
check(shared[0].get("udp") is None, "共享引用被污染复现了 #5 的原 bug 面")
check(snapshot[0].get("udp") == "not a bool", "dict(p) 快照保住了原貌")

# ---------- 3. TPM 闸门不挂死 ----------
print("3) _tpm_wait：need 超限额必须放行（微②）")
_tpm_backup = dict(ai_review._TPM)
try:
    ai_review._TPM["limit"] = 1
    ai_review._TPM["window"] = []
    ai_review._TPM["oversized"] = 0
    t0 = time.time()
    ai_review._tpm_wait(need=10)
    check(time.time() - t0 < 2.0, "need=10 > limit=1：立即返回（原先是 while True 死循环）")
    check(ai_review._TPM["oversized"] == 1, "oversized 已计数")
    check(ai_review.tpm_stats()["oversized"] == 1, "tpm_stats 暴露 oversized")
    ai_review._tpm_wait(need=0)          # need<=limit 且窗口为空：直接放行
    ai_review._TPM["limit"] = 0
    ai_review._tpm_wait(need=10)         # 闸门未启用：直接放行
    check(True, "limit<=0 与正常路径照常放行")
finally:
    ai_review._TPM.clear()
    ai_review._TPM.update(_tpm_backup)

# ---------- 4. review_source 源级合同 ----------
print("4) review_source：源级口径合同（#7 node 模式的地基）")
_re_call_http = ai_review._call_http
_deadline_old = ai_review._DEADLINE[0]
nodes = [{"name": "n%d" % i, "type": "ss", "server": "1.2.3.4", "port": 1000 + i}
         for i in range(5)]
_backends = {"backends": [{"_name": "fake"}], "_names": ["fake"]}
_calls = [0]


def _fake(chunk, soft_map, cfg, max_tokens=None):
    _calls[0] += 1
    return ({"drop": [{"n": 2, "why": "单元测试"}]}, "finish", {})


try:
    ai_review._call_http = _fake
    drops, stats = ai_review.review_source(
        nodes, {"n1": ["软标记样例"]}, "http", _backends, "t-source", lambda m: None)
    check(drops == [1], "返回排序后的**全局**节点下标（_drop_map 内 n=2 -> 下标 1）")
    check(stats.get("reviewed") == 5 and stats.get("dropped") == 1,
          "统一口径键 reviewed/dropped：审 5 剔 1（run.py/report 读的就是这俩）")
    check(stats.get("dropped_clusters") == 0, "源级没有簇概念，dropped_clusters 恒 0")
    dd = stats.get("drop_detail") or []
    check(len(dd) == 1 and dd[0].get("why") == "单元测试"
          and dd[0].get("name") == "n1", "逐条留痕 drop_detail 带节点名与理由")
    check(stats.get("rolled_back") is not True, "剔除 1/5 未触发整体回滚")
finally:
    ai_review._call_http = _re_call_http
    ai_review._DEADLINE[0] = _deadline_old

print("4b) review_source：墙钟预算耗尽时不再碰后端（node 模式的闸门）")
_deadline_old = ai_review._DEADLINE[0]
_calls[0] = 0
try:
    ai_review._call_http = _fake
    ai_review._DEADLINE[0] = time.time() - 100   # 预算已耗尽（set_time_budget 负数会被当作无预算，须直接置）
    drops, stats = ai_review.review_source(
        nodes, {}, "http", _backends, "t-budget", lambda m: None)
    check(drops == [], "预算耗尽 -> 0 剔除")
    check(stats.get("skipped_budget") is True, "stats 带上 skipped_budget（run.py 告警依赖这个键）")
    check(_calls[0] == 0, "一个后端都没被调（不是失败重试，是主动让路）")
finally:
    ai_review._call_http = _re_call_http
    ai_review._DEADLINE[0] = _deadline_old

print("")
print("结果：%s（%d 项失败）" % ("全部通过" if not failures else "有失败", len(failures)))
sys.exit(0 if not failures else 1)
