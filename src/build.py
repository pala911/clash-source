# -*- coding: utf-8 -*-
"""产出 dist/ —— 手机订阅目标。

dist/profile.yaml      完整 profile：模板(组结构/规则/dns) + 注入指向本仓 gh-pages 的 proxy-providers
dist/mobile.yaml       iOS 精简版：单 provider（~120 节点）+ 全 lazy 规则集，给网络扩展省内存
dist/nodes/<src>.yaml  各源过滤后的节点池（provider 格式）
dist/nodes/all.yaml    全源合并池（provider 格式）
dist/nodes/mobile.yaml 精简版单池（源间轮询取样、按 server:port 去重）
dist/manifest.json     本次运行统计（手机排障 / 后续 diff 用）

产出纪律（对应 9-26 探针根治 §29）：
- 9 个自动组探针必须是 youtube/generate_204
- 每个 provider 的 health-check 也必须是 youtube
- 全文不得残留 gstatic
- provider URL 走 gh-proxy 中转的 gh-pages raw（10-31 用户拍板，替代
  jsdelivr@gh-pages：gh-proxy 零缓存、CI 发完池子 ≤1h 内就到手机，
  jsdelivr 分支引用缓存 ~12h 太慢；同理禁用 raw 直链——蜂窝网络
  github.io/raw 都拉不动，中转必须带 gh-proxy.com 前缀）
"""
import datetime
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


def mirror_base(owner, repo):
    """provider 节点池的分发基址（2026-10-31 用户拍板：gh-proxy 替代 jsdelivr）。

    走 gh-proxy.com 中转的 gh-pages raw：**零缓存**，CI 每 6h 重建的池子
    ≤1h 内就到手机（jsdelivr 的 @gh-pages 分支引用缓存 ~12h，新鲜度
    打了折）。同款服务在 fetch.py 的 fallback 链和订阅备2 已多年实测；
    gh-proxy 间歇性抽风时手机端用上次成功的 provider 文件顶住、下个
    拉取周期自愈。raw 直链被墙不用，中转必须带 gh-proxy.com 前缀。
    """
    return "https://gh-proxy.com/raw.githubusercontent.com/%s/%s/gh-pages" % (
        owner if owner != "YOUR_GITHUB_ID" else "YOUR_GITHUB_ID", repo)


HEALTH = os.path.join(ROOT, "state", "source_health.json")

# ---- 稳定性加权（src/node_stability.py 的档案）----
# 三个开关都必须存在，否则历史不足的那几天会把整池节点判成不稳、清空 AUTO。
STABILITY_MIN_KNOWN = 100     # 至少这么多节点攒够 MIN_ROUNDS 轮，才敢开始加权
STABILITY_MIN_PER_SRC = 20    # 单个源至少保留这么多节点
STABILITY_MIN_RATIO = 0.2     # 单个源最多砍掉的比例（保留比例下限）

# ---- 移动端精简版（2026-11-02，iOS 内存修复）----
# 实测：完整 profile（20 provider / 5707 节点 / 33 个非 lazy rule-provider）
# 桌面 mihomo 峰值 ~95MB；iOS 网络扩展上限约 50MB，Clash MI 启动 2 秒即被
# 系统按内存杀掉（jetsam，无错误日志）。精简版把节点压到 120、规则集全 lazy。
MOBILE_NODE_CAP = 120
MOBILE_PER_SRC = 25
# 近 7 天本机口径活率最高的几个源（2026-11-01 数据）；缺哪个就跳过哪个。
MOBILE_PREFERRED = ("zhuhaiuk", "clashdaily", "ssrsub", "ruk1ng001",
                    "leilaomi", "nomorewalls", "automerge")
MOBILE_PROVIDER = "mobile"

# ---- 带宽测速 / 视频组（2026-11-10）----
# 健康检查只证明「连得上」，不证明「跑得动」。本机实测同一源内
# 0.21 ~ 4.61 MB/s 差 20 倍，30/56 个「存活」节点真实下载直接失败。
# 因此视频组只收**本机真实下载**达标的节点：
#   720p ≈ 0.3 MB/s，1080p ≈ 0.6 MB/s，4K ≈ 2.5 MB/s。
# 门槛取 1080p；数据超过 48h 视为过期（构建侧跳过，不拿旧速度骗人）。
SPEED = os.path.join(ROOT, "state", "speed_latest.json")
SPEED_MAX_AGE_H = 48
VIDEO_PROVIDER = "video"
VIDEO_MBPS = 0.6
VIDEO_MAX = 40
VIDEO_PER_SRC = 12
VIDEO_MIN = 4


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


