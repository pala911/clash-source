# -*- coding: utf-8 -*-
"""验证 AI 留痕链：生产端（ai_review）-> 组装（run.py 的 meta["ai"]）-> 消费端（report）。

## 为什么要有这个测试

线上 `reports/latest.md` 长期显示「AI 处置摘要：审 0，剔除 0」、
`dist/manifest.json` 里 `ai_dropped` 恒为 null，而 AI 实际跑了几十次
（`ai_usage.calls` 有数）。根因是**两边键名对不上**：

    生产端 review_clusters（簇级，线上在用的那个）
        -> dropped_clusters / dropped_nodes      （没有 reviewed / dropped）
    生产端 review_source（源级，--ai-unit node 才用）
        -> reviewed / dropped                    （没有 dropped_clusters）
    消费端 report.py / run.py
        -> 读 reviewed / dropped                 （簇级口径一个都没有）

于是 `.get()` 全部落到默认值 0 —— **不报错、不告警，报告上是一份看起来很确定的假结论**。
这一条只靠肉眼看代码极难发现（两个函数各自都是自洽的），所以必须让测试守。

## 测试分四层

  1. 契约层：消费端源码里读到的每个 ai 键，两种口径都必须提供
     —— 这层如果早存在，上面那个 bug 上线当天就会红。
  2. 数值层：屏蔽真后端，喂一个"要剔除第 2 簇"的假回复，
     断言 reviewed/dropped/dropped_clusters 三个数是**真的算出来的**，不是恒 0。
  3. 渲染层：用合成 manifest/meta 跑一遍 report.write_report，断言报告正文里
     真的出现了「N 簇 / M 节点」而不是 0。
  4. 留痕层：跑 report.write_ai_dropped，断言 `reports/ai_dropped.md` 里
     **簇数与节点数都给**（线上实测：旧文案写「共剔除 91 条」，91 是簇数、
     实际涉及 233 个节点 —— 「条」这种写法读者只会当成节点数）、每行带簇内节点数、
     源级模式（没有簇概念）不提簇、零剔除不写「共剔除」。
"""
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import ai_review            # noqa: E402
import report               # noqa: E402

FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                        ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def log(_msg):
    pass


# ---------------------------------------------------------------------------
# 1) 契约层：把消费端源码里读的 ai 键扫出来
# ---------------------------------------------------------------------------
# 允许被读的键（= 生产端承诺提供的键）。加新键必须先加到这里，
# 逼着改动者同时在生产端补上 —— 这正是当初漏掉的那一步。
AI_KEYS = {"reviewed", "dropped", "dropped_clusters", "dropped_nodes",
           "rolled_back", "top_reasons", "drop_detail", "error",
           "skipped_budget", "mode", "chunks", "chunks_failed", "clusters"}
# 汇总口径：两种审核单位都必须提供（报告/manifest 只读这三个）
SUMMARY = ["reviewed", "dropped", "dropped_clusters"]

PAT_A = re.compile(r'(?:\(m\.get\("ai"\)\s*or\s*\{\}\))\.get\("([a-z_]+)"')
PAT_B = re.compile(r'\bai\.get\("([a-z_]+)"')

print("=" * 72)
print("1) 契约层：消费端读的 ai 键必须都在生产端的承诺里")
print("=" * 72)
read_keys = set()
for fn in ("report.py", "run.py"):
    text = open(os.path.join(ROOT, "src", fn), encoding="utf-8").read()
    hits = set(PAT_A.findall(text)) | set(PAT_B.findall(text))
    print("  %-11s 读的 ai 键: %s" % (fn, "、".join(sorted(hits)) or "无"))
    read_keys |= hits
unknown = sorted(read_keys - AI_KEYS)
check(not unknown, "消费端没有读「生产端不存在」的键", "、".join(unknown))
for k in SUMMARY:
    check(k in read_keys, "消费端确实在用汇总键 %s（不然等于没接线）" % k)


# ---------------------------------------------------------------------------
# 2) 数值层：屏蔽真后端，断言三个汇总数是真算出来的
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("2) 数值层：簇级口径的 reviewed/dropped/dropped_clusters 必须真算")
print("=" * 72)

NODES = [{"name": "n%d" % i, "type": "ss", "server": "1.1.1.%d" % (i + 1)}
         for i in range(5)]
