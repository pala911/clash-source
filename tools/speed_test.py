# -*- coding: utf-8 -*-
"""节点带宽实测（本机口径）—— 给「看高清视频」挑真正跑得动的节点。

## 为什么不能只看延迟

现有探针（src/probe.py）用 mihomo 的健康检查测的是 **HTTP 延迟/存活**，
不是吞吐。50ms 的节点完全可能只有 0.2 MB/s（2026-11-10 实测同源内
0.21 ~ 3.02 MB/s，差 14 倍）。高清视频要的是持续带宽：

    720p  ≈ 2.5 Mbps ≈ 0.3 MB/s
    1080p ≈ 5~8 Mbps ≈ 0.6~1.0 MB/s
    4K    ≈ 20~25 Mbps ≈ 2.5~3.1 MB/s

所以这里做**抽样真下载**：起一个独立 mihomo 实例，把候选节点改名成
`spd000…` 放进一个 select 组，逐个切过去，通过 mixed-port 下载固定字节，
算 MB/s。抽样而不是全量：700 个节点 × 2 MB = 1.4 GB，每天跑不现实。

## 用法

    python tools/speed_test.py                    # 每源 8 个，2 MB，写 state/speed_latest.json
    python tools/speed_test.py --per-source 12 --bytes 3000000
    python tools/speed_test.py --sources ssrsub,leilaomi
    python tools/speed_test.py --budget 480 --timeout 10   # 每日 12:30 链用的口径
    python tools/speed_test.py --dry-run          # 只看候选，不启动 mihomo
    python tools/speed_test.py --include-flaky    # 把 --flaky 池也纳入抽样

⚠ 这是**诊断工具**，不参与 22 道门禁，也不自动改订阅；结果文件
`state/speed_latest.json` 供后续「视频组」消费。测速会消耗真实流量
（默认约 50 节点 × 2 MB ≈ 100 MB），别在计费链路上高频跑。
"""
import argparse
import glob
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import node_stability as ns          # noqa: E402

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_MIHOMO = os.environ.get(
    "MIHOMO_BIN", r"C:\Program Files\Clash Verge\verge-mihomo.exe")
DEFAULT_TARGET = "https://speed.cloudflare.com/__down?bytes=%d"
API_PORT = int(os.environ.get("SPEED_API_PORT", "19100"))
MIXED_PORT = int(os.environ.get("SPEED_MIXED_PORT", "17900"))
SECRET = "speedtest-secret"
WORKDIR = os.path.join(ROOT, ".speedtest")
OUT = os.path.join(ROOT, "state", "speed_latest.json")


def load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(obj, path):
    import yaml
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, width=4096)