def dedupe_cross_source(per_source, priority=None):
    """跨源内容指纹去重：同一份节点配置（去掉 name 后整份 dict）只保留一份。

    ## 为什么用「完整内容指纹」而不是 server:port

    同一 IP:port 上可以有多个**合法但不同**的节点：shaoyouvip 曾在同一 IP 上
    开 4 个节点，ruk1ng001 单源内也有 34 个 server:port 相同的节点（凭据不同）。
    按 server:port 去重会把它们误删；`filters.dedupe_key` 同源去重带凭据也是
    这个原因。这里用 `node_stability.fingerprint`（整份配置去掉 name 的 sha1），
    只删**内容完全相同**的节点 —— automerge / nomorewalls 那种 100% 重复
    正好被抓到，又不会误伤同端口的不同账号。

    ## 保留哪一份

    `priority` 是源名列表（建议按本机质量分降序）。同一指纹先出现者保留，
    所以高质量源优先。`priority` 里没有的源按 per_source 原顺序追加。
    返回的 dict 保持 per_source 的原键顺序（provider / 报告行顺序不变），
    只删节点。

    返回 `(deduped, dup_counts)`：`dup_counts[源名]` = 被本函数剔除的节点数。
    """
    import node_stability as ns
    order = [n for n in (priority or []) if n in per_source]
    order += [n for n in per_source if n not in order]
    seen = set()
    deduped = {n: [] for n in per_source}
    dup_counts = {n: 0 for n in per_source}
    for name in order:
        for p in per_source[name]:
            fp = ns.fingerprint(p)
            if fp in seen:
                dup_counts[name] += 1
                continue
            seen.add(fp)
            deduped[name].append(p)
    # 保持原键顺序：profile 的 provider / 报告行顺序都依赖它
    return {n: deduped[n] for n in per_source}, dup_counts


# 质量门槛（与 health.py 的 GOOD_RATE 保持一致）。低于它就不进 AUTO 竞速。
GOOD_RATE = 8.0
# AUTO 最多放几个源。url-test 会在这些源的全部节点上竞速，源太多会让
# 探测开销和「靠数量取胜」的概率一起上升 —— 差源的节点数天然是多源的 4~6 倍。
# AUTO 竞速组成员上限（2026-11-02 拍板 3 组，2026-11-04 用户改为 4 组）。
# 国内口径排名前 4 进 AUTO，其余达标源留在「备用」组手动可切。
# 手机 health-check 压力随成员数线性上升，4 是当前 7 源下的折中。
AUTO_MAX = 4
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


