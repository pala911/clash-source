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
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "profile_template.yaml")


def resolve_owner_repo(owner, repo):
    owner = owner or os.environ.get("GITHUB_REPOSITORY_OWNER") or "YOUR_GITHUB_ID"
    env_repo = os.environ.get("GITHUB_REPOSITORY", "")
    repo = repo or (env_repo.split("/")[-1] if env_repo else "") or "clash-source"
    return owner, repo


def pages_base(owner, repo):
    return "https://%s.github.io/%s" % (owner, repo)


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


def build_profile(enabled_sources, exclude_map, owner, repo):
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = yaml.safe_load(f)

    base = pages_base(owner, repo)
    providers = {}
    for s in enabled_sources:
        providers[s["name"]] = provider_block(
            s["name"], base + "/nodes/%s.yaml" % s["name"],
            exclude_map.get(s["name"], ""))

    tpl["proxy-providers"] = providers
    # 组在模板里按 use: [provider名] 引用，provider 名沿用源名 -> 组无需改动
    used = {n for g in tpl.get("proxy-groups", []) for n in (g.get("use") or [])}
    missing = used - set(providers)
    assert not missing, "模板里引用了未提供的 provider: %s" % missing

    # ---- 校验链（失败即中止，不产出坏 profile）----
    auto = [g for g in tpl["proxy-groups"] if g.get("url")]
    assert len(auto) == len(providers) + 2, \
        "自动组应为 len(SRC)+AUTO+FAILOVER = %d，实为 %d" % (len(providers) + 2, len(auto))
    for g in auto:
        assert g["url"] == YOUTUBE, "%s 探针非 youtube: %s" % (g["name"], g["url"])
    for n, p in providers.items():
        assert p["health-check"]["url"] == YOUTUBE, "%s provider 探针非 youtube" % n
        assert "raw.githubusercontent" not in p["url"], "%s provider URL 用了 raw（手机被墙）" % n
        assert ".github.io/" in p["url"], "%s provider URL 未走 github.io" % n
    raw = yaml.safe_dump(tpl, allow_unicode=True, sort_keys=False, width=4096)
    assert "gstatic" not in raw, "残留 gstatic"
    return tpl, base


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


def write_dist(dist_dir, per_source_nodes, all_nodes, profile, manifest, base):
    nodes_dir = os.path.join(dist_dir, "nodes")
    os.makedirs(nodes_dir, exist_ok=True)
    owner = manifest.get("owner") or "YOUR_GITHUB_ID"
    repo = manifest.get("repo") or "clash-source"
    for name, nodes in per_source_nodes.items():
        dump_yaml({"proxies": nodes},
                  "# clash-source 自动生成 —— 源 %s，共 %d 节点\n"
                  "# 不要手改；改动会在下次定时任务被覆盖（上游 %s/nodes/%s.yaml）"
                  % (name, len(nodes), base, name),
                  os.path.join(nodes_dir, "%s.yaml" % name))
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