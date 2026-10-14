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

  所以：**CI 每日判死，本机每周判优**（2026-10-14 决定不新增云资源、本机探针降频；
  CI 每日跑是因为抓取更新才是日频刚需，跟探针无关）。

阈值：
  - **降级极保守**：CI 连续 3 轮 0 活才进历史库，且永远只是 enabled=false 不删数据。
  - **回收积极**：本机 alive ≥ 5 且通过率 ≥ 8% 连续 2 轮就自动放回（宁可多试，不可错杀好源）。
  - 探针不完整（incomplete，大源没加载完）**不参与判定**，否则会把 2000 节点的
    autojiedian 误判成死源。

产物：state/source_health.json（滚动历史）+ archive/sources.yaml（历史库）
      + 就地改写 src/sources.yaml 的 enabled 标志
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEALTH = os.path.join(ROOT, "state", "source_health.json")
ARCHIVE = os.path.join(ROOT, "archive", "sources.yaml")
SOURCES = os.path.join(HERE, "sources.yaml")
PROBE = os.path.join(ROOT, "state", "probe_latest.json")

DEAD_STREAK = 3        # 连续 N 轮 0 活 -> 降级
GOOD_STREAK = 2        # 连续 N 轮达标 -> 回收
GOOD_ALIVE = 5         # 「变好」的活节点下限（绝对值，不是比例）
GOOD_RATE = 8.0        # 「变好」的通过率下限（%）
KEEP_RUNS = 12         # 每源保留最近 N 轮历史


def load_probe():
    try:
        return json.load(open(PROBE, encoding="utf-8"))
    except Exception:
        return {}


def load_health():
    try:
        return json.load(open(HEALTH, encoding="utf-8"))
    except Exception:
        return {"sources": {}}


def save_health(h):
    os.makedirs(os.path.dirname(HEALTH), exist_ok=True)
    json.dump(h, open(HEALTH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def src_cfg():
    import yaml
    return yaml.safe_load(open(SOURCES, encoding="utf-8")) or {}


def write_src_cfg(cfg):
    import yaml
    with open(SOURCES, "w", encoding="utf-8") as f:
        f.write("# 上游源清单 —— pipeline 的唯一事实来源\n"
                "# 注意：enabled 标志由 src/health.py 依据真探针自动维护\n"
                "#   连续多轮 0 活 -> enabled: false 并移入 archive/sources.yaml（历史库）\n"
                "#   达标后自动回填 enabled: true（源本体永不删除，只改开关）\n")
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=4096)


def arch_cfg():
    import yaml
    try:
        return yaml.safe_load(open(ARCHIVE, encoding="utf-8")) or {}
    except Exception:
        return {"sources": []}


def write_arch(cfg):
    import yaml
    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    with open(ARCHIVE, "w", encoding="utf-8") as f:
        f.write("# 历史库：曾启用但被判死的源。**源本体永不删除**，只是被摘掉。\n"
                "# 判据：真探针（youtube/generate_204）连续 %d 轮 0 活。\n"
                "# 恢复：alive ≥ %d 且通过率 ≥ %s%% 连续 %d 轮 -> health.py 自动回填 enabled: true。\n"
                "# ⚠ 探针 runner 在美国，判据偏保守（宁可多留，不可错杀）。\n"
                % (DEAD_STREAK, GOOD_ALIVE, GOOD_RATE, GOOD_STREAK))
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=4096)


def main():
    import yaml
    probe = load_probe()
    rows = (probe.get("sources") or {})
    scope = probe.get("scope", "ci")
    if not rows:
        print("[health] 无探针数据，跳过（先跑 src/probe.py）")
        return 0

    h = load_health()
    hs = h.setdefault("sources", {})
    cfg = src_cfg()
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
    h["last_probe"] = {"ts": ts, "scope": scope}

    changed_enabled = []
    dup_sources = []
    for name, r in sorted(rows.items()):
        if r.get("incomplete"):
            print("[health] %-24s 跳过本轮（探针未完成：%s/%s 节点已加载）"
                  % (name, r.get("nodes"), r.get("expected")))
            continue
        rec = hs.setdefault(name, {"runs": [], "bad_streak": 0, "good_streak": 0, "state": "active"})
        runs = rec.setdefault("runs", [])
        is_dup = bool(runs) and runs[-1].get("ts") == ts and runs[-1].get("scope") == scope
        if is_dup:
            dup_sources.append(name)
            continue
        runs.append({"ts": ts, "scope": scope, "nodes": r["nodes"],
                     "alive": r["alive"], "rate": r["rate"], "best_ms": r["best_ms"]})
        rec["runs"] = runs[-KEEP_RUNS:]
        alive, rate = r["alive"], r["rate"]

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
        dead = (alive == 0)
        good = (alive >= GOOD_ALIVE and rate >= GOOD_RATE)
        if dead:
            if scope == "ci":
                rec["bad_streak"] += 1
            rec["good_streak"] = 0
        else:
            # 两个口径一致认同的一点：只要有活节点，「没死」这个事实就成立
            rec["bad_streak"] = 0
            if scope == "local":
                rec["good_streak"] = rec["good_streak"] + 1 if good else 0

        if rec["state"] == "active" and rec["bad_streak"] >= DEAD_STREAK:
            # 二次保险：bad_streak 只可能由 scope==ci 攒出来，这里再挡一次
            if scope != "ci":
                pass
            elif name in src_by_name:
                src_by_name[name]["enabled"] = False
                src_by_name[name]["quarantine_reason"] = "真探针连续 %d 轮 0 活" % DEAD_STREAK
                changed_enabled.append("%s -> 降级入历史库" % name)
                arch_by_name.setdefault(name, {})
                arch_by_name[name].update({
                    "name": name, "url": src_by_name[name]["url"],
                    "note": src_by_name[name].get("note", ""),
                    "quarantined_at": now, "quarantine_reason": "真探针连续 %d 轮 0 活" % DEAD_STREAK,
                })
                rec["state"] = "quarantined"
        elif rec["state"] == "quarantined" and rec["good_streak"] >= GOOD_STREAK:
            # good_streak 已由上面的逻辑保证只有 scope==local 才累积，这里是二次保险。
            # CI 口径的分数毫无意义：美国跑出来 ssrsub 90%、shaoyouvip 81%（国内实测垫底 6.2%），
            # 拿它判回收会把差源误收回来。
            if scope != "local":
                print("[health] %-24s CI 口径不判回收（等本机探针确认）" % name)
            elif name in src_by_name:
                src_by_name[name]["enabled"] = True
                src_by_name[name].pop("quarantine_reason", None)
                changed_enabled.append("%s -> 达标回收" % name)
                arch_by_name.pop(name, None)
                rec["state"] = "active"

        print("[health] %-24s scope=%-5s alive=%-4d rate=%-5s 坏%s/好%s 状态=%s"
              % (name, scope, alive, rate, rec["bad_streak"], rec["good_streak"], rec["state"]))

    if changed_enabled:
        write_src_cfg(cfg)
        arch["sources"] = list(arch_by_name.values())
        write_arch(arch)
    save_health(h)
    if dup_sources:
        print("[health] 其中 %d 个源识别为「同一轮探针」（ts=%s）已跳过重复计数"
              % (len(dup_sources), ts))
    if changed_enabled:
        print("[health] 已更新 sources.yaml / archive/sources.yaml: %s" % "，".join(changed_enabled))
    elif not dup_sources:
        print("[health] 无升降级变更")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())