def load_speed(path=None, now=None):
    """读本机带宽测速档案；坏了/过期都**不抛**，返回 `(data, note)`。

    口径与 load_health 一致：辅助档案坏了不能带崩构建，但必须能看见。
    `scope != local` 一律不认 —— CI 美国 runner 的测速结果不能拿来给国内
    手机挑视频节点（跨洋带宽和落地线路完全是两回事）。
    """
    path = path or SPEED
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return None, "测速档案不存在（首次运行？）：%s" % path
    except Exception as e:               # noqa: BLE001
        return None, ("测速档案损坏（%s: %s）—— 本轮不生成视频组；"
                      "损坏文件没有被重建或删除" % (type(e).__name__, str(e)[:100]))
    if not isinstance(d, dict) or not isinstance(d.get("results"), list):
        return None, "测速档案结构不对（缺 results 列表）—— 本轮不生成视频组"
    if d.get("scope") != "local":
        return None, ("测速档案不是本机口径（scope=%r）—— 本轮不生成视频组"
                      % d.get("scope"))
    try:
        tested = datetime.datetime.strptime(str(d.get("tested_at") or ""),
                                            "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None, "测速档案缺少可解析的 tested_at —— 本轮不生成视频组"
    age = (now or datetime.datetime.utcnow()) - tested
    if age > datetime.timedelta(hours=SPEED_MAX_AGE_H):
        return None, ("测速档案已过期（%.1f 小时前 > %d 小时）—— "
                      "本轮不生成视频组，等下一次本机测速"
                      % (age.total_seconds() / 3600.0, SPEED_MAX_AGE_H))
    return d, ""


def pick_video_nodes(speed_doc, stable_nodes, per_src=VIDEO_PER_SRC,
                     cap=VIDEO_MAX, min_nodes=VIDEO_MIN):
    """把本机实测达标的节点挑进「视频」组。

    关联方式是**节点指纹**（node_stability.fingerprint，忽略 name）：CI 每轮
    重新抓源，节点名可能带时间戳/序号漂移，但配置内容不变时指纹不变。
    指纹对不上 = 节点配置变了，旧速度不适用，直接跳过（绝不按名字硬套）。

    返回 (nodes, note)。note 非空 = 没生成视频组，原因要进日志/告警。
    """
    if not speed_doc:
        return [], "无可用测速档案"
    import node_stability as ns
    rows = [r for r in (speed_doc.get("results") or [])
            if isinstance(r, dict) and not r.get("error")
            and (r.get("mbps") or 0) >= VIDEO_MBPS]
    if not rows:
        return [], ("测速结果里没有 >= %.1f MB/s 的节点" % VIDEO_MBPS)

    index = {}
    for src, nodes in (stable_nodes or {}).items():
        for p in nodes:
            if isinstance(p, dict) and p.get("name"):
                index.setdefault(ns.fingerprint(p), (src, p))

    rows.sort(key=lambda r: (-(r.get("mbps") or 0),
                             r.get("median_ms") or 99999))
    picked, seen, used = [], set(), {}
    for r in rows:
        fp = r.get("fp")
        if not fp or fp in seen:
            continue
        hit = index.get(fp)
        if not hit:
            continue                     # 配置已变/本轮没进稳定池，旧速度不复用
        src, p = hit
        if used.get(src, 0) >= per_src:
            continue
        name = "%s_%s" % (src, p.get("name"))
        if any(n.get("name") == name for n in picked):
            continue
        seen.add(fp)
        used[src] = used.get(src, 0) + 1
        node = dict(p)
        node["name"] = name
        picked.append(node)
        if len(picked) >= cap:
            break

    if len(picked) < min_nodes:
        return [], ("达标且能在本轮稳定池里对上的节点只有 %d 个（< %d）"
                    % (len(picked), min_nodes))
    return picked, ""


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

    # 降级时 picked 可能来自上一轮名单，和 spare/dropped 有交集；备用组
    # 必须去掉已经在 AUTO 里的源，否则同一个源会同时出现在两个组，
    # manifest 的 ranking 也会重复（2026-11-04 修）。必须在 picked 定稿
    # 之后过滤，不能用降级前的 auto[:AUTO_MAX]。
    spare = [n for n in spare if n not in picked]
    dropped = [n for n in dropped if n not in picked]

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
    # dropped = 达标但被 AUTO_MAX 挤出、实际仍留在「备用」组的源。
    # 必须一起返回：manifest/report 的「备用」行要列出它们，否则报告会显示
    # 「备用 -」，和用户手机里真实看到的组不一致（2026-11-04 实踩）。
    return groups, picked, spare, watch, dropped


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


def build_profile(enabled_sources, exclude_map, owner, repo, flaky_sources=(),
                  video_nodes=None):
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = yaml.safe_load(f)

    base = pages_base(owner, repo)          # 订阅入口（github.io 主链 + jsdelivr/gh-proxy 备链）仍走原链
    mbase = mirror_base(owner, repo)        # provider 节点池一律走 gh-proxy 中转（零缓存、iOS 蜂窝可达）
    providers = {}
    for s in enabled_sources:
        providers[s["name"]] = provider_block(
            s["name"], mbase + "/nodes/%s.yaml" % s["name"],
            exclude_map.get(s["name"], ""))
    # 被稳定性加权移出的节点单独成为一个 provider，只挂到「备用」组。
    # 命名 SRCFL-<源名>，与源名区分开，避免和 SRC-* 的引用混淆。
    for n in flaky_sources or ():
        providers["SRCFL-" + n] = provider_block(
            "SRCFL-" + n, mbase + "/nodes/%s--flaky.yaml" % n,
            exclude_map.get(n, ""))
    # 视频组：只挂本机实测高带宽节点（nodes/video.yaml）。没有达标节点时
    # 连 provider 都不建 —— 空 provider 会让手机上的组变成空壳。
    video_nodes = list(video_nodes or ())
    if video_nodes:
        providers[VIDEO_PROVIDER] = provider_block(
            VIDEO_PROVIDER, mbase + "/nodes/video.yaml", "")

    names = [s["name"] for s in enabled_sources]
    ranked, degrade_note = rank_sources(names)
    flaky_names = ["SRCFL-" + n for n in (flaky_sources or ())]
    groups, picked, spare, watch, dropped = build_groups(
        names, ranked, flaky_names, degraded_note=degrade_note)
    if video_nodes:
        # 视频组只做 url-test：看视频时手动切到它，内核按 youtube 延迟自动
        # 选当前最快；真正的高带宽候选已经在 nodes/video.yaml 里筛过一遍。
        groups.append({"name": "视频", "type": "url-test",
                       "use": [VIDEO_PROVIDER], "url": YOUTUBE,
                       "expected-status": 204, "interval": 300,
                       "timeout": 5000, "tolerance": 200})
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
            if video_nodes and "视频" not in members:
                pos = members.index("备用") if "备用" in members else len(members)
                members.insert(pos, "视频")
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
        # 不稳定 provider（SRCFL-*）挂在「不稳定」组里，不是 SRC-* 组；
        # 视频 provider 挂在「视频」组里，同理不要求 SRC-* 组。
        if n.startswith("SRCFL-") or n == VIDEO_PROVIDER:
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
        # raw 直链被墙（手机蜂窝拉不动）——但 gh-proxy 中转 URL 里**含**
        # raw.githubusercontent 子串，禁的是「直链起头」不是子串（10-31 教训）
        assert not p["url"].startswith("https://raw.githubusercontent"), \
            "%s provider URL 用了 raw 直链（手机被墙）" % n
        assert p["url"].startswith("https://gh-proxy.com/raw.githubusercontent.com/"), \
            "%s provider URL 未走 gh-proxy 中转（iOS 蜂窝直连 github.io/raw 拉不动）" % n
        assert "/gh-pages/nodes/" in p["url"], "%s provider URL 未引 gh-pages 节点文件" % n
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
    detail = {k: {"rate": v[0], "why": v[2]} for k, v in ranked.items()}
    for n in dropped:
        if n in detail:
            detail[n]["why"] = "%s（达标，但 AUTO 只取前 %d）" % (
                detail[n]["why"], AUTO_MAX)
    ranking = {"auto": picked, "备用": spare + dropped, "观察": watch,
               "不稳定": ["SRCFL-" + n for n in (flaky_sources or ())],
               "degraded": degrade_note,      # 非空 = 本轮是降级发布（run.py 必须喊出来）
               "detail": detail}
    return tpl, base, ranking


def pick_mobile_nodes(per_source_nodes, cap=MOBILE_NODE_CAP, per_src=MOBILE_PER_SRC,
                      preferred=MOBILE_PREFERRED, speed_doc=None):
    """源间轮询取节点（保证多样性），按 (type, server, port) 去重。

    不用「按源顺序取满」——那样前几个源就把名额吃光，等于单源订阅。
    轮询后即使某个源节点全重复，也能从其他源补满。

    `speed_doc` 非空时，每个源的桶内把**实测高带宽节点排前面**：iOS 精简版
    不新增 provider/组（内存不够），只能在现有 120 个名额里优先装快节点。
    没有测速数据的节点保持原顺序，不会被排到已知慢节点后面。
    """
    sources = [s for s in preferred if per_source_nodes.get(s)]
    if not sources:                       # 首选源一个都不在（极端情况）就退回全部
        sources = [s for s, v in per_source_nodes.items() if v]
    buckets = {s: list(per_source_nodes[s]) for s in sources}
    if speed_doc:
        import node_stability as ns
        mbps = {}
        for r in (speed_doc.get("results") or []):
            if isinstance(r, dict) and r.get("fp") and not r.get("error"):
                mbps[r["fp"]] = r.get("mbps") or 0.0
        if mbps:
            for s in sources:
                buckets[s].sort(key=lambda n: (
                    ns.fingerprint(n) not in mbps,
                    -(mbps.get(ns.fingerprint(n)) or 0.0)))
    used = {s: 0 for s in sources}
    picked, seen = [], set()
    while len(picked) < cap:
        progressed = False
        for s in sources:
            if len(picked) >= cap:
                break
            while used[s] < len(buckets[s]) and used[s] < per_src:
                node = buckets[s][used[s]]
                used[s] += 1
                key = (str(node.get("type")), str(node.get("server")),
                       str(node.get("port")))
                if key in seen:
                    continue
                seen.add(key)
                picked.append(dict(node, name="%s_%s" % (s, node.get("name"))))
                progressed = True
                break
        if not progressed:
            break
    return picked, [s for s in sources if used[s] > 0]


def build_mobile_profile(per_source_nodes, owner, repo, speed_doc=None):
    """iOS 精简版：单 provider + select/url-test 两种组 + 全 lazy 规则集。

    为什么单 provider：iOS 网络扩展内存上限约 50MB，节点数是最主要的变量
    （5707 节点实测 95MB，120 节点目标 ≤45MB）。规则集加 lazy 后只在
    命中时加载，33 个全留着不影响启动内存。

    为什么没有 fallback：Karing 官方兼容表明确不支持 fallback / load-balance /
    relay，只保留 select + url-test 才能让 Karing 和 Clash Mi 都正常。
    """
    mbase = mirror_base(owner, repo)
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = yaml.safe_load(f)

    nodes, used_sources = pick_mobile_nodes(per_source_nodes, speed_doc=speed_doc)
    assert nodes, "移动端精简版没有任何节点（per_source_nodes 为空？）"

    provider = provider_block(MOBILE_PROVIDER,
                              mbase + "/nodes/mobile.yaml", "")
    provider["health-check"]["lazy"] = True      # 不用就不测，省电省内存
    tpl["proxy-providers"] = {MOBILE_PROVIDER: provider}
    # 家里的静态 HTTP 代理在手机上没有意义，去掉（也避免组里引用它）
    tpl.pop("proxies", None)

    tpl["proxy-groups"] = [
        {"name": "AUTO", "type": "url-test", "use": [MOBILE_PROVIDER],
         "url": YOUTUBE, "expected-status": 204, "interval": 120,
         "timeout": 5000, "tolerance": 200},
        {"name": "PROXY", "type": "select", "proxies": ["AUTO", "DIRECT"],
         "use": [MOBILE_PROVIDER]},
        {"name": "Claude", "type": "select", "proxies": ["PROXY"],
         "use": [MOBILE_PROVIDER]},
        {"name": "Gemini", "type": "select", "proxies": ["PROXY"],
         "use": [MOBILE_PROVIDER]},
    ]

    # 规则集全部 lazy：启动只建索引，命中才加载。33 个全保留（分流不变）。
    for v in (tpl.get("rule-providers") or {}).values():
        v["lazy"] = True

    # iOS 上 MMDB 可能没随 App 打包；默认下载源是 GitHub，蜂窝下极慢/被墙。
    # 指到 gh-proxy 镜像，首次用到 GEOIP 时也能拿到（Karing 会忽略该键）。
    tpl["geox-url"] = {
        "geoip": "https://gh-proxy.com/https://github.com/MetaCubeX/meta-rules-dat/"
                 "releases/download/latest/geoip.dat",
        "geosite": "https://gh-proxy.com/https://github.com/MetaCubeX/meta-rules-dat/"
                   "releases/download/latest/geosite.dat",
        "mmdb": "https://gh-proxy.com/https://github.com/MetaCubeX/meta-rules-dat/"
                "releases/download/latest/country.mmdb",
    }

    # ---- 校验（手机一进去就报错的坑，必须在出仓前挡住）----
    gtypes = {g["type"] for g in tpl["proxy-groups"]}
    banned = gtypes & {"fallback", "load-balance", "relay"}
    assert not banned, "移动端不能含 Karing 不支持的组类型: %s" % banned
    gp = {g["name"] for g in tpl["proxy-groups"]}
    BUILTIN = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", "GLOBAL"}
    for r in (tpl.get("rules") or []):
        parts = [x.strip() for x in r.split(",")]
        if len(parts) < 2:
            continue
        tgt = parts[-2] if parts[-1] == "no-resolve" else parts[-1]
        if tgt in BUILTIN or tgt in gp or tgt == MOBILE_PROVIDER:
            continue
        raise AssertionError("移动端规则 %r 指向不存在的目标 %r" % (r, tgt))
    assert len(nodes) <= MOBILE_NODE_CAP, "精简版节点数超上限"
    assert provider["url"].startswith("https://gh-proxy.com/raw.githubusercontent.com/")
    assert provider["url"].endswith("/gh-pages/nodes/mobile.yaml")
    # 名字必须全局唯一（provider 内同名会被内核拒绝）
    names = [n["name"] for n in nodes]
    assert len(names) == len(set(names)), "精简版节点名重复"
    return nodes, tpl, used_sources


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
               flaky_nodes=None, mobile=None, video=None):
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
    if video:
        dump_yaml({"proxies": video},
                  "# clash-source 自动生成 —— 视频组节点池，共 %d 节点\n"
                  "# 只收本机真实下载 >= %.1f MB/s（约 1080p）的节点；\n"
                  "# 健康检查存活 ≠ 能看视频，不要手工往这里加没测过的节点。"
                  % (len(video), VIDEO_MBPS),
                  os.path.join(nodes_dir, "video.yaml"))
    if mobile:
        mobile_nodes, mobile_profile, mobile_sources = mobile
        dump_yaml({"proxies": mobile_nodes},
                  "# clash-source 自动生成 —— 移动端精简池，共 %d 节点\n"
                  "# 源间轮询取样 + 按 server:port 去重；只挂 mobile.yaml 一个 provider"
                  % len(mobile_nodes),
                  os.path.join(nodes_dir, "mobile.yaml"))
        dump_yaml(mobile_profile,
                  "# clash-source 移动端精简版（iOS 网络扩展内存优化，2026-11-02）\n"
                  "# 订阅 URL（任选其一）：\n"
                  "# 主:  %s/mobile.yaml\n"
                  "# 备1 gh-proxy raw（零缓存）:\n"
                  "#   https://gh-proxy.com/raw.githubusercontent.com/%s/%s/gh-pages/mobile.yaml\n"
                  "# 备2 gh-proxy raw（main 分支）:\n"
                  "#   https://gh-proxy.com/raw.githubusercontent.com/%s/%s/main/dist/mobile.yaml\n"
                  "# 说明：单 provider（~%d 节点）+ rule-provider 全 lazy；\n"
                  "#   不含 fallback/load-balance（Karing 官方不支持，只有 select/url-test）。\n"
                  "#   完整多源版见同目录 profile.yaml（桌面端用，iOS 上会因内存被杀）。"
                  % (base, owner, repo, owner, repo, MOBILE_NODE_CAP),
                  os.path.join(dist_dir, "mobile.yaml"))
    dump_yaml(profile,
              "# clash-source 自动生成 —— 手机订阅入口\n"
              "# 订阅 URL（任选其一；iOS/手机端建议主链，备2 零缓存最快拿到新配置）：\n"
              "# 主:  %s/profile.yaml\n"
              "# 备1 jsdelivr（国内直连可达；⚠ 分支引用缓存 ~12h，改配置后要等）：\n"
              "#   https://cdn.jsdelivr.net/gh/%s/%s@gh-pages/profile.yaml\n"
              "# 备2 gh-proxy raw（零缓存，推送后立即可拉）：\n"
              "#   https://gh-proxy.com/raw.githubusercontent.com/%s/%s/gh-pages/profile.yaml\n"
              "# 备3 gh-proxy raw（main 分支）:\n"
              "#   https://gh-proxy.com/raw.githubusercontent.com/%s/%s/main/dist/profile.yaml\n"
              "# ⚠ iOS 蜂窝网络下 github.io/raw 直链几乎拉不动 —— proxy-providers 的节点池\n"
              "#   已统一走 gh-proxy 中转（10-31 两段式修复：先 jsdelivr 后按用户拍板换\n"
              "#   gh-proxy 零缓存），订阅 URL 本身拉到即生效，无需改 nodes 链。"
              % (base, owner, repo, owner, repo, owner, repo),
              os.path.join(dist_dir, "profile.yaml"))
    with open(os.path.join(dist_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)