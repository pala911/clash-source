# -*- coding: utf-8 -*-
"""产出 dist/ —— 手机订阅目标。

dist/profile.yaml      完整 profile：模板(组结构/规则/dns) + 注入指向本仓 gh-pages 的 proxy-providers
dist/nodes/<src>.yaml  各源过滤后的节点池（provider 格式）
dist/nodes/all.yaml    全源合并池（provider 格式）
dist/manifest.json     本次运行统计（手机排障 / 后续 diff 用）

产出纪律（对应 9-26 探针根治 §29）：
- 9 个自动组探针必须是 youtube/generate_204
- 每个 provider 的 health-check 也必须是 youtube
- 全文不得残留 gstatic
- provider URL 一律走 github.io（手机端 CN 直连可达），不用 raw.githubusercontent
"""
import json
import os

import yaml

YOUTUBE = "https://www.youtube.com/generate_204"
HOME_PROXY_NAME = "家里路由"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "profile_template.yaml")


def resolve_owner_repo(owner, repo):
    owner = owner or os.environ.get("GITHUB_REPOSITORY_OWNER") or "YOUR_GITHUB_ID"
    env_repo = os.environ.get("GITHUB_REPOSITORY", "")
    repo = repo or (env_repo.split("/")[-1] if env_repo else "") or "clash-source"
    return owner, repo


def pages_base(owner, repo):
    base = "https://%s.github.io/%s" % (owner, repo)
    # 坑（2026-10-14 CI 实测踩到）：GitHub Actions 的 github.repository 是 "owner/repo"，
    # 直接拼会得到 https://<ID>.github.io/<ID>/<repo>/ 这种手机 404 的坏路径。
    # 这里做硬校验，宁可流水线失败也不要静默产出坏订阅地址。
    tail = base.split("//", 1)[1]
    if tail.count("/") != 1 or tail.startswith(owner + "/"):
        raise ValueError("pages 基址非法: %s（repo 应为纯仓库名，不能含 owner/）" % base)
    return base


HEALTH = os.path.join(ROOT, "state", "source_health.json")

# ---- 稳定性加权（src/node_stability.py 的档案）----
# 三个开关都必须存在，否则历史不足的那几天会把整池节点判成不稳、清空 AUTO。
STABILITY_MIN_KNOWN = 100     # 至少这么多节点攒够 MIN_ROUNDS 轮，才敢开始加权
STABILITY_MIN_PER_SRC = 20    # 单个源至少保留这么多节点
STABILITY_MIN_RATIO = 0.2     # 单个源最多砍掉的比例（保留比例下限）


def split_by_stability(per_source):
    """按历史可用率把每个源的节点拆成 stable / flaky。

    返回 (stable, flaky, 说明)。flaky 只包含**真的有节点被移出**的源，
    没有被移出的源不生成额外 provider —— 否则 12 个源变 24 个 provider，
    profile 体积和 url-test 开销都白翻一倍。

    ⚠ 三重保险，缺一不可（每一条都对应一种「把池子砍空」的失败方式）：
      1. 历史整体不够（节点满 MIN_ROUNDS 轮的不足 STABILITY_MIN_KNOWN 个）
         -> **完全不加权**，全部当稳定。宁可暂时不加权，也不要砍空。
      2. 没有历史的节点一律**保留**。新节点/换配置的节点不该因为「未知」被淘汰。
      3. 单源保留数不足地板（绝对值或比例）-> 该源整体不砍。
      4. 档案损坏（load 会改名留证并抛）-> 同上不加权。**构建不能因为一个
         辅助档案坏掉而失败**（CI 每 6 小时跑一次，红了就是 6 小时没新订阅）。
    """
    import node_stability as ns
    try:
        data = ns.load()
    except RuntimeError as e:
        return per_source, {}, "稳定性档案损坏，本轮不稳定性加权（%s）" % e
    nodes = data.get("nodes") or {}
    known = [v for v in nodes.values() if v.get("n", 0) >= ns.MIN_ROUNDS]
    if len(known) < STABILITY_MIN_KNOWN:
        return per_source, {}, "历史不足（%d/%d 个节点攒够 %d 轮），本轮不稳定性加权" % (
            len(known), STABILITY_MIN_KNOWN, ns.MIN_ROUNDS)
    stable, flaky = {}, {}
    kept = dropped = 0
    for name, plist in per_source.items():
        keep, drop = [], []
        for p in plist:
            rec = nodes.get(ns.fingerprint(p))
            # 无历史或样本不足（n < MIN_ROUNDS）一律保留 ——「未知不淘汰」。
            # 新节点第一轮就有档案，旧的「样本不足 -> verdict False -> 移出」会让
            # 1~4 轮的新节点白等 5 天才进竞速池，与本函数第 2 条保险的意图冲突
            # （2026-10-19 拍板：未知=保留）。verdict 只裁「攒够轮数仍可用率低」的。
            if rec is None or rec.get("n", 0) < ns.MIN_ROUNDS:
                keep.append(p)
                continue
            ok, _ = ns.verdict(rec)
            (keep if ok else drop).append(p)
        if drop:
            floor = max(STABILITY_MIN_PER_SRC, len(plist) * STABILITY_MIN_RATIO)
            if len(keep) < floor:
                keep, drop = plist, []
        stable[name] = keep
        if drop:
            flaky[name] = drop
        kept += len(keep)
        dropped += len(drop)
    return stable, flaky, "稳定性加权：保留 %d / 移出 %d 个节点（%d 个源有节点被移出）" % (
        kept, dropped, len(flaky))

