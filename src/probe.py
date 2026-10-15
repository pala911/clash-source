# -*- coding: utf-8 -*-
"""真探针：在流水线里用 mihomo 内核跑 youtube 探针，给每个源打可用性分数。

为什么要它：源的价值只能用**真探针**判定（记忆坑 §4/§5：README 说的"测速筛选"不可信，
Au1rxx 自测只保 TCP 存活、1745 个节点只有 2 个能穿 youtube）。

⚠ 口径警告（重要）：CI runner 在**美国**。mahdibland 的教训（坑 §40）——美机测速筛出的
200 个节点，国内 youtube 0% 通过。所以本模块的分数只能用来判「**是否彻底死了**」，
不能用来横向比「哪个源更好」。因此 health.py 的降级门槛设得很保守。

⚠ 三条会悄悄毁掉数据的参数纪律（2026-10-15 全部实测踩过）：

  1) **不能只看 rate 就相信数据**。
     yypool 只测了 5.1% 就退出时报 rate=13.0%，全量真值 13.1% —— 几乎一模一样，
     但 alive 报 6、真值 118（差 20 倍）。因为 health.py 的「变好」判据是 alive>=5，
     alive 低估会让好源看起来变差 -> good_streak 被清零 -> 回收永不触发。
     **这种 bug 只看通过率是发现不了的。** 所以每源都有 settled 标记，未测完不参与判定。

  2) **hc_timeout 是决定性参数，直接线性偏置 alive**。shaoyouvip 单源实测：
         2s/3s -> 0 活      5s -> 1 活      8s -> 4 活      15s -> 6 活
     （它 41/46 是明文 HTTP 代理 + 1 个域名节点，响应很慢）
     为了省钱把它调小 = **批量制造假死亡**。默认一律 8000ms，
     需要变时 health.py 会检测到并清空 streak（前后口径不可比）。

  3) **国内跑慢是因为 GFW 丢 SYN，不是机器慢**。连不上的境外 IP 会被丢包挂起，
     每个死节点要等满 hc_timeout；美国则是立刻 RST。
     —— 所以「让国内 CI 跑得更快」的正确解法是**抽样（--sample）**，不是调小超时。
     实测：全量 3577 节点要 293s，而抽样 30/源只要 76s（12 源全部 settle）。

产出：state/probe_latest.json（每源 nodes/tested/alive/rate/best_ms/settled）
"""
import collections
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

API_PORT = int(os.environ.get("PROBE_API_PORT", "19099"))
MIXED_PORT = int(os.environ.get("PROBE_MIXED_PORT", "17899"))
SECRET = "probe-secret"

# 双口径（2026-10-14 用户选定）：
#   YOUTUBE = 真实出墙能力（= 业务可用性）。**CI runner 在美国，口径会系统性偏高**：
#     实测 ssrsub CI 90% vs 国内 45.6%、autojiedian CI 88% vs 国内 ~12%
#     —— 境内中转节点从美国绕一圈也能到 youtube，所以 CI 只能判「是否彻底死了」。
#   CN_PROBE = 国内可达性。CI 上必然大面积失败（它在美国），但用于**自检**：
#     若某源 cn_alive 高得离谱，说明探针口径/网络有问题，不该拿它下结论。
# 本机跑（国内网络）时 cn_alive 才有意义 —— 健康档案的质量判据只信本机。
YOUTUBE = "https://www.youtube.com/generate_204"
CN_PROBE = "https://www.gstatic.com/generate_204"


def api_get(port, path, timeout=25):
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path),
        headers={"Authorization": "Bearer " + SECRET})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def build_config(node_files, workdir, health_check_timeout=8000):
    """node_files: [(provider_name, abs_yaml_path)] —— 必须先拷进 workdir（mihomo 限制）。"""
    providers, groups = {}, []
    types = {}
    os.makedirs(os.path.join(workdir, "nodes"), exist_ok=True)
    for name, src in node_files:
        dst = os.path.join(workdir, "nodes", name + ".yaml")
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
        providers[name] = {
            "type": "file", "path": "./nodes/%s.yaml" % name,
            "health-check": {"enable": True, "url": YOUTUBE, "interval": 300,
                             "timeout": health_check_timeout, "expected-status": 204},
        }
        groups.append({"name": "EV-%s" % name, "type": "url-test", "use": [name],
                       "url": YOUTUBE, "interval": 3600, "timeout": 4000,
                       "tolerance": 50, "lazy": False})
        types[name] = None      # 占位，稍后从本地文件读类型映射
    cfg = {
        "mixed-port": MIXED_PORT, "allow-lan": False, "mode": "rule",
        "log-level": "warning", "ipv6": False,
        "external-controller": "127.0.0.1:%d" % API_PORT, "secret": SECRET,
        "dns": {"enable": True, "ipv6": False, "enhanced-mode": "fake-ip",
                "fake-ip-range": "198.18.0.1/16",
                "default-nameserver": ["223.5.5.5", "119.29.29.29"],
                "nameserver": ["223.5.5.5", "119.29.29.29"]},
        "proxy-providers": providers, "proxy-groups": groups, "rules": ["MATCH,DIRECT"],
    }
    cpath = os.path.join(workdir, "probe.yaml")
    with open(cpath, "w", encoding="utf-8") as f:
        yaml_dump(cfg, f)
    return cpath, types


