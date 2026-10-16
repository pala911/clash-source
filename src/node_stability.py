# -*- coding: utf-8 -*-
"""节点级稳定性档案 —— 填补 url-test 看不见的那一维。

## 为什么需要它

Clash 的 `url-test` 每 120 秒重测一次，按**此刻**的延迟选最快的。
它看不出两个节点的长期差别：

    节点甲：此刻 80ms，但一周只有 50% 的时间能用
    节点乙：200ms，但 99% 的时间能用

url-test 会一直选甲，因为它每次测都快。**「长期稳定性」是一个真实存在、
但当前完全空白的维度。**

探针本来就跑在每个节点的 `history` 上（probe.py 逐节点读 mihomo 的 history），
只是从来只汇总到源级就丢掉了。这一层把 per-node 结果留下来，
让 build 能按「可用率 + 典型延迟」而不是「此刻延迟」来决定谁进竞速池。

## ⚠ 为什么只记录 scope=local 的全量轮次

1. **抽样轮次只测了每源 30 个节点**，没被抽到的节点会被误记成「这一轮不可用」，
   把它们的可用率打下去。必须整轮丢弃。
2. **scope=ci 是美国视角**，衡量的是美国网络，不是用户的体验。
   混进来算出来的「稳定性」回答的是另一个问题。
3. **scope=cnci 是抽样**，同上，且机房视角。

所以：只有**本机全量**轮次会写入。频率是每天一次（12:30 计划任务），
攒够 MIN_ROUNDS 轮才开始参与权重计算。

## 节点身份：为什么不能用节点名

节点的 name 每天都在变 —— 国家标签会改、编号会重排
（实测见过 `BY_28` 这种序号型命名）。用 name 做键会导致每天全部错位，
可用率被清零重来。

指纹取的是**去掉 name 后的整份配置**的哈希：类型、服务器、端口、密码…
配置没变就是同一个节点，名字怎么改都不影响。

## 环境约束

云效集群是 Python 3.6.8：不能用 capture_output=/text=（3.7+）、
不碰海象运算符（3.8+）。本文件被 probe.py 连带 import，
而 probe.py 会在云效集群上跑 —— 所以这里也必须过 3.6 门禁。
"""
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STABILITY = os.path.join(ROOT, "state", "node_stability.json")

MIN_ROUNDS = 5          # 少于这么多轮，任何节点都算「样本不足」-> 不参与降权
MIN_UPTIME = 0.7        # 可用率低于此值 -> 判为不稳
KEEP_MS = 8             # 每个节点保留最近多少个存活延迟（算中位数用）
KEEP_DAYS = 30          # 超过这么久没出现的节点丢弃


def fingerprint(proxy):
    """节点指纹：整份配置去掉 name 后的 sha1 前 12 位。"""
    d = {k: v for k, v in (proxy or {}).items() if k != "name"}
    try:
        blob = json.dumps(d, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        blob = repr(sorted(d.items()))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def load(path=STABILITY):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {"version": 1, "nodes": {}}


def save(data, path=STABILITY):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _median(xs):
    s = sorted(xs)
    if not s:
        return None
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def merge(records, scope="local", path=STABILITY, today=None):
    """把一轮 per-node 结果并进档案。records: {fp: {"s":源, "alive":bool, "ms":int}}。

    返回 (写入的节点数, 跳过原因)。**不抛异常** —— 稳定性档案是辅助功能，
    写坏了不该让整轮探针失败。
    """
    if scope != "local":
        return 0, "非本机口径（%s），不写入稳定性档案" % scope
    if not records:
        return 0, "没有 per-node 数据"
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    data = load(path)
    nodes = data.setdefault("nodes", {})
    n = 0
    for fp, r in records.items():
        rec = nodes.get(fp) or {"s": r.get("s"), "n": 0, "up": 0, "ms": [], "t": today}
        # 源变了（同名不同内容）就重开档案，否则会把两个源的可用率混起来
        if rec.get("s") and r.get("s") and rec["s"] != r["s"]:
            rec = {"s": r["s"], "n": 0, "up": 0, "ms": [], "t": today}
        rec["n"] = rec.get("n", 0) + 1
        if r.get("alive"):
            rec["up"] = rec.get("up", 0) + 1
            if r.get("ms"):
                ms = rec.setdefault("ms", [])
                ms.append(int(r["ms"]))
                del ms[:-KEEP_MS]
        rec["t"] = today
        nodes[fp] = rec
        n += 1
    # 剪掉久未出现的
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - KEEP_DAYS * 86400))
    stale = [k for k, v in nodes.items() if (v.get("t") or "") < cutoff]
    for k in stale:
        del nodes[k]
    data["version"] = 1
    data["updated"] = today
    data["scope"] = "local"
    data["pruned"] = len(stale)
    save(data, path)
    return n, "已并入 %d 个节点（剪掉 %d 个超过 %d 天未出现的）" % (n, len(stale), KEEP_DAYS)


def verdict(fp_rec):
    """给一个节点记录定性。

    返回 (ok, reason)：
      ok=True   -> 稳，可以用
      ok=False  -> 不稳或样本不足，build 应把它移出竞速池
    样本不足（n < MIN_ROUNDS）时返回 False 是**故意的**：
    对未知节点保持谨慎，而不是假装它稳。
    """
    if not fp_rec:
        return False, "无历史"
    n = fp_rec.get("n", 0)
    up = fp_rec.get("up", 0)
    if n < MIN_ROUNDS:
        return False, "样本不足（%d/%d 轮）" % (n, MIN_ROUNDS)
    ut = up / float(n)
    if ut < MIN_UPTIME:
        return False, "可用率 %.0f%%（%d/%d）低于 %.0f%%" % (
            ut * 100, up, n, MIN_UPTIME * 100)
    return True, "可用率 %.0f%%（%d/%d）" % (ut * 100, up, n)


def median_ms(fp_rec):
    return _median(fp_rec.get("ms") or [])


def stats(nodes=None, path=STABILITY):
    """给 build / 报告用的一次性汇总。"""
    nodes = nodes if nodes is not None else load(path).get("nodes", {})
    stable = flaky = unknown = 0
    for fp in nodes:
        ok, _ = verdict(nodes[fp])
        if ok:
            stable += 1
        elif nodes[fp].get("n", 0) < MIN_ROUNDS:
            unknown += 1
        else:
            flaky += 1
    return {"total": len(nodes), "stable": stable, "flaky": flaky, "unknown": unknown}