# 质量门槛（与 health.py 的 GOOD_RATE 保持一致）。低于它就不进 AUTO 竞速。
GOOD_RATE = 8.0
# AUTO 最多放几个源。url-test 会在这些源的全部节点上竞速，源太多会让
# 探测开销和「靠数量取胜」的概率一起上升 —— 差源的节点数天然是多源的 4~6 倍。
AUTO_MAX = 6
AUTO_MIN = 3          # 少于这么多个就直接构建失败，宁可不更新也不要空组


def _shout(msg):
    """降级必须能被看见：本地打日志，CI 上额外打 `::warning::` 注解。

    静默降级 = 更坏的「看起来一切正常」——这套系统一直在修的就是这种病。
    """
    print("[build] ⚠ 降级：%s" % msg)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::warning title=源健康档案降级::%s" % msg.replace("\n", " "))


def load_health():
    """读健康档案；**坏了也不抛**，返回 `(data, note)`，note 非空 = 本轮降级了。

    ⚠ 这里原来是 `except Exception: return {}`（§75 #6），两个后果同时发生：
      1. 档案一坏，rank_sources 把每个源都判成「无本机探针数据」→ 全进观察桶
         → build_groups 的 AUTO_MIN 断言炸 → **CI 每 6 小时红一次**，
         而报错信息指向「本机探针没跑」这个**错误方向**（真因是档案坏了）；
      2. 一个字都不说，没人知道为什么。

    现在口径（用户 2026-10-18 拍板）＝**降级发布 + 大声告警**：
      · 订阅照发 —— 手机不能因为一个辅助档案坏掉就 6 小时不更新；
      · 但降级必须喊出来：note 由 run.py 记进 warnings（进 reports/latest.md）
        + 这里直接打 ::warning::；AUTO 名单退化成上一轮 manifest 的名单。
      · 绝不重建/删除损坏文件 —— 那是 health.py 的职责（它会 exit 2 并留证），
        这里只读不写（多轮历史不可恢复，宁可不写）。
    """
    try:
        with open(HEALTH, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or "sources" not in d:
            raise ValueError("结构不对（缺 sources 键）")
        return d, ""
    except FileNotFoundError:
        return {}, ("健康档案不存在（首次运行？）：%s —— 排序退化为「无本机探针数据」，"
                    "AUTO 用上一轮名单" % HEALTH)
    except Exception as e:
        return {}, ("健康档案损坏（%s: %s）—— 本轮按「无历史」排序、AUTO 用上一轮名单；"
                    "损坏文件**没有**被重建或删除，修复见 health.py 的提示"
                    % (type(e).__name__, str(e)[:100]))


def _last_manifest_auto(enabled_names):
    """降级用：读上一轮 `dist/manifest.json` 的 `ranking.auto` 当 AUTO 名单。

    为什么敢用它：manifest 就在仓库里、每轮都提交（dist/ 是事实来源），
    它是**上一轮已知可用的名单**，比「按文件顺序取前 N 个」有依据。
    为什么要过滤 enabled：源可能已经停用，停用的源不能进新 profile。
    返回 (名单, 说明)；拿不到就返回 ([], "")，由调用方再退一步。
    """
    try:
        with open(os.path.join(ROOT, "dist", "manifest.json"), encoding="utf-8") as f:
            m = json.load(f)
        auto = [n for n in ((m.get("ranking") or {}).get("auto") or [])
                if n in enabled_names]
        if auto:
            return auto[:AUTO_MAX], "沿用上一轮 manifest 的 AUTO 名单：%s" % "、".join(auto[:AUTO_MAX])
    except Exception as e:
        return [], "读不到上一轮 manifest（%s）" % type(e).__name__
    return [], "上一轮 manifest 里没有可用的 AUTO 名单"


def rank_sources(names, health=None):
    """按**国内口径**给源排序，决定它们进哪个组。返回 (ranking, degrade_note)。

    ## 为什么用国内口径而不是 CI（美国）的

    实测 Spearman rho（美国 vs 国内）只有 0.48，排名不可信；且
    shaoyouvip 美国 81.2%(#4) / 国内 6.2%(#11 垫底)。所以排序只能用国内。

    ## 为什么主排序只看「本机」

    健康档案里的 tier 是本机 × 云效的联合判定，但在云效攒够 7 轮之前
    tier 恒为 "?"。若等 tier 才排序，等于让整个产出停摆。所以：
      主排序 = 本机 rate（唯一有权判优的口径，已积累 23 轮）
      tier=T2（位置敏感）额外降级到备用 —— 这一条等云效数据到位才生效

    `health` 参数只为测试注入用；不传就走 load_health()（含降级）。
    返回的 degrade_note 非空 = 档案坏/缺，调用方必须喊出来。
    """
    if health is None:
        data, note = load_health()
    else:
        data, note = health, ""
    hs = (data.get("sources") or {})
    out = {}
    for n in names:
        rec = hs.get(n) or {}
        rates = rec.get("tier_rates") or {}
        # tier_rates 是最近若干轮的均值，比单轮稳；没有则回退到最后一轮
        rate = rates.get("local")
        if rate is None:
            last = [r for r in (rec.get("runs") or []) if r.get("scope") == "local"]
            rate = last[-1].get("rate") if last else None
        tier = rec.get("tier") or "?"
        if rate is None:
            out[n] = (None, "观察", "无本机探针数据")
        elif tier == "T2":
            out[n] = (rate, "备用", "位置敏感（本机 %.1f%%/云效 %.1f%%）" % (rate, rates.get("cnci") or 0))
        elif rate >= GOOD_RATE:
            out[n] = (rate, "AUTO", "本机 %.1f%%" % rate)
        elif rate > 0:
            out[n] = (rate, "观察", "本机 %.1f%% 低于 %.0f%%" % (rate, GOOD_RATE))
        else:
            out[n] = (0.0, "观察", "本机 0 活")
    return out, note


def _src_group(name):
    # ⚠ tolerance=200 是防抖关键（2026-10-29 用户反馈「AUTO 组内换点太频繁」）：
    #   url-test 没有 tolerance 时，几十毫秒的延迟抖动也会判定换点 —— 组在
    #   每次测速后都可能换现役，手机侧观感就是「节点跳来跳去而没人变好」。
    #   200ms 的意思是：只有新节点比现役快 200ms 以上（真实优势）才切换；
    #   120s/300s 的测速频率不变，「快速找到最优」不受影响，只是不再被抖动刷屏。
    #   与 profile 模板静态组的既有取值保持一致。
    return {"name": "SRC-%s" % name, "type": "url-test", "use": [name],
            "url": YOUTUBE, "expected-status": 204,
            "interval": 300, "timeout": 5000, "tolerance": 200}


def _probe_group(name, gtype, members, interval):
    g = {"name": name, "type": gtype, "proxies": list(members),
         "url": YOUTUBE, "expected-status": 204,
         "interval": interval, "timeout": 5000}
    # ⚠ 只有 url-test 有「切换容差」语义；fallback（如 FAILOVER）没有这个字段，
    #   别往它身上塞不认识的键（内核行为未知就不赌）。
    if gtype == "url-test":
        g["tolerance"] = 200
    return g


def build_groups(enabled_names, ranked, flaky_names=(), degraded_note=""):
    """按质量分桶生成代理组，取代模板里手写的硬编码列表。

    `degraded_note` 非空 = 健康档案坏/缺（build.load_health 给的降级说明）：
    此时**绝不 assert 失败**（用户 2026-10-18 拍板：降级发布 + 大声告警）——
    AUTO 组必须存在（FAILOVER 组引用它，缺了手机连配置都加载不了），
    名单退化成上一轮 manifest 的 AUTO；再退一步才用启用源顺序。

    ## 为什么要动态生成

    原模板把 AUTO 的 9 个候选写死，结果和实测质量是**反的**：
      在 AUTO 里   ermaozi 本机 2.9%（通过率最低之一）
      不在 AUTO 里 shaoyouvip 24.4%、automerge 29.3%（更好却被排除）
    写得再仔细也一定会漂移 —— 源质量天天变，没有任何静态列表能跟上。
    """
    auto = sorted([n for n in enabled_names if ranked.get(n, (None,))[1] == "AUTO"],
                  key=lambda n: -(ranked[n][0] or 0))
    spare = sorted([n for n in enabled_names if ranked.get(n, (None,))[1] == "备用"],
                   key=lambda n: -(ranked[n][0] or 0))
    watch = sorted([n for n in enabled_names if ranked.get(n, (None,))[1] == "观察"],
                   key=lambda n: -(ranked[n][0] or 0))
    picked, dropped = auto[:AUTO_MAX], auto[AUTO_MAX:]

    if degraded_note:
        why = ""
        if len(picked) < AUTO_MIN:
            fb, why = _last_manifest_auto(enabled_names)
            if not fb:
                fb = list(enabled_names)[:AUTO_MAX]
                why = "降级兜底：按启用源顺序（%s）" % why
            picked = fb
        _shout("%s；自动组改用「%s」（%s），本轮不因档案问题中断订阅"
               % (degraded_note, "、".join(picked), why or "上一轮的可见名单"))
    else:
        assert len(picked) >= AUTO_MIN, (
            "达标源只有 %d 个（%s），不足 %d —— AUTO 组会变得不可用。"
            "宁可构建失败也不要给你一个空/残缺的自动组。"
            "（本机探针若长期没跑，这里就会失败，是预期行为）"
            % (len(picked), "、".join(auto) or "无", AUTO_MIN))

    groups = [_src_group(n) for n in enabled_names]
    if picked:
        groups.append(_probe_group("AUTO", "url-test",
                                   ["SRC-%s" % n for n in picked], 120))
    # 备用/观察用 select 而非 url-test：不参与自动竞速（省掉一半 url-test 开销），
    # 需要时在手机上手动切。这样差源只占「可选」不占「自动」。
    spare_members = (["SRC-%s" % n for n in spare + dropped] if (spare or dropped)
                     else ["SRC-%s" % n for n in enabled_names])
    # 备用组额外挂上「被稳定性加权移出」的 provider —— 它们仍然可用，
    # 只是不参与 AUTO 的自动竞速。这比直接删掉好：万一路由变了还能手工切回来。
    # ⚠ 这里必须引用**组名**「不稳定」，不能引用 provider 名 SRCFL-*。
    #   proxies: 列表里只接受「已定义的组名」或「具体节点名」，
    #   provider 只能通过 use: 引用。写成 SRCFL-* 时内核报
    #   `proxy group[14]: 备用: 'SRCFL-xxx' not found` —— 而断言是绿的，
    #   因为「SRCFL-xxx 在 providers 里」恰好为真，语义却是错的。
    if flaky_names:
        groups.append({"name": "不稳定", "type": "url-test",
                       "use": list(flaky_names), "url": YOUTUBE,
                       "expected-status": 204, "interval": 300, "timeout": 5000,
                       "tolerance": 200})
        spare_members = spare_members + ["不稳定"]
    groups.append({"name": "备用", "type": "select", "proxies": spare_members})
    groups.append({"name": "观察", "type": "select",
                   "proxies": ["SRC-%s" % n for n in watch] or spare_members})
    # FAILOVER 兜底保留**全部**启用源 —— 自动组出问题时的安全网不能被质量分桶削掉
    groups.append(_probe_group("FAILOVER", "fallback",
                               ["AUTO"] + ["SRC-%s" % n for n in enabled_names], 60))
    groups.append({"name": "PROXY", "type": "select",
                   "proxies": ["FAILOVER", "AUTO", "备用", "观察"] +
                              ["SRC-%s" % n for n in enabled_names]})
    # ⚠ Claude / Gemini 也必须在这里重建，不能留在模板里。
    #   它们是 rules 里唯二指向自定义组的目标（rule-set claude -> [Claude]）。
    #   第一版替换整个 proxy-groups 时漏了这两个，内核 -t 直接报
    #   `rules[43] [RULE-SET,claude,Claude] error: proxy [Claude] not found` ——
    #   产出物在手机上**一进去就报错**，而所有 Python 断言都是绿的。
    #   这就是为什么必须用真内核校验，断言只能验证你想到的东西。
    for svc in ("Claude", "Gemini"):
        groups.append({"name": svc, "type": "select", "use": list(enabled_names)})
    return groups, picked, spare, watch


def provider_block(name, url, exclude_filter):
    return {
        "type": "http",
        "url": url,
        "path": "./providers/%s.yaml" % name,
        "interval": 3600,
        "exclude-filter": exclude_filter,
        "health-check": {
            "enable": True,
            "url": YOUTUBE,
            "interval": 300,
            "timeout": 5000,
            "expected-status": 204,
        },
    }


def build_profile(enabled_sources, exclude_map, owner, repo, flaky_sources=()):
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = yaml.safe_load(f)

    base = pages_base(owner, repo)
    providers = {}
    for s in enabled_sources:
        providers[s["name"]] = provider_block(
            s["name"], base + "/nodes/%s.yaml" % s["name"],
            exclude_map.get(s["name"], ""))
    # 被稳定性加权移出的节点单独成为一个 provider，只挂到「备用」组。
    # 命名 SRCFL-<源名>，与源名区分开，避免和 SRC-* 的引用混淆。
    for n in flaky_sources or ():
        providers["SRCFL-" + n] = provider_block(
            "SRCFL-" + n, base + "/nodes/%s--flaky.yaml" % n,
            exclude_map.get(n, ""))

    names = [s["name"] for s in enabled_sources]
    ranked, degrade_note = rank_sources(names)
    flaky_names = ["SRCFL-" + n for n in (flaky_sources or ())]
    groups, picked, spare, watch = build_groups(names, ranked, flaky_names,
                                                degraded_note=degrade_note)
    # 模板里的 proxy-groups 整块丢弃：SRC-*/AUTO/FAILOVER/PROXY 全部改由
    # build_groups 按实测质量动态生成。规则/ dns / 其他键仍保留模板的。
    tpl["proxy-groups"] = groups
    tpl["proxy-providers"] = providers

    # 家里路由是模板里的静态 HTTP 代理：挂到 PROXY 组供手动切换；
    # Claude/Gemini 默认跟随 PROXY，这样手机切一处就能全走家里路由。
    static_proxies = {p.get("name") for p in (tpl.get("proxies") or [])
                      if isinstance(p, dict) and p.get("name")}
    assert HOME_PROXY_NAME in static_proxies, \
        "模板缺少静态代理 %s" % HOME_PROXY_NAME
    for g in tpl["proxy-groups"]:
        if g["name"] == "PROXY":
            members = g.setdefault("proxies", [])
            if HOME_PROXY_NAME not in members:
                pos = 1 if members[:1] == ["FAILOVER"] else 0
                members.insert(pos, HOME_PROXY_NAME)
        elif g["name"] in ("Claude", "Gemini"):
            members = g.setdefault("proxies", [])
            if "PROXY" not in members:
                members.insert(0, "PROXY")

    # ---- 校验链（失败即中止，不产出坏 profile）----
    used = {n for g in tpl["proxy-groups"] for n in (g.get("use") or [])}
    missing = used - set(providers)
    assert not missing, "生成的组引用了未提供的 provider: %s" % missing
    # 每个 SRC-* 组都必须有对应的 provider，且每个 provider 都必须有一个 SRC-*
    for g in tpl["proxy-groups"]:
        if g["name"].startswith("SRC-"):
            assert g["use"], "%s 没有 use 字段" % g["name"]
    for n in providers:
        # 不稳定 provider（SRCFL-*）挂在「不稳定」组里，不是 SRC-* 组
        if n.startswith("SRCFL-"):
            continue
        assert any(g["name"] == "SRC-%s" % n for g in tpl["proxy-groups"]), \
            "provider %s 没有对应的 SRC- 组" % n
    for n in providers:
        if n.startswith("SRCFL-"):
            assert any(n in (g.get("use") or []) for g in tpl["proxy-groups"]), \
                "不稳定 provider %s 没有被任何组引用" % n

    auto = [g for g in tpl["proxy-groups"] if g.get("url")]
    for g in auto:
        assert g["url"] == YOUTUBE, "%s 探针非 youtube: %s" % (g["name"], g["url"])
    for n, p in providers.items():
        assert p["health-check"]["url"] == YOUTUBE, "%s provider 探针非 youtube" % n
        assert "raw.githubusercontent" not in p["url"], "%s provider URL 用了 raw（手机被墙）" % n
        assert ".github.io/" in p["url"], "%s provider URL 未走 github.io" % n
    raw = yaml.safe_dump(tpl, allow_unicode=True, sort_keys=False, width=4096)
    assert "gstatic" not in raw, "残留 gstatic"
    # PROXY 必须引用存在的组或本 profile 的静态代理，否则手机上一进去就报错
    gp = {g["name"] for g in tpl["proxy-groups"]}
    for g in tpl["proxy-groups"]:
        for p in (g.get("proxies") or []):
            # ⚠ 必须断言「p 是已定义的组名，或本 profile 的静态代理」。
            #   之前写成 `p in gp or p in providers` 是错的：provider 名也满足它，
            #   于是「备用: SRCFL-xxx」这种内核根本不接受的形式被放过去了。
            #   家里路由是模板 proxies: 里的静态代理，必须单独放行。
            assert p in gp or p in static_proxies, (
                "组 %s 引用了 %s，它既不是已定义的组，也不是本 profile 的静态代理。"
                "注意 provider 要用 use:" % (g["name"], p))
    # **规则的目标也必须存在** —— 这是漏掉 Claude/Gemini 那次真正该有的断言。
    # 组内部自洽（proxy 指向存在的组）并不够：rules 可以指向任何名字，
    # 指向一个不存在的组时内核直接拒绝加载配置，而订阅脚本一进去就报错。
    BUILTIN = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", "GLOBAL"}
    for r in (tpl.get("rules") or []):
        parts = [x.strip() for x in r.split(",")]
        if len(parts) < 2:
            continue
        tgt = parts[-2] if parts[-1] == "no-resolve" else parts[-1]
        if tgt in BUILTIN or tgt in gp or tgt in providers or tgt in static_proxies:
            continue
        # 内核自带的规则类型（MATCH/DOMAIN-SUFFIX/...）第一段不是代理名
        if parts[0] in ("MATCH", "FINAL"):
            continue
        raise AssertionError(
            "规则 %r 指向不存在的目标 %r —— 现有组: %s。"
            "订阅加载时会直接失败（之前漏掉 Claude/Gemini 就是这个症状）"
            % (r, tgt, "、".join(sorted(gp))))
    # ⚠ 分桶结果**不要**塞进 tpl：它会被写进 profile.yaml，给用户看一堆
    #   下划线开头的内部字段。单独作为第三个返回值交给 run.py 记进 manifest。
    ranking = {"auto": picked, "备用": spare, "观察": watch,
               "不稳定": ["SRCFL-" + n for n in (flaky_sources or ())],
               "degraded": degrade_note,      # 非空 = 本轮是降级发布（run.py 必须喊出来）
               "detail": {k: {"rate": v[0], "why": v[2]} for k, v in ranked.items()}}
    return tpl, base, ranking


def dump_yaml(obj, header, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header.rstrip() + "\n")
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, width=4096)


