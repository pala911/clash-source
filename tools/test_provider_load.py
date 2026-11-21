# -*- coding: utf-8 -*-
"""验证「一个畸形节点不会让整源加载失败」—— 真内核级别的守卫。

## 为什么必须由它来守

2026-10-16 发现：`dist/nodes/autojiedian.yaml` 里第 454 个节点是
`type: hysteria2, sni: false`（布尔塞进 string 字段），mihomo 直接报

    initial proxy provider autojiedian error: proxy 454 error:
    'sni' expected type 'string', got unconvertible type 'bool'

**892 个节点一个都没加载进来**，而当时 7 道门禁全绿：

  * `test_fault_injection.py` 管的是「坏数据进来时明不明确报错」——这个是**合法 YAML**，
    字段名也在白名单里，逐项检查都过；
  * `verify_profile.py` / `test_stability.py` 的 `mihomo -t` 也过 ——
    **`-t` 不加载 provider**，provider 的解析错误只在实例启动时才出现；
  * `probe_field_types.py` 验的是「逐类型规则对不对」，验的不是「产出物能不能加载」。

所以这个洞是「**单元规则对 + 结构对 + 内核 -t 过，但真跑起来整源消失**」。
和坑 §33 是同一类：**provider 级失败是全有全无的，而且不报错、只少一个源。**

## 三个场景

  A 基线复现：原样的文件 -> 内核必须拒绝（0 个加载）。
    ⚠ 这条不能省。如果基线不复现，说明测试自己坏了（比如构造的节点本来就不合法），
      后面的「修复后能加载」就毫无意义。
  B 修复后：同一批节点过 filters.hard_filter -> 全部加载，0 个 error。
  C 不误伤：`password: null` / `sni: 123` 这类**内核实测接受**的写法必须保留 ——
    防的是有人把规则简化成「不是字符串就丢」，那会白丢 226 个正常节点。
"""
import io
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 用与真实探针不同的端口，避免和正在跑的本机探针抢
os.environ.setdefault("PROBE_API_PORT", "19098")
os.environ.setdefault("PROBE_MIXED_PORT", "17898")

sys.path.insert(0, os.path.join(ROOT, "src"))

import yaml                                    # noqa: E402
import filters                                 # noqa: E402
import probe                                   # noqa: E402

MIHOMO = os.environ.get("MIHOMO_BIN", r"C:\Program Files\Clash Verge\verge-mihomo.exe")
WORK = os.path.join(ROOT, ".tools", "_provider_load_test")
NAME = "src"

FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label, ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def well_formed(n):
    """一批内核必然接受的节点（ss，字段齐全）。"""
    return [{"name": "ok-%03d" % i, "type": "ss", "cipher": "aes-128-gcm",
             "password": "p%d" % i, "server": "10.0.0.%d" % (i + 1),
             "port": 1000 + i} for i in range(n)]


BAD_HY2 = {"name": "bad-sni-bool", "type": "hysteria2", "server": "10.1.0.1",
           "port": 443, "password": "pw", "skip-cert-verify": True, "sni": False}


