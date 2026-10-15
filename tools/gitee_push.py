# -*- coding: utf-8 -*-
"""把云端探针内容推到 Gitee（与 Codeup 用同一份内容清单 probe_payload）。

鉴权：Gitee 的 HTTPS 克隆用「用户名 + 私人令牌」。
  用户名从仓库地址推导（https://gitee.com/<user>/<repo>），
  令牌读 gitee.token。

同样只用「凭据嵌一次性 URL + credential.helper 置空 + GIT_TERMINAL_PROMPT=0」
—— Codeup 那轮实测：http.extraHeader 走代理不生效、credential store 不被读取，
只有这个写法能通。
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
REPO_URL = os.environ.get("GITEE_URL", "https://gitee.com/andywx/ci-probe-test")
TOK_FILE = os.path.join(ROOT, "gitee.token")
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")

README = """# ci-probe-test

clash-source 节点源探针的云端执行仓库。

Gitee Go 与阿里云效（Codeup）**共用同一份内容**（见主仓
`tools/probe_payload.py`——唯一来源，避免两处清单漂移）。

## 流水线里跑

```bash
bash tools/sync_and_probe.sh
```

`git reset --hard` 不是可选的：云端构建会复用带缓存的 workspace，
增量同步会漏文件（实测 `ci_probe_run.py` 更新了而 `probe.py` 没更新），
不加就会跑到旧代码上。

结果会 commit 回仓库：`results/probe_cnci_<时间戳>.json` + `results/latest.json`。
取数靠 clone，不靠日志面板（云效的面板实测渲染不出来）。

## 定位

本层数据标记 `scope=cnci`，**只做交叉验证，永不触发任何源的升降级**。
真正有权判死的是美国 GitHub Actions，有权回收的是本机探针。

## 环境约束 ⚠

云端构建镜像的 Python 版本各不相同（云效实测 3.6.8）。
`capture_output=` / `text=` 是 3.7+、海象运算符是 3.8+ ——
本机 3.x 上全都正常，只有真机才炸，且报错极具误导性。
改动任何会在云端执行的 .py 后，务必在主仓跑：

```bash
python tools/check_ci_scripts.py
```
"""


def main():
    if not os.path.exists(TOK_FILE):
        print("缺少 %s（Gitee 设置 → 私人令牌，勾 projects 权限）" % TOK_FILE)
        return 2
    tok = open(TOK_FILE, encoding="utf-8").read().strip()
    # 从 https://gitee.com/<user>/<repo> 里解析用户名与仓库名。
    # ⚠ 别把 gitee.com 当成用户名（我第一版就是这么错的，URL 拼成了
    #   https://https://gitee.com/...）。先去掉 scheme 再按 / 切。
    _path = REPO_URL.split("//", 1)[-1].split("?")[0].rstrip("/")
    host, _seg, tail = _path.partition("/")
    user = tail.split("/")[0] if tail else ""
    repo = tail.split("/")[-1] if tail else ""
    if not user:
        print("无法从 %s 解析出用户名/仓库名，请用 GITEE_URL 覆盖" % REPO_URL)
        return 2
    bare = "https://%s/%s" % (host, tail)
    # 嵌进 user:pass@ 后面时必须**去掉 scheme**，
    # 否则会拼出 https://user:pass@https://gitee.com/...（我第一版的错）。
    netloc = "%s/%s" % (host, tail)

    # 组装内容
    work = os.path.join(tempfile.gettempdir(), "gitee_work_%d" % os.getpid())
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    log = probe_payload.build(work, README)
    print("组装内容到 %s:" % work)
    for rel, kind, size in log:
        print("    + %-30s %-12s %8.2f MB"
              % (rel, kind, size / 1048576.0))

    auth_url = "https://%s:%s@%s.git" % (user, tok, netloc)
    print("目标: %s  用户名: %s" % (bare, user))
    ARGS = [GIT, "-c", "credential.helper=", "-c", "core.askPass="]

    def run(args, cwd=None, timeout=300):
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=ENV)
        out = (((p.stdout or "") + (p.stderr or "")).replace(tok, "***").strip())
        return p.returncode, out

    try:
        rc, out = run(ARGS + ["ls-remote", auth_url], timeout=120)
        print("\n[1] ls-remote exit=%d" % rc)
        if out:
            print("    " + out[:240].replace("\n", "\n    "))
        if rc != 0:
            print("\n鉴权失败。若提示认证错误，检查：令牌是否勾了 projects 权限、")
            print("用户名是否为 %s。Gitee 的私人令牌在「设置 → 私人令牌」生成。" % user)
            return 1

        rc, out = run(ARGS + ["clone", auth_url, work], timeout=600)
        if rc != 0:
            # 仓库有初始提交时 clone 到非空目录会失败，换个干净目录重试
            fresh = work + "_c"
            shutil.rmtree(fresh, ignore_errors=True)
            rc, out = run(ARGS + ["clone", auth_url, fresh])
            if rc != 0:
                print("[2] clone 失败: %s" % out[:240])
                return 1
            work = fresh
        print("[2] clone OK")

        # 覆盖成新内容（clone 下来的旧副本要清掉再放）
        for rel, src, kind in probe_payload.payload_items():
            dst = os.path.join(work, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        nd = os.path.join(work, "nodes")
        shutil.rmtree(nd, ignore_errors=True)
        os.makedirs(nd)
        for f in probe_payload.node_files():
            shutil.copy2(f, os.path.join(nd, os.path.basename(f)))

        for a in (["config", "user.name", "probe-bot"],
                  ["config", "user.email", "probe-bot@users.noreply.github.com"],
                  ["add", "-A"]):
            rc, out = run(ARGS + a, cwd=work)
            if rc != 0:
                print("[3] %s 失败: %s" % (a[0], out[:200]))
                return 1
        rc, out = run(ARGS + ["commit", "-q", "-m", "ci: 云端探针内容更新"], cwd=work)
        print("[3] commit exit=%d %s"
              % (rc, "已提交" if "nothing to commit" not in out else "无变化"))
        if rc != 0 and "nothing to commit" not in out:
            print("    " + out[:240])
            return 1

        rc, out = run(ARGS + ["push", "origin", "HEAD:master"], cwd=work, timeout=600)
        print("[4] push exit=%d" % rc)
        if out:
            print("    " + out[:300].replace("\n", "\n    "))
        if rc != 0:
            print("\n推送失败。常见原因：令牌权限不足，或仓库默认分支不是 master。")
            return 1

        rc, out = run(ARGS + ["ls-remote", "--heads", auth_url])
        print("[5] 远端分支: %s" % (out.replace("\n", " ") or "(无)"))
        print("\n✓ Gitee 推送完成")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(work + "_c", ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())