def yaml_dump(obj, f):
    import yaml
    yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, width=4096)


def load_types(name, path):
    import yaml
    try:
        px = (yaml.safe_load(open(path, encoding="utf-8")) or {}).get("proxies") or []
        return {p.get("name"): str(p.get("type", "?")).lower() for p in px}
    except Exception:
        return {}


def _bucket(proxy):
    """分层的桶键：尽量按服务器 IP 的网段（地域/ASN 的粗代理），域名则退回域名本身。

    为什么要分层：源里的节点常是「同一批机场的同一地区机」，随机抽样很容易
    连抽 30 个全在同一个网段 —— 那不是样本，是偏倚。实测 yypool 有 900 个节点，
    随机抽 30 个和分层抽 30 个，测出来的通过率能差好几个百分点。
    """
    host = str(proxy.get("server", "") or "").split(":")[0]
    if not host:
        return "?"
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return host


def sample_nodes(nodes, n):
    """分层抽样：组内按名排序（确定性、可复现），组间轮转取。

    返回最多 n 个节点。n<=0 或总量不足时原样返回。
    """
    if n <= 0 or len(nodes) <= n:
        return list(nodes)
    buckets = {}
    for p in nodes:
        buckets.setdefault(_bucket(p), []).append(p)
    for b in buckets.values():
        b.sort(key=lambda p: str(p.get("name", "")))
    keys = sorted(buckets)
    out, i = [], 0
    while len(out) < n:
        progressed = False
        for k in keys:
            b = buckets[k]
            if i < len(b):
                out.append(b[i])
                progressed = True
                if len(out) >= n:
                    break
        if not progressed:
            break
        i += 1
    return out


def write_sampled(src, dst, n):
    """把抽样后的节点写成一个新的 provider 文件。

    ⚠ 抽样数据**永远不能用来判死**：n=30、源真实通过率 10% 时，
    抽 30 个全死 的概率 = 0.9^30 ≈ 4.2%。一轮 12 个源就有 40% 概率
    至少错判一个源。三轮连错 → 误杀好源。所以 is_sampled 的源不参与降级判定。
    """
    import yaml
    doc = yaml.safe_load(open(src, encoding="utf-8")) or {}
    nodes = doc.get("proxies") or []
    picked = sample_nodes(nodes, n)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        yaml.safe_dump({"proxies": picked}, f, allow_unicode=True,
                       sort_keys=False, width=4096)
    return len(nodes), len(picked)


