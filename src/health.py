# -*- coding: utf-8 -*-
"""源健康档案：差源降级进历史库，变好自动回收。

⚠ 口径铁律（坑 §40）：CI runner 在**美国**。mahdibland 的教训是「美机测速筛出的
200 个节点，国内 youtube 0% 通过」。所以：
  - **降级极保守**：必须「一条都没活」连续 3 轮才进历史库，且永远只是 disabled 不删数据。
  - **回收积极**：alive ≥ 5 且通过率 ≥ 8% 连续 2 轮就自动放回（宁可多试，不可错杀好源）。
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

    changed_enabled = []
    for name, r in sorted(rows.items()):
        if r.get("incomplete"):
            print("[health] %-24s 跳过本轮（探针未完成：%s/%s 节点已加载）"
                  % (name, r.get("nodes"), r.get("expected")))
            continue
        rec = hs.setdefault(name, {"runs": [], "bad_streak": 0, "good_streak": 0, "state": "active"})
        rec["runs"].append({"ts": now, "nodes": r["nodes"], "alive": r["alive"],
                            "rate": r["rate"], "best_ms": r["best_ms"]})
        rec["runs"] = rec["runs"][-KEEP_RUNS:]
        alive, rate = r["alive"], r["rate"]

        # --- 判定 ---
        if alive == 0:
            rec["bad_streak"] += 1
            rec["good_streak"] = 0
        elif alive >= GOOD_ALIVE and rate >= GOOD_RATE:
            rec["good_streak"] += 1
            rec["bad_streak"] = 0
        else:
            rec["bad_streak"] = 0
            rec["good_streak"] = 0

        if rec["state"] == "active" and rec["bad_streak"] >= DEAD_STREAK:
            if name in src_by_name:
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
            if name in src_by_name:
                src_by_name[name]["enabled"] = True
                src_by_name[name].pop("quarantine_reason", None)
                changed_enabled.append("%s -> 达标回收" % name)
                arch_by_name.pop(name, None)
                rec["state"] = "active"

        print("[health] %-24s alive=%-4d rate=%-5s 坏%s/好%s 状态=%s"
              % (name, alive, rate, rec["bad_streak"], rec["good_streak"], rec["state"]))

    if changed_enabled:
        write_src_cfg(cfg)
        arch["sources"] = list(arch_by_name.values())
        write_arch(arch)
    save_health(h)
    if changed_enabled:
        print("[health] 已更新 sources.yaml / archive/sources.yaml: %s" % "，".join(changed_enabled))
    else:
        print("[health] 无升降级变更")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())