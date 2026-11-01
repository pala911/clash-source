# -*- coding: utf-8 -*-
"""移动端精简版门禁：单 provider、120 上限、去重、Karing 兼容组类型、全 lazy。"""
import io
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import build  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    print("  %s %s%s" % ("✓" if cond else "✗", name, ("  " + detail) if detail else ""))
    if not cond:
        ok = False


def mk_nodes(src, n, port_base):
    return [{"name": "%s-%02d" % (src, i), "type": "ss",
             "server": "10.0.%d.%d" % (port_base, i), "port": 8388 + i,
             "cipher": "aes-128-gcm", "password": "x"} for i in range(n)]


print("=" * 68)
print("场景 A：7 个首选源各 40 节点 -> 轮询取样 + 120 上限 + 去重")
print("=" * 68)
per_source = {s: mk_nodes(s, 40, i + 1)
              for i, s in enumerate(build.MOBILE_PREFERRED)}
# 人为制造跨源重复：让 clashdaily 前 10 个与 zhuhaiuk 前 10 个 server:port 相同
for i in range(10):
    per_source["clashdaily"][i]["server"] = per_source["zhuhaiuk"][i]["server"]
    per_source["clashdaily"][i]["port"] = per_source["zhuhaiuk"][i]["port"]

nodes, prof, used = build.build_mobile_profile(per_source, "pala911", "clash-source")
check("节点数 <= 上限", len(nodes) <= build.MOBILE_NODE_CAP, "%d 个" % len(nodes))
check("达到上限（去重后仍能补满）", len(nodes) == build.MOBILE_NODE_CAP, "%d 个" % len(nodes))
check("覆盖全部首选源", len(used) == len(build.MOBILE_PREFERRED),
      "、".join(used))
keys = [(n["type"], n["server"], n["port"]) for n in nodes]
check("server:port 无重复", len(keys) == len(set(keys)))
check("节点名唯一", len({n["name"] for n in nodes}) == len(nodes))
check("单 provider", list(prof["proxy-providers"]) == [build.MOBILE_PROVIDER])
prov = prof["proxy-providers"][build.MOBILE_PROVIDER]
check("provider 走 gh-proxy + mobile.yaml",
      prov["url"].endswith("/gh-pages/nodes/mobile.yaml")
      and prov["url"].startswith("https://gh-proxy.com/"))
check("health-check lazy", prov["health-check"].get("lazy") is True)
groups = {g["name"]: g for g in prof["proxy-groups"]}
check("组类型只有 select/url-test",
      {g["type"] for g in prof["proxy-groups"]} <= {"select", "url-test"},
      str(sorted({g["type"] for g in prof["proxy-groups"]})))
check("AUTO 是 url-test 且挂 mobile provider",
      groups["AUTO"]["type"] == "url-test" and groups["AUTO"]["use"] == [build.MOBILE_PROVIDER])
check("PROXY 是 select", groups["PROXY"]["type"] == "select")
check("规则集全部 lazy",
      all(v.get("lazy") is True for v in prof["rule-providers"].values()))
check("无静态代理（手机不需要家里路由）", "proxies" not in prof)
check("geox-url 走 gh-proxy 镜像",
      all(u.startswith("https://gh-proxy.com/") for u in prof["geox-url"].values()))

print("")
print("=" * 68)
print("场景 B：首选源全缺 -> 退回全部可用源，不许炸")
print("=" * 68)
only = {"yypool": mk_nodes("yypool", 30, 9)}
nodes2, prof2, used2 = build.build_mobile_profile(only, "pala911", "clash-source")
check("仍能出节点（单源按 25 上限取样）",
      len(nodes2) == build.MOBILE_PER_SRC, "%d 个" % len(nodes2))
check("源清单正确", used2 == ["yypool"], str(used2))

print("")
print("=" * 68)
print("场景 C：没有节点 -> 必须构建失败（宁可构建失败也不出坏订阅）")
print("=" * 68)
try:
    build.build_mobile_profile({}, "pala911", "clash-source")
    check("空输入必须 assert", False)
except AssertionError:
    check("空输入已 assert", True)

print("")
print("=" * 68)
print("场景 D：write_dist 必须把 mobile.yaml + nodes/mobile.yaml 落盘")
print("=" * 68)
import tempfile  # noqa: E402

tmp = tempfile.mkdtemp(prefix="mobile_dist_")
manifest = {"owner": "pala911", "repo": "clash-source"}
build.write_dist(tmp, {"zhuhaiuk": per_source["zhuhaiuk"]},
                 [dict(n) for n in nodes], {"proxy-groups": []}, manifest,
                 "https://pala911.github.io/clash-source",
                 mobile=(nodes, prof, used))
mp = os.path.join(tmp, "mobile.yaml")
np_ = os.path.join(tmp, "nodes", "mobile.yaml")
check("mobile.yaml 落盘", os.path.isfile(mp))
check("nodes/mobile.yaml 落盘", os.path.isfile(np_))
head = io.open(mp, encoding="utf-8").read()
check("头注释带订阅地址", "/mobile.yaml" in head)
pool = yaml.safe_load(io.open(np_, encoding="utf-8"))
check("节点池数量一致", len(pool.get("proxies") or []) == len(nodes))
loaded = yaml.safe_load(io.open(mp, encoding="utf-8"))
check("落盘配置可解析且组类型合规",
      {g["type"] for g in loaded["proxy-groups"]} <= {"select", "url-test"})

print("")
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)
