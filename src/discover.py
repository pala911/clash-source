# -*- coding: utf-8 -*-
"""GitHub 共享源自动发现 —— 只产出「候选」，绝不自动入池。

设计原则（2026-10-14 定）：
- 发现的源一律进候选池（data/discovered_pool.json），**必须经真探针评估**才由人/流程移入 sources.yaml。
  理由：README 说"每日更新""测速筛选"不可信（记忆坑 §4/§5/§40），自动入池等于把垃圾直接喂给手机。
- 只抓 README 里**明文写出的**订阅地址，不猜路径、不爬站点。猜路径今天已验证命中率极低
  （freefq/ALIILAPRO/Pawdroid/mfbpn/ovmvo/aiboboxx/NodeFree/wrfree 八次全 404）。
- 抓不到就跳过，全程 fail-soft，任何异常都不影响主流程。
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "discovered_pool.json")
SOURCES_YAML = os.path.join(HERE, "sources.yaml")

# 搜索式：多角度覆盖，命中去重
QUERIES = [
    "clash 订阅 in:name,description",
    "clash free nodes subscription",
    "免费节点 订阅 clash",
    "clash 节点 每日更新",
    "v2ray clash nodes free",
]
PER_QUERY = 12
MAX_CANDIDATES = 40

UA = "clash-source-discovery/1.0"
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

# README 里可能出现的订阅链接（clash 配置常见文件名 + 常见托管）
HINT = re.compile(
    r"https?://[^\s`\"'<>\)\]]+?"
    r"(?:clash|clashmeta|clash_meta|mihomo|meta|list|sub|config|node|nodes|free|all)"
    r"[^\s`\"'<>\)\]]*?\.(?:ya?ml|txt)",
    re.I)


def token():
    for k in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(k):
            return os.environ[k].strip()
    return ""


def api_get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
        **({"Authorization": "Bearer " + token()} if token() else {})})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def search_repos():
    """GitHub 搜索候选仓（按最近更新排序，优先有星标的）。"""
    found = {}
    for q in QUERIES:
        url = ("https://api.github.com/search/repositories?q="
               + urllib.parse.quote(q) + "&sort=updated&order=desc&per_page=%d" % PER_QUERY)
        try:
            data = api_get(url)
        except Exception as e:      # 限流/网络异常都跳过，不影响其他查询
            print("  [discover] 搜索失败 %r: %s" % (q[:28], str(e)[:70]))
            continue
        for it in (data.get("items") or []):
            name = it.get("full_name")
            if not name:
                continue
            found[name] = {
                "repo": name,
                "stars": it.get("stargazers_count", 0),
                "pushed_at": it.get("pushed_at", ""),
                "description": (it.get("description") or "")[:100],
                "default_branch": it.get("default_branch") or "main",
                "urls": [],
            }
        time.sleep(2)              # 搜索 API 未认证 10 次/分钟，认证 30 次/分钟
    return sorted(found.values(), key=lambda r: (-r["stars"], r["pushed_at"]), reverse=True)


def fetch_readme(repo):
    """走 GitHub API 读 README（自动处理分支/编码）。

    ⚠ 2026-10-14 实测：`raw.githubusercontent.com` 在国内**直连必被墙**（WinError 10054），
    而 api.github.com 正常。所以不能直接拉 raw，只能用 contents/readme API 拿 base64。
    """
    try:
        data = api_get("https://api.github.com/repos/%s/readme" % repo, timeout=20)
    except Exception:
        return None
    if data.get("encoding") == "base64" and data.get("content"):
        try:
            import base64
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        except Exception:
            return None
    return None


def repo_default_branch(repo):
    try:
        data = api_get("https://api.github.com/repos/%s" % repo, timeout=15)
        return data.get("default_branch") or "main"
    except Exception:
        return "main"


def fetch_text(url, timeout=20):
    """直取文本（仅用于校验候选订阅地址本身；注意 raw 域名在国内不可达）。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
        return r.read(400000).decode("utf-8", "replace")


def extract_urls(readme_text):
    urls = []
    for m in HINT.finditer(readme_text or ""):
        u = m.group(0).rstrip(".,;:)]}'\"")
        # 去掉 markdown 行内链接的尾部符号
        u = u.split(" ")[0]
        if u not in urls:
            urls.append(u)
    return urls


def known_urls():
    """已配置源的所有 URL，用来去重（含 exclude 段）。"""
    try:
        import yaml
        cfg = yaml.safe_load(open(SOURCES_YAML, encoding="utf-8")) or {}
        out = set()
        for s in (cfg.get("sources") or []) + (cfg.get("excluded") or []):
            if s.get("url"):
                out.add(s["url"])
        return out
    except Exception:
        return set()