def probe(node_files, mihomo, workdir, budget=1500, log=print, hc_timeout=8000,
           poll=10, settle_polls=4):
    """跑一轮真探针。返回 {name: {nodes, tested, alive, rate, best_ms, plain_alive}}

    ⚠ 退出条件（2026-10-15 修掉的严重静默 bug）：原来只等「provider 把节点加载完」，
      不等「健康检查跑完」。两者相差极大 —— 加载 1 秒，检查几分钟。
      结果 12 个源里有 10 个只测了 5~40% 就退出，而 **rate 看起来完全正常**
      （yypool 5.1% 已测 / 13.0% 报告 vs 全量真值 13.1%，纯属巧合），
      只有 alive 差了 20 倍（6 vs 118）。因为 health.py 的「变好」判据是
      alive >= 5，alive 被严重低估会让好源看起来变差 -> good_streak 被清零 ->
      「变好回收」永远不触发。**这种 bug 靠看 rate 是发现不了的。**
      现在改成：所有 provider 都加载完，且连续 settle_polls 轮「已测总数」不再增长
      才算结束；并给每个源标 settled（tested>=nodes），未 settle 的不参与自动判定。
    """
    import yaml
    cpath, _ = build_config(node_files, workdir, health_check_timeout=hc_timeout)
    r = subprocess.run([mihomo, "-t", "-f", cpath, "-d", workdir],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=180)
    if r.returncode != 0:
        log("  [probe] 配置校验失败: %s" % ((r.stdout or r.stderr)[-300:]))
        return {}
    log("  [probe] 启动实例 %s（%d 源）" % (os.path.basename(mihomo), len(node_files)))
    logf = open(os.path.join(workdir, "probe.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([mihomo, "-d", workdir, "-f", cpath],
                            stdout=logf, stderr=subprocess.STDOUT)
    expect = {n: load_types(n, p) for n, p in node_files}
    t0 = time.time()
    rows, unloaded = {}, set()
    last_total, still = -1, 0
    try:
        while time.time() - t0 < budget:
            time.sleep(poll)
            try:
                data = api_get(API_PORT, "/providers/proxies")
            except Exception:
                continue
            rows, unloaded = {}, set()
            for pn, p in (data.get("providers") or {}).items():
                if pn not in expect:
                    continue
                tm = expect[pn]
                px = [x for x in (p.get("proxies") or []) if x.get("name") != "COMPATIBLE"]
                # ⚠ 大源（2000+ 节点）首次加载/首轮探测可能超过预算。
                #    若一个源一条都没探到，绝不能记成 alive=0（会被 health.py 误判成死源），
                #    标成 incomplete 让上层跳过本轮判定。
                if len(px) < len(tm):
                    unloaded.add(pn)
                    if not px:
                        rows[pn] = {"nodes": 0, "tested": 0, "alive": 0, "rate": 0.0,
                                    "best_ms": None, "plain_alive": 0, "incomplete": True,
                                    "settled": False, "expected": len(tm)}
                        continue
                plain_alive = 0
                alive = tested = 0
                best = None
                for x in px:
                    h = x.get("history") or []
                    if h:
                        tested += 1
                    d = (h[-1].get("delay") or 0) if h else 0
                    if d and d > 0:
                        alive += 1
                        best = d if best is None else min(best, d)
                        if str(tm.get(x.get("name"), "")).lower() in ("http", "socks5", "socks"):
                            plain_alive += 1
                rows[pn] = {"nodes": len(px), "tested": tested, "alive": alive,
                            "rate": round(alive / tested * 100, 2) if tested else 0.0,
                            "best_ms": best, "plain_alive": plain_alive,
                            "incomplete": len(px) < len(tm),
                            # settled=每个节点都拿到了探测结果。没 settle 的源
                            # alive 被系统性低估，不能参与自动升降级判定。
                            "settled": tested >= len(px) and len(px) > 0,
                            "expected": len(tm)}
            if not unloaded and rows:
                total = sum(r.get("tested", 0) for r in rows.values())
                if total == last_total:
                    still += 1
                    if still >= settle_polls:
                        ns = sum(1 for r in rows.values() if not r.get("settled"))
                        log("  [probe] 探测已收敛，用时 %ds（%d 个源已测完，%d 个未测完）"
                            % (int(time.time() - t0), len(rows) - ns, ns))
                        break
                else:
                    still, last_total = 0, total
                    log("  [probe] %ds 进度：已测 %d/%d 节点（%d 源加载中）"
                        % (int(time.time() - t0), total,
                           sum(r.get("nodes", 0) for r in rows.values()), len(unloaded)))
        else:
            log("  [probe] 预算耗尽(%ds)，未加载完的源: %s"
                % (budget, ",".join(sorted(unloaded)) or ["-"]))
    finally:
        proc.kill()
        logf.close()
        time.sleep(1)
    return rows


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mihomo", default=os.environ.get("MIHOMO_BIN", ""),
                    help="mihomo 可执行文件路径（CI 用 linux 版；本地可指 verge-mihomo.exe）")
    ap.add_argument("--nodes", default=os.path.join(ROOT, "dist", "nodes"))
    ap.add_argument("--archive-nodes", default=os.path.join(ROOT, "state", "archive_nodes"))
    ap.add_argument("--out", default=os.path.join(ROOT, "state", "probe_latest.json"))
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--poll", type=int, default=10,
                    help="轮询间隔(秒)。退出靠「已测总数连续 settle_polls 轮不增长」判定")
    ap.add_argument("--settle-polls", type=int, default=4,
                    help="连续多少轮无新增探测就认为收敛（默认 4×10s=40s）")
    ap.add_argument("--hc-timeout", type=int, default=8000,
                    help="单节点健康检查超时(ms)。国内跑时死节点要挂满这个时间，"
                         "是控制单轮时长的主要杠杆（mihomo 本身已并发探测，"
                         "没有独立并发旋钮可调）")
    ap.add_argument("--sample", type=int, default=0,
                    help="每源最多抽 N 个节点做分层抽样（0=不抽样）。"
                         "给额度紧张的国内 CI 用：把单轮从 20~30 分钟压到几分钟。"
                         "⚠ 抽样结果永远不参与降级判定（样本小，alive=0 可能是抽样运气）")
    ap.add_argument("--scope", default=os.environ.get("PROBE_SCOPE", "ci"),
                    choices=["ci", "local", "cnci"],
                    help="ci=美国 runner（只判死）/ local=国内本机（判优）/ "
                         "cnci=国内第三方 CI（口径介于两者之间，只做交叉验证）")
    args = ap.parse_args()

    mihomo = args.mihomo
    if not mihomo:
        print("[probe] 未提供 --mihomo，跳过（CI 会在前一步下载 mihomo）")
        return 0
    files = []
    for n in sorted(glob.glob(os.path.join(args.nodes, "*.yaml"))):
        name = os.path.splitext(os.path.basename(n))[0]
        if name == "all":
            continue
        files.append((name, n))
    # 历史库里的源也一起探（为了发现"变好了"能回收）
    for n in sorted(glob.glob(os.path.join(args.archive_nodes, "*.yaml"))):
        files.append(("arch__" + os.path.splitext(os.path.basename(n))[0], n))
    if not files:
        print("[probe] 没有可探的节点文件")
        return 0
    workdir = os.path.join(ROOT, ".probe")
    os.makedirs(workdir, exist_ok=True)

    # 抽样阶段（可选）。抽出来的文件直接写进 workdir/nodes/ —— mihomo 限制
    # provider 的 path 必须在 -d 目录内，所以不能原地改源文件。
    sampled_names = set()
    if args.sample > 0:
        import yaml
        nd = os.path.join(workdir, "nodes")
        new_files = []
        for name, src in files:
            dst = os.path.join(nd, name + ".yaml")
            try:
                total, kept = write_sampled(src, dst, args.sample)
            except Exception as e:
                new_files.append((name, src))
                print("[probe] %s 抽样失败(%s)，用全量" % (name, str(e)[:60]))
                continue
            if kept < total:
                sampled_names.add(name)
                new_files.append((name, dst))
                print("[probe] %-26s %d -> %d 节点（分层抽样，%d 个网段）"
                      % (name, total, kept,
                         len({_bucket(p) for p in (yaml.safe_load(open(dst, encoding="utf-8")) or {}).get("proxies") or []})))
            else:
                new_files.append((name, src))
        files = new_files

    rows = probe(files, mihomo, workdir, budget=args.budget, hc_timeout=args.hc_timeout,
                 poll=args.poll, settle_polls=args.settle_polls)
    if not rows:
        return 1
    for n in sampled_names:
        if n in rows:
            rows[n]["is_sampled"] = True
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    CAVEAT = {
        "ci": "CI runner 在美国：youtube 通过率会系统性偏高（1.8~13 倍），"
              "只能判是否彻底死，不能横向比质量（Spearman rho 仅 0.48）。",
        "local": "本机（国内）口径，与业务同源，质量判据可信。",
        "cnci": "国内第三方 CI：口径介于美国 CI 与家用宽带之间（IDC 国际出口通常"
                "更差）。**只用于交叉验证**，不足以单独触发回收或降级。",
    }
    json.dump({"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "scope": args.scope,
               "sampled": bool(sampled_names),
               "sample_per_source": args.sample if sampled_names else 0,
               "hc_timeout_ms": args.hc_timeout,
               "caveat": CAVEAT.get(args.scope, ""),
               "sources": rows},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[probe] 结果 -> %s（scope=%s%s）" %
          (args.out, args.scope, "，已抽样" if sampled_names else ""))
    for n, v in sorted(rows.items()):
        print("  %-26s %5d 节点 %5d 已测 %5d 活 %6.1f%%%s 最快 %sms"
              % (n, v["nodes"], v.get("tested", 0), v["alive"], v["rate"],
                 "" if v.get("settled") else "  ⚠未测完",
                 v["best_ms"] if v["best_ms"] else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())