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
    args = ap.parse_args()

    with open(os.path.join(HERE, "sources.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    exclude_default = cfg.get("exclude_filter_default") or ""
    enabled = [s for s in cfg["sources"] if s.get("enabled", True)]
    # 逐源 exclude-filter（生产实测值）：统一化会误杀好节点，见 sources.yaml 注释
    excl_map = {s["name"]: (s.get("exclude_filter") or exclude_default) for s in enabled}
    log("源清单：%d 个启用（另有 %d 个已评估排除）"
        % (len(enabled), len(cfg.get("excluded") or [])))

    mode = ai_review.resolve_mode(args.ai_mode)
    aicfg = ai_review.config_from_env()
    if mode == "http":
        log("AI 后端：http（%s / %s）" % (aicfg["base_url"], aicfg["model"]))
    elif mode == "opencode":
        log("AI 后端：opencode CLI（%s）" % aicfg["opencode_exe"])
    else:
        log("AI 后端：off（本轮纯规则过滤）")

    per_source = {}
    metas = []
    warnings = []
    raw_keep = {}

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

        # 3) AI 裁决（只剔除，fail-soft）
        soft_map = {}
        for p in kept:
            h = filters.soft_hits(p["name"])
            if h:
                soft_map[p["name"]] = h
        drop_idx, astats = ai_review.review_source(kept, soft_map, mode, aicfg, name, log)
        if astats.get("error"):
            warnings.append("%s AI 调用失败（已保留全部节点）：%s" % (name, astats["error"]))
        if astats.get("rolled_back"):
            warnings.append("%s AI 剔除比例超阈值，已整体回滚" % name)
        if drop_idx:
            ds = set(drop_idx)
            kept = [p for i, p in enumerate(kept) if i not in ds]
            log("   AI 剔除 %d%s" % (len(drop_idx),
                                     ("（%s）" % "，".join(astats.get("top_reasons") or []))
                                     if astats.get("top_reasons") else ""))

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
                   "merged": len(all_nodes)},
        "warnings": warnings,
    }

    dist = os.path.join(ROOT, "dist")
    build.write_dist(dist, per_source, all_nodes, profile, manifest, base)

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
    log("完成：%d 源 / 产出 %d 节点（合并 %d）/ AI=%s -> %s"
        % (len(per_source), manifest["totals"]["kept"], len(all_nodes), mode, dist))
    return 0


if __name__ == "__main__":
    sys.exit(main())