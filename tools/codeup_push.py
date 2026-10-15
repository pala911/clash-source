# -*- coding: utf-8 -*-
"""把 ci_check_paste.py 推进云效 Codeup 空仓。

之后流水线的脚本框里只需粘 `python3 ci_check_paste.py`（22 字符），
而不是 5.6KB 的 base64 单行。

鉴权（三种写法都实测过，这是唯一能通的）：
  · http.extraHeader=Authorization: Basic  -> 走代理时不生效，git 弹凭据框被取消
  · credential.helper=store --file=临时文件 -> 文件根本没被读取
                                              报 could not read Username
  · 凭据嵌进一次性 URL                        -> ✅ 可用
    代价是密码短暂出现在进程命令行。已把 credential.helper 置空，
    git 不会把它写进 .git/config 或凭据存储；并设 GIT_TERMINAL_PROMPT=0
    避免弹交互框卡死。

凭据来源：codeup.https（两行 = 登录账号 / 个人令牌）。
注意云效 Region 版页面提示「请使用登录账号 / 个人令牌进行克隆」——
用户名是**登录账号**，不是组织前缀 myxk（用 myxk 会得到
「Https克隆账号或密码错误」）。codeup_auth.py 负责自动试出可用组合。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"
RPATH = "codeup/ci-probe-test.git"
FILES = ["ci_check_paste.py", "ci_preflight.py", "ci_probe_run.py",
         "probe.py", "health.py", "mihomo-linux-amd64.gz"]

CRED_FILE = os.path.join(ROOT, "codeup.https")
if not os.path.exists(CRED_FILE):
    print("缺少 %s —— 先跑 python tools/codeup_auth.py 自动试出凭据组合" % CRED_FILE)
    sys.exit(2)
_lines = [l.strip() for l in open(CRED_FILE, encoding="utf-8").read().splitlines() if l.strip()]
if len(_lines) < 2:
    print("%s 需要两行（登录账号 / 个人令牌），实际 %d 行" % (CRED_FILE, len(_lines)))
    sys.exit(2)
USER, PASSWD = _lines[0], _lines[1]
AUTH_URL = "https://%s:%s@%s/%s" % (USER, PASSWD, HOST, RPATH)

PROXY = ["-c", "http.proxy=http://127.0.0.1:7897",
         "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % HOST]
AUTH = ["-c", "credential.helper=", "-c", "core.askPass="]
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")

README = """# ci-probe-test

云效（阿里）国内 CI 的 clash 节点探针。

## 这个仓库是什么

`pala911/clash-source` 的**第三视角探针**。产出标记 `scope=cnci`，
按设计**只记录、只交叉验证，永不触发任何源的升降级**。

真正的分工：
| 层 | 位置 | 频率 | 权限 |
|---|---|---|---|
| L1 | 美国 GitHub Actions（全量） | 每日 | 唯一有权**判死** |
| L2 | 本机 Windows 计划任务（全量） | 每周 | 唯一有权**回收** |
| L3 | 本仓库（云效杭州，抽样 30/源） | 每周 | 只交叉验证 |

## 流水线里跑哪条命令

    python3 ci_probe_run.py

结果落在 `probe_cnci.json`（**不是** probe_latest.json —— 那个由 L1/L2 独占写，
两边写同一个文件会互相覆盖，而 CI 与云效的运行时间并不互斥）。

## 目录说明

- `ci_probe_run.py`  主入口：解压 mihomo -> 装 PyYAML -> 跑探针 -> 打摘要
- `ci_check_paste.py` 平台能力判定（网络/端口/clone/回传路径）
- `ci_preflight.py`   部署前置检查（二进制来源、PyPI、内存）
- `mihomo-linux-amd64.gz`  预置内核。**不现场下载** —— 云效 runner 访问
  GitHub 时好时坏（实测两轮一通一不通），现场拉会随机失败
- `probe.py` / `health.py`  从主仓拷来，与主仓保持同源
- `nodes/*.yaml`      已过滤的节点配置

## ⚠ 环境约束

云效公共构建集群是 **Python 3.6.8**、2 核、~38GB 可用磁盘。
交付前必须跑主仓的 `python tools/check_ci_scripts.py` 按 3.6 规则静态检查
（`capture_output=` 是 3.7+、`海象运算符` 是 3.8+、引号不配平 ——
这三类错误在本机 3.11 上全都正常，只有真机才炸，且报错信息极具误导性）。

## 抽样而不是全量

