# -*- coding: utf-8 -*-
"""候选源评估：把 discovered_pool.json 里的 pending 候选送真探针，写回 verdict。

背景（为什么有这个脚本）：
  discover.py（CI 每 6h）只负责把新源扫进候选池，verdict 恒为 pending ——
  评估这半段从上线起就没人接（坑 §49 的实例：低频方被高频方冲成死环节）。
  本脚本补上：候选池 -> 抓取/清洗 -> 真探针（本机国内口径，判优）-> verdict。

口径纪律（坑 §48，不能忘）：
  判优只能在国内跑。CI runner（美国）口径虚高 1.8~13 倍，只能判死；
  云效（国内 IDC）介于两者之间且系统性 +11.9pp，只做交叉验证。
  所以本脚本默认在本机跑（scope=local 的网络环境）。

 verdict 含义：
  approved  通过率达标（默认 rate>=5% 且 alive>=3）—— 可入 sources.yaml
  rejected  抓不到 / 清洗后节点太少 / 探针通过率不达标 —— 附原因
  uncertain 探针没测完（incomplete）—— 不做判断，下轮再来
            （探针纪律：没 settle 的数据不能当 0% 用，等于批量制造假死亡）

用法：
  python tools/eval_candidates.py                 # 清空全部 pending
  python tools/eval_candidates.py --top 20        # 只评 signals 前 20 条
  python tools/eval_candidates.py --dry-run       # 只打印，不写回

 用 anaconda 的 python（要有 pyyaml）。mihomo 默认用 Clash Verge 自带内核。
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import yaml                                     # noqa: E402
import filters                                  # noqa: E402
import fetch as fetch_mod                       # noqa: E402
import probe as probe_mod                       # noqa: E402

POOL = os.path.join(ROOT, "data", "discovered_pool.json")
SOURCES_YAML = os.path.join(ROOT, "src", "sources.yaml")
WORKDIR = os.path.join(ROOT, ".probe_eval")       # mihomo -d 目录（探针每批清空）
STAGEDIR = os.path.join(ROOT, ".probe_eval_stage")  # 候选 provider 暂存（不能放 WORKDIR，
                                                  # 否则会被批次清理连文件带路径一起删掉）
DEFAULT_MIHOMO = r"C:\Program Files\Clash Verge\verge-mihomo.exe"

MIN_NODES = 5          # 清洗后少于这个数直接拒（真实源不会只有 4 个节点）
NAME_RE = re.compile(r"[^A-Za-z0-9_\-]")


def load_exclude_default():
    doc = yaml.safe_load(open(SOURCES_YAML, encoding="utf-8")) or {}
    rx = doc.get("exclude_filter_default") or ""
    try:
        re.compile(rx)
        return rx
    except re.error:
        return ""


def clean_candidate(proxies, exclude_rx):
    """对候选节点跑与正式源同一套消毒：hard_filter + 名字去重。"""
    out = []
    for p in proxies:
        if not isinstance(p, dict):
            continue
        try:
            ok, _why = filters.hard_filter(p, exclude_rx)
        except Exception:
            ok = False
        if ok:
            out.append(p)
    return filters.unique_names(out, "eval")


def _fetch_one(url, timeout=15):
    return fetch_mod.fetch(url, timeout=timeout, tries=2)


def stage1(pending, exclude_rx, cap, log):
    """抓取+清洗+落 provider 文件。返回 (ready, results)。

    ready:  [(cand_key, yaml_path)]，进探针
    results: {url: {verdict, note, nodes}}，不进探针的直接判掉

    ⚠ 抓取必须两轮重试：gh-proxy 有间歇性抽风（坑 §34，实测 2026-10-28 一轮
      6/6 全挂在镜像上、几分钟后同一 URL 秒通）。把「镜像临时不可达」判成
      「源死了」会往池子里写假死刑 —— 这正是坑 §52 说的「比率正常、绝对数全错」
      的近亲。所以第一轮全跑完后，失败的一律再补一轮，两轮都挂才判 rejected。
    ⚠ 并发抓取（8 线程）：97 个候选里死 URL 每个 worst case 要吃 15s×2×2，
      串行抓一遍要 10+ 分钟，会撞上 PowerShell 前台 10 分钟超时（实测批次1
      阶段1 单独跑了 13 分钟）。抓取是纯 IO，并行完全安全；后续清洗仍按
      原顺序串行，保证结果确定性。
    """
    from concurrent.futures import ThreadPoolExecutor
    ready, results = [], {}
    todo = list(range(len(pending)))
    for round_no in (1, 2):
        urls = [pending[i]["url"] for i in todo]
        with ThreadPoolExecutor(max_workers=8) as ex:
            datas = list(ex.map(lambda u: _fetch_one(u), urls))
        still, nxt = [], []
        for i, (c, (data, used, _dt, _att)) in enumerate(zip(
                [pending[j] for j in todo], datas)):
            url = c["url"]
            if data is None:
                still.append(todo[i])
                if round_no == 2:
                    results[url] = {"verdict": "rejected",
                                    "note": "抓取失败(直连+镜像,两轮共4次)", "nodes": 0}
                    log("  [%3d] %-60s rejected 抓取失败(两轮)" % (
                        todo[i], c.get("repo", "?")))
                continue
            if round_no == 2:
                log("  [%3d] %-60s 第2轮抓取成功" % (todo[i], c.get("repo", "?")))
            nxt.append(todo[i])
        # 清洗按原顺序串行（确定性），只处理抓到数据的
        data_by_url = {pending[j]["url"]: datas[k][0] for k, j in enumerate(todo)
                       if datas[k][0] is not None}
        for j in nxt:
            c, url = pending[j], pending[j]["url"]
            data = data_by_url[url]
            proxies, err = fetch_mod.parse_proxies(data)
            if proxies is None:
                results[url] = {"verdict": "rejected", "note": "无法解析: %s" % err,
                                "nodes": 0}
                log("  [%3d] %-60s rejected %s" % (j, c.get("repo", "?"), err[:40]))
                continue
            cleaned = clean_candidate(proxies, exclude_rx)
            if len(cleaned) < MIN_NODES:
                results[url] = {"verdict": "rejected",
                                "note": "清洗后仅 %d 节点(<%d)，原始 %d" % (
                                    len(cleaned), MIN_NODES, len(proxies)),
                                "nodes": len(cleaned)}
                log("  [%3d] %-60s rejected 清洗后%d节点" % (
                    j, c.get("repo", "?"), len(cleaned)))
                continue
            picked = probe_mod.sample_nodes(cleaned, cap)
            ndir = os.path.join(STAGEDIR, "nodes")
            os.makedirs(ndir, exist_ok=True)
            path = os.path.join(ndir, "cand%04d.yaml" % j)
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"proxies": picked}, f, allow_unicode=True,
                               sort_keys=False, width=4096)
            ready.append(("cand%04d" % j, path))
            results[url] = {"verdict": None, "note": "", "nodes": len(picked),
                            "raw": len(proxies), "key": "cand%04d" % j}
            log("  [%3d] %-60s 待探针  原始%d -> 清洗%d -> 抽%d" % (
                j, c.get("repo", "?"), len(proxies), len(cleaned), len(picked)))
        if not still:
            break
        if round_no == 1 and still:
            log("  [stage1] 第一轮抓取失败 %d 条，稍后重试一轮" % len(still))
            import time as _t
            _t.sleep(20)
        todo = still
    return ready, results


def probe_batches(ready, mihomo, batch, budget, hc_timeout, log):
    """分批真探针。返回 {key: probe 行}。"""
    rows = {}
    for bi in range(0, len(ready), batch):
        chunk = ready[bi:bi + batch]
        # ⚠ 每批先清装置目录：mihomo -d 会残留上次文件（local_probe 同款坑）
        if os.path.isdir(WORKDIR):
            import shutil
            shutil.rmtree(WORKDIR, ignore_errors=True)
        files = [(k, p) for k, p in chunk]
        log("  [batch %d/%d] %d 个候选，预算 %ds" %
            (bi // batch + 1, (len(ready) + batch - 1) // batch, len(chunk), budget))
        r = probe_mod.probe(files, mihomo, WORKDIR, budget=budget,
                            hc_timeout=hc_timeout, log=log)
        rows.update(r or {})
    return rows


def judge(key, row, results, rate_min, alive_min, log):
    """把探针行变成 verdict，写回所有同 URL 候选。"""
    url = None
    for u, r in results.items():
        if r.get("key") == key:
            url = u
            break
    if url is None:
        return
    slot = results[url]
    if row is None or row.get("incomplete"):
        slot["verdict"] = "uncertain"
        slot["note"] = "探针未测完(tested %s/%s)，不下结论" % (
            row.get("tested"), row.get("nodes")) if row else "探针无结果"
        log("  [eval] %-60s uncertain" % url[-60:])
        return
    rate, alive = row.get("rate", 0.0), row.get("alive", 0)
    slot["rate"], slot["alive"] = rate, alive
    slot["best_ms"] = row.get("best_ms")
    if rate >= rate_min and alive >= alive_min:
        slot["verdict"] = "approved"
        slot["note"] = "rate=%.1f%% alive=%d best=%sms" % (
            rate, alive, row.get("best_ms") or 0)
    else:
        slot["verdict"] = "rejected"
        slot["note"] = "rate=%.1f%% alive=%d (<门槛 %.0f%%/%d)" % (
            rate, alive, rate_min, alive_min)
    log("  [eval] %-60s %s %s" % (url[-60:], slot["verdict"].upper(), slot["note"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mihomo", default=DEFAULT_MIHOMO)
    ap.add_argument("--top", type=int, default=0, help="只评 signals 前 N 条（0=全部 pending）")
    ap.add_argument("--batch", type=int, default=10, help="每批探针的候选数")
    ap.add_argument("--cap", type=int, default=60, help="每候选最多探多少节点（分层抽样）")
    ap.add_argument("--budget", type=int, default=900, help="每批探针秒数预算")
    ap.add_argument("--hc-timeout", type=int, default=8000)
    ap.add_argument("--rate-min", type=float, default=5.0)
    ap.add_argument("--alive-min", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.mihomo):
        print("[eval] 找不到 mihomo: %s" % args.mihomo)
        return 1
    pool = json.load(open(POOL, encoding="utf-8"))
    cands = pool.get("candidates") or []
    pending = [c for c in cands if c.get("verdict") == "pending"]
    if args.top > 0:
        pending.sort(key=lambda c: -(c.get("signals") or 0))
        pending = pending[:args.top]
    print("[eval] 候选池 %d 条，本次评 %d 条 pending" % (len(cands), len(pending)))
    if not pending:
        return 0

    # 云效粗筛结果（data/eval_cloud.json，ci_eval_candidates.py 在云效流水线产出）：
    #   cloud_rejected  -> 直接落 rejected（云效口径还系统性虚高 +11.9pp 都过不了
    #                      5%，本机更没戏），不占本机探针时间
    #   cloud_approved / 无云数据 -> 本机真探针终审（终审权在本机）
    # ⚠ 云效 0% 可能是"节点封机房 IP"假死 —— 但这是准入筛选（宁可错杀），
    #   不是在册源判死，这个偏差方向是安全的。
    cloud, pre_reject_urls = {}, set()
    cf = os.path.join(ROOT, "data", "eval_cloud.json")
    if os.path.exists(cf):
        try:
            cd = json.load(open(cf, encoding="utf-8"))
            cloud = {c["url"]: c for c in (cd.get("candidates") or [])}
            print("[eval] 云效粗筛数据 %s（%d 条）" % (
                cd.get("generated_at"), len(cloud)))
        except Exception as e:
            print("[eval] ⚠ eval_cloud.json 读取失败，忽略：%r" % e)
    if cloud:
        to_eval, n_pre = [], 0
        for c in pending:
            cv = (cloud.get(c.get("url")) or {}).get("cloud_verdict")
            if cv == "cloud_rejected":
                pre_reject_urls.add(c["url"])
                n_pre += 1
            else:
                to_eval.append(c)
        if n_pre:
            print("[eval] 云效粗筛已毙 %d 条（不占本机探针）" % n_pre)
        pending = to_eval
        if not pending:
            print("[eval] 云效粗筛把 pending 全毙了，只写回结论")
            now0 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            for c in cands:
                if c.get("verdict") == "pending" and c.get("url") in pre_reject_urls:
                    cv = cloud.get(c["url"]) or {}
                    c["verdict"] = "rejected"
                    c["note"] = "云效粗筛拒: %s" % (cv.get("note") or "")
                    c["evaluated_at"] = now0
                    for k in ("cloud_rate", "cloud_alive"):
                        if cv.get(k) is not None:
                            c[k] = cv[k]
            if not args.dry_run:
                probe_mod.save_json_atomic(POOL, pool)
                print("[eval] 已原子写回 %s" % POOL)
            return 0

    # 同 URL 多条只探一次，verdict 广播回去
    seen, uniq = {}, []
    for c in pending:
        seen.setdefault(c["url"], []).append(c)
        if all(x["url"] != c["url"] for x in uniq):
            uniq.append(c)
    print("[eval] 去重后 %d 条 URL（同 URL 重复 %d 条将直接共享结论）"
          % (len(uniq), len(pending) - len(uniq)))

    exclude_rx = load_exclude_default()
    import shutil
    shutil.rmtree(STAGEDIR, ignore_errors=True)   # 上一轮残留的候选文件清掉
    print("[eval] 阶段1：抓取+清洗（exclude_filter_default 同正式源）")
    ready, results = stage1(uniq, exclude_rx, args.cap, print)
    print("[eval] 阶段1 完成：进探针 %d，直接判掉 %d"
          % (len(ready), len([1 for r in results.values() if r["verdict"]])))

    if ready:
        print("[eval] 阶段2：真探针（mihomo, hc_timeout=%dms, scope=本机国内口径）"
              % args.hc_timeout)
        rows = probe_batches(ready, args.mihomo, args.batch, args.budget,
                             args.hc_timeout, print)
        for k, _p in ready:
            judge(k, rows.get(k), results, args.rate_min, args.alive_min, print)

    # 写回：verdict 广播到所有同 URL 条目
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    n = {"approved": 0, "rejected": 0, "uncertain": 0}
    # 云效粗筛毙掉的直接落锤
    for c in cands:
        if c.get("verdict") == "pending" and c.get("url") in pre_reject_urls:
            cv = cloud.get(c["url"]) or {}
            c["verdict"] = "rejected"
            c["note"] = "云效粗筛拒: %s" % (cv.get("note") or "")
            c["evaluated_at"] = now
            for k in ("cloud_rate", "cloud_alive"):
                if cv.get(k) is not None:
                    c[k] = cv[k]
            n["rejected"] += 1
    for c in cands:
        r = results.get(c.get("url"))
        if not r or not r.get("verdict"):
            continue
        if c.get("verdict") != "pending":
            continue
        c["verdict"] = r["verdict"]
        c["note"] = r.get("note", "")
        c["evaluated_at"] = now
        for k in ("nodes", "rate", "alive", "best_ms"):
            if r.get(k) is not None:
                c[k] = r[k]
        n[r["verdict"]] = n.get(r["verdict"], 0) + 1
    print("[eval] 结果：approved=%d rejected=%d uncertain=%d" %
          (n["approved"], n["rejected"], n["uncertain"]))
    if not args.dry_run:
        probe_mod.save_json_atomic(POOL, pool)
        print("[eval] 已原子写回 %s" % POOL)
    else:
        print("[eval] dry-run，未写回")
    return 0


if __name__ == "__main__":
    sys.exit(main())
