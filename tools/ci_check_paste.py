#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国内 CI 能力判定（粘贴版）—— 5 分钟决定这条路走不走得通。

⚠ 必须兼容 **Python 3.6**（云效公共构建集群实测是 3.6.8）：
   - subprocess.run(capture_output=...) 是 3.7+ 才有的，用 3.6 会直接 TypeError。
     第一次实测就被这条坑了：clone 测试报
     「__init__() got an unexpected keyword argument 'capture_output'」，
     看起来像平台能力不足，其实是脚本自己的 bug —— **别把这种假阴性当平台结论。**
   - 同理不能用 f-string（3.6 支持但保持风格一致），这里统一用 % 格式化。

用法：整段粘进 CI 的脚本任务，或仓库里直接 python3 ci_check_paste.py

出网测试目标用的是**我们节点实际在用的境外服务器**（按出现频次取样，
并跨网段去重），不是 1.1.1.1 / OpenDNS —— 那类公共 DNS 在国内常被
特殊处理（污染/丢弃），拿它测出来的结果不能代表「这个 runner 能不能
连到节点真正所在的服务器」。
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

# 真实节点服务器（境外，跨网段去重；2026-10-15 从 dist/nodes 按频次抽样）
TARGETS = [
    "193.176.84.32:9002",
    "84.239.49.201:9002",
    "84.17.47.125:9002",
    "37.120.233.18:443",
    "149.22.85.65:443",
    "149.22.86.14:443",
    "purposebydesig.club:443",
]

R = []


def chk(name, ok, note, fatal=True):
    R.append((name, ok, note, fatal))
    print("[%-4s] %-28s %s"
          % ({True: "PASS", False: "FAIL", None: "INFO"}[ok], name, note),
          flush=True)


def go(fn):
    """跑 fn，返回 (值, 耗时, 异常)。不抛异常 —— 判定表必须完整打印出来。"""
    t0 = time.time()
    try:
        return fn(), time.time() - t0, None
    except Exception as e:
        return None, time.time() - t0, e


def tcp(host, port, timeout=6):
    s = socket.create_connection((host, port), timeout=timeout)
    s.close()
    return True


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "ci-cap-check"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def main():
    d = tempfile.mkdtemp()
    du = shutil.disk_usage(d)
    print("环境: %d 核 / 可用 %.1f GB / python %s"
          % (os.cpu_count() or 0, du.free / 1024.0 ** 3,
             sys.version.split()[0]))
    print()

    # ---- 1) 出网到**真实节点服务器**（探针的实际需求）----
    print("--- 出网到真实节点服务器（探针要连的就是这些）---")
    ok_cnt = 0
    for hp in TARGETS:
        host, _, port = hp.rpartition(":")
        val, dt, err = go(lambda h=host, p=int(port): tcp(h, p))
        good = val is True
        if good:
            ok_cnt += 1
        chk("连 %s" % hp, None if good else False,
            "%.2fs" % dt if good else (err.__class__.__name__), fatal=False)
    chk("出网综合", True if ok_cnt >= len(TARGETS) // 2 else False,
        "%d/%d 通（探针至少要能连上一半节点才谈得上）" % (ok_cnt, len(TARGETS)))

    # ---- 2) DNS 解析 ----
    val, dt, err = go(lambda: socket.gethostbyname("github.com"))
    chk("DNS 解析 github.com", None if val else False,
        val or err.__class__.__name__)

    # ---- 3) 监听本地端口（mihomo 必需）----
    def bind():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.listen(1)
        s.close()
        return p
    val, dt, err = go(bind)
    chk("监听本地端口", bool(val), "端口 %s" % val if val else str(err))

    # ---- 4) 子进程 + git ----
    # 注：git 不是致命项 —— 仓库已经放在 Codeup 里了，正常流程是从 Codeup 拉，
    # 不必 clone GitHub。这里只是顺带告诉你「能不能直接从 GitHub 同步」。
    if shutil.which("git") is None:
        chk("git 命令", None, "环境里没有 git（无妨：从 Codeup 拉代码不需要它）")
    else:
        def clone():
            p = subprocess.run(
                ["git", "clone", "--depth", "1",
                 "https://github.com/pala911/clash-source", os.path.join(d, "c")],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, timeout=180)
            return p.returncode, (p.stderr or p.stdout or "")[-200:]
        val, dt, err = go(clone)
        if val is None:
            chk("clone GitHub 仓库", None, "%s（%.0fs）——无妨，代码从 Codeup 拉" % (err, dt))
        else:
            rc, out = val
            good = (rc == 0) and os.path.isdir(os.path.join(d, "c", "src"))
            chk("clone GitHub 仓库", None if good else False,
                "%.0fs ✓ 可直连 GitHub" % dt if good
                else out.replace("\n", " ")[:100] + " —— 无妨，代码从 Codeup 拉")

    # ---- 5) 回传路径 ----
    val, dt, err = go(lambda: http_get("https://api.github.com/rate_limit"))
    chk("api.github.com（回传免代理）", None if val else False,
        "HTTP %s" % val if val else str(err)[:60], fatal=False)
    val, dt, err = go(lambda: http_get(
        "https://raw.githubusercontent.com/pala911/clash-source/main/README.md"))
    chk("raw.githubusercontent", None if val else False,
        "HTTP %s" % val if val else "不通（国内预期如此，正常）", fatal=False)

    # ---- 汇总 ----
    print("=" * 64)
    bad = [r for r in R if r[1] is False and r[3]]
    warn = [r for r in R if r[1] is False and not r[3]]
    if bad:
        print("结论：不建议在此平台部署（致命项失败 %d 个）" % len(bad))
        for n, _, note, _f in bad:
            print("   x %s —— %s" % (n, note))
        if any("clone" in n for n, _, _, _ in bad):
            print("\n   出路：把仓库镜像到 Codeup/Gitee。但 mihomo 二进制"
                  "（GitHub Release）同样拉不到，维护成本翻倍。")
    else:
        print("结论：技术上可行。")
        print("提醒：即使出网没问题，云 IDC 的国际出口质量与家用宽带不同，")
        print("      测出来的数据只能用于**交叉验证**，不能替代本机口径。")
    if warn:
        print("\n非致命告警：")
        for n, _, note, _f in warn:
            print("   ! %s —— %s" % (n, note))
    print("=" * 64)
    shutil.rmtree(d, ignore_errors=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())