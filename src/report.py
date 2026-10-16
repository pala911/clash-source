# -*- coding: utf-8 -*-
"""生成 reports/latest.md —— 每次运行的可审计留痕。"""
import datetime
import os


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
    L.append("| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 分组 | 备注 |")
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
        L.append("| %s | %s | %s | %s | %s | %s | %s |"
                 % (m["name"], m.get("raw_nodes", "-"), m.get("kept", "-"),
                    (m.get("ai") or {}).get("dropped", "-"),
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
            line = "- **%s**：审 %d，剔除 %d" % (m["name"], ai.get("reviewed", 0), ai.get("dropped", 0))
            if ai.get("rolled_back"):
                line += "（超阈值已回滚）"
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