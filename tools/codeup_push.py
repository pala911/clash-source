# -*- coding: utf-8 -*-
"""把云端探针内容推到阿里云效 Codeup。

与 gitee_push.py **共用同一份内容清单**（tools/probe_payload.py）——
⚠ 绝不能各自维护一份文件列表：两份清单迟早漂移（推了 A 没推 B），
而漂移极难发现，因为两边都能正常跑，只是内容不同。
2026-10-15 就因为"3.6 门禁漏扫 probe.py"栽过一次同类的坑。

鉴权（Cloudup Region 版 cn-shenzhen）：
  页面提示「请使用**登录账号** / 个人令牌进行克隆」——
  用户名是登录账号（aliyun.token 里那个），**不是组织前缀 myxk**，
  用 myxk 会得到「Https克隆账号或密码错误」。
  另外登录密码含 '@'，嵌进 URL 会被 git 判「URL rejected: Bad hostname」，
  所以必须用令牌。codeup_auth.py 会自动试出可用组合并写入 codeup.https。

git 鉴权只有一种写法能通（三种都实测过）：
  · http.extraHeader=Authorization: Basic  -> 走代理时不生效，弹凭据框
  · credential.helper=store --file=临时文件 -> 文件根本没被读取
  · 凭据嵌一次性 URL + credential.helper 置空 + GIT_TERMINAL_PROMPT=0  -> ✅
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import probe_payload  # noqa: E402

GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"
RPATH = "codeup/ci-probe-test.git"
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")

README = """# ci-probe-test

clash-source 节点源探针的云端执行仓库（阿里云效 Codeup 镜像）。

Gitee 与 Codeup **共用同一份内容**（主仓 `tools/probe_payload.py` 是唯一来源，
避免两处清单漂移）。

## 流水线里跑

```bash
bash tools/sync_and_probe.sh
```

`git reset --hard` 不是可选的：云效会复用带缓存的 workspace
（实测 build id 一直停在首次运行），增量同步会漏文件
（`ci_probe_run.py` 更新了而 `probe.py` 没更新），不加就会跑到旧代码上。

结果会 commit 回仓库：`results/probe_cnci_<时间戳>.json` + `results/latest.json`。
取数靠 clone，不靠日志面板（云效的面板实测渲染不出来）。

## 定位

本层数据标记 `scope=cnci`，**只做交叉验证，永不触发任何源的升降级**。
有权判死的是美国 GitHub Actions，有权回收的是本机探针。

实测（12 源，云效抽样30 vs 本机全量）：Spearman rho=0.734，
但云效系统性偏高 +11.9pp（阿里云杭州国际出口优于家用宽带）；
反例 snakem982 云效 0/30 而本机 15.4% —— 该源节点封机房 IP，
**「云效 0 活」绝不能据此淘汰源**。

## 环境约束 ⚠

云效公共构建集群实测 **Python 3.6.8**、2 核、38GB 可用磁盘。
`capture_output=` / `text=` 是 3.7+、海象运算符是 3.8+ ——
本机 3.x 上全都正常，只有真机才炸，且报错极具误导性。
改动任何会在云端执行的 .py 后，务必在主仓跑：

```bash
python tools/check_ci_scripts.py
```
"""


def main():
    cred = os.path.join(ROOT, "codeup.https")
    if not os.path.exists(cred):
        print("缺少 %s —— 先跑 python tools/codeup_auth.py 自动试出凭据组合" % cred)
        return 2
    lines = [l.strip() for l in open(cred, encoding="utf-8").read().splitlines()
             if l.strip()]
    if len(lines) < 2:
        print("%s 需要两行（登录账号 / 个人令牌）" % cred)
        return 2
    user, pw = lines[0], lines[1]
    # 嵌进 user:pass@ 后面必须去 scheme，否则会拼出 https://u:p@https://...
    auth_url = "https://%s:%s@%s/%s" % (user, pw, HOST, RPATH)

    # 用唯一目录名：之前有失败残留 + 文件锁导致 rmtree 静默失败，
    # 紧接着 makedirs 就 FileExistsError。
    base = tempfile.gettempdir()
    tag = "%d_%d" % (os.getpid(), len(os.listdir(base)))
    stage = os.path.join(base, "codeup_stage_" + tag)   # 暂存：先组装内容
    work = os.path.join(base, "codeup_work_" + tag)     # 目标：clone 下来再覆盖
    for d in (stage, work):
        shutil.rmtree(d, ignore_errors=True)

    # 内容组装交给共享清单 probe_payload —— 与 gitee_push.py 同源。
    # ⚠ 绝不能在这里另写一份文件列表：两份清单迟早漂移（推了 A 没推 B），
    #   而漂移极难发现，因为两边都能正常跑，只是内容不同。
    for rel, kind, size in probe_payload.build(stage, README):
        print("    + %-30s %-12s %8.2f MB" % (rel, kind, size / 1048576.0))

    # 代理优先、断时直连：codeup/gitee 是国内站，直连本来就没有墙的问题；
    # 2026-10-30 实踩 Clash 进程消失（7897 无监听），写死 proxy 会把整条
    # 刷远端链锁死 —— 所以探测一把端口，活着走代理、死了直连。
    alive = False
    try:
        import socket
        with socket.create_connection(("127.0.0.1", 7897), timeout=2):
            alive = True
    except Exception:
        pass
    PROXY = (["-c", "http.proxy=http://127.0.0.1:7897",
              "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % HOST]
             if alive else [])
    if not alive:
        print("[proxy] 7897 无监听 -> codeup 直连（国内站不需要代理）")
    AUTH = ["-c", "credential.helper=", "-c", "core.askPass="]

    def run(args, cwd=None, timeout=300):
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=ENV)
        out = (((p.stdout or "") + (p.stderr or "")).replace(pw, "***").strip())
        return p.returncode, out

    def show(tag, rc, out):
        print("[%s] %s exit=%d" % (tag, "OK  " if rc == 0 else "FAIL", rc))
        if out:
            print("    " + out[:400].replace("\n", "\n    "))

    rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", auth_url], timeout=120)
    show("1 ls-remote", rc, out)
    if rc != 0:
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["clone", auth_url, work], timeout=300)
    show("2 clone", rc, out)
    if rc != 0:
        return 1

    # clone 下来的旧副本必须先清掉再覆盖，否则 copytree/dir 会撞
    # FileExistsError（yaml/ 与 nodes/ 在旧仓里已存在）
    for name in os.listdir(stage):
        s = os.path.join(stage, name)
        d = os.path.join(work, name)
        if os.path.isdir(s):
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(s, d)

    for a in (["config", "user.name", "probe-bot"],
              ["config", "user.email", "probe-bot@users.noreply.github.com"],
              ["add", "-A"]):
        rc, out = run([GIT] + AUTH + a, cwd=work)
        if rc != 0:
            show("3 %s" % a[0], rc, out)
            return 1

    rc, out = run([GIT] + AUTH + ["commit", "-q", "-m", "ci: 云端探针内容更新"],
                  cwd=work)
    changed = "nothing to commit" not in out
    print("[3 commit] exit=%d %s" % (rc, "已提交" if changed else "无变化"))
    if rc != 0 and changed:
        print("    " + out[:300])
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["push", "origin", "HEAD:master"],
                  cwd=work, timeout=300)
    show("4 push", rc, out)
    if rc != 0:
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", "--heads", auth_url])
    print("[5 远端分支] %s" % (out.replace("\n", " ") or "(无)"))
    print("\n✓ Codeup 推送完成。云效流水线脚本步骤里跑：")
    print("    bash tools/sync_and_probe.sh")
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(stage, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
