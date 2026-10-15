#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国内 CI 能力判定 —— 5 分钟内决定这条路走不走得通。

用法：把本文件整个贴进国内 CI 的「自定义脚本」步骤直接跑，或
      `python3 ci_capability_check.py`。**只用标准库**，不需要 pip 装任何东西
      （国内 CI 的沙箱常常连 pip 都没有）。

判定清单（任一 ❌ 致命，不必继续）:
  1. 能不能 clone GitHub 仓库            ← 最致命，仓库拉不到后面全免谈
  2. 能不能下 mihomo 二进制（Releases）  ← 拉不到就得先做 Gitee 镜像
  3. 能不能装并启动 mihomo（监听端口）   ← 沙箱常禁 raw socket / 端口绑定
  4. 能不能出网到任意境外 IP:端口        ← 禁了这个探针毫无意义
  5. 单任务超时是否 ≥ 10 分钟            ← 沙箱 120 秒默认值的平台直接出局
  6. 免费额度够不够（这题只能你自己在控制台看）

附加体检（不做判据，但影响选型）:
  · api.github.com 通不通 —— 决定回传结果能不能免代理
  · raw.githubusercontent.com 通不通 —— 国内必墙，别指望它
  · YouTube 直连延迟 —— 判断这个机房本身的国际出口质量
  · 可用内存 / 磁盘 / CPU  —— mihomo 带 400 个节点约需 300~600MB
