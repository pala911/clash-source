# -*- coding: utf-8 -*-
"""源健康档案：差源降级进历史库，变好自动回收。

⚠ 双口径铁律（2026-10-14 实测校准，坑 §40/§48）：
  CI runner 在**美国**，国内口径只能由本机提供。两者**不是同一件事**，必须分开：

      口径          能判什么          不能判什么
      ────────────────────────────────────────────────────────────
      CI(美国)      是否彻底死了      好不好、能不能排序
      本机(国内)    好不好、能否回收   是否彻底死了（alive=0 是歧义的）

  美国口径不能判优：同一批节点从美国看，通过率系统性虚高 1.8~13 倍
  （shaoyouvip 美国 81.2%(#4) / 国内 6.2%(#11 垫底)，yypool 84.3% / 13.1%），
  Spearman 秩相关只有 0.48，排名基本不可信。mahdibland 的教训正是如此。

  国内口径不能判死：从国内发起的 alive=0 有两种可能 —— 节点真死了，或
  **它的 IP 被 GFW 阻断、我根本连不上**。两者在数据上长得一模一样。
  美国 runner 能直连全球节点 IP，它说「0 活」才近似等于「这节点真废了」。

  所以：**CI 判死，本机判优**（2026-10-14 决定不新增云资源；
  本机探针 12:30 每日跑，CI 从 2026-10-16 起每 6 小时跑）。

阈值：
  - **降级极保守**：CI 连续 3 轮 0 活、**且这些轮次横跨 ≥ 48 小时**才进历史库，
    且永远只是 enabled=false 不删数据。
    （跨度这条是 2026-10-16 加的：L1 的 cron 从每周提到每 6 小时后，
     只数轮数会让判死从 3 周变成 18 小时 —— 见 DEAD_STREAK_HOURS。）
  - **回收积极**：本机 alive ≥ 5 且通过率 ≥ 8% 连续 2 轮就自动放回（宁可多试，不可错杀好源）。
  - 探针不完整（incomplete，大源没加载完）**不参与判定**，否则会把 2000 节点的
    autojiedian 误判成死源。

产物：state/source_health.json（滚动历史）+ archive/sources.yaml（历史库）
      + 就地改写 src/sources.yaml 的 enabled 标志
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEALTH = os.path.join(ROOT, "state", "source_health.json")
ARCHIVE = os.path.join(ROOT, "archive", "sources.yaml")
SOURCES = os.path.join(HERE, "sources.yaml")
PROBE = os.path.join(ROOT, "state", "probe_latest.json")

DEAD_STREAK = 3        # 连续 N 轮 0 活 -> 降级
# 判死还必须**横跨**这么多小时。为什么不是只看轮数：
#   「连续 3 轮 0 活」这条规则的本意是「持续观察三段时间」，不是「数三次」。
#   2026-10-16 把 L1 的 cron 从「每周一」提到「每 6 小时」时会顺手把它变成
#   **18 小时就判死**（原来是 3 周），而本机+云效的回收闸门要 2 轮本机 + 7 轮云效，
#   代价不对称：误杀一个源要等好几天才可能收回来。
#   所以改成「轮数 ≥ DEAD_STREAK **且** 首末轮相隔 ≥ DEAD_STREAK_HOURS」——
#   对任何 cron 频率都自动等价于「观察满两天」，改频率不必再回来调常数。
DEAD_STREAK_HOURS = 48
GOOD_STREAK = 2        # 连续 N 轮达标 -> 回收
GOOD_ALIVE = 5         # 「变好」的活节点下限（绝对值，不是比例）
GOOD_RATE = 8.0        # 「变好」的通过率下限（%）
KEEP_RUNS = 12         # 每源保留最近 N 轮历史（**每个口径各留 N 轮**）

# ---------------------------------------------------------------------------
# 双视角分级（2026-10-15 新增，回应「手机位置是移动的」这一事实）
# ---------------------------------------------------------------------------
# 出发点：本机和云效**都是固定视角**，而用户的手机跨运营商、跨地区、跨 4G/家宽。
# 单个固定视角测的是「那一个网络」，不等于手机的实际体验。实测 rho(云效,本机)
# 仅 0.734 —— 两个视角看的是不同的网络，各自成立但都不完整。
#
# => **分歧本身就是要用的信息**，不是噪音：
#      两边都达标       -> T1 到处能用，可回收
#      本机达标云效不行 -> T2 位置敏感（你手机能用与否取决于在哪，绝不自动回收）
#      本机不行云效行   -> T3 机房友好（家里被压，机房能用）
#      两边都不行       -> T4 到处都不行
#
# 云效**只有否决权、没有决定权**：回收（enabled: false -> true）要求
# 「本机达标 且 云效达标」双视角同意。这让回收只会变**更保守**，
# 符合全系统的保守失败原则；且 T2 类源自动被排除在自动回收之外 ——
# 而这类源恰恰是最不该自动处置的（它在手机上的可用性最不稳定）。
#
# ⚠ 阈值尚未校准。cnci 单轮噪声实测 avg 5.5pp / max 16.7pp（同一份配置、
#   相隔 2 小时的两次运行），与 8% 阈值同量级，单轮结果不可用于判定。
#   因此 cnci 必须攒够 TIER_MIN_CNCI_RUNS 轮、并取最近 TIER_WINDOW 轮均值
#   （理论噪声 5.5/sqrt(7) ≈ 2.1pp）后才参与回收判定。攒够之前只做展示分级。
#   **两周后用实际累积数据回来校准 CNCI 的阈值**，别在此之前调这些常数。
CNCI = os.path.join(ROOT, "state", "probe_cnci_latest.json")
# 稳定性加权写出的「移出竞速池」节点文件的后缀（见 src/build.py 的 write_dist）。
# 探针会测量它们（否则无法翻盘），但它们不是独立的源。
FLAKY_SUFFIX = "--flaky"
TIER_MIN_CNCI_RUNS = 7    # cnci 轮次不足就不参与回收判定（只展示分级）
TIER_WINDOW = 7            # 取最近 N 轮算均值
TIER_REQUIRE_CNCI = True   # True=回收需双视角同意；False=退回本机单视角


def load_probe():
    try:
        return json.load(open(PROBE, encoding="utf-8"))
    except Exception:
        return {}


def load_cnci():
    """读云效（国内第三方 CI，scope=cnci）的探针结果。

    这份数据**可能是过期的甚至缺失的** —— 它来自另一个仓（Codeup），
    要靠推送/同步才能到主仓。所以必须容错，且缺失时不能阻塞主流程。
    """
    try:
        d = json.load(open(CNCI, encoding="utf-8"))
    except Exception:
        return {}
    return d if d.get("scope") == "cnci" else {}


def _num(v, lo=None, hi=None):
    """把探针字段安全转成 float，不合格返回 None。

    ⚠ 为什么需要：实测把某个源的 rate 改成字符串后，
      `recent_mean` 里直接 `sum(vals)/len(vals)` 抛
      `TypeError: '>=' not supported between 'str' and 'float'`，
      **整个 health.py 带 traceback 崩掉** —— 一个源的字段类型漂移
      （上游 JSON 改版、人工改文件都可能）就干掉了整轮健康判定。

      更糟的是它崩在 `save_health()` **之前还是之后**取决于代码顺序，
      也就是说「崩了」和「历史丢了」是同一个 bug 的两种结局。

      探针是本系统里唯一不可信的数据源（它直接吃免费源订阅的内容），
      所以在**入口**做类型与范围校验，而不是等到用它算数时才炸。
    """
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):   # NaN / inf
        return None
    if lo is not None and f < lo:
        return None
    if hi is not None and f > hi:
        return None
    return f


def sanitize_rows(rows):
    """把一轮探针结果里每个源的数值字段校验一遍。

    不合格的**只丢那个源**，其余源照常参与判定 ——
    丢一个源是「少一份信息」，让整轮崩掉是「一份信息都没有」。
    """
    bad = []
    out = {}
    for name, r in (rows or {}).items():
        if not isinstance(r, dict):
            bad.append("%s(不是对象)" % name)
            continue
        rate = _num(r.get("rate"), 0.0, 100.0)
        alive = _num(r.get("alive"), 0)
        nodes = _num(r.get("nodes"), 0)
        if rate is None and r.get("rate") is not None:
            bad.append("%s(rate=%r)" % (name, r.get("rate")))
        if alive is None:
            alive = 0
        if nodes is None:
            nodes = 0
        rr = dict(r)
        if rate is not None:
            rr["rate"] = rate
        else:
            rr["rate"] = None          # recent_mean 会跳过 None
        rr["alive"] = int(alive)
        rr["nodes"] = int(nodes)
        out[name] = rr
    if bad:
        print("[health] ⚠ %d 个源的数值字段不合格，已置空（该源本轮不参与均值/达标判定）：%s"
              % (len(bad), "、".join(bad[:8])))
    return out


def recent_mean(runs, scope, window, field="rate"):
    """取最近 window 轮某口径的均值。

    ⚠ 只用**已 settle 且非 incomplete** 的轮次。alive 在未测完时被系统性低估
      （实测 yypool 只测 5.1% 就退出，alive 报 6、真值 118），混进均值会污染。

    ⚠ window 曾经收了却没用（文档说「最近 window 轮」，实现是「全部轮次」）。
      单口径时代看不出问题，因为总轮数本来就 ≤ 12；但 build.py 的 AUTO 分桶
      直接拿这个均值排序，窗口不封顶就等于让半年前的一轮和昨天的一轮等权 ——
      源的质量变了排名却不动。必须真的按时间取最后 window 轮。
    """
    picked = [r for r in runs
              if r.get("scope") == scope and r.get("settled", True)
              and not r.get("incomplete") and r.get(field) is not None]
    picked = picked[-window:]
    if not picked:
        return None, 0
    vals = [r.get(field) for r in picked]
    return sum(vals) / len(vals), len(vals)


def _hours_between(t0, t1):
    """两个 ISO(UTC) 时间戳之间的小时数。解析不了返回 None。

    ⚠ 用 calendar.timegm + strptime 而不是 datetime.fromisoformat：
      `fromisoformat` 是 Python 3.7+，而本仓有 3.6.8 的运行环境（云效）。
    """
    import calendar
    try:
        a = calendar.timegm(time.strptime(t0, "%Y-%m-%dT%H:%M:%SZ"))
        b = calendar.timegm(time.strptime(t1, "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return None
    return (b - a) / 3600.0


def is_dup_run(runs, ts, scope):
    """这一轮 (ts, scope) 是否已经记过。

    ⚠ 必须扫**整个列表**，不能只看 runs[-1]。曾经只看最后一条，于是当 cnci
      的轮次插到本机轮次之间时，本机那一轮的去重永远失败 —— 同一次探针会被
      反复计数。这个 bug 在只有单一口径时不可见，是引入多视角后才暴露的。
    """
    return any(x.get("ts") == ts and x.get("scope") == scope for x in runs)


def trim_runs(runs, keep=KEEP_RUNS):
    """按口径**各自**裁剪，而不是对整个列表做总数裁剪。

    ⚠ 三种口径的频率差 3 个数量级：CI 每日、cnci 每日、本机每周。
      若按总数裁剪（曾经就是这么写的，KEEP_RUNS=12），日更的 ci 会把
      本机/cnci 的历史整段挤出去 —— 实测灌 7 轮 cnci + 8 轮 local 后
      只剩 6 轮 cnci，导致分级永远判「数据不足」。按口径裁剪才对。
    """
    out, by = [], {}
    for r in runs:
        sc = r.get("scope", "?")
        by.setdefault(sc, []).append(r)
    for sc, rs in by.items():
        out.extend(rs[-keep:])
    out.sort(key=lambda r: r.get("ts") or "")
    return out


def load_health():
    """读健康档案。

    ⚠⚠ 这里原来写的是 `except Exception: return {"sources": {}}` ——
      档案损坏时**静默从零开始**。实测后果：把 source_health.json 写坏后
      再跑一次，anaer 的 5 轮真实历史变成 1 轮，**exit=0、一个字都没说**。

      磁盘满 / 写入中断 / 云效推主仓被截断，任何一个都会触发。
      而 AUTO 分桶的排序质量正是靠这个多轮均值算的 —— 历史一丢，
      排名立刻退化成「只看昨天」。

      不一致的后果严重程度完全不对称：
        跑不成 health.py  -> 质量数据变陈旧，**可恢复**（明天自动补上）
        覆盖掉损坏文件   -> 多轮历史永久消失，**不可恢复**
      所以「文件不存在」可以当空档案开始，「文件存在但读不出来」必须
      **拒绝运行并保留原文件**，绝不静默重建。
    """
    if not os.path.exists(HEALTH):
        return {"sources": {}}
    try:
        with open(HEALTH, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        sys.stderr.write(
            "[health] ═══════════════════════════════════════════════\n"
            "[health] ✗ 拒绝运行：健康档案已损坏，且**没有**重建它。\n"
            "[health]   文件    : %s\n"
            "[health]   原因    : %s: %s\n"
            "[health]   为什么不能静默重建：档案里是累积的多轮历史，\n"
            "[health]   覆盖掉就是永久丢失（磁盘满/写入中断都会走到这里）。\n"
            "[health]   不一致的后果不对称 —— 跑不成只是数据变陈旧（可恢复），\n"
            "[health]   覆盖掉是历史永久消失（不可恢复）。\n"
            "[health]   处理    : 先把损坏文件挪走，再跑本脚本即可从零重建。\n"
            "[health]             mv \"%s\" \"%s.bak\"\n"
            "[health] ═══════════════════════════════════════════════\n"
            % (HEALTH, type(e).__name__, str(e)[:80], HEALTH, HEALTH))
        sys.exit(2)
    if not isinstance(d, dict) or "sources" not in d:
        sys.stderr.write("[health] ✗ 拒绝运行：健康档案结构不对（缺 sources 键）：%s\n" % HEALTH)
        sys.exit(2)
    return d


def _atomic_write(path, text):
    """先写临时文件再 os.replace —— 崩溃时原文件完好无损。

    之前是 `json.dump(h, open(path, "w"))`，写到一半崩溃就留下**半截 JSON**，
    而下一次 load_health 又会把它当损坏处理 → 触发一轮历史丢失。
    两件事叠加，磁盘抖一下历史就没了。
    """
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())          # 真落盘再 rename
    os.replace(tmp, path)             # 3.3+，同目录内是原子操作


def save_health(h):
    _atomic_write(HEALTH, json.dumps(h, ensure_ascii=False, indent=2))


def src_cfg():
    import yaml
    return yaml.safe_load(open(SOURCES, encoding="utf-8")) or {}


def write_src_cfg(cfg, prev_count=None):
    """写回源清单。

    ⚠ 理智守卫：源清单是整个 pipeline 的**唯一事实来源**，而且进 git。

      实测两个失败方式：
        ·传进 `sources: []`   -> 99 行的 12 源清单被改写成空，然后 commit 上去
        · 传进只剩 1 个源      -> 同上，只是没这么显眼

      「归零」和「暴跌」是同一类事故。**降级是逐个源、跨多轮、且只改 enabled
      开关的渐进过程**，任何一次调用都不该把源数量砍掉一半以上——
      真要那么干，说明上游出事了，而这时候最该做的是停下来报警，不是照写。

      所以：归零、或少于上一轮的一半，一律拒绝。
      真要人工大批量删源，用 --allow-source-shrink 显式解锁（需人工确认）。
    """
    import yaml
    n = len(cfg.get("sources") or [])
    if n == 0:
        raise SystemExit(
            "[health] ✗ 拒绝写入：源清单里一个源都没有（sources 为空）。\n"
            "         宁可不改，也不能把 pipeline 的唯一事实来源写成空 ——\n"
            "         这个文件进 git，一旦提交上去整个仓库的源就全没了。")
    if (prev_count and n < prev_count * 0.5 and not
            os.environ.get("ALLOW_SOURCE_SHRINK")):
        raise SystemExit(
            "[health] ✗ 拒绝写入：源数量从 %d 骤降到 %d（不到一半）。\n"
            "         降级只会逐个源、跨多轮、只改 enabled 开关，不会一次砍掉一半。\n"
            "         这种降幅几乎总是上游出事了（清单被截断/解析失败/变量没展开）。\n"
            "         确认要删就设 ALLOW_SOURCE_SHRINK=1 再跑。" % (prev_count, n))
    body = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=4096)
    _atomic_write(SOURCES,
                  "# 上游源清单 —— pipeline 的唯一事实来源\n"
                  "# 注意：enabled 标志由 src/health.py 依据真探针自动维护\n"
                  "#   连续多轮 0 活 -> enabled: false 并移入 archive/sources.yaml（历史库）\n"
                  "#   达标后自动回填 enabled: true（源本体永不删除，只改开关）\n"
                  + body)


def arch_cfg():
    import yaml
    try:
        return yaml.safe_load(open(ARCHIVE, encoding="utf-8")) or {}
    except Exception:
        return {"sources": []}


def write_arch(cfg):
    """历史库也走原子写 —— 它同样在 git 里，同样不能被半截 YAML 覆盖。"""
    import yaml
    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    _atomic_write(ARCHIVE,
                  "# 历史库：曾启用但被判死的源。**源本体永不删除**，只是被摘掉。\n"
                  "# 判据：真探针（youtube/generate_204）连续 %d 轮 0 活，且横跨 ≥ %d 小时。\n"
                  "# 恢复：alive ≥ %d 且通过率 ≥ %s%% 连续 %d 轮 -> health.py 自动回填 enabled: true。\n"
                  "# ⚠ 探针 runner 在美国，判据偏保守（宁可多留，不可错杀）。\n"
                  % (DEAD_STREAK, DEAD_STREAK_HOURS, GOOD_ALIVE, GOOD_RATE, GOOD_STREAK)
                  + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=4096))


def main():
    import yaml
    probe = load_probe()
    rows = (probe.get("sources") or {})
    scope = probe.get("scope", "ci")
    if not rows:
        print("[health] 无探针数据，跳过（先跑 src/probe.py）")
        return 0

    # ⚠ 在入口校验数值字段，不要等到用它算数时才炸。
    #   探针是唯一直接吃外部内容的数据源，字段类型漂移是迟早的事；
    #   而一个源的坏字段不该让整轮健康判定崩掉（只丢那个源即可）。
    rows = sanitize_rows(rows)

    h = load_health()
    hs = h.setdefault("sources", {})
    cfg = src_cfg()
    # 写回前先记住源数量：write_src_cfg 用它识别「源数量暴跌」。
    # 降级是逐个源、跨多轮、只改 enabled 开关的渐进过程，
    # 一次调用砍掉一半以上的源几乎总是上游出事了。
    prev_src_count = len(cfg.get("sources") or [])
    arch = arch_cfg()
    arch_by_name = {s["name"]: s for s in (arch.get("sources") or [])}
    src_by_name = {s["name"]: s for s in (cfg.get("sources") or [])}
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # 用**探针自己的时间戳**当这一轮的身份，而不是 health.py 的运行时刻。
    # 这样重复跑（CI 重试 / 手动再跑一次 / local_probe 的 --scope-only）能被识别为
    # 「同一轮」而不重复计数 —— 否则一次真实探针就能凭空攒出 good_streak=2 触发回收。
    #
    # ⚠ 回退分支必须用纳秒级唯一值：probe.probed_at 是秒级精度，若回退也用秒级，
    #   同一秒内的两次调用会被误判成同一轮而**漏计**（实测踩到：连续 3 轮 0 活
    #   只攒出 bad_streak=1，降级永远不触发）。
    ts = probe.get("probed_at") or ("%s#%d" % (now, time.time_ns()))
    hc_to = probe.get("hc_timeout_ms")
    h["last_probe"] = {"ts": ts, "scope": scope, "hc_timeout_ms": hc_to}

    # ------------------------------------------------------------------
    # 先把云效（scope=cnci）这一轮记进档案 —— **只记档，不碰任何 streak**。
    # 必须排在主探针循环之前：下面的回收判定要读 cnci 的均值来当否决闸门。
    # ------------------------------------------------------------------
    cnci = load_cnci()
    cnci_rows = (cnci.get("sources") or {})
    cnci_ts = cnci.get("probed_at") or ""
    cnci_ok = 0
    if not cnci_rows:
        print("[health] ⚠ 无云效(cnci)数据 -> 分级标为未知"
              + ("，回收需要双视角同意，本轮不回收任何源" if TIER_REQUIRE_CNCI else ""))
    else:
        for name, r in sorted(cnci_rows.items()):
            if name not in hs:
                continue
            # 未 settle / incomplete 的轮次直接丢弃，不进历史。
            # cnci 是抽样(n=30)，未测完会让 alive 归零，把好源误标成「机房不可用」。
            if r.get("incomplete") or not r.get("settled", True):
                continue
            runs = hs[name].setdefault("runs", [])
            # 幂等：同一 probed_at 重复推送不重复计数。
            if is_dup_run(runs, cnci_ts, "cnci"):
                continue
            runs.append({"ts": cnci_ts, "scope": "cnci", "sampled": True,
                         "hc_timeout_ms": cnci.get("hc_timeout_ms"),
                         "nodes": r.get("nodes"), "tested": r.get("tested"),
                         "alive": r.get("alive"), "rate": r.get("rate"),
                         "best_ms": r.get("best_ms"),
                         "settled": True, "incomplete": False})
            # ⚠ 必须回写给局部变量。trim_runs 返回**新列表**，若只赋给
            #   rec["runs"] 而不更新 runs，后面 recent_mean(runs,...) 读到的
            #   仍是裁剪前的旧列表 -> 云效轮次永远只数到 1 轮，分级永远「数据不足」。
            #   这个别名不同步的坑在单口径时代一直潜伏着（当时没人读 runs 的历史），
            #   是引入多视角分级后才第一次真正发作。
            runs = trim_runs(runs)
            hs[name]["runs"] = runs
            cnci_ok += 1

    changed_enabled = []
    dup_sources = []
    unsettled = {}
    tiers = {}
    for name, r in sorted(rows.items()):
        # ⚠ 跳过「不稳定节点」那部分产生的伪源名。
        #   稳定性加权会把移出竞速池的节点写进 dist/nodes/<源>--flaky.yaml，
        #   而探针的发现逻辑是 glob('*.yaml')，所以它们**确实会被测量** ——
        #   这是刻意的：不测就永远无法翻盘。但它们不该作为独立「源」进档案。
        #   今天不跳过也不会误降级（降级有 `name in src_by_name` 兜底），
        #   但档案里会凭空多出「anaer--flaky」这种不存在的源、reports 里出现噪声，
        #   攒到 bad_streak=3 还会让人误以为真出了个新源。直接过滤干净。
        if name.endswith(FLAKY_SUFFIX):
            continue
        if r.get("incomplete"):
            print("[health] %-24s 跳过本轮（探针未完成：%s/%s 节点已加载）"
                  % (name, r.get("nodes"), r.get("expected")))
            continue
        # ⚠ 未 settle（还有节点没跑到探测结果）的源，alive 被**系统性低估** ——
        #   2026-10-15 实踩：yypool 只测了 5.1% 就退出，alive 报 6（真值 118），
        #   而 rate 却是 13.0%（真值 13.1%）几乎看不出异常。只看 rate 根本发现不了。
        #   因为「变好」判据是 alive >= 5，低估会让好源看起来变差 -> good_streak
        #   被清零 -> 回收永远不触发。这类源只记录、不参与自动判定。
        if not r.get("settled", True):
            unsettled[name] = r
            print("[health] %-24s 跳过本轮（未测完：%s/%s 已测，alive 低估不可用）"
                  % (name, r.get("tested"), r.get("nodes")))
            continue
        rec = hs.setdefault(name, {"runs": [], "bad_streak": 0, "good_streak": 0,
                                   "bad_since": None, "state": "active"})
        runs = rec.setdefault("runs", [])
        is_dup = is_dup_run(runs, ts, scope)
        if is_dup:
            dup_sources.append(name)
            # ⚠ 这里原来是无条件 continue，那是个真 bug：
            #   主探针重复（local_probe --scope-only / CI 重试 / 手动再跑一次）
            #   时会**整段跳过**下面的分级计算 —— 而云效那一轮恰恰是刚刚
            #   新追加进来的。结果是：云效每天都跑了新数据，分级却永远停在
            #   第一次的快照上，看起来像「云效的数据没生效」。
            #   所以改成：只跳过 streak 累积与升降级，分级照算。
            is_new = False
        else:
            is_new = True
            runs.append({"ts": ts, "scope": scope, "sampled": bool(r.get("is_sampled")),
                         "hc_timeout_ms": hc_to,
                         "nodes": r["nodes"], "alive": r["alive"], "rate": r["rate"],
                         "best_ms": r["best_ms"]})
            # ⚠ 同上：回写局部变量，否则下面的 recent_mean 读到的是旧列表。
            runs = trim_runs(runs)
            rec["runs"] = runs
            # ⚠ hc_timeout 直接线性偏置 alive（shaoyouvip 单源实测：
            #   2s/3s -> 0 活，5s -> 1 活，8s -> 4 活，15s -> 6 活）。
            #   换了这个参数，前后两轮的 alive 就不可比了 —— 拿旧口径攒的 streak
            #   去判新口径的升降级是错的。参数一变就清零重新攒。
            #   ⚠ 只跟**同一口径**的历史比：cnci 改了超时不该把本机的 streak 清零，
            #   反之亦然（那是两个不同视角的测量口径，各自独立）。
            prev_to = next((x.get("hc_timeout_ms") for x in reversed(runs[:-1])
                            if x.get("scope") == scope
                            and x.get("hc_timeout_ms") is not None), None)
            if prev_to is not None and hc_to is not None and prev_to != hc_to:
                rec["bad_streak"] = rec["good_streak"] = 0
                rec["bad_since"] = None
                print("[health] %-24s ⚠ hc_timeout %s -> %s ms，测量口径已变，"
                      "连续计数清零重新攒" % (name, prev_to, hc_to))
        alive, rate = r["alive"], r["rate"]
        sampled = bool(r.get("is_sampled"))

        # --- 判定（2026-10-14 修正，这里原有真实 bug）---
        # 两条计数器**各自独占一种口径**，对称且互不干扰：
        #
        #   bad_streak  只由 CI（美国）口径累积 —— 判死。
        #     因为从国内看 alive=0 是**歧义的**：节点真死了？或它的 IP 被 GFW 阻断、
        #     我们根本连不上？美国 runner 能直连全球节点 IP，它说 0 活才可信。
        #     （反过来说，也正因为如此，「判死」不能搬到任何国内机器上去做。）
        #
        #   good_streak 只由本机（国内）口径累积 —— 判优 / 回收。
        #     原实现里 else 分支（alive>0 但 rate 未达标）会无条件清零 good_streak，
        #     而 CI 每天都在跑，于是本机攒的 good_streak 每天被抹掉，
        #     「变好回收」永远达不到 GOOD_STREAK —— 那是死代码。
        #     美国口径也不该参与：实测 ssrsub 美国#2/国内#2 尚可，但 shaoyouvip
        #     美国 81.2%(#4) / 国内 6.2%(#11 垫底)，Spearman rho 仅 0.48，不可信。
        #
        # 另加两条护栏（给「国内第三方 CI + 抽样」这条路用的）：
        #   抽样数据永远不参与降级。n=30、真实通过率 10% 时抽 30 个全死的概率
        #   = 0.9^30 ≈ 4.2%，一轮 12 源就有 40% 概率至少错判一个。
        #   scope=cnci **不参与降级**（判死仍然只由美国 CI 口径做，铁律①不动），
        #   但从 2026-10-15 起它对**回收**有否决权（见下面的 tier 闸门）。
        dead = (alive == 0)
        # ⚠ rate 可能是 None（sanitize_rows 把不合格的字段置空了）。
        #   此时**必须整段跳过该源的 streak 累积**，而不是当成「不达标」。
        #   区别很大：当成不达标 -> good_streak 被清零；而如果 alive 恰好是 0，
        #   还会去累加 bad_streak -> **触发降级**，那是不可逆的误杀。
        #   数据坏掉时唯一正确的反应是「这一轮我不知道」，不是「这一轮它差」。
        rate_unknown = (rate is None)
        good = (not rate_unknown) and alive >= GOOD_ALIVE and rate >= GOOD_RATE
        if is_new:
            if rate_unknown:
                dup_sources.append(name)      # 复用同一套「本轮跳过」提示
            elif dead:
                if scope == "ci" and not sampled:
                    if not rec["bad_streak"]:
                        # 记下「连续 0 活」是从哪一轮开始的。判死要用它算跨度，
                        # 而不是数轮数 —— 理由见 DEAD_STREAK_HOURS 的注释。
                        rec["bad_since"] = ts
                    elif not rec.get("bad_since"):
                        # 老档案（本次改动之前建的）没有这个字段。
                        # 保守起见把起点当成「现在」：宁可晚判死，不可早判死。
                        rec["bad_since"] = ts
                        print("[health] %-24s 旧档案缺 bad_since，跨度从本轮重新起算"
                              % name)
                    rec["bad_streak"] += 1
                rec["good_streak"] = 0
            else:
                # 两个口径一致认同的一点：只要有活节点，「没死」这个事实就成立
                rec["bad_streak"] = 0
                rec["bad_since"] = None
                if scope == "local":
                    rec["good_streak"] = rec["good_streak"] + 1 if good else 0

        # --- 双视角分级（2026-10-15 新增，见文件头 TIER_* 常量的说明）---
        # 两个视角都是**固定**的，而用户的手机在移动。所以单点达标不等于
        # 到处可用；反过来，单点不达标也不等于到处不可用。分歧要单独标出来。
        lrate, ln = recent_mean(runs, "local", TIER_WINDOW)
        crate, cn = recent_mean(runs, "cnci", TIER_WINDOW)
        if os.environ.get("HEALTH_DEBUG"):
            # 留着的理由：这个块曾经静默失效过一次（主探针重复轮次提前 continue，
            # 分级永远停在第一次快照），而症状是「云效明明跑了却没反应」——
            # 光看 code 很难看出来。设 HEALTH_DEBUG=1 就能看到它到底看见了什么。
            import collections
            print("[DEBUG] %s runs列表长=%d 各口径=%s cnci轮=%d" %
                  (name, len(runs), dict(collections.Counter(
                      x.get("scope") for x in runs)), cn))
        # cnci 只看 rate、绝不看 alive：抽样 30 个节点时 alive>=5 相当于
        # 通过率 >= 16.7%，而本机全量 300 节点时 alive>=5 只相当于 >= 1.7%，
        # 同一个绝对阈值在两边的含义差 10 倍，直接比会得出荒谬结论。
        cnci_ready = cn >= TIER_MIN_CNCI_RUNS
        if lrate is None:
            tier, why = "?", "无本机口径数据"
        elif crate is None:
            tier, why = "?", "无云效口径数据"
        elif not cnci_ready:
            tier, why = "?", "云效仅 %d/%d 轮，样本不足" % (cn, TIER_MIN_CNCI_RUNS)
        elif lrate >= GOOD_RATE and crate >= GOOD_RATE:
            tier, why = "T1", "两视角均达标"
        elif lrate >= GOOD_RATE:
            tier, why = "T2", "本机 %.1f%%/云效 %.1f%% -> 位置敏感" % (lrate, crate)
        elif crate >= GOOD_RATE:
            tier, why = "T3", "本机 %.1f%%/云效 %.1f%% -> 机房友好" % (lrate, crate)
        else:
            # ⚠ 这一格以前不存在。四格表（README §7）里第4 行是「两边都差 ->
            #   到处都不行」，但代码只有三个分支，else 把「本机差+云效也差」
            #   和「本机差+云效达标」混在一起，统统标成 T3「机房友好」。
            #   危害不是显示难看：T3 按规划要用于**降优先级**，一个到处都不行的
            #   源被标成「机房友好」等于**主动误导**——运维看到 T3 会以为
            #   「家里不行但机房能用，值得留」，而事实是两头都不行。
            #   真实数据里 snakem982 就是这一格：本机 4 轮均值 5.5% / 云效 0.0%。
            tier, why = "T4", "本机 %.1f%%/云效 %.1f%% -> 两视角都不达标" % (lrate, crate)
        rec["tier"], rec["tier_why"] = tier, why
        rec["tier_rates"] = {"local": lrate, "cnci": crate, "cnci_runs": cn}
        tiers[name] = tier

        # ⚠ 升降级只在**新增**轮次时执行。重复轮次上重复执行会让
        #   「刚被降级、紧接着重跑一次」立刻又升回来，等于取消降级。
        if not is_new:
            print("[health] %-24s scope=%-5s [重复轮] alive=%-4d rate=%-5s "
                  "坏%s/好%s 分级=%-2s 状态=%s"
                  % (name, scope, alive, rate,
                     rec["bad_streak"], rec["good_streak"], tier, rec["state"]))
            continue

        if rec["state"] == "active" and rec["bad_streak"] >= DEAD_STREAK:
            # 三重保险：bad_streak 只可能在 scope==ci 且非抽样时累积，这里再挡一次
            span = _hours_between(rec.get("bad_since") or ts, ts)
            if scope != "ci" or sampled:
                pass
            elif span is None:
                # 时间戳解析不出来 = 「我不知道这跨度有多久」，唯一正确的反应是
                # 不判死（判死不可逆，回收要等好几天），但**必须说出来**，
                # 否则又是一次静默失败。
                print("[health] %-24s ⚠ 轮次时间戳无法解析（bad_since=%r），"
                      "本轮不判死" % (name, rec.get("bad_since")))
            # 再加一道**跨度**闸门：轮数够了还要看这些轮次横跨了多久。
            # 只看轮数会随着 cron 提速而自动变激进（每 6 小时 = 18 小时判死，
            # 原来是 3 周），而回收的代价高得多 —— 见 DEAD_STREAK_HOURS 的注释。
            elif span < DEAD_STREAK_HOURS:
                print("[health] %-24s 连续 %d 轮 0 活，但只横跨 %.1fh（< %dh）："
                      "判死不提速（cron 变快不等于判死变快）"
                      % (name, rec["bad_streak"], span, DEAD_STREAK_HOURS))
            elif name in src_by_name:
                src_by_name[name]["enabled"] = False
                src_by_name[name]["quarantine_reason"] = \
                    "真探针连续 %d 轮 0 活（横跨 %.0fh）" % (DEAD_STREAK, span)
                changed_enabled.append("%s -> 降级入历史库" % name)
                arch_by_name.setdefault(name, {})
                arch_by_name[name].update({
                    "name": name, "url": src_by_name[name]["url"],
                    "note": src_by_name[name].get("note", ""),
                    "quarantined_at": now,
                    "quarantine_reason": "真探针连续 %d 轮 0 活（横跨 %.0fh）"
                                         % (DEAD_STREAK, span),
                })
                rec["state"] = "quarantined"
        elif rec["state"] == "quarantined" and rec["good_streak"] >= GOOD_STREAK:
            # good_streak 已由上面的逻辑保证只有 scope==local 才累积，这里是二次保险。
            # CI 口径的分数毫无意义：美国跑出来 ssrsub 90%、shaoyouvip 81%（国内实测垫底 6.2%），
            # 拿它判回收会把差源误收回来。
            #
            # 2026-10-15 起再加一道**云效否决闸门**：回收要求两个视角都达标（T1）。
            # 设计取向是「让回收更保守、绝不更激进」——
            #   * 云效否决 = 不回收。失败方向是「多留一个源在历史库里」，可逆、无害。
            #   * 云效若能单独放行 = 会把差源捞回池子。那是不可逆的污染。
            # 所以云效只有否决权。没有决定权。
            if scope != "local":
                print("[health] %-24s CI 口径不判回收（等本机探针确认）" % name)
            elif TIER_REQUIRE_CNCI and not cnci_ready:
                print("[health] %-24s 暂不回收（云效样本 %d/%d 轮不足，双视角未达成一致）"
                      % (name, cn, TIER_MIN_CNCI_RUNS))
            elif TIER_REQUIRE_CNCI and tier != "T1":
                print("[health] %-24s 暂不回收（云效否决：%s）" % (name, why))
            elif name in src_by_name:
                src_by_name[name]["enabled"] = True
                src_by_name[name].pop("quarantine_reason", None)
                changed_enabled.append("%s -> 达标回收（T1 双视角）" % name)
                arch_by_name.pop(name, None)
                rec["state"] = "active"

        print("[health] %-24s scope=%-5s%s alive=%-4d rate=%-5s 坏%s/好%s 分级=%-2s 状态=%s"
              % (name, scope, "[抽样]" if sampled else "     ", alive, rate,
                 rec["bad_streak"], rec["good_streak"], tier, rec["state"]))

    if changed_enabled:
        # 传上一轮的源数量，让 write_src_cfg 能识别「暴跌」而不只是「归零」
        write_src_cfg(cfg, prev_count=prev_src_count)
        arch["sources"] = list(arch_by_name.values())
        write_arch(arch)
    save_health(h)
    if dup_sources:
        print("[health] 其中 %d 个源识别为「同一轮探针」（ts=%s）已跳过重复计数"
              % (len(dup_sources), ts))
    if unsettled:
        print("[health] ⚠ %d 个源未测完，本轮不参与自动判定（alive 被低估）：%s"
              % (len(unsettled), "、".join(sorted(unsettled))))
    if changed_enabled:
        print("[health] 已更新 sources.yaml / archive/sources.yaml: %s" % "，".join(changed_enabled))
    elif not dup_sources:
        print("[health] 无升降级变更")

    # ---- 分级汇总：把「云效的数据到底怎么用」摊开给人看 ----
    if tiers:
        print("")
        print("[health] === 双视角分级（本机 vs 云效，两个固定视角，手机位置是移动的）===")
        buckets = {"T1": [], "T2": [], "T3": [], "T4": [], "?": []}
        for nm in sorted(tiers):
            buckets.setdefault(tiers[nm], []).append(nm)
        label = {"T1": "两视角都达标，到处能用",
                 "T2": "本机行/云效不行 -> 位置敏感，自动回收会排除它",
                 "T3": "本机不行/云效行 -> 机房友好",
                 "T4": "两视角都不行 -> 到处都不行，该考虑降级",
                 "?": "数据不足，暂不判定"}
        for k in ("T1", "T2", "T3", "T4", "?"):
            if not buckets.get(k):
                continue
            print("[health] %-3s %-38s %s" % (k, label.get(k, ""), "、".join(buckets[k])))
        max_cnci_runs = max([(hs[n].get("tier_rates") or {}).get("cnci_runs") or 0
                             for n in tiers] or [0])
        print("[health] 本轮记入云效数据 %d 个源；单源最多已有 %d 轮%s"
              % (cnci_ok, max_cnci_runs,
                 "" if max_cnci_runs >= TIER_MIN_CNCI_RUNS else
                 "（< %d，分级仅供参考，**不参与回收判定**）" % TIER_MIN_CNCI_RUNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())