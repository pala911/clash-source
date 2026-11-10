# -*- coding: utf-8 -*-
"""「视频」组与带宽测速消费链的门禁。

覆盖：
  A load_speed：缺失/损坏/非本机口径/过期 -> 一律跳过视频组，绝不抛
  B pick_video_nodes：阈值、指纹关联、单源上限、总量上限、最少节点
  C build_profile：视频 provider/组/PROXY 引用；没有视频节点时完全不出现
  D write_dist + prune：video.yaml 落盘；本轮没生成时旧文件会被清理
  E 移动端：不新增 provider/组，只在现有池内优先装测速快的节点
"""
import datetime
import io
import json
import os
import shutil
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import build          # noqa: E402
import node_stability as ns  # noqa: E402
import run as run_mod  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    print("  %s %s%s" % ("✓" if cond else "✗", name,
                         ("  " + detail) if detail else ""))
    if not cond:
        ok = False


def mk_node(src, i):
    return {"name": "%s-%02d" % (src, i), "type": "ss",
            "server": "10.%d.%d.%d" % (ord(src[-1]), i // 250, i % 250 + 1),
            "port": 10000 + i, "cipher": "aes-128-gcm", "password": "x"}


def speed_row(node, mbps, error=None):
    return {"source": "s", "name": node["name"], "fp": ns.fingerprint(node),
            "mbps": mbps, "error": error, "median_ms": 100}


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


print("=" * 68)
print("场景 A：load_speed 的失败方向（跳过视频组，不抛）")
print("=" * 68)
tmp = tempfile.mkdtemp(prefix="video_gate_")
try:
    good = os.path.join(tmp, "good.json")
    now = datetime.datetime(2026, 11, 10, 12, 0, 0)
    write_json(good, {"tested_at": "2026-11-10T11:00:00Z", "scope": "local",
                      "results": [{"fp": "x", "mbps": 1.0, "error": None}]})
    doc, note = build.load_speed(good, now=now)
    check("有效档案可读", doc is not None and note == "")

    doc, note = build.load_speed(os.path.join(tmp, "nope.json"), now=now)
    check("缺失 -> None + 说明", doc is None and "不存在" in note)

    bad = os.path.join(tmp, "bad.json")
    io.open(bad, "w", encoding="utf-8").write("{not json")
    doc, note = build.load_speed(bad, now=now)
    check("损坏 -> None + 说明", doc is None and "损坏" in note)

    foreign = os.path.join(tmp, "foreign.json")
    write_json(foreign, {"tested_at": "2026-11-10T11:00:00Z", "scope": "cnci",
                         "results": []})
    doc, note = build.load_speed(foreign, now=now)
    check("非 local 口径不认", doc is None and "本机口径" in note)

    stale = os.path.join(tmp, "stale.json")
    write_json(stale, {"tested_at": "2026-11-08T11:00:00Z", "scope": "local",
                       "results": [{"fp": "x", "mbps": 1.0, "error": None}]})
    doc, note = build.load_speed(stale, now=now)
    check("过期 49h -> None + 说明", doc is None and "过期" in note)

    print("")
    print("=" * 68)
    print("场景 B：pick_video_nodes 的阈值/指纹/上限")
    print("=" * 68)
    nodes = {s: [mk_node(s, i) for i in range(20)] for s in ("srcA", "srcB")}
    rows = [
        speed_row(nodes["srcA"][0], 0.59),          # 低于 1080p 门槛
        speed_row(nodes["srcA"][1], 0.60),          # 刚好达标
        speed_row(nodes["srcA"][2], 4.61),          # 4K
        speed_row(nodes["srcA"][3], 1.0, error="boom"),  # 失败不算
        {"fp": "unknown-fp", "mbps": 99.0, "error": None},  # 对不上本轮节点
    ]
    doc = {"scope": "local", "results": rows}
    picked, note = build.pick_video_nodes(doc, nodes, min_nodes=1)
    names = [p["name"] for p in picked]
    check("只收 >=0.6 且无 error 的节点", len(picked) == 2, "、".join(names))
    check("按速度降序", names == ["srcA_%s" % nodes["srcA"][2]["name"],
                                  "srcA_%s" % nodes["srcA"][1]["name"]],
          "、".join(names))
    check("指纹对不上不硬套", not any("unknown" in n for n in names))

    # 单源上限
    rows = [speed_row(n, 1.0) for n in nodes["srcA"][:20]]
    picked, note = build.pick_video_nodes({"scope": "local", "results": rows},
                                          nodes, per_src=12, cap=40)
    check("单源最多 12 个", len(picked) == 12, "%d 个" % len(picked))

    # 总量上限
    many = {s: [mk_node(s, i) for i in range(20)] for s in
            ("s1", "s2", "s3", "s4", "s5")}
    rows = [speed_row(n, 1.0) for src in many.values() for n in src]
    picked, note = build.pick_video_nodes({"scope": "local", "results": rows},
                                          many, per_src=12, cap=40)
    check("总量最多 40 个", len(picked) == 40, "%d 个" % len(picked))

    # 最少节点
    rows = [speed_row(n, 1.0) for n in nodes["srcA"][:3]]
    picked, note = build.pick_video_nodes({"scope": "local", "results": rows},
                                          nodes, min_nodes=4)
    check("不足 4 个 -> 不生成", picked == [] and "只有 3 个" in note)

    print("")
    print("=" * 68)
    print("场景 C：build_profile 注入视频 provider/组")
    print("=" * 68)
    _rank = build.rank_sources
    build.rank_sources = lambda names: (
        {n: (70.0, "AUTO", "合成测试") for n in names}, "")
    enabled = [{"name": n} for n in ("srcA", "srcB", "srcC", "srcD")]
    video = [dict(mk_node("srcA", 1), name="srcA_srcA-01")]
    try:
        prof, base, ranking = build.build_profile(
            enabled, {}, "pala911", "clash-source", video_nodes=video)
        gp = {g["name"]: g for g in prof["proxy-groups"]}
        check("有 video provider", "video" in prof["proxy-providers"])
        check("provider 指向 nodes/video.yaml",
              prof["proxy-providers"]["video"]["url"].endswith("/nodes/video.yaml"))
        check("有「视频」组且 use video",
              gp.get("视频", {}).get("use") == ["video"])
        check("「视频」是 url-test", gp.get("视频", {}).get("type") == "url-test")
        check("PROXY 引用「视频」", "视频" in gp["PROXY"]["proxies"])
        check("不要求 video 有 SRC- 组",
              not any(g["name"] == "SRC-video" for g in prof["proxy-groups"]))

        prof2, _, _ = build.build_profile(
            enabled, {}, "pala911", "clash-source", video_nodes=[])
        gp2 = {g["name"]: g for g in prof2["proxy-groups"]}
        check("没有视频节点 -> 无 provider", "video" not in prof2["proxy-providers"])
        check("没有视频节点 -> 无「视频」组", "视频" not in gp2)
        check("没有视频节点 -> PROXY 不引用", "视频" not in gp2["PROXY"]["proxies"])
    finally:
        build.rank_sources = _rank

    print("")
    print("=" * 68)
    print("场景 D：write_dist / prune 的 video.yaml 生命周期")
    print("=" * 68)
    dist = os.path.join(tmp, "dist")
    os.makedirs(os.path.join(dist, "nodes"))
    io.open(os.path.join(dist, "nodes", "a.yaml"), "w").close()
    io.open(os.path.join(dist, "nodes", "mobile.yaml"), "w").close()
    io.open(os.path.join(dist, "nodes", "video.yaml"), "w").close()
    run_mod._prune_dist_stale(dist, {"a"})
    check("本轮没生成视频 -> 旧 video.yaml 被清",
          not os.path.isfile(os.path.join(dist, "nodes", "video.yaml")))
    check("mobile.yaml 仍保留", os.path.isfile(os.path.join(dist, "nodes", "mobile.yaml")))

    io.open(os.path.join(dist, "nodes", "video.yaml"), "w").close()
    run_mod._prune_dist_stale(dist, {"a"}, extra_keep={build.VIDEO_PROVIDER})
    check("本轮生成了视频 -> video.yaml 保留",
          os.path.isfile(os.path.join(dist, "nodes", "video.yaml")))

    _rank = build.rank_sources
    build.rank_sources = lambda names: (
        {n: (70.0, "AUTO", "合成测试") for n in names}, "")
    try:
        prof3, base3, _ = build.build_profile(
            [{"name": n} for n in ("srcA", "srcB", "srcC")], {},
            "pala911", "clash-source", video_nodes=video)
    finally:
        build.rank_sources = _rank
    build.write_dist(dist, {"a": [mk_node("a", 0)]}, [mk_node("a", 0)],
                     prof3, {"owner": "pala911", "repo": "clash-source"},
                     base3, video=video)
    video_path = os.path.join(dist, "nodes", "video.yaml")
    check("write_dist 落盘 nodes/video.yaml", os.path.isfile(video_path))
    loaded = yaml.safe_load(io.open(video_path, encoding="utf-8"))
    check("视频池内容一致", loaded["proxies"] == video)

    print("")
    print("=" * 68)
    print("场景 E：iOS 精简版只在现有池内优先快节点")
    print("=" * 68)
    slow_first = [mk_node("zhuhaiuk", i) for i in range(10)]
    # 故意把快节点放在桶尾：不排序时前 2 个会选中 00/01
    fast_a, fast_b = slow_first[8], slow_first[9]
    rows = [speed_row(fast_a, 5.0), speed_row(fast_b, 4.0)]
    picked, used = build.pick_mobile_nodes(
        {"zhuhaiuk": slow_first}, cap=2, per_src=2,
        preferred=("zhuhaiuk",), speed_doc={"scope": "local", "results": rows})
    check("快节点被优先装进移动池",
          [p["name"] for p in picked] == ["zhuhaiuk_zhuhaiuk-08",
                                          "zhuhaiuk_zhuhaiuk-09"],
          "、".join(p["name"] for p in picked))
    check("移动池仍只有 2 个节点", len(picked) == 2)
    mp = build.build_mobile_profile({"zhuhaiuk": slow_first}, "pala911",
                                    "clash-source", speed_doc={"results": rows})[1]
    check("移动端没有视频 provider", "video" not in mp["proxy-providers"])
    check("移动端没有「视频」组",
          not any(g["name"] == "视频" for g in mp["proxy-groups"]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("")
print("结果：%s" % ("全部通过" if ok else "有失败项"))
sys.exit(0 if ok else 1)