def write_nodes(dist_dir, per_source_nodes, all_nodes, base=""):
    """只写节点文件（调试 --sources 局部跑时用，避免 profile 断言/覆盖）。"""
    nodes_dir = os.path.join(dist_dir, "nodes")
    os.makedirs(nodes_dir, exist_ok=True)
    for name, nodes in per_source_nodes.items():
        dump_yaml({"proxies": nodes},
                  "# clash-source 自动生成（局部调试跑）—— 源 %s，共 %d 节点"
                  % (name, len(nodes)),
                  os.path.join(nodes_dir, "%s.yaml" % name))
    if all_nodes is not None:
        dump_yaml({"proxies": all_nodes},
                  "# clash-source 自动生成（局部调试跑）—— 合并 %d 节点" % len(all_nodes),
                  os.path.join(nodes_dir, "all.yaml"))


def write_dist(dist_dir, per_source_nodes, all_nodes, profile, manifest, base,
               flaky_nodes=None):
    nodes_dir = os.path.join(dist_dir, "nodes")
    os.makedirs(nodes_dir, exist_ok=True)
    owner = manifest.get("owner") or "YOUR_GITHUB_ID"
    repo = manifest.get("repo") or "clash-source"
    for name, nodes in per_source_nodes.items():
        dump_yaml({"proxies": nodes},
                  "# clash-source 自动生成 —— 源 %s，共 %d 节点"
                  "（稳定性加权后留在竞速池内的部分）\n"
                  "# 不要手改；改动会在下次定时任务被覆盖（上游 %s/nodes/%s.yaml）"
                  % (name, len(nodes), base, name),
                  os.path.join(nodes_dir, "%s.yaml" % name))
    for name, nodes in (flaky_nodes or {}).items():
        dump_yaml({"proxies": nodes},
                  "# clash-source 自动生成 —— 源 %s，被稳定性加权移出的 %d 个节点\n"
                  "# 历史可用率偏低，不参与 AUTO 自动竞速；需要时可从「备用」组手工切。"
                  % (name, len(nodes)),
                  os.path.join(nodes_dir, "%s--flaky.yaml" % name))
    dump_yaml({"proxies": all_nodes},
              "# clash-source 自动生成 —— 全源合并，共 %d 节点（名字带源前缀）\n"
              "# 供多源合并场景使用；profile.yaml 默认按源分文件挂载" % len(all_nodes),
              os.path.join(nodes_dir, "all.yaml"))
    dump_yaml(profile,
              "# clash-source 自动生成 —— 手机订阅入口\n"
              "# 主:  %s/profile.yaml\n"
              "# 备1 jsdelivr（免 Pages 设置，国内直连实测可达）:\n"
              "#   https://cdn.jsdelivr.net/gh/%s/%s@gh-pages/profile.yaml\n"
              "# 备2 gh-proxy raw（github.io 不达时）:\n"
              "#   https://gh-proxy.com/raw.githubusercontent.com/%s/%s/gh-pages/profile.yaml\n"
              "# 备3 gh-proxy raw（main 分支）:\n"
              "#   https://gh-proxy.com/raw.githubusercontent.com/%s/%s/main/dist/profile.yaml"
              % (base, owner, repo, owner, repo, owner, repo),
              os.path.join(dist_dir, "profile.yaml"))
    with open(os.path.join(dist_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)