def load_candidates(nodes_dir, sources=None, include_flaky=False, per_source=8,
                    seed=20261110):
    """按源抽样候选节点。返回 [{source, name, server, fp, median_ms, uptime}]。

    抽样纪律（避免只看延迟挑出一堆「低延迟窄管道」）：
      · 一半取历史中位延迟最快的（视频首帧/拖动更跟手）
      · 一半从其余节点里确定性随机抽（带宽和延迟不相关，得给慢热节点机会）
      · 跨源按指纹去重（同一份配置只测一次）
      · 历史可用率 <30%（且样本 >=5 轮）的节点跳过，别把时间花在病秧子上
    """
    want = set(sources or [])
    files = []
    for path in sorted(glob.glob(os.path.join(nodes_dir, "*.yaml"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name in ("all", "mobile"):
            # mobile.yaml 是给 iOS 的合成池（从各源轮询取样），不是独立源；
            # 测它等于重复测各源节点，还会让「按源」统计失真。
            continue
        if name.endswith("--flaky") and not include_flaky:
            continue
        if want and name not in want:
            continue
        files.append((name, path))

    hist = (ns.load() or {}).get("nodes") or {}
    seen = set()
    out = []
    for source, path in files:
        proxies = (load_yaml(path).get("proxies") or [])
        pool = []
        for p in proxies:
            if not isinstance(p, dict) or not p.get("name"):
                continue
            fp = ns.fingerprint(p)
            if fp in seen:
                continue
            rec = hist.get(fp) or {}
            n = int(rec.get("n") or 0)
            up = int(rec.get("up") or 0)
            if n >= 5 and up / float(n) < 0.3:
                continue
            ms = ns.median_ms(rec) if rec else None
            pool.append({"source": source, "name": p.get("name"),
                         "server": str(p.get("server") or ""),
                         "fp": fp, "median_ms": ms,
                         "uptime": round(up / float(n), 3) if n else None,
                         "_p": p})
        if not pool:
            continue
        # 跨源去重必须在抽样前做：同一份配置在 A 源没被抽中、却在 B 源被抽中，
        # 说明它仍只该测一次（否则预算浪费在重复节点上，且统计会重复计数）。
        pool = [x for x in pool if x["fp"] not in seen]
        # 同源内也可能有完全重复的条目（不同 name、同配置），同样只留一个。
        uniq, local_seen = [], set()
        for x in pool:
            if x["fp"] in local_seen:
                continue
            local_seen.add(x["fp"])
            uniq.append(x)
        pool = uniq
        if not pool:
            continue
        # 历史延迟升序；没有历史数据的排后面（它们仍可能被随机抽到）
        pool.sort(key=lambda x: (x["median_ms"] is None,
                                 x["median_ms"] if x["median_ms"] is not None else 0,
                                 x["name"]))
        fast_n = min((per_source + 1) // 2, len(pool))
        picked = pool[:fast_n]
        rest = pool[fast_n:]
        rnd_n = min(per_source - len(picked), len(rest))
        if rnd_n > 0:
            rng = random.Random("%s|%s" % (seed, source))
            picked += rng.sample(rest, rnd_n)
        # 整个 pool 都记入 seen（不只是抽中的）：后面源里的同配置节点不必再测。
        for item in pool:
            seen.add(item["fp"])
        for item in picked:
            out.append(item)
    # 按源轮转，保证预算被掐断时每个源都测到一批，而不是前几个源吃满预算。
    by_src = {}
    for item in out:
        by_src.setdefault(item["source"], []).append(item)
    merged, i = [], 0
    while len(merged) < len(out):
        progressed = False
        for src in sorted(by_src):
            if i < len(by_src[src]):
                merged.append(by_src[src][i])
                progressed = True
        if not progressed:
            break
        i += 1
    return merged


def build_workdir(candidates, workdir=WORKDIR):
    """写临时 provider + mihomo 配置，返回 (config_path, renamed)。

    ⚠ 节点名在源之间可能重名（不同源都有 `US_01`），select 组按名字切换
      会切错。这里统一改名成 `spd000…`，原信息留在 renamed 里。
    """
    import yaml
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(os.path.join(workdir, "nodes"), exist_ok=True)
    renamed = []
    proxies = []
    for i, item in enumerate(candidates):
        p = dict(item["_p"])
        new_name = "spd%03d" % i
        p["name"] = new_name
        proxies.append(p)
        renamed.append({"idx": i, "test_name": new_name,
                        "source": item["source"], "name": item["name"],
                        "server": item["server"], "fp": item["fp"],
                        "median_ms": item["median_ms"],
                        "uptime": item["uptime"]})
    dump_yaml({"proxies": proxies}, os.path.join(workdir, "nodes", "speed.yaml"))
    cfg = {
        "mixed-port": MIXED_PORT, "allow-lan": False, "mode": "rule",
        "log-level": "warning", "ipv6": False,
        "external-controller": "127.0.0.1:%d" % API_PORT, "secret": SECRET,
        "dns": {"enable": True, "ipv6": False, "enhanced-mode": "fake-ip",
                "fake-ip-range": "198.18.0.1/16",
                "default-nameserver": ["223.5.5.5", "119.29.29.29"],
                "nameserver": ["223.5.5.5", "119.29.29.29"]},
        "proxy-providers": {"speed": {"type": "file",
                                      "path": "./nodes/speed.yaml"}},
        "proxy-groups": [{"name": "SPD", "type": "select", "use": ["speed"]}],
        "rules": ["MATCH,SPD"],
    }
    cpath = os.path.join(workdir, "speed.yaml")
    dump_yaml(cfg, cpath)
    return cpath, renamed


def _api(method, path, body=None, timeout=10):
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (API_PORT, path), method=method,
        headers={"Authorization": "Bearer " + SECRET,
                 "Content-Type": "application/json"},
        data=(json.dumps(body).encode() if body is not None else None))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def wait_api(seconds=20):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            _api("GET", "/version", timeout=2)
            return True
        except Exception:            # noqa: BLE001
            time.sleep(0.25)
    return False


def measure_one(test_name, target_url, timeout=12):
    """切到指定节点，下载一次，返回 (bytes, seconds, error)。"""
    try:
        _api("PUT", "/proxies/SPD", {"name": test_name})
    except Exception as e:           # noqa: BLE001
        return 0, 0.0, "切换节点失败: %s" % str(e)[:120]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(
        {"http": "http://127.0.0.1:%d" % MIXED_PORT,
         "https": "http://127.0.0.1:%d" % MIXED_PORT}))
    req = urllib.request.Request(target_url, headers={
        "User-Agent": "clash-source-speedtest/1.0",
        "Cache-Control": "no-cache"})
    t0 = time.perf_counter()
    try:
        with opener.open(req, timeout=timeout) as resp:
            data = resp.read()
        return len(data), time.perf_counter() - t0, None
    except Exception as e:           # noqa: BLE001
        return 0, time.perf_counter() - t0, "%s: %s" % (type(e).__name__,
                                                       str(e)[:120])


def summarize(results):
    ok = [r for r in results if r.get("mbps")]
    tiers = [
        ("4K (>=2.5 MB/s)", 2.5),
        ("1080p (>=0.6 MB/s)", 0.6),
        ("720p (>=0.3 MB/s)", 0.3),
    ]
    out = {}
    for label, need in tiers:
        out[label] = sum(1 for r in ok if r["mbps"] >= need)
    return out


def print_table(results, limit=20):
    print("")
    print("%-4s %-9s %-9s %-8s %-12s %s" %
          ("#", "MB/s", "Mbps", "延迟ms", "源", "节点"))
    print("-" * 96)
    for i, r in enumerate(results[:limit], 1):
        if r.get("error"):
            print("%-4d %-9s %-9s %-8s %-12s %s  ⚠ %s" % (
                i, "-", "-", r.get("median_ms") or "-", r["source"],
                str(r["name"])[:36], r["error"][:40]))
        else:
            print("%-4d %-9.2f %-9.1f %-8s %-12s %s" % (
                i, r["mbps"], r["mbps"] * 8,
                r.get("median_ms") or "-", r["source"], str(r["name"])[:36]))


def main():
    ap = argparse.ArgumentParser(description="节点带宽实测（本机口径）")
    ap.add_argument("--nodes", default=os.path.join(ROOT, "dist", "nodes"))
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--mihomo", default=DEFAULT_MIHOMO)
    ap.add_argument("--sources", default="",
                    help="逗号分隔的源名；空=全部（不含 --flaky）")
    ap.add_argument("--per-source", type=int, default=8,
                    help="每源抽样节点数（一半最快 + 一半随机）")
    ap.add_argument("--bytes", type=int, default=2_000_000,
                    help="每个节点下载字节数（默认 2 MB）")
    ap.add_argument("--timeout", type=float, default=12.0,
                    help="单节点下载超时秒数")
    ap.add_argument("--seed", type=int, default=20261110)
    ap.add_argument("--budget", type=float, default=420.0,
                    help="整轮墙钟预算（秒，默认 420）；超预算后剩余候选标记 skipped")
    ap.add_argument("--include-flaky", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只列候选，不启动内核")
    ap.add_argument("--keep", action="store_true", help="保留 .speedtest 工作目录")
    args = ap.parse_args()

    if not os.path.exists(args.mihomo):
        print("[speed] 找不到 mihomo：%s（用 --mihomo 或 MIHOMO_BIN 指定）"
              % args.mihomo)
        return 2
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    cands = load_candidates(args.nodes, sources=sources,
                            include_flaky=args.include_flaky,
                            per_source=args.per_source, seed=args.seed)
    if not cands:
        print("[speed] 没有可测候选（dist/nodes 为空或全被过滤）")
        return 1
    print("[speed] 候选 %d 个（每源上限 %d，%s）" %
          (len(cands), args.per_source,
           "含 --flaky" if args.include_flaky else "不含 --flaky"))
    by_src = {}
    for c in cands:
        by_src[c["source"]] = by_src.get(c["source"], 0) + 1
    print("[speed] 分布：%s" % "、".join("%s=%d" % kv for kv in sorted(by_src.items())))
    if args.dry_run:
        for c in cands:
            print("  %-12s %-40s %s" % (c["source"], str(c["name"])[:40],
                                        ("%dms" % c["median_ms"])
                                        if c["median_ms"] else "-"))
        return 0

    cpath, renamed = build_workdir(cands)
    r = subprocess.run([args.mihomo, "-t", "-f", cpath, "-d", WORKDIR],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=180,
                       creationflags=NOWIN)
    if r.returncode != 0:
        print("[speed] 配置校验失败：%s" % ((r.stdout or r.stderr)[-400:]))
        return 1

    logf = open(os.path.join(WORKDIR, "mihomo.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([args.mihomo, "-d", WORKDIR, "-f", cpath],
                            stdout=logf, stderr=subprocess.STDOUT,
                            creationflags=NOWIN)
    target = DEFAULT_TARGET % args.bytes
    results = []
    skipped = []
    started = time.perf_counter()
    try:
        if not wait_api():
            print("[speed] mihomo API 没起来，见 .speedtest/mihomo.log")
            return 1
        for i, item in enumerate(renamed):
            if args.budget > 0 and time.perf_counter() - started >= args.budget:
                # 预算掐断：剩下的原样记进 skipped（保留指纹），构建侧只认
                # results 里实测过的；skipped 用来解释「为什么这轮少了几个源」。
                skipped = [dict(x) for x in renamed[i:]]
                print("[speed] ⏱ 预算 %.0fs 用尽，跳过剩余 %d 个候选"
                      % (args.budget, len(skipped)))
                break
            print("[speed] %d/%d  %-12s %s" %
                  (i + 1, len(renamed), item["source"],
                   str(item["name"])[:44]), end="")
            nbytes, secs, err = measure_one(item["test_name"], target,
                                            timeout=args.timeout)
            mbps = (nbytes / secs / 1e6) if (secs > 0 and nbytes) else 0.0
            row = dict(item)
            row.pop("idx", None)
            row.pop("test_name", None)
            row.update({"bytes": nbytes, "seconds": round(secs, 3),
                        "mbps": round(mbps, 3), "error": err})
            results.append(row)
            print("  -> %s" % ("%.2f MB/s" % mbps if not err else "✗ " + err[:40]))
    finally:
        proc.kill()
        logf.close()
        time.sleep(0.5)
        if not args.keep:
            shutil.rmtree(WORKDIR, ignore_errors=True)

    for x in skipped:
        x.pop("idx", None)
        x.pop("test_name", None)
    results.sort(key=lambda x: (-(x.get("mbps") or 0),
                                x.get("median_ms") or 99999))
    doc = {
        "tested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "local",
        "target": target,
        "bytes": args.bytes,
        "timeout_s": args.timeout,
        "per_source": args.per_source,
        "budget_s": args.budget,
        "sources": sorted(by_src),
        # partial=True = 候选没测完（预算用尽/中途退出）；构建侧仍可用已测结果，
        # 但报告要能看出这轮不是全量。
        "partial": bool(skipped),
        "skipped": skipped,
        "summary": summarize(results),
        "results": results,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, args.out)
    print_table(results, limit=25)
    print("")
    for label, count in doc["summary"].items():
        print("  %-22s %d 个节点" % (label, count))
    print("")
    print("[speed] 结果 -> %s（实测 %d 个，失败 %d，跳过 %d%s）" %
          (args.out, len(results),
           sum(1 for x in results if x.get("error")), len(skipped),
           "，partial" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
