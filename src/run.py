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

    for s in enabled:
        name = s["name"]
        raw_nodes, meta = fetch.fetch_source(s, timeout=args.timeout)
        metas.append(meta)
        if meta.get("error"):
            warnings.append("%s 抓取失败：%s（本轮产出空文件，不影响其他源）" % (name, meta["error"]))
            per_source[name] = []
            continue
        log("→ %s：原始 %d 节点 / %d bytes / %.1fs%s"
            % (name, len(raw_nodes), meta.get("bytes", 0), meta.get("fetch_sec", 0),
               "（已回退镜像）" if meta.get("mirror_used") else ""))
        if args.keep_raw:
            raw_keep[name] = list(raw_nodes)

        # 1) 同源去重：同 server:port+协议+凭据 只留一个
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

        # 2) 硬过滤
        drop_types = s.get("drop_types") or ()
        kept, reasons = [], {}
        for p in dedup:
            ok, why = filters.hard_filter(p, excl_map[name], drop_types)
            if ok:
                kept.append(p)
            else:
                key = why.split("(")[0].strip()
                reasons[key] = reasons.get(key, 0) + 1
        log("   去重 %d -> 硬过滤后 %d%s"
            % (len(dedup), len(kept),
               ("（丢弃 TOP：%s）" % "，".join("%s×%d" % (k, v)
                                        for k, v in sorted(reasons.items(), key=lambda x: -x[1])[:4]))
               if reasons else ""))

        # 3) AI 裁决（簇级：判一次清一整簇同族克隆节点）
        #
        # token 账（2026-10-14 实测）：单节点送审一批 60 条 prompt≈6263 字符≈4.5k token，
        # 12 源全量≈81 批≈40 万 token/轮；簇级后 nomorewalls 的 290 个同族广告位
        # 只占 1 簇，全 12 源预计 <20 批 ≈ 1.5 万 token —— 省 95%+。
        #   --ai-unit node    旧的单节点模式（保留作对照/兜底）
        #   --ai-unit cluster 簇级模式（默认）
        ai_reviewed[name] = 0
        if mode != "off" and kept:
            if args.ai_unit == "cluster":
                clusters = filters.group_clusters(kept)
                cap = args.ai_max_clusters
                if cap and len(clusters) > cap:
                    clusters = clusters[:cap]          # 已按簇大小降序，保留信息量最大的
                drop_c, cstats = ai_review.review_clusters(
                    clusters, kept, mode, aicfg, name, log)
                astats = cstats
                if cstats.get("error"):
                    warnings.append("%s AI 簇级审核不可用（保留全部节点）：%s"
                                    % (name, cstats["error"]))
                if cstats.get("rolled_back"):
                    warnings.append("%s AI 剔除超阈值，已整体回滚" % name)
                if drop_c:
                    kill = set()
                    for ci in drop_c:
                        kill.update(clusters[ci][1])
                    kept = [p for i, p in enumerate(kept) if i not in kill]
                    log("   AI 剔除 %d 簇 / %d 节点%s"
                        % (len(drop_c), len(kill),
                           ("（%s）" % "，".join(cstats.get("top_reasons") or []))
                           if cstats.get("top_reasons") else ""))
                ai_reviewed[name] = len(clusters)
                log("   簇审：%d 节点 -> %d 簇（送审 %d 簇）"
                    % (len(kept) + len(kill if drop_c else []), len(clusters),
                       len(clusters)))
            else:
                review_idx = []
                if scope == "all":
                    review_idx = list(range(len(kept)))
                elif scope == "flagged":
                    review_idx = [i for i, p in enumerate(kept) if filters.soft_hits(p["name"])]
                else:
                    flg = [i for i, p in enumerate(kept) if filters.soft_hits(p["name"])]
                    rest = [i for i in range(len(kept)) if i not in set(flg)]
                    if rest and args.ai_sample > 0:
                        step = max(1, len(rest) // max(1, args.ai_sample))
                        review_idx = sorted(set(flg) | set(rest[::step][:args.ai_sample]))
                    else:
                        review_idx = sorted(set(flg))
                subset = [kept[i] for i in review_idx]
                soft_map = {p["name"]: filters.soft_hits(p["name"]) for p in subset
                            if filters.soft_hits(p["name"])}
                log("   AI 送审 %d/%d 条（scope=%s）" % (len(subset), len(kept), scope))
                drop_local, astats = ai_review.review_source(
                    subset, soft_map, mode, aicfg, name, log)
                drop_idx = [review_idx[i] for i in drop_local]
                ai_reviewed[name] = len(subset)
                if astats.get("error"):
                    warnings.append("%s 部分批次 AI 不可用（相关批次保留全部节点）：%s"
                                    % (name, astats["error"]))
                if astats.get("rolled_back"):
                    warnings.append("%s AI 剔除比例超阈值，已整体回滚" % name)
                if drop_idx:
                    ds = set(drop_idx)
                    kept = [p for i, p in enumerate(kept) if i not in ds]
                    log("   AI 剔除 %d%s" % (len(drop_idx),
                                             ("（%s）" % "，".join(astats.get("top_reasons") or []))
                                             if astats.get("top_reasons") else ""))
        else:
            astats = {"mode": mode}

        # 4) 数量上限（控手机 health-check 规模）
        mx = int(s.get("max_nodes") or 0)
        if mx and len(kept) > mx:
            log("   超过 max_nodes=%d，截断至 %d" % (mx, mx))
            warnings.append("%s 产出 %d 超过 max_nodes=%d，已截断（考虑淘汰最差尾部）" % (name, len(kept), mx))
            kept = kept[:mx]

        filters.unique_names(kept, "")
        per_source[name] = kept
        meta["kept"] = len(kept)
        meta["ai"] = astats
        meta["hard_drop_reasons"] = reasons
        log("   产出 %d 节点" % len(kept))

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

    profile, _ = build.build_profile(enabled, excl_map, owner, repo)
    if args.pages_base:
        for n, p in profile["proxy-providers"].items():
            p["url"] = p["url"].replace(build.pages_base(owner, repo), base)
        # 覆盖后仍要保证不是 raw 直链
        for n, p in profile["proxy-providers"].items():
            assert "raw.githubusercontent" not in p["url"], "%s 用了 raw 直链" % n

    manifest = {
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "owner": owner,
        "repo": repo,
        "pages_base": base,
        "ai_mode": mode,
        "sources": [{
            "name": m["name"],
            "raw": m.get("raw_nodes"),
            "kept": m.get("kept"),
            "bytes": m.get("bytes"),
            "mirror": m.get("mirror_used"),
            "ai_dropped": (m.get("ai") or {}).get("dropped"),
            "error": m.get("error"),
        } for m in metas],
        "totals": {"kept": sum(len(v) for v in per_source.values()),
                   "merged": len(all_nodes),
                   "ai_reviewed": sum(ai_reviewed.values())},
        "ai_scope": scope,
        "ai_usage": ai_review.usage_report(),
        "warnings": warnings,
    }

    dist = os.path.join(ROOT, "dist")
    build.write_dist(dist, per_source, all_nodes, profile, manifest, base)
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
    report.write_report(os.path.join(ROOT, "reports", "latest.md"),
                        manifest, metas, warnings, per_source)

    # AI 逐条留痕：删了哪个节点、模型给的理由（调 prompt / 复核误杀都靠它）
    ai_rows = []
    for m in metas:
        for d in ((m.get("ai") or {}).get("drop_detail") or []):
            ai_rows.append((m["name"], d))
    ai_path = os.path.join(ROOT, "reports", "ai_dropped.md")
    with open(ai_path, "w", encoding="utf-8") as f:
        f.write("# AI 审核逐条留痕（生成于 %s，模型 `%s`）\n\n"
                % (manifest["generated_at"], manifest["ai_mode"]))
        if not ai_rows:
            f.write("本轮 AI 未剔除任何节点（或未启用 AI）。\n")
        else:
            f.write("共剔除 %d 条。若发现误杀，把节点名与理由贴回来即可针对性收窄 prompt。\n\n"
                    % len(ai_rows))
            cur = None
            for src, d in ai_rows:
                if src != cur:
                    cur = src
                    f.write("\n## %s\n\n| 节点名 | 类型 | server | 模型理由 |\n|---|---|---|---|\n" % src)
                f.write("| %s | %s | %s | %s |\n"
                        % (str(d.get("name"))[:60], d.get("type"), d.get("server"),
                           str(d.get("why"))[:40]))
    log("AI 逐条留痕 -> %s（%d 条）" % (ai_path, len(ai_rows)))
    log("完成：%d 源 / 产出 %d 节点（合并 %d）/ AI=%s -> %s"
        % (len(per_source), manifest["totals"]["kept"], len(all_nodes), mode, dist))
    return 0


if __name__ == "__main__":
    sys.exit(main())