CLUSTERS = [("fp1", [0, 1]), ("fp2", [2, 3]), ("fp3", [4])]
CFG = {"backends": [{"_name": "fake", "max_tokens": 100}]}

ORIG = ai_review._call_http_raw


def fake_drop_second(prompt, system, cfg, max_tokens, timeout_cap=None):
    """假模型：只剔除第 2 簇（2 个节点）。"""
    return {"drop": [{"c": 2, "why": "同族 server 全在同一个 /24"}]}


ai_review._call_http_raw = fake_drop_second
try:
    drops, st = ai_review.review_clusters(CLUSTERS, NODES, "all", CFG, "t_src", log)
finally:
    ai_review._call_http_raw = ORIG

print("  review_clusters -> %s" % {k: st.get(k) for k in
                                   ("reviewed", "dropped", "dropped_clusters",
                                    "dropped_nodes", "rolled_back")})
check(drops == {1}, "剔除了第 2 簇（下标 1）", "实际 %s" % sorted(drops))
check(st.get("reviewed") == 5, "reviewed = 送审节点数 5", "实际 %s" % st.get("reviewed"))
check(st.get("dropped") == 2, "dropped = 剔除节点数 2（原来这个键根本不存在）",
      "实际 %s" % st.get("dropped"))
check(st.get("dropped_clusters") == 1, "dropped_clusters = 1",
      "实际 %s" % st.get("dropped_clusters"))
check(bool(st.get("drop_detail")), "drop_detail 有内容（喂给 reports/ai_dropped.md）")

missing = [k for k in SUMMARY if k not in st]
check(not missing, "簇级口径提供了全部汇总键", "缺 %s" % "、".join(missing))

# 熔断回滚：剔除比例超阈值时，**三个数都必须归零** —— 回滚了却还报「剔除 N」
# 是另一种假结论（报告说剔了，池子里其实一个没少）。
# ⚠ 阈值是**严格大于**（`ratio > DROP_RATIO_GUARD`，0.6）：恰好 60% 不触发。
#   两个用例把这条边界钉住，免得以后有人把 `>` 改成 `>=`（或反过来）没人发现。
BOUND = [("fp1", [0, 1, 2]), ("fp2", [3, 4])]      # 剔 3/5 = 0.60 -> 不触发
BIG = [("fp1", [0, 1, 2, 3]), ("fp2", [4])]        # 剔 4/5 = 0.80 -> 触发


def fake_drop_first(prompt, system, cfg, max_tokens, timeout_cap=None):
    return {"drop": [{"c": 1, "why": "全死"}]}


ai_review._call_http_raw = fake_drop_first
try:
    _, st_b = ai_review.review_clusters(BOUND, NODES, "all", CFG, "t_src", log)
    drops2, st2 = ai_review.review_clusters(BIG, NODES, "all", CFG, "t_src", log)
finally:
    ai_review._call_http_raw = ORIG
print("  边界 3/5=0.60 -> %s" % {k: st_b.get(k) for k in
                                ("rolled_back", "dropped")})
print("  超阈 4/5=0.80 -> %s" % {k: st2.get(k) for k in
                                ("rolled_back", "dropped", "dropped_clusters")})
check(st_b.get("rolled_back") is False and st_b.get("dropped") == 3,
      "恰好 60% 不触发熔断（阈值是严格大于）",
      "实际 rolled_back=%s dropped=%s" % (st_b.get("rolled_back"), st_b.get("dropped")))
check(st2.get("rolled_back") is True, "超阈值 -> 已回滚")
check(drops2 == set(), "回滚时不真剔除任何簇")
check(st2.get("dropped") == 0 and st2.get("dropped_clusters") == 0,
      "回滚后 dropped/dropped_clusters 都是 0（不能一边回滚一边报剔除）",
      "实际 %s/%s" % (st2.get("dropped"), st2.get("dropped_clusters")))

# 源级口径同样要提供汇总键（否则切回 --ai-unit node 就会重演同一个 bug）
_, st3 = ai_review.review_source(NODES, None, "off", CFG, "t_src", log)
missing3 = [k for k in SUMMARY if k not in st3]
print("  review_source(mode=off) 的键: %s" % "、".join(sorted(st3)))
check(not missing3, "源级口径也提供了全部汇总键", "缺 %s" % "、".join(missing3))


