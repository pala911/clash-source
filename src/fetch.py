# -*- coding: utf-8 -*-
"""拉取上游订阅：直连优先，失败自动回退 CN 镜像。

CI（GitHub runner 在美国）直连 raw.githubusercontent 即可；
本地 PC / 国内网络直连 raw 会被墙 -> 自动回退 gh-proxy -> jsdelivr（两者都实测过直连可达）。
"""
import base64
import re
import ssl
import time
import urllib.request

import yaml

UA = "clash-verge-rev/2.x (clash-source pipeline)"


def jsdelivr_url(raw_url):
    """raw.githubusercontent.com -> cdn.jsdelivr.net（refs/heads/main 形式要还原成分支）。"""
    m = re.match(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/(.+)$", raw_url)
    if not m:
        return None
    owner, repo, rest = m.groups()
    m2 = re.match(r"refs/heads/([^/]+)/(.+)$", rest)
    if m2:
        branch, path = m2.groups()
    else:
        branch, path = rest.split("/", 1)
    return "https://cdn.jsdelivr.net/gh/%s/%s@%s/%s" % (owner, repo, branch, path)


def url_chain(url):
    """按优先级排的抓取尝试链。"""
    chain = [url]
    if "raw.githubusercontent.com" in url:
        chain.append("https://gh-proxy.com/" + url)
        j = jsdelivr_url(url)
        if j:
            chain.append(j)
    return chain


_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
        data = r.read()
    return data, time.time() - t0


def fetch(url, timeout=45, tries=2):
    """返回 (data, 实际使用的 url, 耗时秒, 尝试记录)。data 为 None 表示全链失败。"""
    attempts = []
    for u in url_chain(url):
        for i in range(tries):
            try:
                data, dt = _get(u, timeout)
                attempts.append({"url": u, "ok": True, "bytes": len(data), "sec": round(dt, 2)})
                if u != url:
                    attempts.append({"note": "直连失败，已回退镜像"})
                return data, u, dt, attempts
            except Exception as e:
                attempts.append({"url": u, "try": i + 1, "ok": False, "error": str(e)[:120]})
    return None, None, 0.0, attempts


B64_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")


def parse_proxies(data):
    """解析订阅为 proxy 字典列表；识别非 clash 格式（base64 v2ray 列表）。"""
    text = data.decode("utf-8", "replace").lstrip("\ufeff")
    try:
        cfg = yaml.safe_load(text)
    except Exception as e:
        return None, "YAML 解析失败: %s" % str(e)[:100]
    if isinstance(cfg, dict):
        px = cfg.get("proxies") or []
        if isinstance(px, list):
            return [p for p in px if isinstance(p, dict)], None
        return None, "是完整配置但无 proxies 列表"
    if isinstance(cfg, list):
        # ⚠ 原来只查首项（`isinstance(cfg[0], dict)`）就返回**整个列表**：
        #   混在中间/末尾的字符串、数字会一路流到 run.py 的 `p.get("name")`
        #   -> AttributeError 把整轮炸掉（§75 #10）。现在逐项过滤，
        #   一个 dict 都没有时明确报错（不静默当空）。
        ok = [p for p in cfg if isinstance(p, dict)]
        if ok:
            return ok, None
        if not cfg:
            return None, "是空列表（不是 clash 配置）"
        return None, "是列表但没有 proxy 字典（首项类型 %s）" % type(cfg[0]).__name__
    # base64 的 v2ray 链接列表 —— 本仓不做协议转换
    stripped = "".join(text.split())
    if len(stripped) > 40 and B64_RE.match(stripped):
        try:
            dec = base64.b64decode(stripped + "=" * (-len(stripped) % 4)).decode("utf-8", "replace")
            if dec.lstrip().startswith(("vmess://", "vless://", "ss://", "trojan://")):
                return None, "base64 v2ray 链接格式（本仓只处理 clash 格式）"
        except Exception:
            pass
    return None, "无法识别的订阅格式（首行: %s）" % text.strip().splitlines()[0][:60] if text.strip() else "空响应"


def fetch_source(src, timeout=45):
    """抓一个源，返回 (proxies, meta)。meta 含 attempts/错误，供报告审计。

    ⚠ 承诺「一个源坏掉只影响它自己」：上游给了畸形结构（非 dict 的 proxy、
    诡异编码、列表里混字符串……）也必须在这里兜住，**不能把整轮炸掉** ——
    这个承诺原来只写在 docstring 里，函数体根本没有 try/except（§75 #10）。
    """
    meta = {"name": None, "url": None}
    try:
        meta["name"], meta["url"] = src.get("name"), src.get("url")
        data, used, dt, attempts = fetch(src["url"], timeout=timeout)
        meta["attempts"] = attempts
        meta["mirror_used"] = (used != src["url"]) if used else None
        if data is None:
            meta["error"] = "全部 URL 尝试均失败"
            return [], meta
        meta["bytes"] = len(data)
        meta["used_url"] = used
        meta["fetch_sec"] = round(dt, 2)
        proxies, err = parse_proxies(data)
        if proxies is None:
            meta["error"] = err
            return [], meta
        meta["raw_nodes"] = len(proxies)
        return proxies, meta
    except Exception as e:
        meta["error"] = "抓取/解析异常（已兜住，本源按空处理）：%s: %s" % (
            type(e).__name__, str(e)[:80])
        return [], meta