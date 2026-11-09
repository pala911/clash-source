# -*- coding: utf-8 -*-
"""7 源末位淘汰联赛 —— 本机（国内口径）每轮排名，挑战者换掉在册末位。

拍板（2026-11-02，用户）：enabled 稳态 = 7 个源；AUTO 只挂前 4 竞速
（build.py AUTO_MAX=4，2026-11-04 由 3 调整）；挑战者（云效粗筛通过的本机终审候选 + 被降级的
relegated 源）在国内口径排名超过在册末位 +5pp 就换位。**被淘汰源不进
excluded、不消失**——打 relegated 日期标留在 sources.yaml，每轮重探参加
竞争，翻盘了就换回来。

写者纪律（三通道各一个写者，沿用 2026-10-29 refill 的分域设计）：
  - discovered_pool.json = CI discover 独享
  - eval_verdicts.json   = 本机 eval 独享
  - sources.yaml 的 enabled 翻转 = health.py（质量死/隔离）+ **本文件（排名
    换位）**。两者语义不同：health 管「死了/隔离」，league 管「排名靠后」；
    league 换位前会检查 health tier，quality-death 的源不归 league 管。

数据源（都是现成产物，本脚本不自建事实）：
  - state/probe_latest.json   scope=local 的每源 rate（本机 12:30 探针，settled）
  - data/eval_verdicts.json   通道 approved 候选（本机终审 rate）
  - relegated 源的 fresh rate 本脚本每轮自己重探（fetch→清洗→抽样 25→真探针）

节流：换位 ≥24h 间隔 + 每轮 ≤1 次（state/league_last.json）。
失败方向：任何异常都「不换位」并大声说明，绝不带崩 12:30 主链。

用法：
    python src/league.py                # 真跑（重探 relegated + 决策 + 写入 + state）
    python src/league.py --dry-run     # 全程打印，不写 sources.yaml/state
    python src/league.py --skip-reprobe  # relegated 用上轮记录的 rate，本轮不重探
    LEAGUE_DISABLE=1                   # 紧急停用开关
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import yaml                                     # noqa: E402
import health                                   # noqa: E402  (_src_entries/_atomic_write/_hours_between)
import refill                                   # noqa: E402  (TARGET_CAP/_plain)

SOURCES = os.path.join(HERE, "sources.yaml")
PROBE_LATEST = os.path.join(ROOT, "state", "probe_latest.json")
VERDICTS = os.path.join(ROOT, "data", "eval_verdicts.json")
STATE = os.path.join(ROOT, "state", "league_last.json")

MIHOMO = os.environ.get("MIHOMO_BIN", r"C:\Program Files\Clash Verge\verge-mihomo.exe")
WORKDIR = os.path.join(ROOT, ".league_work")
STAGEDIR = os.path.join(ROOT, ".league_stage")

MARGIN_PP = 5.0          # 挑战者必须比在册末位高这么多 pp 才换位（防抖动）
CHALL_MIN_ALIVE = 3      # 挑战者最少活节点
CHANNEL_MIN_NODES = 20   # 通道候选最少样本数（2026-11-02 真事故：7 节点 3 活的
                         # 小源 42.9% 差点换掉 184 节点的 leilaomi —— 样本太小，
                         # 比率不可比。relegated 重探固定抽 25，不存在这个问题）
REPROBE_SAMPLE = 25      # relegated 重探抽样数（分层）
MIN_GAP_HOURS = 24       # 两次换位最小间隔


def say(m):
    print("[league] %s" % m)


def warn(m):
    print("[league] ⚠ %s" % m)


def fnum(v, default=0.0):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default
    return float(v)


# ---------------------------------------------------------------------------
# 纯决策函数（IO 无关，单测直接打这里）
# ---------------------------------------------------------------------------
def decide(enabled_rates, challenger_rates, cap, margin_pp=MARGIN_PP):
    """enabled_rates/challenger_rates: {name: (rate, alive)}。

    返回 (action, out_name, in_name, why)：
      swap   -> out_name(在册末位) 换成 in_name(最强挑战者)
      promote-> in_name 补空位（enabled < cap，无 margin 要求）
      hold   -> 不动（why 说明原因）
    纪律：并列时 rate 相同取 alive 高者；挑战者 alive < CHALL_MIN_ALIVE 不配。
    """
    def rk_best(t):
        """最强：rate 降序，并列取 alive 降序。"""
        rate, alive = t
        return (-fnum(rate), -fnum(alive))

    def rk_worst(t):
        """最弱：rate 升序，并列取 alive 降序（先砍活节点少的）。"""
        rate, alive = t
        return (fnum(rate), -fnum(alive))

    if len(enabled_rates) < cap:
        if challenger_rates:
            best = sorted(challenger_rates.items(),
                          key=lambda kv: rk_best(kv[1]))[0]
            if fnum(best[1][1]) >= CHALL_MIN_ALIVE:
                return "promote", None, best[0], "补空位（enabled %d/%d）" % (
                    len(enabled_rates), cap)
        return "hold", None, None, "缺员但无可晋升挑战者"
    if not enabled_rates:
        return "hold", None, None, "enabled 为空"
    worst = sorted(enabled_rates.items(), key=lambda kv: rk_worst(kv[1]))[0]
    if not challenger_rates:
        return "hold", None, None, "无挑战者"
    qualified = {n: t for n, t in challenger_rates.items()
                 if fnum(t[1]) >= CHALL_MIN_ALIVE}
    if not qualified:
        return "hold", None, None, "挑战者全部 alive < %d" % CHALL_MIN_ALIVE
    best = sorted(qualified.items(), key=lambda kv: rk_best(kv[1]))[0]
    gap = fnum(best[1][0]) - fnum(worst[1][0])
    if gap >= margin_pp:
        return "swap", worst[0], best[0], (
            "挑战者 %.1f%% > 在册末位 %s %.1f%%（+%.1fpp ≥ %.0fpp）"
            % (fnum(best[1][0]), worst[0], fnum(worst[1][0]), gap, margin_pp))
    return "hold", None, None, (
        "最强挑战者 %s %.1f%% 未超在册末位 %s %.1f%%（差 %.1fpp < %.0fpp）"
        % (best[0], fnum(best[1][0]), worst[0], fnum(worst[1][0]),
           max(gap, 0), margin_pp))


# ---------------------------------------------------------------------------
# 数据读取
# ---------------------------------------------------------------------------
def load_local_rates():
    """probe_latest.json 必须是 scope=local 且 settled 的每源 rate（国内口径）。

    CI（美国）刚覆盖完的文件 scope=ci —— 直接放弃：美国口径不能排名（rho=0.48）。
    """
    try:
        d = json.load(open(PROBE_LATEST, encoding="utf-8"))
    except Exception as e:                          # noqa: BLE001
        warn("probe_latest.json 读不了：%r" % e)
        return None
    if d.get("scope") != "local":
        warn("probe_latest.json 是 scope=%s（美国 CI 口径），不能用于排名，本轮放弃"
             % d.get("scope"))
        return None
    out = {}
    for name, row in (d.get("sources") or {}).items():
        if name.endswith("--flaky"):
            continue
        if not row.get("settled"):
            # 0 节点 = 源本轮确实产出空（上游 404 / 抓取失败 / 100% 重复未挂载），
            # 按 0 分参与排名：否则一个死源会让「缺速率 -> 整轮 hold」永久冻结
            # 联赛（2026-11-09 free-nodes 上游 404 实踩）。
            # nodes>0 但未 settled 是探针时间盒没测完，仍按「缺速率」处理，
            # 不能把好源误判成末位（原纪律不变）。
            if int(row.get("nodes") or 0) == 0:
                out[name] = (0.0, 0.0)
            continue
        out[name] = (fnum(row.get("rate")), fnum(row.get("alive") or 0))
    return out or None


_IDENT_RAW = re.compile(r"raw\.githubusercontent\.com/(.+)$", re.I)
_IDENT_GHRAW = re.compile(r"github\.com/([^/]+)/([^/]+)/(?:raw|blob)/([^/]+)/(.+)$", re.I)
_IDENT_JSD = re.compile(r"jsdelivr\.net/gh/([^/]+)/([^/@]+)@[^/]+/(.+)$", re.I)
_IDENT_CNB = re.compile(r"cnb\.cool/([^/]+)/([^/]+)/-/git/raw/[^/]+/(.+)$", re.I)


def _clean_path(p):
    return p.split("?")[0].split("#")[0].strip("/")


def source_identity(url):
    """把镜像/分支差异归一成「仓库内文件身份」，用于判重。

    ghproxy.net/https://raw.githubusercontent.com/a/b/main/x.yaml
    raw.githubusercontent.com/a/b/refs/heads/main/x.yaml
    cdn.jsdelivr.net/gh/a/b@main/x.yaml
    三者都 -> gh:a/b/x.yaml
    """
    u = str(url or "").strip()
    m = _IDENT_RAW.search(u)
    if m:
        parts = _clean_path(m.group(1)).split("/")
        if len(parts) >= 3:
            owner, repo, rest = parts[0], parts[1], parts[2:]
            if rest[:2] == ["refs", "heads"]:
                rest = rest[2:]
            if len(rest) >= 2:                      # 第一段是分支
                return ("gh:%s/%s/%s"
                        % (owner, repo, "/".join(rest[1:]))).lower()
    m = _IDENT_GHRAW.search(u)                      # ghproxy.net/github.com/...
    if m:
        return ("gh:%s/%s/%s"
                % (m.group(1), m.group(2), _clean_path(m.group(4)))).lower()
    m = _IDENT_JSD.search(u)
    if m:
        return ("gh:%s/%s/%s"
                % (m.group(1), m.group(2), _clean_path(m.group(3)))).lower()
    m = _IDENT_CNB.search(u)
    if m:
        return ("cnb:%s/%s/%s"
                % (m.group(1), m.group(2), _clean_path(m.group(3)))).lower()
    return None


def source_repo(url):
    """同一仓库（忽略文件路径/分支）—— 挡住「同一运营方的另一个文件」。"""
    ident = source_identity(url)
    if not ident:
        return None
    kind, rest = ident.split(":", 1)
    parts = rest.split("/")
    if len(parts) < 2:
        return None
    return "%s:%s/%s" % (kind, parts[0], parts[1])


def load_challengers_from_channel(known_urls):
    """评估通道里 approved 且尚未入组的候选（本机终审 rate 就是国内口径）。

    判重不能只看 URL 字符串：同一个源在通道里会有 raw / ghproxy / jsdelivr
    三种写法（2026-11-02 实测 Reconss 一份源三条结论），同一个仓库也可能
    被不同分支/文件的结论带回来。所以按「仓库内文件身份」+「仓库」两级挡。
    """
    try:
        d = json.load(open(VERDICTS, encoding="utf-8"))
    except Exception as e:                          # noqa: BLE001
        warn("eval_verdicts.json 读不了：%r" % e)
        return {}
    known_urls = known_urls or set()
    known_ids, known_repos = set(), set()
    for u in known_urls:
        ident, repo = source_identity(u), source_repo(u)
        if ident:
            known_ids.add(ident)
        if repo:
            known_repos.add(repo)
    best = {}
    for c in (d.get("candidates") or []):
        if not isinstance(c, dict) or c.get("verdict") != "approved":
            continue
        url = c.get("url")
        if not url or url in known_urls:
            continue
        ident, repo = source_identity(url), source_repo(url)
        if ident and ident in known_ids:
            continue
        if repo and repo in known_repos:
            continue
        rate, alive = fnum(c.get("rate")), fnum(c.get("alive"))
        nodes = fnum(c.get("nodes") or 0)
        if rate <= 0:
            continue
        if nodes < CHANNEL_MIN_NODES:
            # 样本太小：7 节点里 3 个活 = 42.9%，与 184 节点的 26% 不是同一量纲。
            # 这类候选留在通道里继续观察，但不进本轮换位比较。
            continue
        name = c.get("name") or (c.get("repo") or "").rsplit("/", 1)[-1] or url
        key = ident or ("url:" + url)
        old = best.get(key)
        if old is None or (rate, alive) > (old[0], old[1]):
            best[key] = (rate, alive, url, name, c)
    out = {}
    for _key, (rate, alive, url, name, c) in best.items():
        out["channel:" + url] = (rate, alive, {"url": url, "name": name,
                                               "src": "channel", "cand": c})
    return out


def resolve_challenger(challengers, in_name, taken_names):
    """把 decide() 返回的参赛键翻译成写入所需的三元组。

    decide() 用带前缀的键参赛（channel:<url> / relegated:<name>），
    写入层却需要「块名 / 回归源名」。2026-11-02 首跑就是在这里按
    meta["name"] 反查键，永远对不上，换位被放弃。

    返回 (cand_meta, cand_block_name, ret_name)；任何一项为 None 都表示
    该路径不适用。调用方必须放弃写入，不许猜。
    """
    hit = challengers.get(in_name)
    if not hit:
        return None, None, None
    meta = hit[2] if isinstance(hit[2], dict) else {}
    if in_name.startswith("channel:"):
        cand = dict(meta.get("cand") or {})
        cand.setdefault("url", meta.get("url"))
        cand.setdefault("rate", hit[0])
        cand.setdefault("alive", hit[1])
        return cand, refill.derive_name(cand, taken_names), None
    if in_name.startswith("relegated:"):
        return None, None, (meta.get("name") or in_name.split(":", 1)[1])
    return None, None, None


def reprobe_relegated(relegated, mihomo, log):
    """重探 relegated 源：fetch → 清洗 → 分层抽样 25 → 真探针。逐源兜底。"""
    import fetch as fetch_mod                       # noqa: E402
    import filters as filters_mod                   # noqa: E402
    import probe as probe_mod                       # noqa: E402
    import shutil                                   # noqa: E402

    shutil.rmtree(STAGEDIR, ignore_errors=True)      # 上一轮失败留下的半成品
    exclude_rx = ""
    try:
        doc = yaml.safe_load(open(SOURCES, encoding="utf-8")) or {}
        exclude_rx = doc.get("exclude_filter_default") or ""
    except Exception:                               # noqa: BLE001
        pass
    out = {}
    staged = []
    for name, info in relegated.items():
        try:
            data, _used, _dt, _att = fetch_mod.fetch(info["url"], timeout=20, tries=2)
            if data is None:
                warn("relegated %s 抓取失败，本轮不参赛" % name)
                continue
            proxies, err = fetch_mod.parse_proxies(data)
            if proxies is None:
                warn("relegated %s 解析失败：%s" % (name, err))
                continue
            cleaned = []
            for p in proxies:
                if isinstance(p, dict):
                    try:
                        ok, _w = filters_mod.hard_filter(p, exclude_rx)
                    except Exception:               # noqa: BLE001
                        ok = False
                    if ok:
                        cleaned.append(p)
            cleaned = filters_mod.unique_names(cleaned, "lg")
            if not cleaned:
                warn("relegated %s 清洗后 0 节点，rate 记 0" % name)
                out[name] = (0.0, 0.0)
                continue
            picked = probe_mod.sample_nodes(cleaned, REPROBE_SAMPLE)
            nd = os.path.join(STAGEDIR, "nodes")
            os.makedirs(nd, exist_ok=True)
            path = os.path.join(nd, "%s.yaml" % name)
            with open(path, "w", encoding="utf-8") as f:
                import yaml as _y
                _y.safe_dump({"proxies": picked}, f, allow_unicode=True,
                             sort_keys=False, width=4096)
            staged.append((name, path))
        except Exception as e:                      # noqa: BLE001
            warn("relegated %s 重探准备失败（跳过）：%r" % (name, e))
    if not staged:
        return out
    shutil.rmtree(WORKDIR, ignore_errors=True)
    try:
        rows = probe_mod.probe(staged, mihomo, WORKDIR, budget=300,
                               hc_timeout=8000, log=log)
    except Exception as e:                          # noqa: BLE001
        warn("relegated 重探失败（不影响主链）：%r" % e)
        return out
    finally:
        shutil.rmtree(WORKDIR, ignore_errors=True)
    for name, _p in staged:
        row = rows.get(name)
        if row is None or row.get("incomplete") or not row.get("settled"):
            warn("relegated %s 未测完，本轮不参赛（不给 0 分）" % name)
            continue
        out[name] = (fnum(row.get("rate")), fnum(row.get("alive") or 0))
    return out


# ---------------------------------------------------------------------------
# sources.yaml 写入（换位 = 翻转 worst + append challenger，源数 +1 enabled 数不变）
# ---------------------------------------------------------------------------
def _flip_to_relegated(text, name, today):
    """把 name 条目翻成 enabled:false 并打 relegated 日期标。返回新文本。

    逐字节精神：只动该条目块内的 enabled 行，其余一个字符不碰。
    """
    entries = health._src_entries(text)
    tgt = None
    for e in entries:
        if e[0] == name:
            tgt = e
            break
    if tgt is None:
        raise SystemExit("[league] ✗ 在 sources.yaml 里找不到 %s，拒绝盲写" % name)
    lines = text.split("\n")
    start, end = tgt[1], tgt[2]
    flipped = False
    for i in range(start, end):
        if lines[i].strip() == "enabled: true":
            lines[i] = lines[i].replace("enabled: true", "enabled: false")
            flipped = True
    if not flipped:
        raise SystemExit("[league] ✗ %s 块内没有 enabled: true，形状异常拒绝写" % name)
    # 插在字段区末尾，而不是块尾：块尾可能跟着空行和「下一段」的分段注释。
    # end 是下一个条目/顶层键的行号，注释也算在本块里；直接 insert(end) 会让
    # relegated 落在注释之后 —— YAML 仍归属本块（注释不结束 mapping），但读起来
    # 像是下一段的字段，容易误判。2026-11-04 首次换位就出现过这种排版。
    insert_at = end
    while insert_at > start and (
            not lines[insert_at - 1].strip()
            or lines[insert_at - 1].lstrip().startswith("#")):
        insert_at -= 1
    lines.insert(insert_at, "    relegated: '%s'" % today)
    return "\n".join(lines)


def verify_swap(before_doc, after_text, out_name, in_name, prev_enabled,
                d_src, d_en, expect_relegated):
    """写入前对账（任何一条不满足都在碰磁盘前拒绝）。

    d_src / d_en：源数、enabled 数的期望增量。
      swap(通道挑战者)   = +1 /  0   （在册降级，挑战者 append）
      swap(relegated回归) =  0 /  0   （在册降级，回归源原地翻回）
      promote(通道)       = +1 / +1
      promote(relegated)  =  0 / +1
    expect_relegated：out_name 是否必须带 relegated 标 + enabled=false。
    """
    after = yaml.safe_load(after_text)
    sb = [s for s in (before_doc.get("sources") or []) if isinstance(s, dict)]
    sa = after["sources"]
    if len(sa) != len(sb) + d_src:
        raise SystemExit("[league] ✗ 对账失败：源数应 %+d，实际 %+d"
                         % (d_src, len(sa) - len(sb)))
    en_diff = refill.enabled_count(after) - prev_enabled
    if en_diff != d_en:
        raise SystemExit("[league] ✗ 对账失败：enabled 数应 %+d，实际 %+d"
                         % (d_en, en_diff))
    if expect_relegated:
        worst = next((s for s in sa if isinstance(s, dict)
                      and s.get("name") == out_name), None)
        if not worst or worst.get("enabled") is not False or not worst.get("relegated"):
            raise SystemExit("[league] ✗ 对账失败：%s 未正确降级" % out_name)
    if d_src == 1:                                  # 只有 append 才有「新条目」
        new = sa[len(sb)]
        if not (new.get("enabled") is True and new.get("name") == in_name):
            raise SystemExit("[league] ✗ 对账失败：新条目不是 %s" % in_name)
    if refill.enabled_count(after) > refill.TARGET_CAP:
        raise SystemExit("[league] ✗ 对账失败：enabled 超 cap")


def save_state(prev, rec):
    st = prev if isinstance(prev, dict) else {}
    hist = list(st.get("history") or [])
    hist.append({k: rec[k] for k in rec if k != "history"})
    st["history"] = hist[-30:]
    st["last_swap_at"] = rec["at"]
    st["last_out"] = rec["out"]
    st["last_in"] = rec["in"]
    st["v"] = 1
    health._atomic_write(STATE, json.dumps(st, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="7 源末位淘汰联赛（本机国内口径）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-reprobe", action="store_true",
                    help="relegated 源本轮不重探（用 state 里上轮 rate）")
    args = ap.parse_args(argv)
    if os.environ.get("LEAGUE_DISABLE"):
        say("LEAGUE_DISABLE=1，紧急停用开关生效，本轮跳过")
        return 0

    try:
        text = open(SOURCES, encoding="utf-8").read()
        doc = yaml.safe_load(text)
    except Exception as e:                          # noqa: BLE001
        warn("sources.yaml 读不了：%s: %s" % (type(e).__name__, str(e)[:100]))
        return 2
    enabled = [s for s in (doc.get("sources") or [])
               if isinstance(s, dict) and s.get("enabled", True)]
    relegated = {s["name"]: {"url": s["url"]}
                 for s in (doc.get("sources") or [])
                 if isinstance(s, dict) and s.get("relegated") and not s.get("enabled")}
    say("在册 %d 个（cap=%d），relegated 池 %d 个"
        % (len(enabled), refill.TARGET_CAP, len(relegated)))

    enabled_rates = load_local_rates()
    if enabled_rates is None:
        return 0
    # 只保留在册源的 rate；不在册的不参与「在册末位」比较
    enabled_rates = {s["name"]: enabled_rates[s["name"]]
                     for s in enabled if s["name"] in enabled_rates}
    missing = [s["name"] for s in enabled if s["name"] not in enabled_rates]
    if missing:
        # 缺速率不等于 0 分：本机探针没测完（网络差/时间盒）时给 0 分会把
        # 好源误判成末位。与 health 的「未测完不参与判定」保持同一纪律。
        warn("在册源缺本机速率（未测/未 settled）：%s —— 本轮不排名（不给 0 分）"
             % "、".join(missing))
        return 3

    known = set()
    for s in (doc.get("sources") or []) + (doc.get("excluded") or []):
        if isinstance(s, dict) and s.get("url"):
            known.add(s["url"])
    challengers = {}
    for key, (rate, alive, meta) in load_challengers_from_channel(known).items():
        challengers[key] = (rate, alive, meta)
    if relegated and not args.skip_reprobe:
        say("重探 %d 个 relegated 源（抽样 %d/源）…" % (len(relegated), REPROBE_SAMPLE))
        for name, (rate, alive) in reprobe_relegated(
                relegated, MIHOMO, say).items():
            challengers["relegated:" + name] = (rate, alive, {
                "url": relegated[name]["url"], "name": name, "src": "relegated"})
    elif relegated:
        say("--skip-reprobe：relegated 本轮不参赛")

    action, out_name, in_name, why = decide(
        {k: v for k, v in enabled_rates.items()},
        {k: (v[0], v[1]) for k, v in challengers.items()},
        refill.TARGET_CAP)
    say("决策：%s —— %s" % (action, why))
    if action == "hold":
        return 3

    st = None
    try:
        st = json.load(open(STATE, encoding="utf-8"))
    except Exception:                               # noqa: BLE001
        pass
    last = (st or {}).get("last_swap_at")
    if last:
        gap = health._hours_between(
            last, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        if gap is not None and gap < MIN_GAP_HOURS:
            say("距上次换位 %.1fh（< %dh），节流生效本轮不换" % (gap, MIN_GAP_HOURS))
            return 3

    today = time.strftime("%Y-%m-%d", time.gmtime())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if args.dry_run:
        say("--dry-run：未写入（out=%s in=%s）" % (out_name, in_name))
        return 3

    # 挑战者分两类，写法与对账口径完全不同：
    #   channel:*   = 评估通道里的新源 -> append 块（复用 refill 的渲染/插入）
    #   relegated:* = 被降级的老源回归 -> 原条目原地翻回 enabled:true + 摘掉标记
    taken = {s.get("name") for s in (doc.get("sources") or [])
             if isinstance(s, dict) and s.get("name")}
    cand_meta, cand_name, ret_name = resolve_challenger(
        challengers, in_name, taken)
    is_promote = (action == "promote")

    new_text = text
    d_src, d_en, expect_releg = 0, 0, False
    if action == "swap":
        new_text = _flip_to_relegated(text, out_name, today)
        expect_releg = True
    if cand_meta is not None:                       # 通道新源 append
        block = refill.render_block(cand_name, cand_meta, now)
        new_text = refill.insert_block(new_text, block)
        d_src = 1
    elif ret_name is not None:                      # relegated 回归
        new_text = _flip_enabled_back(new_text, ret_name)
        new_text = _drop_relegated_field(new_text, ret_name)
    else:
        warn("挑战者 %s 既不在通道也不是 relegated，写入路径缺失，本轮放弃" % in_name)
        return 3
    if is_promote:
        d_en = 1                                    # 补空位：enabled 净增 1

    check_name = cand_name if cand_meta is not None else ret_name
    try:
        verify_swap(doc, new_text, out_name, check_name, len(enabled),
                    d_src, d_en, expect_releg)
    except SystemExit as e:
        print(str(e))
        return 2
    health._atomic_write(SOURCES, new_text)
    rec = {"at": now, "out": out_name, "in": check_name, "why": why}
    save_state(st or {}, rec)
    try:
        state_disp = os.path.relpath(STATE, ROOT)
    except ValueError:                          # 测试把 STATE 放到别的盘
        state_disp = STATE
    say("✅ 换位完成：%s → relegated，%s 入册（state=%s）"
        % (out_name, check_name, state_disp))
    return 0


def _flip_enabled_back(text, name):
    """relegated 源回归：把它的 enabled:false 翻回 true（回归专用）。"""
    entries = health._src_entries(text)
    tgt = next((e for e in entries if e[0] == name), None)
    if tgt is None:
        raise SystemExit("[league] ✗ 回归源 %s 不在 sources.yaml 里" % name)
    lines = text.split("\n")
    start, end = tgt[1], tgt[2]
    for i in range(start, end):
        if lines[i].strip() == "enabled: false":
            lines[i] = lines[i].replace("enabled: false", "enabled: true")
            return "\n".join(lines)
    raise SystemExit("[league] ✗ %s 块内没有 enabled: false" % name)


def _drop_relegated_field(text, name):
    """回归时移除 relegated 标（它回场了，不再是被淘汰者）。"""
    entries = health._src_entries(text)
    tgt = next((e for e in entries if e[0] == name), None)
    lines = text.split("\n")
    if tgt:
        start, end = tgt[1], tgt[2]
        kept = [ln for i, ln in enumerate(lines)
                if not (start <= i < end and ln.strip().startswith("relegated:"))]
        return "\n".join(kept)
    return text


if __name__ == "__main__":
    sys.exit(main())