# ---------------------------------------------------------------------------
# 3) 渲染层：报告正文里真的出现数字
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("3) 渲染层：reports/latest.md 里的 AI 数字必须是真的")
print("=" * 72)

manifest = {
    "generated_at": "2026-10-18T04:20:00Z",
    "ai_mode": "all",
    "pages_base": "https://pala911.github.io/clash-source",
    "owner": "pala911",
    "repo": "clash-source",
    "ranking": {"auto": ["anaer"], "备用": [], "观察": ["ermaozi"],
                "detail": {"anaer": {"rate": 78.6, "why": "两视角均达标"},
                           "ermaozi": {"rate": 2.9, "why": "机房友好"}}},
    "totals": {"kept": 100, "merged": 200},
}
metas = [
    {"name": "anaer", "raw_nodes": 868, "kept": 100, "mirror_used": False,
     "ai": {"mode": "all", "reviewed": 100, "dropped": 12, "dropped_clusters": 2,
            "dropped_nodes": 12, "rolled_back": False, "top_reasons": ["同族全死"]}},
    {"name": "ermaozi", "raw_nodes": 744, "kept": 744, "mirror_used": True,
     "ai": {"mode": "all", "reviewed": 744, "dropped": 0, "dropped_clusters": 0,
            "rolled_back": True}},
    {"name": "yypool", "raw_nodes": 900, "kept": 900},      # 没有 ai 记录
]
tmp = tempfile.mkdtemp(prefix="rpai_")
path = os.path.join(tmp, "latest.md")
try:
    report.write_report(path, manifest, metas, ["测试告警"], {})
    md = open(path, encoding="utf-8").read()
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for ln in md.splitlines():
    if "anaer" in ln or "ermaozi" in ln or "yypool" in ln or "审 " in ln:
        print("    %s" % ln[:118])
print()
check("2 簇 / 12 节点" in md, "漏斗表出现「2 簇 / 12 节点」（簇数与节点数都在）")
check("审 100 节点，剔除 12 节点（2 个簇）" in md,
      "AI 摘要行同时给出节点数与簇数")
check("扣除 0" not in md and "审 0，剔除 0" not in md,
      "不再出现「审 0，剔除 0」这种假结论")
check("超阈值已回滚" in md, "回滚状态有单独标注（不然读者以为它剔了 0 个是因为没意见）")
check("| yypool | 900 | 900 | - |" in md,
      "没有 ai 记录的源显示 -（而不是伪装成 0）")
# 备用入口链接必须带 repo 段：少了它 gh-proxy 会 404（原文只有 owner）。
# build.py 顶部注释里写的是对的（owner/repo 两段都有），report.py 这里漏了 ——
# 同一个事实在两处写法不一致，所以断言**完整 URL**，而不是只看「含 gh-proxy」。
check("https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml" in md,
      "gh-proxy 备用链接带 owner/repo 两段（少 repo 会 404）")
check("https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml" in md,
      "jsdelivr 备用链接同样是两段")
# 降级（§75 #6）就是走 warnings 这条路进报告的：这里钉住渲染，免得以后
# 只在日志里喊、报告上却看不出「本轮是降级发布」。
check("测试告警" in md, "warnings 会渲染进报告（降级说明的落地通道）")

