# -*- coding: utf-8 -*-
"""带宽测速工具的纯逻辑门禁（不启动 mihomo、不消耗流量）。

覆盖：
  A 抽样纪律：每源一半最快 + 一半确定性随机，跨源按指纹去重
  B 排除项：mobile 合成池、--flaky 池默认不测
  C 按源轮转：预算被掐断时每个源都先测到，不会前几个源吃满
  D 工作目录：节点统一改名 spdNNN（跨源重名不会切错），配置可解析
  E 统计口径：720p/1080p/4K 分档计数
"""
import io
import os
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.chdir(ROOT)

import speed_test as st  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    print("  %s %s%s" % ("✓" if cond else "✗", name,
                         ("  " + detail) if detail else ""))
    if not cond:
        ok = False


def mk_nodes(src, n, port_base, dup_with=None):
    out = []
    for i in range(n):
        node = {"name": "%s-%02d" % (src, i), "type": "ss",
                "server": "10.0.%d.%d" % (port_base, i),
                "port": 8388 + i, "cipher": "aes-128-gcm", "password": "x"}
        if dup_with is not None and i < len(dup_with):
            node["server"] = dup_with[i]["server"]
            node["port"] = dup_with[i]["port"]
        out.append(node)
    return out


def write_nodes(path, name, nodes):
    with io.open(os.path.join(path, name + ".yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump({"proxies": nodes}, f, allow_unicode=True, sort_keys=False)


print("=" * 68)
print("场景 A：每源抽样 + 跨源指纹去重")
print("=" * 68)
tmp = tempfile.mkdtemp(prefix="speed_test_")
try:
    a = mk_nodes("srcA", 12, 1)
    b = mk_nodes("srcB", 12, 2, dup_with=a[:3])
    write_nodes(tmp, "srcA", a)
    write_nodes(tmp, "srcB", b)
    write_nodes(tmp, "mobile", mk_nodes("mobile", 5, 9))
    write_nodes(tmp, "srcA--flaky", mk_nodes("srcAfl", 3, 8))

    cands = st.load_candidates(tmp, per_source=4, seed=7)
    names = [c["name"] for c in cands]
    check("每源 4 个（2 快 + 2 随机）", len(cands) == 8, "%d 个" % len(cands))
    check("不含 mobile 合成池", not any(c["source"] == "mobile" for c in cands))
    check("默认不含 --flaky", not any(c["source"].endswith("--flaky") for c in cands))
    check("跨源重复节点只测一次", len(names) == len(set(names)))
    check("重复节点归第一个源", any(c["source"] == "srcA" and c["name"] == "srcA-00"
                                     for c in cands))
    check("srcB 的重复项被跳过",
          not any(c["source"] == "srcB" and c["name"] == "srcB-00" for c in cands))

    cands2 = st.load_candidates(tmp, per_source=4, seed=7)
    check("同 seed 结果确定", [c["name"] for c in cands2] == names)

    cands3 = st.load_candidates(tmp, per_source=4, seed=8)
    check("换 seed 随机半区会变", [c["name"] for c in cands3] != names)

    print("")
    print("=" * 68)
    print("场景 B：按源轮转（预算掐断时仍覆盖每个源）")
    print("=" * 68)
    sources = [c["source"] for c in cands]
    first_four = sources[:4]
    check("前 4 个候选覆盖 2 个源", set(first_four) == {"srcA", "srcB"},
          "、".join(first_four))
    check("轮转顺序 A/B 交替", first_four == ["srcA", "srcB", "srcA", "srcB"],
          "、".join(first_four))

    print("")
    print("=" * 68)
    print("场景 C：工作目录改名与配置")
    print("=" * 68)
    work = os.path.join(tmp, "work")
    cpath, renamed = st.build_workdir(cands, workdir=work)
    check("配置落盘", os.path.isfile(cpath))
    check("节点统一改名 spdNNN",
          [r["test_name"] for r in renamed] == ["spd%03d" % i for i in range(8)])
    cfg = yaml.safe_load(io.open(cpath, encoding="utf-8"))
    check("provider 指向工作目录内", cfg["proxy-providers"]["speed"]["path"] ==
          "./nodes/speed.yaml")
    check("select 组只有一个", [g["name"] for g in cfg["proxy-groups"]] == ["SPD"])
    proxies = yaml.safe_load(io.open(os.path.join(work, "nodes", "speed.yaml"),
                                     encoding="utf-8"))["proxies"]
    check("改名后的节点名全局唯一",
          len({p["name"] for p in proxies}) == len(proxies) == 8)

    print("")
    print("=" * 68)
    print("场景 D：分档统计")
    print("=" * 68)
    results = [
        {"mbps": 3.0}, {"mbps": 2.5}, {"mbps": 1.0}, {"mbps": 0.6},
        {"mbps": 0.3}, {"mbps": 0.0}, {"mbps": 0, "error": "x"},
    ]
    summary = st.summarize(results)
    check("4K 档 >=2.5", summary["4K (>=2.5 MB/s)"] == 2)
    check("1080p 档 >=0.6", summary["1080p (>=0.6 MB/s)"] == 4)
    check("720p 档 >=0.3", summary["720p (>=0.3 MB/s)"] == 5)
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print("")
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)
