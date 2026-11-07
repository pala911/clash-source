# -*- coding: utf-8 -*-
"""阈值校准数据报告 —— 只出数据，**不改任何阈值**（校准是人的决定）。

背景（2026-10-16 定下的）：分级已生效，但 GOOD_RATE=8%、7 轮窗口、
TIER_MIN_CNCI_RUNS=7 这些阈值是在云效只有 1 轮数据时定的。约定跑满两周后
（10-30）用实际累积数据校准一次。

回答三个问题（全部只读 state/source_health.json）：

  1) GOOD_RATE=8% 合理吗
     —— 各源本机/云效的轮级通过率分布，以及 8% 这条线落在分布的哪里：
        有多少源卡在线附近（|均值-8| < 3pp 的「临界源」会在两档之间来回跳）。
  2) 7 轮窗口够不够
     —— 对 N=1..10 逐个算「N 轮均值的噪声」（滚动均值相邻差），
        给出噪声降到 ~2pp 需要的最小 N（理论 σ/√N 与实测两条都给）。
  3) 数据质量够不够
     —— 每源轮数、hc_timeout 是否一致（口径变了数据不可比）、
        是否混入了 incomplete/抽样轮。样本不足就明说，不硬算。

产出：reports/calibration_<日期>.md（**必须写文件**：本脚本由计划任务用
pythonw 跑，没有控制台可看）+ 控制台摘要（手动跑时）。

用法：
    python tools\\calibrate_report.py            # 出报告（随时可跑）
    schtasks /run /tn clash-source-calibrate     # 计划任务手动触发
"""
import io
import json
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEALTH = os.path.join(ROOT, "state", "source_health.json")
OUT_DIR = os.path.join(ROOT, "reports")

GOOD_RATE = 8.0            # 与 src/health.py 保持一致
WINDOW = 7                 # TIER_WINDOW
MIN_CNCI = 7               # TIER_MIN_CNCI_RUNS
CRIT = 3.0                 # 距 8% 线多少 pp 算「临界源」
TARGET_NOISE = 2.0         # 噪声目标（pp），当初 7 轮的定妆依据是 σ/√7 ≈ 2.1pp


def rates_of(rec, scope):
    """该口径下按时间排序的轮级 rate（只收数值，标注口径属性）。"""
    out = []
    for r in (rec.get("runs") or []):
        if r.get("scope") != scope:
            continue
        v = r.get("rate")
        if isinstance(v, (int, float)):
            out.append((r.get("ts") or "", float(v),
                        bool(r.get("sampled")), r.get("hc_timeout_ms")))
    out.sort()
    return out


def mean_n_noise(rates, n):
    """滚动 n 轮均值之间的平均绝对差（样本少时的实测粗估）。"""
    if len(rates) < n + 1:
        return None
    vals = [r[1] for r in rates]
    means = [sum(vals[i:i + n]) / n for i in range(len(vals) - n + 1)]
    diffs = [abs(means[i + 1] - means[i]) for i in range(len(means) - 1)]
    return sum(diffs) / len(diffs) if diffs else 0.0


def analyze(rec, scope):
    rates = rates_of(rec, scope)
    if len(rates) < 3:
        return None
    vals = [r[1] for r in rates]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    sd = var ** 0.5
    timeouts = {r[3] for r in rates}
    row = {
        "n": len(rates), "mean": mean, "sd": sd,
        "min": min(vals), "max": max(vals),
        "crit": abs(mean - GOOD_RATE) < CRIT,
        "timeouts": timeouts,
        "noise": {},
    }
    for n in (1, 3, 5, 7, 10):
        row["noise"][n] = mean_n_noise(rates, n)
    return row