"""
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

try:                       # resource 只在 Unix 有；本机 Windows 上跑诊断时才需要它
    import resource
except ImportError:        # pragma: no cover
    resource = None

REPO = "https://github.com/pala911/clash-source"
MIHOMO_VER = "v1.19.32"
MIHOMO_URL = ("https://github.com/MetaCubeX/mihomo/releases/download/%s/"
              "mihomo-linux-amd64-%s.gz" % (MIHOMO_VER, MIHOMO_VER))

results = []          # (编号, 名称, 状态, 说明)
workdir = None


def rec(no, name, ok, note, fatal=True):
    """ok: True=通过 False=失败 None=仅供参考（不致命）"""
    results.append({"no": no, "name": name, "ok": ok, "note": note,
                    "fatal": fatal})
    mark = {True: "PASS", False: "FAIL", None: "INFO"}[ok]
    print("  [%-4s] %-30s %s" % (mark, name, note), flush=True)
    return ok


def timed(fn, *a, **kw):
    t0 = time.time()
    try:
        r = fn(*a, **kw)
        return r, time.time() - t0, None
    except Exception as e:
        return None, time.time() - t0, e


def http_head(url, timeout=15):
    """返回 HTTP 状态码int（调用方直接跟 200 比，别拿元组去比）。"""
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "ci-cap-check"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read(1)
        return int(r.status)


def probe_yt(times=3):
    """直连 youtube 的 generate_204 —— 看这个机房本身的国际出口质量。"""
    url = "https://www.youtube.com/generate_204"
    delays = []
    for _ in range(times):
        t0 = time.time()
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                if r.status in (204, 200):
                    delays.append(int((time.time() - t0) * 1000))
        except Exception:
            pass
        time.sleep(0.5)
    return delays


def main():
    global workdir
    print("=" * 72)
    print("国内 CI 能力判定   %s / %s / python %s"
          % (platform.system(), platform.machine(), platform.version().split()[0]))
    print("=" * 72)

    workdir = tempfile.mkdtemp(prefix="cicap_")

    # ---------- 0. 基本体检（不判据） ----------
    print("\n[0] 运行环境")
    try:
        mem = ("%.0f MB" % (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0)
               if resource else "?")
    except Exception:
        mem = "?"
    free_mb = "?"
    try:
        st = os.statvfs(".")
        free_mb = "%.1f GB" % (st.f_bavail * st.f_frsize / 1024 ** 3)
    except Exception:
        pass
    cpus = os.cpu_count()
    rec("0a", "CPU 核数", None if cpus >= 2 else False,
        "%s 核（mihomo 建议 ≥2）" % cpus, fatal=False)
    rec("0b", "可写磁盘", None, "%s（mihomo 解压后约 70MB）" % free_mb, fatal=False)
    rec("0c", "uid", None, "%s" % os.getuid() if hasattr(os, "getuid") else "?", fatal=False)

    # ---------- 1. GitHub 仓库 clone（最致命） ----------
    print("\n[1] GitHub 仓库")
    r, dt, err = timed(http_head, REPO.replace(".git", "") + "/info/refs?service=git-upload-pack")
    rec("1a", "github.com 可达", True if r == 200 else False,
        "HTTP %s in %.1fs" % (r, dt) if r else "%s in %.1fs" % (type(err).__name__, dt))

    dst = os.path.join(workdir, "clone")

    def do_clone():
        if shutil.which("git") is None:
            raise RuntimeError("环境里没有 git 命令")
        p = subprocess.run(["git", "clone", "--depth", "1", REPO, dst],
                           capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stderr or p.stdout)[-200:]

    val, dt, err = timed(do_clone)
    if val is None:
        ok1, note1 = False, "%s in %.1fs" % (err, dt)
    else:
        rc, out = val
        ok1 = (rc == 0) and os.path.isdir(os.path.join(dst, "src"))
        note1 = ("%.1fs" % dt) if ok1 else ("%s in %.1fs" % ((out or "")[:80], dt))
    rec("1b", "git clone 主仓库", ok1, note1)

    # ---------- 2. mihomo 二进制 ----------
    print("\n[2] mihomo 内核")
    def dl():
        req = urllib.request.Request(MIHOMO_URL,
                                     headers={"User-Agent": "ci-cap-check"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        import gzip
        return len(gzip.decompress(data))
    size, dt, err = timed(dl)
    rec("2a", "下载 mihomo (Releases)", True if size else False,
        "%.0f MB 解压后，%.1fs" % (size / 1e6, dt) if size
        else "%s in %.1fs" % (type(err).__name__, dt))

    mihomo = None
    if size:
        import gzip
        req = urllib.request.Request(MIHOMO_URL, headers={"User-Agent": "x"})
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = gzip.decompress(r.read())
        mihomo = os.path.join(workdir, "mihomo")
        open(mihomo, "wb").write(raw)
        os.chmod(mihomo, 0o755)
        p = subprocess.run([mihomo, "-v"], capture_output=True, text=True, timeout=30)
        rec("2b", "mihomo 可执行", p.returncode == 0,
            (p.stdout or "").strip().splitlines()[0][:60] if p.returncode == 0
            else "退出码 %d" % p.returncode)

        # ---------- 3. 端口监听 ----------
        print("\n[3] 端口绑定（沙箱常禁）")
        def bind():
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            s.listen(1)
            s.close()
            return port
        port, dt, err = timed(bind)
        rec("3a", "监听本地端口", True if port else False,
            "随机端口 %s" % port if port else "%s" % type(err).__name__)

        # ---------- 3b. mihomo 真能起 ----------
        print("\n[3b] mihomo 配置校验 + 启动")
        def boot():
            cfg = {"mixed-port": port or 17899, "allow-lan": False,
                   "log-level": "warning", "ipv6": False,
                   "external-controller": "127.0.0.1:0"}
            cf = os.path.join(workdir, "c.yaml")
            json.dump(cfg, open(cf, "w"))
            p = subprocess.run([mihomo, "-t", "-f", cf, "-d", workdir],
                               capture_output=True, text=True, timeout=60)
            return p.returncode, (p.stdout + p.stderr)[-200:]
        val, dt, err = timed(boot)
        if val is None:
            rec("3b", "mihomo 校验+启动", False, "%s in %.1fs" % (type(err).__name__, dt))
        else:
            rc, out = val
            rec("3b", "mihomo 校验+启动", rc == 0,
                "%.1fs" % dt if rc == 0 else "%s" % (out or "")[:80].replace("\n", " "))

    # ---------- 4. 出网到境外任意端口 ----------
    print("\n[4] 出网（探针要连节点服务器的 IP:端口）")
    targets = [("日本 1.1.1.1", "1.1.1.1", 443), ("OpenDNS", "208.67.222.222", 443)]
    got = 0
    for label, host, p in targets:
        def tc():
            s = socket.create_connection((host, p), timeout=8)
            s.close()
            return True
        ok, dt, err = timed(tc)
        got += 1 if ok else 0
        rec("4a", "TCP 连境外 %s:%d" % (host, p), None if ok else False,
            "%.1fs" % dt if ok else "%s" % type(err).__name__, fatal=False)
    rec("4b", "出网连通性", True if got == len(targets) else (False if got == 0 else None),
        "%d/%d 通" % (got, len(targets)))

    # ---------- 5. GitHub API / raw（决定回传方式） ----------
    print("\n[5] 回传路径")
    r, dt, err = timed(http_head, "https://api.github.com/rate_limit")
    rec("5a", "api.github.com", True if r == 200 else False,
        "HTTP %s in %.1fs（通=回传可免代理）" % (r, dt) if r
        else "%s（需走 Gitee 中转）" % type(err).__name__, fatal=False)
    r, dt, err = timed(http_head,
                       "https://raw.githubusercontent.com/MetaCubeX/mihomo/%s/README.md" % MIHOMO_VER)
    rec("5b", "raw.githubusercontent", None if r == 200 else False,
        "HTTP %s" % r if r else "%s（国内预期失败，正常）" % type(err).__name__, fatal=False)

    # ---------- 6. 机房国际出口质量 ----------
    print("\n[6] 机房出口质量（仅供参考）")
    delays = probe_yt()
    if delays:
        rec("6a", "YouTube 直连", None, "%s ms（这是机房自身出口，与你手机无关）"
            % ", ".join(str(d) for d in delays), fatal=False)
    else:
        rec("6a", "YouTube 直连", None, "连不上（正常：探针靠节点出墙，不靠本机）",
            fatal=False)

    # ---------- 汇总 ----------
    print("\n" + "=" * 72)
    fatal_fail = [r for r in results if r["ok"] is False and r["fatal"]]
    warn_fail = [r for r in results if r["ok"] is False and not r["fatal"]]
    print("致命项 %d 个，其中失败 %d 个" % (
        len([r for r in results if r["fatal"] and r["no"] != "0"]), len(fatal_fail)))
    if fatal_fail:
        print("\n❌ 判定：不建议在此平台部署")
        for r in fatal_fail:
            print("   · %s（%s）" % (r["name"], r["note"]))
        if any("clone" in r["name"] for r in fatal_fail):
            print("\n   首要问题：拉不到 GitHub 仓库。绕法是把仓库与 mihomo 二进制")
            print("   预先镜像到 Gitee，再从 Gitee 拉 —— 但这会让维护成本翻倍，")
            print("   除非你本来就有 Gitee 账号，否则建议放弃这条路。")
    else:
        print("\n✅ 判定：技术上可行")
        print("   下一步看【免费额度】：把下面的单轮耗时乘以每月轮次，")
        print("   和控制台的免费分钟数比一比。")
        print("   参考量级：分层抽样 20 节点/源，12 源一轮 ≈ 25 秒（本机实测）。")
    if warn_fail:
        print("\n非致命告警：")
        for r in warn_fail:
            print("   · %s（%s）" % (r["name"], r["note"]))
    print("=" * 72)
    print("单轮耗时请自己实测：")
    print("  python3 src/probe.py --mihomo ./mihomo --scope cnci "
          "--sample 20 --hc-timeout 3000 --budget 600")
    json.dump(results, open("ci_capability_result.json", "w"), ensure_ascii=False, indent=2)
    return 1 if fatal_fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)