# -*- coding: utf-8 -*-
"""生成 reports/latest.md（运行报告）与 reports/ai_dropped.md（AI 逐条留痕）。"""
import datetime
import os


def write_ai_dropped(path, manifest, metas):
    """写 reports/ai_dropped.md —— AI 逐条留痕（调 prompt / 复核误杀都靠它）。

    ⚠ **两个口径都要给**（簇数 / 节点数），2026-10-18 补：
      · 簇级模式（`ai_review.review_clusters`）下 `drop_detail` 是**每簇一条**
        （代表节点），条目里的 `count` 是该簇实际覆盖的节点数
        ⇒ **行数 = 簇数 ≠ 节点数**。线上实测：91 行 = 91 簇、涉及 233 个节点，
        而旧文案只写「共剔除 91 条」，读者会把 91 当成节点数（差 2.5 倍）。
      · 源级模式（`review_source`）没有簇概念（`dropped_clusters` 恒 0），
        此时行数 = 节点数。

    返回 `(clusters, nodes, rows, covered)`：前三个来自汇总键，
    `covered` 是表内各行「节点数」列之和 —— 簇级模式下它必须等于 `nodes`
    （两组数来自同一批 drops），调用方据此对账，别让不一致静默留在文件里。
    """
    clusters = sum(int(((m.get("ai") or {}).get("dropped_clusters") or 0)) for m in metas)
    nodes = sum(int(((m.get("ai") or {}).get("dropped") or 0)) for m in metas)
    rows = []
    for m in metas:
        for d in ((m.get("ai") or {}).get("drop_detail") or []):
            rows.append((m.get("name"), d))
    covered = sum(int(d.get("count") or 1) for _s, d in rows)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# AI 审核逐条留痕（生成于 %s，模型 `%s`）\n\n"
                % (manifest.get("generated_at"), manifest.get("ai_mode")))
        if not rows:
            f.write("本轮 AI 未剔除任何节点（或未启用 AI）。\n")
        else:
            if clusters:
                f.write("共剔除 %d 簇 / %d 节点（下表每簇列一条代表节点 + 理由，"
                        "「节点数」列是该簇实际覆盖的节点数）。"
                        "若发现误杀，把节点名与理由贴回来即可针对性收窄 prompt。\n\n"
                        % (clusters, nodes))
            else:
                f.write("共剔除 %d 节点。若发现误杀，把节点名与理由贴回来即可"
                        "针对性收窄 prompt。\n\n" % nodes)
            cur = None
            for src, d in rows:
                if src != cur:
                    cur = src
                    f.write("\n## %s\n\n| 节点名 | 类型 | server | 节点数 | 模型理由 |\n"
                            "|---|---|---|---|---|\n" % src)
                f.write("| %s | %s | %s | %d | %s |\n"
                        % (str(d.get("name"))[:60], d.get("type"), d.get("server"),
                           int(d.get("count") or 1), str(d.get("why"))[:40]))
    return clusters, nodes, len(rows), covered