def md_table(scope, rows):
    lines = []
    lines.append("| 源 | 轮数 | 均值 | σ | 最小~最大 | 噪声 N=1 | N=3 | N=5 | N=7 | 距 8% |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for name, row in sorted(rows.items()):
        if row is None:
            lines.append("| %s | 数据不足（<3 轮） | | | | | | | | |" % name)
            continue
        crit = "**临界**" if row["crit"] else "%.1f" % abs(row["mean"] - GOOD_RATE)
        def nn(n):
            v = row["noise"].get(n)
            return "—" if v is None else "%.1f" % v
        lines.append("| %s | %d | %.1f | %.1f | %.0f~%.0f | %s | %s | %s | %s | %s |"
                     % (name, row["n"], row["mean"], row["sd"],
                        row["min"], row["max"],
                        nn(1), nn(3), nn(5), nn(7), crit))
    return lines


def build_md():
    h = json.load(io.open(HEALTH, encoding="utf-8"))
    srcs = h.get("sources") or {}
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    md = ["# 阈值校准数据报告（%s）" % now, "",
          "只出数据，不改阈值。约定：跑满两周（10-30 前后）人工据此校准一次。",
          "数据来自 `state/source_health.json`（每口径只保留最近 %d 轮）。" % 12, ""]

    for scope, title in (("local", "本机口径（唯一有权判优）"),
                         ("cnci", "云效口径（回收的否决权）")):
        rows = {}
        for name, rec in sorted(srcs.items()):
            rows[name] = analyze(rec, scope)
        md.append("## %s" % title)
        md.append("")
        md += md_table(scope, rows)
        md.append("")

        done = {n: r for n, r in rows.items() if r}
        if not done:
            md.append("> 该口径样本不足（没有一个源攒够 3 轮），本节不下结论。\n")
            continue

        crit = sorted(n for n, r in done.items() if r["crit"])
        md.append("**临界源（|均值-8| < 3pp，会在两档之间来回跳）**：%s"
                  % ("、".join(crit) or "无"))
        md.append("")

        # 噪声-窗口曲线（各源平均；只统计样本够的源）
        curve = []
        for n in (1, 3, 5, 7, 10):
            vals = [r["noise"].get(n) for r in done.values()
                    if r["noise"].get(n) is not None]
            if vals:
                curve.append((n, sum(vals) / len(vals)))
        if curve:
            md.append("**噪声-窗口曲线**（滚动 N 轮均值的平均相邻差，越低越稳）：")
            md.append("")
            md.append("| N | " + " | ".join(str(n) for n, _ in curve) + " |")
            md.append("|---|" + "---|" * len(curve))
            md.append("| 噪声(pp) | " + " | ".join("%.1f" % v for _, v in curve) + " |")
            md.append("")
            ok_n = [n for n, v in curve if v <= TARGET_NOISE]
            theo = {}
            for n in (1, 3, 5, 7, 10):
                sds = [r["sd"] for r in done.values()]
                if sds:
                    theo[n] = (sum(sds) / len(sds)) / (n ** 0.5)
            md.append("- 实测：噪声降到 ≤%.0fpp 所需的最小 N = %s"
                      % (TARGET_NOISE,
                         ("、".join(str(n) for n in ok_n[:1]) or "样本内没降到"))
                      if ok_n else
                      "- 实测：样本内没有任何 N 把噪声降到 ≤%.0fpp" % TARGET_NOISE)
            md.append("- 理论 σ/√N：" + "、".join("N=%d→%.1f" % (n, v)
                                                 for n, v in sorted(theo.items())))
            md.append("- 两者差距大 = 轮次之间存在**相关性**（同天连跑/上游同批轮换），"
                      "样本量要打折看。")
        md.append("")

        tos = {}
        for r in done.values():
            for to in r["timeouts"]:
                if to is None:
                    continue          # 老轮次没记这个字段，别当成「混了口径」
                tos[to] = tos.get(to, 0) + 1
        if len(tos) > 1:
            md.append("⚠ **该口径内 hc_timeout 不一致**：%s —— 口径变了数据不可比，"
                      "校准前先确认没混口径。\n" % tos)

    # 总结
    md.append("## 结论怎么写（给人看的模板）")
    md.append("")
    md.append("1. 8% 这条线要不要动：看临界源多不多、它们的真实表现；")
    md.append("2. 7 轮要不要动：看噪声-窗口曲线在 7 处是否已 ≤2pp；")
    md.append("3. 数据够不够：每源至少 10 轮才有意义（现在每口径只留 12 轮）。")
    md.append("")
    md.append("（本报告只提供以上数据；阈值改动由人决定并需同步 src/health.py 与测试。）")
    return "\n".join(md)


def main():
    try:
        md = build_md()
        err = None
    except Exception:                          # noqa: BLE001
        md = "校准报告生成失败\n\n```\n%s\n```" % traceback.format_exc()
        err = 1
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "calibration_%s.md"
                       % time.strftime("%Y%m%d"))
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("报告已写: %s" % out)
    print(md[-1500:])
    return err or 0


if __name__ == "__main__":
    sys.exit(main())
