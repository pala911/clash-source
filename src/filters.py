# -*- coding: utf-8 -*-
"""确定性硬过滤 —— 不依赖 AI，可复现、可审计。

原则（踩过的坑）：
- 命名引流/占位节点会躲过命名过滤，必须同时做字段级校验（坑 §6）
- 「TCP 通」严重高估质量，硬过滤只删明显垃圾，绝不据此保留（坑 §5）
- CN 中转伪装（ukn_dokng 那种）是 AI 阶段的活儿，这里只标记不删（坑 §27）
"""
import re

# 允许的协议。
# 注意：明文 http / socks5 必须放行 —— 实测它们是真在用的免费机场 HTTP CONNECT 代理
# （ssrsub 43%、zhuhaiuk 52% 通过率的主力就是这类），不能凭「明文」就当垃圾删（2026-10-13 教训）。
ALLOWED_TYPES = {"ss", "ssr", "vmess", "vless", "trojan", "hysteria2", "tuic",
                 "anytls", "snell", "http", "socks5", "socks"}

# 字段级必填项：type -> 必填字段（明文代理无凭据要求）
REQUIRED_FIELDS = {
    "ss": ("cipher", "password"),
    "ssr": ("cipher", "password"),
    "vmess": ("uuid",),
    "vless": ("uuid",),
    "trojan": ("password",),
    "hysteria2": ("password",),
    "tuic": ("uuid", "password"),
    "anytls": ("password",),
    "snell": ("psk",),
    "http": (),
    "socks5": (),
    "socks": (),
}

# mihomo 严格模式：一个畸形节点会让整个 provider 拒绝加载（实测：autojiedian 里
# 一个「有 obfs 无 obfs-password」的节点 → 2101 个节点全部不加载，日志只留一行 error）。
# 所以流水线必须做 mihomo 同款的字段配对校验，规则宁严勿松。
KNOWN_PLUGINS = {"obfs", "obfs-local", "v2ray-plugin", "shadow-tls", "restls"}


def _field_pair_check(node, ptype):
    """返回原因字符串，空串 = 通过。"""
    obfs = node.get("obfs")
    obfs_pwd = node.get("obfs-password")
    plugin = str(node.get("plugin") or "")
    if (obfs and not obfs_pwd) or (plugin == "obfs" and not obfs_pwd):
        return "有 obfs/plugin 但缺 obfs-password（会让整个 provider 加载失败）"
    if ptype == "ss" and not node.get("cipher"):
        return "ss 缺 cipher"
    if ptype in ("vless",) and node.get("reality-opts") and \
            not (node.get("reality-opts") or {}).get("public-key"):
        return "reality-opts 缺 public-key"
    if ptype == "hysteria2" and not node.get("up") and not node.get("down"):
        pass  # up/down 可选，不拦
    return ""


# 命中即丢的命名垃圾 —— 只保留「无歧义」的那些。
# 2026-10-13 对照实测（peekpro/probe_variants.py，2085 节点真探针）后的教训：
#   * 早先规则里的 www\. / .com$ / 教程|客户端|app / vip|付费 / test|假 属于过度过滤 ——
#     ermaozi 的 [www.v2nodes.com] 是正常节点；anytls 里被 test|限速 类规则误杀了 3 个活的。
#   * 语义类判断（是不是引流/广告/伪装）交给 ai_review.py，硬过滤只做兜底。
#   * 明文 http/socks5 必须放行：545 个明文通过 177（32%），733 个加密协议只通过 14（1.9%）。
JUNK_PATTERNS = [
    r"(?i)cf\s*referral",
    r"(?i)cloudflare\s*challenge",
    r"(?i)(过期|失效|剩余流量|流量剩余|到期时间|重置时间)",   # 状态占位
    r"(?i)(官网|导航站|订阅地址|加群|群组|客服)",                # 明确广告位
    r"(?i)(占位|placeholder)",
    r"[\u200b-\u200f\ufeff]",                                  # 零宽字符（藏推广）
]

# 命中只标记给 AI 看，不删
SOFT_PATTERNS = [
    r"(?i)(中转|落地|回国|专线|内网)",
    r"[\U0001F1E6-\U0001F1FF]{2}",   # 国旗 emoji，地区标注可信但值得 AI 复核
    r"(?i)(ukn|uk\d|usa\d+\d+)",      # 数字混淆的伪装出口名（坑 §27 样本）
]
SOFT_RE = [re.compile(p) for p in SOFT_PATTERNS]
JUNK_RE = [re.compile(p) for p in JUNK_PATTERNS]