def write_report(path, manifest, metas, warnings, per_source):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = []
    L.append("# clash-source 运行报告")
    L.append("")
    L.append("- 生成时间：%s（UTC 记录：%s）" % (now, manifest["generated_at"]))
    L.append("- AI 模式：`%s`" % manifest["ai_mode"])
    L.append("- 订阅入口：`%s/profile.yaml`" % manifest["pages_base"])
    L.append("- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/"
             "%s/gh-pages/profile.yaml`" % manifest["owner"])
    L.append("- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/%s/%s@gh-pages/profile.yaml`"
             % (manifest["owner"], manifest["repo"]))
    L.append("")
    # 质量分桶必须写在报告最显眼处 —— 「为什么这个源在那组」是这套系统里
    # 最需要向人解释、也最容易被质疑的决策。
    rank = manifest.get("ranking") or {}
    if rank:
        L.append("## 质量分桶（决定手机上 AUTO 组里有哪些源）")
        L.append("")
        L.append("| 组 | 含义 | 源 |")
        L.append("|---|---|---|")
        L.append("| AUTO | 参与自动竞速 | %s |"
                 % ("、".join(rank.get("auto") or []) or "-"))
        L.append("| 备用 | 不自动竞速，手动切 | %s |"
                 % ("、".join(rank.get("备用") or []) or "-"))
        L.append("| 观察 | 本机实测不达标 | %s |"
                 % ("、".join(rank.get("观察") or []) or "-"))
        L.append("")
        L.append("排序依据是**国内口径**（本机全量探针的多轮均值）。"
                 "美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。")
        L.append("")
        L.append("| 源 | 多轮均值 | 分组依据 |")
        L.append("|---|---:|---|")
        for n in sorted((rank.get("detail") or {})):
            d = rank["detail"][n]
            L.append("| %s | %s | %s |" % (n, ("%.1f%%" % d["rate"]) if d.get("rate") is not None else "-", d.get("why") or "-"))
        L.append("")
    L.append("## 各源漏斗")
    L.append("")
    L.append("| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |")
    L.append("|---|---:|---:|---:|---|---|---|")
    detail = (rank or {}).get("detail") or {}
    bucket = {}
    for b in ("auto", "备用", "观察"):
        for n in (rank.get(b) or []):
            bucket[n] = b
    for m in metas:
        note = m.get("error") or ""
        if m.get("mirror_used"):
            note = (note + " " if note else "") + "直连失败走镜像"
        # AI 剔除同时给出「簇数 / 节点数」：簇数说明模型做了几次判定，
        # 节点数才与其他列（原始/产出）同量纲。只看簇数会把「1 簇 300 节点」
        # 读成无关紧要，只看节点数又看不出判定粒度。
        ai = m.get("ai") or {}
        if not ai:
            ai_cell = "-"
        elif ai.get("dropped_clusters"):
            ai_cell = "%d 簇 / %d 节点" % (ai["dropped_clusters"], ai.get("dropped", 0) or 0)
        else:
            ai_cell = "%d 节点" % (ai.get("dropped", 0) or 0)
        L.append("| %s | %s | %s | %s | %s | %s | %s |"
                 % (m["name"], m.get("raw_nodes", "-"), m.get("kept", "-"),
                    ai_cell,
                    "是" if m.get("mirror_used") else "否",
                    bucket.get(m["name"], "-"), note or "-"))
    L.append("")
    L.append("合计产出 **%d** 节点（合并池 %d）。"
             % (manifest["totals"]["kept"], manifest["totals"]["merged"]))
    L.append("")
    L.append("> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**"
             "（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。")
    L.append("")
    if warnings:
        L.append("## ⚠ 本次告警")
        L.append("")
        for w in warnings:
            L.append("- %s" % w)
        L.append("")
    else:
        L.append("## 本次告警")
        L.append("")
        L.append("无。")
        L.append("")
    L.append("## 硬过滤命中 TOP（按源）")
    L.append("")
    any_reasons = False
    for m in metas:
        rs = m.get("hard_drop_reasons") or {}
        if rs:
            any_reasons = True
            top = sorted(rs.items(), key=lambda x: -x[1])[:6]
            L.append("- **%s**：%s" % (m["name"], "，".join("%s×%d" % (k, v) for k, v in top)))
    if not any_reasons:
        L.append("- 无记录")
    L.append("")
    L.append("## AI 处置摘要")
    L.append("")
    if manifest["ai_mode"] == "off":
        L.append("本轮未启用 AI（未配置 `AI_BASE_URL`/`AI_API_KEY`，或显式 `--ai-mode off`）。")
    else:
        for m in metas:
            ai = m.get("ai") or {}
            if not ai:
                continue
            ncl = ai.get("dropped_clusters", 0) or 0
            line = "- **%s**：审 %d 节点，剔除 %d 节点" % (
                m["name"], ai.get("reviewed", 0) or 0, ai.get("dropped", 0) or 0)
            if ncl:
                line += "（%d 个簇）" % ncl
            if ai.get("rolled_back"):
                line += "（超阈值已回滚）"
            if ai.get("skipped_budget"):
                line += "（墙钟预算用尽，未审）"
            if ai.get("error"):
                line += "（%s）" % ai["error"]
            if ai.get("top_reasons"):
                line += "；理由 TOP：%s" % "，".join(ai["top_reasons"])
            L.append(line)
    L.append("")
    L.append("## 产物")
    L.append("")
    L.append("- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）")
    L.append("- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）")
    L.append("- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）")
    L.append("- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）")
    L.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))