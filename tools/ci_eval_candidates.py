#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云效候选池**粗筛**（discover.py 下游缺失的自动半段，2026-10-28 补上）。

定位（与三层探针的分工对齐，别越权）：
    L1 美国 CI    每 6h    唯一有权判死（现有源）
    L2 本机       每天     唯一有权判优（现有源排序分桶 + 候选终审）
    L3 云效(本文件) 每天   **只做候选准入粗筛**：把明显没用的候选毙掉，
                             看起来能用的标 cloud_approved 交给本机终审。

为什么不直接定 verdict：
  - 云效是数据中心 IP：免费节点常封机房段（snakem982 在云效 0 活、本机有活），
    0% 可能是假死 -> 只能拒准入（宁可错杀），不能碰已在册源；
  - 云效口径系统性虚高 +11.9pp（实测 rho=0.734）-> cloud_approved 只是
    「值得花本机探针时间」，终审仍在本机（tools/eval_candidates.py 消费本文件产物）。

输出两路：
  1) eval_cloud.json -> 主仓 data/eval_cloud.json（Contents API，通道与 ci_push_main 同款）
     本机 eval_candidates.py 读它：cloud_rejected 直接落 verdict，
     cloud_approved / 无云数据的照常本机真探针终审。
  2) results/eval_cloud_<时间戳>.json -> commit 回 Codeup（审计留痕，与探针同款）。

候选池来源：运行时用 Contents API 现拉主仓 data/discovered_pool.json
  （Codeup 快照会过期；api.github.com 国内实测可直连，通道见 ci_push_main.py）。

⚠ Python 3.6（云效集群 3.6.8）：不用 capture_output / f-string / 海象运算符。
⚠ 与 ci_probe_run.py 相同的铁律：粗筛失败绝不让流水线变红（探针才是正戏）。
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MIHOMO_GZ = os.path.join(HERE, "mihomo-linux-amd64.gz")
MIHOMO = os.path.join(HERE, ".mihomo")
OUT = os.path.join(HERE, "eval_cloud.json")
WORKDIR = os.path.join(HERE, ".eval")
STAGEDIR = os.path.join(HERE, ".eval_stage")

REPO = os.environ.get("MAIN_REPO", "pala911/clash-source")
BRANCH = os.environ.get("MAIN_BRANCH", "main")
POOL_PATH = "data/discovered_pool.json"

EVAL_MAX = int(os.environ.get("EVAL_MAX", "40"))       # 单轮最多评多少条（控流水线时长）
CAP = int(os.environ.get("EVAL_CAP", "60"))            # 每候选最多探多少节点
BATCH = int(os.environ.get("EVAL_BATCH", "10"))
BUDGET = int(os.environ.get("EVAL_BUDGET", "600"))     # 每批秒数
HC_TIMEOUT = int(os.environ.get("EVAL_HC_TIMEOUT", "8000"))
RATE_MIN = float(os.environ.get("EVAL_RATE_MIN", "5"))
ALIVE_MIN = int(os.environ.get("EVAL_ALIVE_MIN", "3"))
MIN_NODES = 5


def say(m):
    print("[eval-cloud] %s" % m)


def warn(m):
    print("[eval-cloud] ⚠ %s" % m)


def load_pool():
    """候选池：Contents API 现拉主仓（防 Codeup 快照过期），失败退本地文件。"""
    pat = os.environ.get("GH_PAT", "").strip()
    if pat:
        url = "https://api.github.com/repos/%s/contents/%s" % (REPO, POOL_PATH)
        for i in range(3):
            req = None
            try:
                import urllib.request
                req = urllib.request.Request(url)
                req.add_header("Authorization", "token " + pat)
                req.add_header("Accept", "application/vnd.github.v3+json")
                req.add_header("User-Agent", "clash-source-cnci-eval")
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(r.read().decode("utf-8", "replace"))
                raw = base64.b64decode(d.get("content") or "")
                pool = json.loads(raw.decode("utf-8"))
                say("候选池已从主仓 API 现拉（%d 条）" % len(pool.get("candidates") or []))
                return pool
            except Exception as e:                    # noqa: BLE001
                warn("主仓 API 第 %d 次拉取失败：%r" % (i + 1, e))
                time.sleep(5)
    local = os.path.join(HERE, "data", "discovered_pool.json")
    if os.path.exists(local):
        warn("API 不可用，退回 Codeup 快照（可能过期）")
        return json.load(open(local, encoding="utf-8"))
    return None