def load_in_mihomo(nodes, tag):
    """返回 (加载到的节点数, error 行列表)。

    只看「加载」，不看「通不通」：provider 的内容与健康检查结果无关，
    所以这里不需要网络，几秒就能出结论。
    """
    wd = os.path.join(WORK, tag)
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(os.path.join(wd, "nodes"))
    src = os.path.join(wd, "nodes", NAME + ".yaml")
    with io.open(src, "w", encoding="utf-8") as f:
        probe.yaml_dump({"proxies": nodes}, f)
    cpath, _ = probe.build_config([(NAME, src)], wd, health_check_timeout=3000)

    logf = io.open(os.path.join(wd, "mihomo.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([MIHOMO, "-d", wd, "-f", cpath],
                            stdout=logf, stderr=subprocess.STDOUT)
    got = 0
    t0 = time.time()
    try:
        while time.time() - t0 < 20:
            time.sleep(2)
            try:
                data = probe.api_get(probe.API_PORT, "/providers/proxies")
            except Exception:
                continue
            pr = (data.get("providers") or {}).get(NAME) or {}
            n = len([x for x in (pr.get("proxies") or [])
                     if x.get("name") != "COMPATIBLE"])
            if n:
                got = n
                break
    finally:
        proc.kill()
        logf.close()
        time.sleep(1)
    with io.open(os.path.join(wd, "mihomo.log"), encoding="utf-8") as f:
        errs = [ln for ln in f.read().splitlines() if "level=error" in ln]
    return got, errs


def cleaned(nodes):
    """复刻 run.py 里「逐节点过 hard_filter」这一步。"""
    out = []
    for p in nodes:
        p = dict(p)
        ok, _ = filters.hard_filter(p, [], ())
        if ok:
            out.append(p)
    return out


def main():
    if not os.path.exists(MIHOMO):
        print("  找不到 mihomo（%s），跳过" % MIHOMO)
        return 0
    shutil.rmtree(WORK, ignore_errors=True)
    nodes = well_formed(6) + [dict(BAD_HY2)]
    total = len(nodes)
    print("构造 %d 个节点，其中 1 个是 hysteria2 + sni:false" % total)
    print("")

    print("场景 A：基线复现（文件原样喂给内核，必须拒绝）")
    got, errs = load_in_mihomo(nodes, "before")
    check(got == 0, "内核加载 0 个节点（整源被拒）", "实际 %d" % got)
    check(any("sni" in e for e in errs), "error 里点名 sni 字段",
          errs[0][-90:] if errs else "一条 error 都没有")
    print("")

    print("场景 B：过 filters.hard_filter 之后")
    fixed = cleaned(nodes)
    check(len(fixed) == total, "一个节点都没被硬过滤丢掉",
          "%d/%d" % (len(fixed), total))
    got2, errs2 = load_in_mihomo(fixed, "after")
    check(got2 == total, "内核加载 %d 个节点" % total, "实际 %d" % got2)
    check(not errs2, "0 条 error", errs2[0][-90:] if errs2 else "")
    print("")

    print("场景 C：内核实测接受的写法必须原样保留（不误伤）")
    # ⚠ password:null 要用 socks5 举例：ss 的 password 是**必填字段**，
    #   缺了会被 REQUIRED_FIELDS 挡掉 —— 那是另一条规则（而且是对的）。
    #   实测会被丢的是「协议不要求凭据、但上游写了 password: null」那 226 个节点。
    keep = [{"name": "null-pw", "type": "socks5", "server": "10.2.0.1",
             "port": 1080, "password": None},
            {"name": "int-sni", "type": "hysteria2", "server": "10.2.0.2",
             "port": 443, "password": "pw", "sni": 12345}]
    got0, errs0 = load_in_mihomo(keep, "keep-raw")
    check(got0 == 2 and not errs0, "内核本来就接受这两种写法（基线）",
          "加载 %d，error %d 条" % (got0, len(errs0)))
    kept = cleaned(keep)
    check(len(kept) == 2, "过 filters 后两个节点都保留", "%d/2" % len(kept))
    if len(kept) == 2:
        check("password" in kept[0], "password=null 没有被当成畸形丢掉")
        check(kept[1].get("sni") == 12345, "sni=数字 保留（内核会强转）")
    got3, errs3 = load_in_mihomo(kept, "keep")
    check(got3 == 2 and not errs3, "过滤产物的内核行为没变",
          "加载 %d，error %d 条" % (got3, len(errs3)))
    print("")

    shutil.rmtree(WORK, ignore_errors=True)
    print("=" * 66)
    if FAILS:
        print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
        return 1
    print("结果：全部通过（基线能复现，修复后整源可加载，边界写法零误伤）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