ZERO_WIDTH = re.compile(r"[\u200b-\u200f\ufeff]")

STATS = {}


def _bump(key, n=1):
    STATS[key] = STATS.get(key, 0) + n


def stats():
    return dict(STATS)


def load_exclude_filter(sources_cfg):
    """从 sources.yaml 取全局 exclude-filter 串。"""
    return sources_cfg.get("exclude_filter") or ""


def soft_hits(name):
    """返回该节点命中的软标记列表（供 AI 阶段参考）。"""
    hits = []
    for p, rx in zip(SOFT_PATTERNS, SOFT_RE):
        if rx.search(name):
            hits.append(p)
    return hits


def hard_filter(node, exclude_filter, drop_types=()):
    """返回 (是否保留, 原因)。原因非空即被丢弃。"""
    name = ZERO_WIDTH.sub("", str(node.get("name", ""))).strip()
    ptype = str(node.get("type", "")).lower()

    if not name:
        return False, "空名"
    if ptype in set(drop_types or ()):
        return False, "协议在 drop_types(%s)" % ptype
    if ptype not in ALLOWED_TYPES:
        return False, "不支持的协议 %s" % (ptype or "空")
    for f in REQUIRED_FIELDS.get(ptype, ()):
        if not node.get(f):
            return False, "缺必填字段 %s" % f

    server = node.get("server")
    if not server or not str(server).strip():
        return False, "无 server"
    try:
        port = int(node.get("port"))
    except (TypeError, ValueError):
        return False, "port 非法"
    if not (0 < port < 65536):
        return False, "port 越界"

    if exclude_filter and re.search(exclude_filter, name):
        return False, "命名命中 exclude-filter"
    for rx in JUNK_RE:
        if rx.search(name):
            return False, "命名垃圾(%s)" % rx.pattern[:24]

    why = _field_pair_check(node, ptype)
    if why:
        return False, why

    # 清理节点：只留 name/type/server/port（已归一）+ 协议所需字段，丢掉上游杂项
    extra = {"cipher", "password", "username", "uuid", "alterId", "alterid", "sni", "servername",
             "network", "ws-opts", "ws-headers", "ws-path", "path", "host", "headers",
             "tls", "udp", "skip-cert-verify", "client-fingerprint", "alpn",
             "plugin", "plugin-opts", "obfs", "obfs-opts", "obfs-password",
             "encryption", "flow", "reality-opts", "public-key", "short-id",
             "allowInsecure", "up", "down", "congestion-controller", "version",
             "packet-addr", "packet-port", "xudp", "xudp-congestion-controller",
             "sni-h2", "ech", "dialer-proxy", "interface-name", "routing-mark",
             "smux", "ports", "passwords", "final", "idle-timeout"}
    # 剔除 mihomo 会拒绝或持续告警的脏字段
    plug = str(node.get("plugin") or "")
    if plug and plug not in KNOWN_PLUGINS:
        node.pop("plugin", None)
        node.pop("plugin-opts", None)
    elif not plug:
        node.pop("plugin-opts", None)
    cf = str(node.get("client-fingerprint") or "").strip().lower()
    if cf in ("", "none", "unsafe"):
        node.pop("client-fingerprint", None)

    out = {"name": name, "type": ptype, "server": str(server).strip(), "port": port}
    for k, v in node.items():
        if k in extra:
            out[k] = v
    node.clear()
    node.update(out)
    return True, ""


def dedupe_key(node):
    """同源去重键：协议 + server + port + 关键凭据（shaoyouvip 曾在同一 IP 上开 4 个节点）。"""
    ptype = str(node.get("type", "")).lower()
    cred = ""
    for f in ("password", "uuid", "psk"):
        if node.get(f):
            cred = str(node[f])
            break
    return (ptype, str(node.get("server", "")).lower(), int(node.get("port") or 0), cred)


def unique_names(nodes, tag):
    """保证文件内节点名唯一（跨源合并时用源标签前缀）。"""
    seen = {}
    for p in nodes:
        base = ZERO_WIDTH.sub("", str(p.get("name", "node"))).strip() or "node"
        base = base[:60]
        if tag:
            base = "%s_%s" % (tag, base)
        if base in seen:
            seen[base] += 1
            base = "%s_%d" % (base, seen[base])
        else:
            seen[base] = 1
        p["name"] = base
    return nodes