def prep_mihomo():
    """与 ci_probe_run.py 同款：随仓库带的内核，不现场下载。"""
    if os.path.exists(MIHOMO):
        return True
    if not os.path.exists(MIHOMO_GZ):
        warn("找不到 mihomo 内核 %s" % os.path.basename(MIHOMO_GZ))
        return False
    import gzip
    with open(MIHOMO, "wb") as f:
        f.write(gzip.decompress(open(MIHOMO_GZ, "rb").read()))
    os.chmod(MIHOMO, 0o755)
    return True


def clean_candidate(proxies, exclude_rx, filters_mod):
    """与 tools/eval_candidates.py 同一套消毒（硬过滤 + 名字去重）。"""
    out = []
    for p in proxies:
        if not isinstance(p, dict):
            continue
        try:
            ok, _why = filters_mod.hard_filter(p, exclude_rx)
        except Exception:
            ok = False
        if ok:
            out.append(p)
    return filters_mod.unique_names(out, "ceval")


def run_eval(pending, probe_mod, fetch_mod, filters_mod, yaml, exclude_rx):
    """阶段1 抓取清洗（两轮重试，8 线程）+ 阶段2 分批探针。

    返回 {url: {cloud_verdict, cloud_rate, cloud_alive, note}}
    """
    from concurrent.futures import ThreadPoolExecutor
    results = {}
    todo = list(range(len(pending)))
    ready = []                     # [(key, staged_path, url)]
    for round_no in (1, 2):
        urls = [pending[i]["url"] for i in todo]

        def _get(u):
            return fetch_mod.fetch(u, timeout=15, tries=2)

        with ThreadPoolExecutor(max_workers=8) as ex:
            datas = list(ex.map(_get, urls))
        still, nxt = [], []
        for k, i in enumerate(todo):
            url = pending[i]["url"]
            data = datas[k][0]
            if data is None:
                still.append(i)
                if round_no == 2:
                    results[url] = {"cloud_verdict": "cloud_rejected",
                                    "note": "抓取失败(直连+镜像两轮)"}
                continue
            nxt.append(i)
        data_by_url = {}
        for k, i in enumerate(todo):
            if datas[k][0] is not None:
                data_by_url[pending[i]["url"]] = datas[k][0]
        for i in nxt:
            c = pending[i]
            url = c["url"]
            proxies, err = fetch_mod.parse_proxies(data_by_url[url])
            if proxies is None:
                results[url] = {"cloud_verdict": "cloud_rejected",
                                "note": "无法解析: %s" % err}
                continue
            cleaned = clean_candidate(proxies, exclude_rx, filters_mod)
            if len(cleaned) < MIN_NODES:
                results[url] = {"cloud_verdict": "cloud_rejected",
                                "note": "清洗后仅 %d 节点(<%d)" % (
                                    len(cleaned), MIN_NODES)}
                continue
            picked = probe_mod.sample_nodes(cleaned, CAP)
            ndir = os.path.join(STAGEDIR, "nodes")
            if not os.path.isdir(ndir):
                os.makedirs(ndir)
            key = "cand%04d" % i
            path = os.path.join(ndir, key + ".yaml")
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"proxies": picked}, f, allow_unicode=True,
                               sort_keys=False, width=4096)
            ready.append((key, path, url))
            results[url] = {"cloud_verdict": None, "note": "", "cloud_nodes": len(picked)}
        if not still:
            break
        if round_no == 1 and still:
            say("第一轮抓取失败 %d 条，20s 后补一轮" % len(still))
            time.sleep(20)
        todo = still

    say("阶段1 完成：进探针 %d，直接判掉 %d" % (
        len(ready), len([1 for r in results.values() if r["cloud_verdict"]])))

    rows = {}
    if ready:
        for bi in range(0, len(ready), BATCH):
            chunk = ready[bi:bi + BATCH]
            shutil.rmtree(WORKDIR, ignore_errors=True)   # mihomo -d 残留（老坑）
            say("[batch %d/%d] %d 个候选" % (
                bi // BATCH + 1, (len(ready) + BATCH - 1) // BATCH, len(chunk)))
            r = probe_mod.probe([(k, p) for k, p, _u in chunk], MIHOMO, WORKDIR,
                                budget=BUDGET, hc_timeout=HC_TIMEOUT, log=say)
            rows.update(r or {})
    for key, _p, url in ready:
        row = rows.get(key)
        slot = results[url]
        if row is None or row.get("incomplete"):
            slot["cloud_verdict"] = "cloud_uncertain"
            slot["note"] = "探针未测完，留给本机"
            continue
        rate, alive = row.get("rate", 0.0), row.get("alive", 0)
        slot["cloud_rate"], slot["cloud_alive"] = rate, alive
        if rate >= RATE_MIN and alive >= ALIVE_MIN:
            slot["cloud_verdict"] = "cloud_approved"
            slot["note"] = "cloud rate=%.1f%% alive=%d best=%sms" % (
                rate, alive, row.get("best_ms") or 0)
        else:
            slot["cloud_verdict"] = "cloud_rejected"
            slot["note"] = "cloud rate=%.1f%% alive=%d (<%.0f%%/%d)" % (
                rate, alive, RATE_MIN, ALIVE_MIN)
    return results


def push_to_main(results, n_summary):
    """eval_cloud.json 推主仓（Contents API，复用 ci_push_main 的通道与重试）。"""
    pat = os.environ.get("GH_PAT", "").strip()
    if not pat:
        warn("无 GH_PAT，粗筛结果推不了主仓（本机 eval 将看不到云结论）")
        return False
    try:
        sys.path.insert(0, HERE)
        import ci_push_main as pm
    except Exception as e:                            # noqa: BLE001
        warn("import ci_push_main 失败：%r" % e)
        return False
    doc = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "cnci",
        "hc_timeout_ms": HC_TIMEOUT,
        "thresholds": {"rate_min": RATE_MIN, "alive_min": ALIVE_MIN},
        "summary": n_summary,
        "candidates": [{"url": u, "repo": v.get("repo", ""),
                        "cloud_verdict": v.get("cloud_verdict"),
                        "cloud_rate": v.get("cloud_rate"),
                        "cloud_alive": v.get("cloud_alive"),
                        "cloud_nodes": v.get("cloud_nodes"),
                        "note": v.get("note", "")}
                       for u, v in sorted(results.items())],
    }
    # 去重：同 URL 只留一条（discover 池里有镜像重复项）
    seen, out = set(), []
    for c in doc["candidates"]:
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        out.append(c)
    doc["candidates"] = out
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    stamp = doc["generated_at"].replace(":", "").replace("-", "")
    ok, why = pm.api_put_retry(REPO, "data/eval_cloud.json", OUT,
                               "云效候选粗筛 %s" % stamp[:13], BRANCH, pat)
    say("主仓 data/eval_cloud.json：%s" % why if ok else
        "主仓推送失败（不阻塞）：%s" % why)
    if ok:
        pm.api_put_retry(REPO, "results/eval_cloud_%s.json" % stamp[:13], OUT,
                         "云效候选粗筛存档 %s" % stamp[:13], BRANCH, pat)
    return ok


def commit_to_codeup():
    """eval_cloud.json 归档进 Codeup results/（审计留痕，同 ci_probe_run.push_result）。"""
    if not os.path.exists(OUT):
        return
    stamp = time.strftime("%Y%m%d-%H%M")
    try:
        if not os.path.isdir("results"):
            os.makedirs("results")
        shutil.copy2(OUT, os.path.join("results", "eval_cloud_%s.json" % stamp))
        shutil.copy2(OUT, os.path.join("results", "eval_cloud_latest.json"))
    except Exception as e:                            # noqa: BLE001
        warn("归档失败: %s" % e)
        return

    def g(*a):
        return subprocess.run(["git"] + list(a), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              universal_newlines=True, timeout=300)

    g("config", "user.name", "cnci-probe")
    g("config", "user.email", "cnci-probe@users.noreply.github.com")
    g("add", "-A", "results")
    c = g("commit", "-m", "云效候选粗筛 %s" % stamp)
    if "nothing to commit" in (c.stdout or ""):
        return
    if c.returncode != 0:
        warn("Codeup 提交失败: %s" % (c.stdout or "")[:160])
        return
    p = g("push", "origin", "HEAD:master")
    if p.returncode != 0:
        g("pull", "--rebase", "--autostash", "origin", "master")
        p = g("push", "origin", "HEAD:master")
    if p.returncode == 0:
        say("已归档 Codeup results/eval_cloud_%s.json" % stamp)
    else:
        warn("Codeup 推送失败（结果仍在 workspace）：%s" % (p.stdout or "")[:160])


def main():
    say("环境 python %s" % sys.version.split()[0])
    if not prep_mihomo():
        return 0                                      # 不染红：粗筛缺内核是配置问题
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import yaml
    except Exception as e:                            # noqa: BLE001
        warn("vendor yaml 不可用：%r" % e)
        return 0
    try:
        import fetch as fetch_mod
        import filters as filters_mod
        import probe as probe_mod
    except Exception as e:                            # noqa: BLE001
        warn("import 主仓模块失败（payload 没带齐 fetch/filters/probe？）：%r" % e)
        return 0

    pool = load_pool()
    if not pool:
        warn("没有候选池，跳过")
        return 0
    cands = pool.get("candidates") or []
    pending = [c for c in cands if c.get("verdict") == "pending"]
    pending.sort(key=lambda c: -(c.get("signals") or 0))
    # 同 URL 去重（探一次，结论广播）
    seen, uniq = set(), []
    for c in pending:
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        uniq.append(c)
    pending = uniq[:EVAL_MAX]
    if not pending:
        say("没有 pending 候选，无事可做")
        return 0
    say("待粗筛 %d 条（cap=%d/条, batch=%d, hc=%dms）" % (
        len(pending), CAP, BATCH, HC_TIMEOUT))

    exclude_rx = ""
    try:
        sx = os.path.join(HERE, "sources_exclude.txt")
        if os.path.exists(sx):
            exclude_rx = open(sx, encoding="utf-8").read().strip()
    except Exception:
        exclude_rx = ""

    shutil.rmtree(STAGEDIR, ignore_errors=True)
    try:
        results = run_eval(pending, probe_mod, fetch_mod, filters_mod, yaml,
                           exclude_rx)
    except Exception as e:                            # noqa: BLE001
        import traceback
        warn("粗筛自身异常（不染红）：%r" % e)
        print(traceback.format_exc())
        return 0

    # repo 名塞进 slot 供推送用；统计
    for c in pending:
        v = results.get(c["url"])
        if v is not None:
            v.setdefault("repo", c.get("repo", ""))
    from collections import Counter                    # py3.6 OK
    n = Counter(v.get("cloud_verdict") for v in results.values())
    say("粗筛结果：%s" % dict(n))
    try:
        push_to_main(results, dict(n))
    except Exception as e:                            # noqa: BLE001
        warn("推主仓异常（不阻塞）：%r" % e)
    commit_to_codeup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
