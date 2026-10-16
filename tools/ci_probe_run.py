#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云效 Codeup 国内 CI 侧的真探针执行器（scope=cnci）。

定位（重要，别误用）：这一层的产出标记为 **cnci**，按 src/health.py 的设计
**只记录、只交叉验证，永不触发任何自动升降级**。真正干活的分工是：

    L1  美国 GitHub Actions（每 6 小时，全量） -> 唯一有权**判死**
    L2  本机 Windows 计划任务（每天 12:30，全量） -> 唯一有权**回收**
    L3  本文件（云效杭州，每天 04:00，分层抽样）-> 只提供第三方国内视角

为什么不参与判定：
  云 IDC 的国际出口与家用宽带不同（通常更差），实测出网可达性与本机一致，
  但**丢包率/延迟分布不一样**。而国内口径的 alive=0 本身又是歧义的
  （节点真死 OR 它的 IP 被墙、我们连不上）。让它参与自动决策风险大于收益。

输出到 **probe_cnci.json**（不是 probe_latest.json）：
  probe_latest.json 由 L1/L2 独占写 —— 两边都写同一个文件会互相覆盖，
  而 CI 与云效的运行时间点并不互斥。

⚠ Python 3.6（云效集群实测 3.6.8）：不用 capture_output / f-string / 海象运算符。
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MIHOMO_GZ = os.path.join(HERE, "mihomo-linux-amd64.gz")
MIHOMO = os.path.join(HERE, ".mihomo")
OUT = os.path.join(HERE, "probe_cnci.json")
# 分层抽样：国内探针跑全量要 25~30 分钟（GFW 丢 SYN 导致每个死节点挂满
# hc_timeout），跑不起也不必要。抽样 30/源实测 76 秒且全部 settle。
SAMPLE = int(os.environ.get("CNCI_SAMPLE", "30"))
BUDGET = int(os.environ.get("CNCI_BUDGET", "900"))


def run(cmd, timeout=900, cwd=None):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=timeout)
    return p.returncode, (p.stdout or ""), time.time() - t0


def die(msg, rc=1):
    print("[cnci] 失败: %s" % msg)
    return rc