国内探针跑全量要 25~30 分钟：GFW 丢 SYN 导致每个连不上的节点要挂满
`hc_timeout`（8 秒）才判定失败，美国那边则是立刻 RST。
抽样 30/源实测 **76 秒且 12 个源全部收敛**。
"""


def run(args, cwd=None, timeout=180):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=ENV)
    out = (((p.stdout or "") + (p.stderr or "")).replace(PASSWD, "***").strip())
    return p.returncode, out


def show(tag, rc, out):
    print("[%s] %s exit=%d" % (tag, "OK  " if rc == 0 else "FAIL", rc))
    if out:
        print("    " + out[:400].replace("\n", "\n    "))


def main():
    # 用带 pid 的唯一目录：固定名会在上一次失败后残留，导致 git clone 报
    # "destination path ... already exists and is not an empty directory"
    work = os.path.join(tempfile.gettempdir(), "codeup_work_%d" % os.getpid())
    shutil.rmtree(work, ignore_errors=True)

    rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", AUTH_URL], timeout=120)
    show("1 ls-remote", rc, out)
    if rc != 0:
        return 1

    # clone 下来在其上提交：目标仓已有一个初始化提交，
    # 直接 git init 再推会撞 non-fast-forward。
    rc, out = run([GIT] + PROXY + AUTH + ["clone", AUTH_URL, work], timeout=300)
    show("2 clone", rc, out)
    if rc != 0:
        return 1

    for name in FILES:
        src = (os.path.join(ROOT, ".tools", name) if name.endswith(".gz")
               else os.path.join(ROOT, "tools", name)
               if os.path.exists(os.path.join(ROOT, "tools", name))
               else os.path.join(ROOT, "src", name))
        shutil.copy2(src, os.path.join(work, name))
        print("    + %-26s %7.2f MB"
              % (name, os.path.getsize(src) / 1048576.0))

    # 节点配置（probe.py 的输入）
    import glob
    nd = os.path.join(work, "nodes")
    os.makedirs(nd, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(ROOT, "dist", "nodes", "*.yaml"))):
        if os.path.basename(f) == "all.yaml":
            continue
        shutil.copy2(f, os.path.join(nd, os.path.basename(f)))
    print("    + nodes/*.yaml           %6.2f MB"
          % (sum(os.path.getsize(os.path.join(nd, b)) for b in os.listdir(nd))
             / 1048576.0))

    # vendor 的 PyYAML（纯 Python，不现场 pip）
    ys = os.path.join(ROOT, ".tools", "yaml_vendor", "yaml")
    yd = os.path.join(work, "yaml")
    if os.path.isdir(ys):
        # clone 出来的旧副本里可能已经有 yaml/（上一版推的），copytree 会撞
        shutil.rmtree(yd, ignore_errors=True)
        shutil.copytree(ys, yd,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # 本机验证时产生的 .pyc 是 cp311 的，对云效的 3.6 纯属垃圾还误导排查
        pc = os.path.join(yd, "__pycache__")
        if os.path.isdir(pc):
            shutil.rmtree(pc, ignore_errors=True)
        print("    + yaml/*.py (vendor)    %6.2f MB  %d 个文件（已排除 __pycache__）"
              % (sum(os.path.getsize(os.path.join(yd, b)) for b in os.listdir(yd))
                 / 1048576.0, len(os.listdir(yd))))
    else:
        print("    ! vendor yaml 缺失: %s" % ys)

    with open(os.path.join(work, "README.md"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(README)

    for args in (["config", "user.name", "probe-bot"],
                 ["config", "user.email", "probe-bot@users.noreply.github.com"],
                 ["add", "-A"]):
        rc, out = run([GIT] + args, cwd=work)
        if rc != 0:
            show("3 %s" % args[0], rc, out)
            return 1

    rc, out = run([GIT, "commit", "-q", "-m", "ci: 能力判定脚本（云效探路用）"],
                  cwd=work)
    changed = "nothing to commit" not in out
    print("[3 commit] exit=%d %s" % (rc, "已提交" if changed else "无变化（已是最新）"))
    if rc != 0 and changed:
        print("    " + out[:300])
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["push", "origin", "HEAD:master"],
                  cwd=work, timeout=300)
    show("4 push", rc, out)
    if rc != 0:
        return 1

    rc, out = run([GIT] + PROXY + AUTH + ["ls-remote", "--heads", AUTH_URL])
    print("[5 远端分支] %s" % (out.replace("\n", " ") or "(无)"))
    print()
    print("✓ 推送完成。云效流水线的「脚本」步骤里跑这一行：")
    print("    python3 ci_check_paste.py")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())