def dead_urls():
    """历史库（archive/sources.yaml）里的 URL —— 曾经试过且被判死的，不再重复发现。"""
    p = os.path.join(ROOT, "archive", "sources.yaml")
    try:
        import yaml
        cfg = yaml.safe_load(open(p, encoding="utf-8")) or {}
        return {s.get("url") for s in (cfg.get("sources") or []) if s.get("url")}
    except Exception:
        return set()


RAW_RE = re.compile(r"https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$", re.I)
DATE_SEG = re.compile(r"/(20\d{2})[/_-]?(0[1-9]|1[0-2])?[/_-]?(20\d{2})?/\d{0,2}[-_.]?(20\d{6})?\d*\.(?:ya?ml|txt)$", re.I)


def _shape_key(url):
    """把「同一份东西的不同日期切片」归一成同一个 key，用于同仓去重。"""
    u = url.lower()
    u = DATE_SEG.sub("/<dated>\\1", u)
    u = re.sub(r"/\d{8}/", "/<dated>/", u)
    u = re.sub(r"\d{8}", "<date>", u)
    u = re.sub(r"[0-9]+", "<n>", u)
    return u


def looks_like_subscription(url, timeout=18):
    """粗筛：确认是真正的 clash 配置（proxies: / proxy-groups: / proxy-providers:）。

    raw.githubusercontent.com 国内不可达 -> 改走 API contents；非 raw 的 URL（如 github.io Pages）直连。
    """
    head = ""
    m = RAW_RE.match(url)
    if m:
        owner, repo, ref, path = m.groups()
        try:
            data = api_get("https://api.github.com/repos/%s/%s/contents/%s?ref=%s"
                           % (owner, repo, urllib.parse.quote(path), urllib.parse.quote(ref)),
                           timeout=timeout)
        except Exception:
            return None
        import base64
        if (data.get("encoding") == "base64" and data.get("content")):
            try:
                head = base64.b64decode(data["content"]).decode("utf-8", "replace")[:6000]
            except Exception:
                return None
        else:
            return None
    else:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
                head = r.read(6000).decode("utf-8", "replace")
        except Exception:
            return None
    low = head.lower()
    if "proxies:" in low or "proxy-providers:" in low or "proxy-groups:" in low:
        return low.count("- name:") or low.count("proxies:")
    return None


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("[discover] 开始扫描 GitHub…")
    repos = search_repos()
    print("[discover] 候选仓 %d 个，开始抽 README 里的订阅链接" % len(repos))

    seen = known_urls() | dead_urls()
    results = []
    scanned = 0
    # 同一仓往往有多条同模式链接（如 uploads/2026/10/{0,1,2}-YYYYMMDD.yaml），
    # 那是「同一份东西按日期切片」，只留最新的一条，否则候选池会被日期文件灌水。
    repo_best = {}
    for repo in repos:
        if len(results) >= MAX_CANDIDATES:
            break
        scanned += 1
        text = fetch_readme(repo["repo"])
        if not text:
            continue
        for u in extract_urls(text)[:8]:
            if u in seen:
                continue
            seen.add(u)
            n = looks_like_subscription(u)
            if n is None:
                continue
            key = _shape_key(u)
            prev = repo_best.get(repo["repo"])
            if prev is None or key == prev[0]:
                if prev is None:
                    repo_best[repo["repo"]] = (key, {
                        "repo": repo["repo"],
                        "stars": repo["stars"],
                        "pushed_at": repo["pushed_at"],
                        "url": u,
                        "signals": n,
                        "found_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "verdict": "pending",
                        "note": "",
                    })
                continue
            # 不同形态的链接（如既有 uploads 日期文件、又有稳定 sub.yml）都值得看
            results.append({
                "repo": repo["repo"], "stars": repo["stars"], "pushed_at": repo["pushed_at"],
                "url": u, "signals": n,
                "found_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "verdict": "pending", "note": "",
            })
    # 同形态的取最后一条（README 通常按新到旧排列，最后一条最新）
    for _repo, (_shape, item) in repo_best.items():
        results.append(item)

    old = {}
    try:
        old = {c["url"]: c for c in json.load(open(OUT, encoding="utf-8"))["candidates"]}
    except Exception:
        pass
    for c in results:            # 保留历史结论，别把已判死的重新标成 pending
        if c["url"] in old:
            c["verdict"] = old[c["url"]].get("verdict", "pending")
            c["note"] = old[c["url"]].get("note", "")
    for c in old.values():
        if c["url"] not in {r["url"] for r in results}:
            results.append(c)    # 历史条目也留着，保留判死记录

    json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "scanned_repos": scanned,
               "candidates": results},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    pend = [c for c in results if c.get("verdict") == "pending"]
    print("[discover] 扫描 %d 个仓，发现 %d 个新候选（历史池共 %d，pending %d）-> %s"
          % (scanned, len(pend), len(results), len(pend), OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())