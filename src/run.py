# -*- coding: utf-8 -*-
"""clash-source 流水线主入口。

    python src/run.py                      # 自动探测 AI（没配 key 就关掉）
    python src/run.py --ai-mode http       # 强制走 OpenAI 兼容接口
    python src/run.py --ai-mode off        # 纯规则
    python src/run.py --keep-raw           # 额外导出未过滤原始文件做对比

设计原则：
- 全程 fail-soft：单个源抓取失败 / AI 挂了 / 解析失败，都只影响该源，绝不产出空仓
- 每个源都留漏斗计数（原始 -> 去重 -> 硬过滤 -> AI -> 截断 -> 产出）到 manifest 与报告
"""
import argparse
import datetime
import os
import sys
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import ai_review      # noqa: E402
import build          # noqa: E402
import fetch          # noqa: E402
import filters        # noqa: E402
import report         # noqa: E402


def log(msg):
    print(msg, flush=True)


def _prune_dist_stale(dist_dir, keep_names):
    """把 dist/nodes、dist/raw 里「本轮已不存在的源」的快照删掉（2026-10-19 微项）。

    源被停用/改名后，上一轮的 per-source 文件会一直留在 main 的 dist/ 里：
    profile 不引用它们（gh-pages 每轮全量重建），但仓库里越积越旧，没人清理
    就更没人敢信。keep_names = 本轮源名集合；--sources 局部调试不调（只跑了
    部分源，没跑的源本来就是完整有效的，不能删）。
    """
    for sub in ("nodes", "raw"):
        d = os.path.join(dist_dir, sub)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            stem, ext = os.path.splitext(fn)
            if ext not in (".yaml", ".yml"):
                continue
            if stem == "all" or (stem.endswith("--flaky") and stem[:-7] in keep_names):
                continue
            if stem in keep_names:
                continue
            try:
                os.remove(os.path.join(d, fn))
                log("   清理 dist/%s 残留：%s" % (sub, fn))
            except OSError as e:
                log("⚠ 清理 dist/%s/%s 失败：%s" % (sub, fn, e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai-mode", default="auto",
                    choices=["auto", "http", "opencode", "off"])
    ap.add_argument("--owner", default=None, help="GitHub 用户名（CI 自动取）")
    ap.add_argument("--repo", default=None, help="仓库名（CI 自动取）")
    ap.add_argument("--pages-base", default=None,
                    help="覆盖订阅基址，如 https://cdn.jsdelivr.net/gh/you/clash-source@gh-pages")
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--keep-raw", action="store_true")
    ap.add_argument("--sources", default=None,
                    help="逗号分隔，只跑指定源（调试用）")
    ap.add_argument("--ai-scope", default=os.environ.get("AI_SCOPE", "mixed"),
                    choices=["all", "flagged", "mixed"],
                    help="AI 审阅范围：all=全量 flagged=仅可疑 mixed=可疑+抽样(默认)")
    ap.add_argument("--ai-sample", type=int, default=int(os.environ.get("AI_SAMPLE", "60")),
                    help="mixed 模式下每源均匀抽样条数")
    ap.add_argument("--ai-unit", default=os.environ.get("AI_UNIT", "cluster"),
                    choices=["cluster", "node"],
                    help="簇级审核(默认，省 95% token) / 单节点审核(对照用)")
    ap.add_argument("--ai-max-clusters", type=int,
                    default=int(os.environ.get("AI_MAX_CLUSTERS", "150")),
                    help="每源送审簇数上限（按簇大小降序取前 N）")
    ap.add_argument("--ai-time-budget", type=int,
                    default=int(os.environ.get("AI_TIME_BUDGET", "0")),
                    help="AI 阶段墙钟预算（秒，0=不限）。超预算后剩余源按纯规则产出")
    args = ap.parse_args()

    with open(os.path.join(HERE, "sources.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    exclude_default = cfg.get("exclude_filter_default") or ""
    enabled = [s for s in cfg["sources"] if s.get("enabled", True)]
    if args.sources:
        want = {x.strip() for x in args.sources.split(",")}
        enabled = [s for s in enabled if s["name"] in want]
        log("调试模式：只跑 %s" % ", ".join(s["name"] for s in enabled))
    # 逐源 exclude-filter（生产实测值）：统一化会误杀好节点，见 sources.yaml 注释
    excl_map = {s["name"]: (s.get("exclude_filter") or exclude_default) for s in enabled}
    log("源清单：%d 个启用（另有 %d 个已评估排除）"
        % (len(enabled), len(cfg.get("excluded") or [])))

    mode = ai_review.resolve_mode(args.ai_mode)
    aicfg = ai_review.config_from_env()
    scope = args.ai_scope
    ai_review.set_time_budget(args.ai_time_budget)   # 墙钟预算：保证流水线不被 AI 拖死
    if args.ai_time_budget:
        log("AI 墙钟预算: %ds" % args.ai_time_budget)
    if mode == "http":
        names = aicfg.get("_names") or ["env-single"]
        log("AI 后端：http（%s）" % " → ".join(names))
    elif mode == "opencode":
        log("AI 后端：opencode CLI（%s）" % aicfg["opencode_exe"])
    else:
        log("AI 后端：off（本轮纯规则过滤）")

    per_source = {}
    metas = []
    warnings = []
    raw_keep = {}
    ai_reviewed = {}
    ai_stats = {}       # 各源 AI 统计 -> meta["ai"] -> 报告与 ai_dropped.md

    # ================= 阶段一：抓取 + 硬过滤（源间并发） =================
    # 抓取是纯网络 IO、互不依赖，源间并发能把这一段从 12×N 秒压到约 N 秒。
    # AI 判定则延后到阶段二统一并发（见下）。
    def prep_one(s):
        """返回 (name, kept, meta, reasons)。异常在内部兜住，不影响其他源。"""
        name = s["name"]
        raw_nodes, meta = fetch.fetch_source(s, timeout=args.timeout)
        if meta.get("error"):
            return name, [], meta, {}
        if args.keep_raw:
            # 逐节点浅拷贝留下「原貌」：下方 hard_filter 接受节点时会 node.clear()
            # +update 就地清洗（2026-10-19 §75#5），若仍共享引用，dist/raw 里的活
            # 节点全是清洗后的样子、只有被弃节点保留原貌，对比/取证就失真了。
            raw_keep[name] = [dict(p) for p in raw_nodes]

        seen = set()
        dedup = []
        for p in raw_nodes:
            if not isinstance(p.get("name"), str):
                p["name"] = str(p.get("name", ""))
            try:
                k = filters.dedupe_key(p)
            except (TypeError, ValueError):
                k = (str(p.get("type")), str(p.get("server")), str(p.get("port")),
                     str(p.get("password") or p.get("uuid") or ""))
            if k in seen:
                continue
            seen.add(k)
            dedup.append(p)

        drop_types = s.get("drop_types") or ()
        kept, reasons = [], {}
        for p in dedup:
            ok, why = filters.hard_filter(p, excl_map[name], drop_types)
            if ok:
                kept.append(p)
            else:
                key = why.split("(")[0].strip()
                reasons[key] = reasons.get(key, 0) + 1
        return name, kept, meta, reasons

    fetch_workers = max(1, int(os.environ.get("FETCH_CONCURRENCY", "6")))
    if fetch_workers > 1:
        import concurrent.futures as cf
        with cf.ThreadPoolExecutor(max_workers=fetch_workers) as pool:
            prepared = list(pool.map(prep_one, enabled))
    else:
        prepared = [prep_one(s) for s in enabled]

    cluster_jobs = []      # (源名, 簇列表或 None, 代表节点全集) None=源级（node 模式）
    prepared_by_name = {}

    for name, kept, meta, reasons in prepared:
        metas.append(meta)
        prepared_by_name[name] = kept
        if meta.get("error"):
            warnings.append("%s 抓取失败：%s（本轮产出空文件，不影响其他源）" % (name, meta["error"]))
            per_source[name] = []
            continue
        log("→ %s：原始 %d 节点 / %d bytes / %.1fs%s"
            % (name, meta.get("raw_nodes", 0), meta.get("bytes", 0),
               meta.get("fetch_sec", 0),
               "（已回退镜像）" if meta.get("mirror_used") else ""))
        log("   去重后 %d -> 硬过滤后 %d%s"
            % (meta.get("raw_nodes", 0), len(kept),
               ("（丢弃 TOP：%s）" % "，".join("%s×%d" % (k, v)
                                        for k, v in sorted(reasons.items(), key=lambda x: -x[1])[:4]))
               if reasons else ""))
        if kept:
            if args.ai_unit == "cluster":
                clusters = filters.group_clusters(kept)
                cap = args.ai_max_clusters
                if cap and len(clusters) > cap:
                    clusters = clusters[:cap]      # 已按簇大小降序，保留信息量最大的
                ai_reviewed[name] = len(clusters)
                cluster_jobs.append((name, clusters, kept))
            else:
                ai_reviewed[name] = len(kept)
                cluster_jobs.append((name, None, kept))   # node 模式：整源一批，阶段二走 review_source

    log("阶段一完成：%d 个源 / 产出 %d 节点 / 待 AI 审核 %d 个任务"
        % (len(prepared_by_name), sum(len(v) for v in prepared_by_name.values()), len(cluster_jobs)))

    # ================= 阶段二：AI 审核（全源簇任务统一并发） =================
    # 为什么单独一段：原先是「源与源串行、源内 3 路并发」，大源一堵就卡住整条流水线。
    # 现在把所有簇任务摊平进一个队列，天然负载均衡；配合 ai_review 的
    # TPM 速率闸门（5 个后端同属一个硅基账号，额度共享，加并发必须配速率控制）。
    if cluster_jobs and mode != "off":
        import concurrent.futures as cf
        ai_workers = max(1, int(os.environ.get("AI_CONCURRENCY", "6")))

        def judge(job):
            name, clusters, kept = job
            if clusters is None:
                # node 模式：整源一批走源级审核。软标记这时才真正派上用场——
                # 簇级 prompt 里没有它，源级 _fmt_chunk 会渲染 [软标记:…]。
                smap = {p.get("name", ""): filters.soft_hits(p.get("name", ""))
                        for p in kept}
                smap = {k: v for k, v in smap.items() if v}
                drops, st = ai_review.review_source(kept, smap, mode, aicfg, name, log)
            else:
                drops, st = ai_review.review_clusters(
                    clusters, kept, mode, aicfg, name, log)
            return name, drops, st

        t_ai = time.time()
        log("阶段二：%d 个任务交给 %d 路并发 AI（%s级审核）"
            % (len(cluster_jobs), ai_workers,
               "源" if any(c[1] is None for c in cluster_jobs) else "簇"))
        with cf.ThreadPoolExecutor(max_workers=ai_workers) as pool:
            ai_results = list(pool.map(judge, cluster_jobs))
        log("阶段二完成，用时 %.0fs" % (time.time() - t_ai))

        for name, drops, st in ai_results:
            clusters = next(c[1] for c in cluster_jobs if c[0] == name)
            kept = prepared_by_name[name]
            # ⚠ 必须写进 meta["ai"]：报告与 ai_dropped.md 都从这里读 ——
            #   原来赋给一个没人读的局部变量（astats），整条 AI 留痕断裂：
            #   报告显示「审 0 剔除 0」，而 AI 实际跑了几十次。
            ai_stats[name] = st
            if st.get("error"):
                warnings.append("%s AI 部分批次不可用（相关批次保留全部节点）：%s"
                                % (name, st["error"]))
            if st.get("rolled_back"):
                warnings.append("%s AI 剔除超阈值，已整体回滚" % name)
            if st.get("skipped_budget"):
                warnings.append("%s AI 因墙钟预算耗尽被跳过（该源按纯规则产出）" % name)
            if drops:
                kill = set()
                if clusters is None:       # node 模式：drops 直接就是节点下标
                    kill.update(drops)
                else:
                    for ci in drops:
                        kill.update(clusters[ci][1])
                kept = [p for i, p in enumerate(kept) if i not in kill]
                why = ("（%s）" % "，".join(st.get("top_reasons") or [])) \
                    if st.get("top_reasons") else ""
                if clusters is None:
                    log("   %s：AI 剔除 %d 节点%s" % (name, len(kill), why))
                else:
                    log("   %s：AI 剔除 %d 簇 / %d 节点%s"
                        % (name, len(drops), len(kill), why))
            else:
                kind = ("整源 %d 节点" % len(kept)) if clusters is None \
                    else ("簇数 %d" % len(clusters))
                log("   %s：AI 未剔除（%s）" % (name, kind))
            prepared_by_name[name] = kept

    # 汇总产物
    for s in enabled:
        name = s["name"]
        kept = prepared_by_name.get(name, [])
        mx = int(s.get("max_nodes") or 0)
        if mx and len(kept) > mx:
            log("   %s 超过 max_nodes=%d，截断至 %d" % (name, mx, mx))
            warnings.append("%s 产出 %d 超过 max_nodes=%d，已截断" % (name, len(kept), mx))
            kept = kept[:mx]
        filters.unique_names(kept, "")
        per_source[name] = kept
        meta = next((m for m in metas if m["name"] == name), None)
        if meta is not None:
            meta["kept"] = len(kept)
            if name in ai_stats:
                meta["ai"] = ai_stats[name]
        log("   产出 %d 节点：%s" % (len(kept), name))


    # 合并池（带源前缀，名字全局唯一）
    all_nodes = []
    for name, nodes in per_source.items():
        for p in nodes:
            all_nodes.append(dict(p, name="%s_%s" % (name, p["name"])))
    filters.unique_names(all_nodes, "")

    owner, repo = build.resolve_owner_repo(args.owner, args.repo)
    if args.pages_base:
        base = args.pages_base.rstrip("/")
        log("订阅基址（覆盖）：%s" % base)
    else:
        base = build.pages_base(owner, repo)
        if owner == "YOUR_GITHUB_ID":
            warnings.append("未指定 GitHub 用户名，profile 里的订阅地址是占位符 "
                            "YOUR_GITHUB_ID（CI 上会自动取真实值；本地预览请传 --owner）")
        log("订阅基址：%s" % base)

    debug = bool(args.sources)
    if debug:
        # 局部调试跑：只写节点文件，不生成 profile（模板引用全部源，局部跑必然断言失败）
        log("调试模式：只写 nodes/，跳过 profile 生成")
        build.write_nodes(os.path.join(ROOT, "dist"), per_source, all_nodes)
        log("完成（调试）：%d 源 / 产出 %d 节点 / AI=%s" % (len(per_source), len(all_nodes), mode))
        return 0

    stable_nodes, flaky_nodes, stab_note = build.split_by_stability(per_source)
    log("稳定性加权：%s" % stab_note)

    profile, _, ranking = build.build_profile(enabled, excl_map, owner, repo,
                                              flaky_sources=sorted(flaky_nodes))
    log("质量分桶（国内口径）：AUTO=%s" % ("、".join(ranking["auto"]) or "无"))
    if ranking.get("degraded"):
        # 降级发布（用户 2026-10-18 拍板）：档案坏/缺时**不中断订阅**，
        # 但降级必须能被看见 —— 进 warnings（会印在 reports/latest.md 的告警区），
        # build 侧另外打了 ::warning:: 注解（CI 运行摘要上直接可见）。
        warnings.append("⚠ 源健康档案降级（订阅照发，AUTO 用上一轮名单）：%s"
                        % ranking["degraded"])
        log("⚠ 源健康档案降级（订阅照发）—— 详见上方 [build] 行")
    log("  备用=%s" % ("、".join(ranking["备用"]) or "无"))
    log("  观察=%s" % ("、".join(ranking["观察"]) or "无"))
    log("  不稳定（不进自动竞速，仅备用组可选）=%s"
        % ("、".join(ranking["不稳定"]) or "无"))
    if args.pages_base:
        for n, p in profile["proxy-providers"].items():
            p["url"] = p["url"].replace(build.mirror_base(owner, repo), base)
        # 覆盖后仍要保证不是 raw 直链（gh-proxy 中转 URL 含 raw 子串，看的是起头）
        for n, p in profile["proxy-providers"].items():
            assert not p["url"].startswith("https://raw.githubusercontent"), \
                "%s 用了 raw 直链" % n

    manifest = {
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "owner": owner,
        "repo": repo,
        "pages_base": base,
        "ai_mode": mode,
        "ranking": ranking,
        "sources": [{
            "name": m["name"],
            "raw": m.get("raw_nodes"),
            "kept": m.get("kept"),
            "bytes": m.get("bytes"),
            "mirror": m.get("mirror_used"),
            "ai_dropped": (m.get("ai") or {}).get("dropped"),
            "ai_dropped_clusters": (m.get("ai") or {}).get("dropped_clusters"),
            "error": m.get("error"),
        } for m in metas],
        "totals": {"kept": sum(len(v) for v in per_source.values()),
                   "merged": len(all_nodes),
                   # 统一口径 = **节点数**。原来簇级模式塞簇数、源级模式塞节点数，
                   # 同一个键两个量纲（日志里还把它标成「送审 N 条」）。
                   "ai_reviewed": (sum((s.get("reviewed") or 0) for s in ai_stats.values())
                                   if ai_stats else sum(ai_reviewed.values()))},
        "ai_scope": scope,
        "ai_usage": ai_review.usage_report(),
        "warnings": warnings,
    }

    dist = os.path.join(ROOT, "dist")
    build.write_dist(dist, stable_nodes, all_nodes, profile, manifest, base,
                     flaky_nodes=flaky_nodes)
    u = manifest["ai_usage"]
    log("AI 用量：送审 %d 条 / %d 次调用 / prompt %d + completion %d = %d token（超时记账 %d 次）"
        % (manifest["totals"]["ai_reviewed"], u.get("calls", 0), u.get("prompt", 0),
           u.get("completion", 0), u.get("prompt", 0) + u.get("completion", 0),
           u.get("timeouts", 0)))
    for b, v in (u.get("by_backend") or {}).items():
        log("   后端 %-22s %d 次  %d token" % (b, v["calls"], v["prompt"] + v["completion"]))

    # 产物不变量：mihomo 严格模式下「一个畸形节点 = 整个 provider 加载失败」，
    # 所以出仓前把这类致命字段组合再扫一遍，宁可流水线自己炸也不要手机静默变空池。
    for name, nodes in per_source.items():
        for p in nodes:
            assert not (p.get("obfs") and not p.get("obfs-password")), \
                "%s 有 obfs 无 obfs-password 的节点（会让 mihomo 拒绝整个 provider）" % name
            assert str(p.get("client-fingerprint") or "").lower() not in ("unsafe", "none"), \
                "%s 残留 client-fingerprint:unsafe" % name
    names_all = [p["name"] for p in all_nodes]
    assert len(names_all) == len(set(names_all)), "all.yaml 节点名重复"
    if args.keep_raw and raw_keep:
        import build as _b
        for name, nodes in raw_keep.items():
            _b.dump_yaml({"proxies": nodes},
                         "# 未过滤原始快照（对比用，勿订阅）—— 源 %s" % name,
                         os.path.join(dist, "raw", "%s.yaml" % name))
    if not args.sources:
        _prune_dist_stale(dist, set(per_source.keys()))
    report.write_report(os.path.join(ROOT, "reports", "latest.md"),
                        manifest, metas, warnings, per_source)

    # AI 逐条留痕：删了哪个节点、模型给的理由（调 prompt / 复核误杀都靠它）
    # ⚠ 两个口径都要给（簇数 / 节点数）—— 旧文案「共剔除 N 条」里的 N 是**簇数**，
    #   线上实测 91 行 = 91 簇、涉及 233 个节点，读者会把 N 当成节点数。详见
    #   report.write_ai_dropped 的说明。
    ai_path = os.path.join(ROOT, "reports", "ai_dropped.md")
    ai_clusters, ai_nodes, ai_rows_n, ai_covered = report.write_ai_dropped(
        ai_path, manifest, metas)
    if ai_clusters and ai_rows_n != ai_clusters:
        log("⚠ AI 留痕行数 %d ≠ 簇数 %d（本该每簇一条，检查 drop_detail）"
            % (ai_rows_n, ai_clusters))
    if ai_clusters and ai_covered != ai_nodes:
        log("⚠ AI 留痕覆盖 %d ≠ 剔除节点 %d（两组数来自同一批 drops，不该不等）"
            % (ai_covered, ai_nodes))
    log("AI 逐条留痕 -> %s（%d 簇 / %d 节点，表内 %d 行）"
        % (ai_path, ai_clusters, ai_nodes, ai_rows_n))
    log("完成：%d 源 / 产出 %d 节点（合并 %d）/ AI=%s -> %s"
        % (len(per_source), manifest["totals"]["kept"], len(all_nodes), mode, dist))
    return 0


if __name__ == "__main__":
    sys.exit(main())