# ---------------------------------------------------------------------------
# 4) 留痕文件：reports/ai_dropped.md 的「簇 / 节点」两个口径
# ---------------------------------------------------------------------------
# 线上实测（2026-10-18）：文件里写「共剔除 91 条」，91 其实是**簇数**，
# 涉及 233 个节点 —— 旧文案只有「条」，读者会当成节点数（差 2.5 倍）。
print()
print("=" * 72)
print("4) 留痕文件：ai_dropped.md 不能把「簇数」写成「条/节点数」")
print("=" * 72)
tmp2 = tempfile.mkdtemp(prefix="aidrop_")
try:
    # 4a) 簇级模式：2 簇，覆盖 12 个节点（每簇一条代表节点）
    metas_cl = [
        {"name": "yypool", "ai": {"dropped": 10, "dropped_clusters": 1,
                                  "drop_detail": [{"name": "n1", "type": "vmess",
                                                   "server": "1.2.3.4", "why": "推广",
                                                   "count": 10}]}},
        {"name": "anaer", "ai": {"dropped": 2, "dropped_clusters": 1,
                                 "drop_detail": [{"name": "n2", "type": "http",
                                                  "server": "5.6.7.8", "why": "回环",
                                                  "count": 2}]}},
    ]
    p = os.path.join(tmp2, "ai_dropped.md")
    got = report.write_ai_dropped(p, {"generated_at": "T", "ai_mode": "http"}, metas_cl)
    md = open(p, encoding="utf-8").read()
    check(got == (2, 12, 2, 12), "返回 (簇, 节点, 行, 覆盖) = (2,12,2,12)",
          "实际 %s" % (got,))
    check("共剔除 2 簇 / 12 节点" in md, "表头同时给出簇数与节点数",
          md.splitlines()[2][:90] if len(md.splitlines()) > 2 else md[:90])
    check("| 节点数 |" in md, "每条留痕带「节点数」列（否则 2 行看不出覆盖了 12 个）")
    check("| n1 | vmess | 1.2.3.4 | 10 | 推广 |" in md, "行里带上簇内节点数")

    # 4b) 源级模式：没有簇概念（dropped_clusters 恒 0），行数 = 节点数
    metas_src = [{"name": "src", "ai": {
        "dropped": 3, "dropped_clusters": 0,
        "drop_detail": [{"name": "a", "type": "ss", "server": "x", "why": "占位"},
                        {"name": "b", "type": "ss", "server": "y", "why": "占位"},
                        {"name": "c", "type": "ss", "server": "z", "why": "占位"}]}}]
    p2 = os.path.join(tmp2, "ai_dropped2.md")
    got2 = report.write_ai_dropped(p2, {"generated_at": "T", "ai_mode": "off"}, metas_src)
    md2 = open(p2, encoding="utf-8").read()
    check(got2[:3] == (0, 3, 3), "源级模式 (簇, 节点, 行) = (0,3,3)", "实际 %s" % (got2,))
    check("共剔除 3 节点" in md2 and "簇" not in md2.splitlines()[2],
          "源级模式不提「簇」（它没有簇概念）")
    check("| a | ss | x | 1 | 占位 |" in md2, "源级模式每行的节点数 = 1")

    # 4c) 零剔除：不许出现「共剔除」
    p3 = os.path.join(tmp2, "ai_dropped3.md")
    report.write_ai_dropped(p3, {"generated_at": "T", "ai_mode": "http"},
                            [{"name": "s", "ai": {"dropped": 0, "dropped_clusters": 0,
                                                  "drop_detail": []}}])
    md3 = open(p3, encoding="utf-8").read()
    check("共剔除" not in md3 and "未剔除任何节点" in md3, "零剔除时写「未剔除任何节点」")

    # 4d) 单元格转义：节点名自带 | 会把 5 列的表格撑成 6~7 列（线上 4/53 行中招）；
    #     理由里的换行同样会破表（漏成新行，后面的行全被解析错）。
    metas_esc = [{"name": "s|1", "ai": {
        "dropped": 2, "dropped_clusters": 1,
        "drop_detail": [{"name": "🇺🇸 美国 | USA #2", "type": "vless",
                         "server": "a.example|b", "why": "占位\n第二行",
                         "count": 2}]}}]
    p4 = os.path.join(tmp2, "ai_dropped4.md")
    report.write_ai_dropped(p4, {"generated_at": "T", "ai_mode": "http"}, metas_esc)
    md4 = open(p4, encoding="utf-8").read()
    data_rows = [l for l in md4.splitlines()
                 if l.startswith("| ") and "节点名" not in l]
    widths = [len(re.split(r"(?<!\\)\|", l.strip())) for l in data_rows]
    check(bool(widths) and set(widths) == {7},
          "带 | 的节点名转义后表格仍是 5 列（= 未转义竖线切出 7 段）",
          "各行列数=%s" % (widths,))
    check("\\| USA #2" in md4 and "占位 第二行" in md4,
          "| 被转义、理由里的换行被折成空格")
    check("\n第二行" not in md4, "理由里的换行没有漏成新行（否则后面全串行）")
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

print()
print("=" * 72)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（AI 留痕链：契约一致 / 数值真实 / 报告不为 0 / 留痕两个口径都在）")