def main():
    print("[cnci] 环境 python %s / %d 核"
          % (sys.version.split()[0], os.cpu_count() or 0))

    # --- 1. mihomo 二进制：随仓库带过来，不依赖 GitHub ---
    if not os.path.exists(MIHOMO):
        if not os.path.exists(MIHOMO_GZ):
            return die("找不到 %s（仓库里应已包含）" % os.path.basename(MIHOMO_GZ))
        print("[cnci] 解压 mihomo...")
        import gzip
        raw = gzip.decompress(open(MIHOMO_GZ, "rb").read())
        with open(MIHOMO, "wb") as f:
            f.write(raw)
        os.chmod(MIHOMO, 0o755)
    rc, out, dt = run([MIHOMO, "-v"], timeout=60)
    if rc != 0:
        return die("mihomo 不可执行: %s" % out[:200])
    print("[cnci] mihomo: %s" % out.strip().splitlines()[0])

    # --- 2. PyYAML：用**仓库里 vendor 的那份**，不现场 pip install ---
    # 现场 pip 是这条链路上唯一还会失败的环（镜像可达性/TLS/pip 版本/
    # --user 不在 sys.path…）。云效集群实测已经栽过一次，而且我当时
    # 把 pip 的真实报错截断成 tail，根本看不出原因。vendor 之后整类失败消失。
    #
    # ⚠ 这里必须把 vendor 目录放到 sys.path **最前面**并让 probe.py 所在目录
    #   也在里面，否则 import yaml 可能命中系统里另一个版本。
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import yaml
        print("[cnci] PyYAML %s（vendor，纯 Python: %s）来自 %s"
              % (yaml.__version__, not yaml.__with_libyaml__,
                 os.path.relpath(yaml.__file__, HERE)))
    except Exception as e:
        # 兜底：万一 vendor 没随仓库进来，才尝试 pip（并打印**完整**报错，
        # 不要再只留 tail —— 上次就是这样把自己坑了）
        print("[cnci] vendor yaml 不可用(%s)，退回 pip..." % e)
        rc, out, dt = run([sys.executable, "-m", "pip", "install", "--user",
                           "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                           "PyYAML"], timeout=420)
        print("[cnci] pip exit=%d %.1fs，完整输出：" % (rc, dt))
        print(out)
        if rc != 0:
            return die("PyYAML 装不上")
        sys.path.insert(0, HERE)

    # --- 3. 跑探针 ---
    if not os.path.isdir(os.path.join(HERE, "nodes")):
        return die("找不到 nodes/ 目录")
    t0 = time.time()
    rc, out, dt = run(
        [sys.executable, os.path.join(HERE, "probe.py"),
         "--mihomo", MIHOMO,
         "--nodes", os.path.join(HERE, "nodes"),
         "--scope", "cnci",
         "--sample", str(SAMPLE),
         "--out", OUT,
         "--budget", str(BUDGET)],
        timeout=BUDGET + 240)
    for ln in out.splitlines():
        print("[cnci] " + ln)

    if not os.path.exists(OUT):
        return die("探针没产出 %s" % os.path.basename(OUT))

    # --- 4. 摘要（给控制台一眼看，不看也得能从文件拿全量）---
    try:
        d = json.load(open(OUT, encoding="utf-8"))
    except Exception as e:
        return die("结果解析失败: %s" % e)
    rows = d.get("sources") or {}
    settled = sum(1 for v in rows.values() if v.get("settled"))
    uns = sum(1 for v in rows.values() if not v.get("settled"))
    print()
    print("=" * 64)
    print("scope=%s  抽样=%d/源  hc_timeout=%sms  用时=%ds"
          % (d.get("scope"), SAMPLE, d.get("hc_timeout_ms"), int(time.time() - t0)))
    print("源: %d 个（已收敛 %d，未测完 %d）" % (len(rows), settled, uns))
    print("%-18s %7s %7s %9s" % ("源", "样本", "活", "通过率"))
    for k in sorted(rows):
        v = rows[k]
        print("%-18s %7d %7d %8.1f%%%s"
              % (k, v.get("tested", 0), v.get("alive", 0), v.get("rate", 0),
                 "" if v.get("settled") else "  (未测完)"))
    print("=" * 64)
    print("注意：本层数据仅供交叉验证，不会触发任何源升降级。")
    print("完整结果: %s" % os.path.basename(OUT))

    # --- 5. 把结果推回 Codeup ---
    # 为什么必须推回：探针结果只写在临时 workspace 里，跑完就被回收，
    #   想看历史就只能靠翻日志 —— 而云效的日志面板有渲染不出来的时候
    #   （已经栽过一次：执行命令跑了 67 秒但面板只有请求环境的输出）。
    #   推回仓库后，历史数据就在 git 里，随时可 clone，不依赖任何 UI。
    push_result()
    return 0


def push_result():
    """把 probe_cnci.json 提交回 Codeup。失败也不影响主流程。"""
    import subprocess as sp
    if not os.path.exists(OUT):
        return
    # 时间戳文件名，避免每次提交都产生 diff 噪音；latest.json 保留最新一份
    stamp = time.strftime("%Y%m%d-%H%M")
    try:
        os.makedirs("results", exist_ok=True)
        shutil.copy2(OUT, os.path.join("results", "probe_cnci_%s.json" % stamp))
        shutil.copy2(OUT, os.path.join("results", "latest.json"))
    except Exception as e:
        print("[cnci] 归档结果失败: %s" % e)
        return

    def g(*a):
        return sp.run(["git"] + list(a), stdout=sp.PIPE, stderr=sp.STDOUT,
                      universal_newlines=True, timeout=300)

    g("config", "user.name", "cnci-probe")
    g("config", "user.email", "cnci-probe@users.noreply.github.com")
    g("add", "-A", "results")
    c = g("commit", "-m", "cnci 探针 %s" % stamp)
    if "nothing to commit" in (c.stdout or ""):
        print("[cnci] 结果无变化，跳过提交")
        return
    if c.returncode != 0:
        print("[cnci] 提交失败: %s" % (c.stdout or "")[:200])
        return
    p = g("push", "origin", "HEAD:master")
    if p.returncode != 0:
        # 并发保护：定时跑和手动跑可能撞车，两者都往 master 推会 non-fast-forward。
        # 先 rebase 再推一次；还失败就如实报出来（不硬推，绝不 --force）。
        g("pull", "--rebase", "--autostash", "origin", "master")
        p = g("push", "origin", "HEAD:master")
    if p.returncode == 0:
        print("[cnci] 结果已推回 Codeup: results/probe_cnci_%s.json" % stamp)
    else:
        # 常见于流水线 clone 时没留凭据；这时日志才是唯一出口，所以要说清楚。
        # 绝不 --force —— master 上还有别人推的东西。
        print("[cnci] ⚠ 推送失败（流水线可能没配 git 凭据），"
              "结果只在本次 workspace 里：%s" % (p.stdout or "")[:160])


if __name__ == "__main__":
    sys.exit(main())