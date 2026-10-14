# -*- coding: utf-8 -*-
"""真探针：在流水线里用 mihomo 内核跑 youtube 探针，给每个源打可用性分数。

为什么要它：源的价值只能用**真探针**判定（记忆坑 §4/§5：README 说的"测速筛选"不可信，
Au1rxx 自测只保 TCP 存活、1745 个节点只有 2 个能穿 youtube）。

⚠ 口径警告（重要）：CI runner 在**美国**。mahdibland 的教训（坑 §40）——美机测速筛出的
200 个节点，国内 youtube 0% 通过。所以本模块的分数只能用来判「**是否彻底死了**」，
不能用来横向比「哪个源更好」。因此 health.py 的降级门槛设得很保守。

产出：state/probe_latest.json（每源 nodes/tested/alive/rate/best_ms）
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


def probe(node_files, mihomo, workdir, budget=1500, log=print):
    """跑一轮真探针。返回 {name: {nodes, tested, alive, rate, best_ms, plain_alive}}"""
    import yaml
    cpath, _ = build_config(node_files, workdir)
    r = subprocess.run([mihomo, "-t", "-f", cpath, "-d", workdir],
                       capture_output=True, text=True, timeout=180)
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
    try:
        while time.time() - t0 < budget:
            time.sleep(20)
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
                                    "expected": len(tm)}
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
                            "expected": len(tm)}
            if not unloaded and rows:
                log("  [probe] 全部测完，用时 %ds" % int(time.time() - t0))
                break
        else:
            log("  [probe] 预算耗尽，未加载完的源: %s" % ",".join(sorted(unloaded) or ["-"]))
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
    ap.add_argument("--scope", default=os.environ.get("PROBE_SCOPE", "ci"),
                    choices=["ci", "local"],
                    help="ci=美国 runner（只用于判死）/ local=国内本机（口径可信）")
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
    rows = probe(files, mihomo, workdir, budget=args.budget)
    if not rows:
        return 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump({"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "scope": args.scope,
               "caveat": ("CI runner 在美国：youtube 通过率会系统性偏高，只能判是否彻底死，"
                          "不能横向比质量（实测 ssrsub CI 90% vs 国内 45.6%）。"
                          if args.scope == "ci" else
                          "本机（国内）口径，与业务同源，质量判据可信。"),
               "sources": rows},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[probe] 结果 -> %s（scope=%s）" % (args.out, args.scope))
    for n, v in sorted(rows.items()):
        print("  %-26s %5d 节点 %5d 活 %6.1f%%  最快 %sms" %
              (n, v["nodes"], v["alive"], v["rate"],
               v["best_ms"] if v["best_ms"] else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())