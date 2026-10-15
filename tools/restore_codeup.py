# -*- coding: utf-8 -*-
"""云效 Codeup 探针仓库的**灾难恢复**脚本。

场景：阿里云文档写明「欠费后立即停机，停机满 15 天释放所有云效组织，
研发数据无法找回」。本脚本把恢复过程自动化到一条命令。

⚠ 它能恢复什么、不能恢复什么（这个边界必须说清，否则出事时容易误判）：

  能恢复：
    · Codeup 仓库内容（代码 + 22MB mihomo 内核 + vendor yaml + 节点配置）
      —— 从本机主仓推（首选，代码是唯一来源），失败则从 Gitee 镜像拉
    · 校验恢复结果与预期清单逐字节一致

  **不能恢复**：
    · 流水线配置（那条 `git fetch && git reset --hard && python3 ci_probe_run.py`
      命令、cron 触发器）—— 它们存在**云效自己的数据库里，不在仓库中**。
      必须按 tools/ci_pipeline.yaml + tools/CI_RECOVERY.md 手工重建。
      这就是为什么那两件事被单独维护的原因。

用法：
    python tools/restore_codeup.py            # 先看现状再决定要不要恢复
    python tools/restore_codeup.py --apply    # 实际执行
    python tools/restore_codeup.py --apply --from-gitee   # 强制从 Gitee 镜像恢复
"""
import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import probe_payload  # noqa: E402

GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"
HOST = "myxk-cn-shenzhen.devops.aliyuncs.com"
RPATH = "codeup/ci-probe-test"
GITEE = "https://gitee.com/andywx/ci-probe-test.git"
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")
APPLY = "--apply" in sys.argv
FROM_GITEE = "--from-gitee" in sys.argv

README = """# ci-probe-test

clash-source 节点源探针的云端执行仓库（由 tools/restore_codeup.py 恢复）。

Gitee 与 Codeup 共用同一份内容清单（主仓 tools/probe_payload.py 是唯一来源）。

## 流水线命令

```bash
bash tools/sync_and_probe.sh
```

`git reset --hard` 不是可选的：云效会复用带缓存的 workspace，增量同步会漏文件。

## 定位

`scope=cnci` 只做交叉验证，永不触发任何源的升降级。
有权判死的是美国 GitHub Actions，有权回收的是本机探针。

环境约束：云效公共构建集群实测 Python 3.6.8 —— `capture_output=`/`text=`
是 3.7+，改动后在主仓跑 `python tools/check_ci_scripts.py`。
"""


def run(args, cwd=None, timeout=300, secret=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=ENV)
    out = (p.stdout or "") + (p.stderr or "")
    if secret:
        out = out.replace(secret, "***")
    return p.returncode, out.strip()


def codeup_auth():
    f = os.path.join(ROOT, "codeup.https")
    if not os.path.exists(f):
        print("  ✗ 缺少 codeup.https")
        print("    里面应是两行：云效**登录账号** / 个人令牌")
        print("    （组织前缀 myxk 不能当用户名，服务端会回「Https克隆账号或密码错误」）")
        return None
    lines = [l.strip() for l in open(f, encoding="utf-8").read().splitlines() if l.strip()]
    if len(lines) < 2:
        print("  ✗ codeup.https 需要两行，实际 %d 行" % len(lines))
        return None
    return "https://%s:%s@%s/%s" % (lines[0], lines[1], HOST, RPATH), lines[0], lines[1]


def gitee_auth():
    f = os.path.join(ROOT, "gitee.token")
    if not os.path.exists(f):
        return GITEE, None
    tok = open(f, encoding="utf-8").read().strip()
    return "https://andywx:%s@gitee.com/andywx/ci-probe-test" % tok, tok


def git_args(host):
    return [GIT, "-c", "http.proxy=http://127.0.0.1:7897",
            "-c", "http.https://%s.proxy=http://127.0.0.1:7897" % host,
            "-c", "credential.helper=", "-c", "core.askPass="]


def _norm_hash(path):
    """按文本归一化行尾后再算 sha256。

    ⚠ 必要：Windows 上 git 检出的是 CRLF，本地源文件是 LF。
      直接比字节会把 20 个文件误报成"内容不同"，让恢复脚本以为备份也坏了
      —— 而它其实完全正常。这个误报会让人在最需要它的时候不敢用备份。
    """
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":          # gzip 等二进制，不归一化
        return hashlib.sha256(raw).hexdigest()
    try:
        return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    except Exception:
        return hashlib.sha256(raw).hexdigest()


def expected_hashes():
    out = {}
    for rel, src, kind in probe_payload.payload_items():
        if os.path.exists(src):
            out[rel] = _norm_hash(src)
    for f in probe_payload.node_files():
        out["nodes/" + os.path.basename(f)] = _norm_hash(f)
    return out


def survey(url, host, secret, tries=3, gap=15, stats=None):
    """看远端现状：能不能连、有哪些文件、和预期差多少。

    ⚠ 窗口必须够长（默认 3 次×15 秒 ≈ 40 秒；恢复模式会再放大）：
      云效 Codeup 的 git 端点**间歇性**对已鉴权请求回 302 跳 SSO，
      实测存在「好窗口/坏窗口」交替（同一令牌同参数：4/4 成功 → 0/8 失败）。
      探测窗口太短会整段落进坏窗口，从而**误判成"令牌失效"**，
      让人去折腾本来没问题的凭据 —— 这比"多等一会儿"有害得多。
    """
    last = ""
    for i in range(tries):
        d = tempfile.mkdtemp(prefix="restore_survey_")
        rc, out = run(git_args(host) + ["clone", "--depth", "1", url, d],
                      timeout=600, secret=secret)
        if rc == 0:
            have = {}
            for dp, dn, fn in os.walk(d):
                dn[:] = [x for x in dn if x != ".git"]
                for f in fn:
                    if f.endswith(".pyc"):
                        continue
                    full = os.path.join(dp, f)
                    rel = os.path.relpath(full, d).replace("\\", "/")
                    have[rel] = _norm_hash(full)
            shutil.rmtree(d, ignore_errors=True)
            if stats is not None:
                stats['ok_at'] = i + 1
            return have, ""
        shutil.rmtree(d, ignore_errors=True)
        last = out.strip().splitlines()[-1] if out.strip() else "?"
        if i < tries - 1:
            print("      (第 %d 次失败，%d 秒后重试: %s)"
                  % (i + 1, gap, last[:66]))
            time.sleep(gap)
    return None, last


def classify(url, user, pw):
    """认证失效 / 仓库不存在 / 服务故障 —— 三者要分清，处置方式完全不同。

    为什么要分清：2026-10-15 实际踩到 —— 令牌失效时云效把 git 请求 302 到
    阿里云登录页，git 跟随后连 80 端口失败，报出来的是 `502 Bad Gateway`
    或 `Failed to connect ... port 80`。这两个信息**极具误导性**：
      · 502 看着像"服务端故障/组织挂了"，实际是令牌失效
      · port 80 看着像"网络不通"，实际是 302 跳转的下游
    如果不分清，值班的人会去查服务端/网络，方向完全错。
    """
    import urllib.error
    import urllib.request
    probe = url.split("://", 1)[-1]
    probe = probe.split("@")[-1]
    ep = "https://%s/info/refs?service=git-upload-pack" % probe.split(":")[0]
    req = urllib.request.Request(ep)
    if user and pw:
        tok = base64.b64encode(("%s:%s" % (user, pw)).encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    req.add_header("User-Agent", "git/2.55.0")
    # 必须显式走代理：本机到 myxk-cn-shenzhen 直连会 WinError 10060 超时
    # （实测），不指定代理的话这个超时会��会被误判成"服务端故障"，方向完全错。
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **kw):
            return None          # 交回上层，于是 3xx 会作为 HTTPError 抛出
    _op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897",
                                     "https": "http://127.0.0.1:7897"}),
        _NoRedirect)
    try:
        with _op.open(req, timeout=25) as r:
            return "ok", "HTTP %s" % r.status
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "") or ""
        if e.code in (401, 403):
            return "auth", "HTTP %s 未授权 —— 令牌无效或权限不足" % e.code
        if e.code in (301, 302, 307) or "login" in loc.lower():
            return "auth", ("HTTP %s 跳转到登录页（%s）—— **令牌已失效**，"
                            "需去 Codeup 个人设置重新生成"
                            % (e.code, loc.split("?")[0][:70]))
        if e.code == 404:
            return "missing", "HTTP 404 —— 仓库不存在（或组织已被释放）"
        return "service", "HTTP %s" % e.code
    except Exception as ex:
        return "network", str(ex)[:90]


def main():
    print("=" * 70)
    print("云效 Codeup 探针仓库 —— 灾难恢复检查")
    print("=" * 70)

    auth = codeup_auth()
    if not auth:
        return 2
    curl, user, pw = auth

    want = expected_hashes()
    total_mb = 0.0
    for rel, src, kind in probe_payload.payload_items():
        if os.path.exists(src):
            total_mb += os.path.getsize(src) / 1048576.0
    for f in probe_payload.node_files():
        total_mb += os.path.getsize(f) / 1048576.0
    print("\n预期内容: %d 个文件, %.1f MB（其中 mihomo 内核占绝大部分，"
          "这是恢复时最耗时的一步）" % (len(want), total_mb))

    print("\n--- 1) 现状 ---")
    have, err = survey(curl, HOST, pw, tries=6, gap=15)
    if have is None:
        kind, why = classify(curl, user, pw)
        print("  ✗ Codeup 仓库不可达：%s" % err.splitlines()[-1] if err else "")
        print("  诊断: %s" % why)
        repo_missing = (kind == "missing")
        if kind == "auth":
            print("""
  → 收到 302 跳 SSO 登录页。**两种可能，处理方式完全相反**：
    (a) 令牌真失效
    (b) 云效 SSO/后端在抖动 —— 2026-10-15 实测存在好/坏窗口交替：
        同一有效令牌、同样参数，18:40 是 4/4 成功，18:42 就变成 0/8 失败。

    先跑下面这条，**多试几分钟**，能成功就说明是 (b)：
        python tools/codeup_auth.py
      · 任意一次报「可用组合」 → 是 (b)，等一会儿再重跑本脚本即可，
        **不要换令牌**（换了也没用，还白折腾）
      · 连续多次全失败 → 大概率是 (a)，再去重新生成令牌：
        Codeup → 个人设置 → 私人令牌（勾代码仓库读写），
        存回 codeup.token 后跑 python tools/codeup_auth.py 自动同步到 codeup.https
        （注意：第一行是云效**登录账号**，不是组织前缀 myxk）""")
        elif kind == "missing":
            print("""
  → 仓库确实不存在。**若云效组织已被释放（欠费 15 天到期），必须先手工重建**：
    1. 阿里云控制台 → 云效 → 创建组织（**个人使用模式**，最多 5 人，0 元；
       ⚠ 千万别选企业协作模式，按日峰值人数 2 元/人/天计费）
    2. 代码管理 → 新建仓库，路径必须是：%s
    3. 不要初始化 README（留空仓）
    4. 回到本脚本重跑 --apply""" % RPATH)
        else:
            print("""
  → 看起来是网络或服务端问题，不是凭据问题。等一会儿重试；
    若持续出现，用下面的命令复核：
      curl -sS -o NUL -w "%%{http_code}\\n" -u <账号>:<令牌> \\
        https://%s/%s/info/refs?service=git-upload-pack""" % (HOST, RPATH))
    else:
        missing = sorted(set(want) - set(have))
        differ = sorted(k for k in set(want) & set(have) if want[k] != have[k])
        extra = sorted(set(have) - set(want) - {"results", "README.md",
                                                "results/latest.json"})
        repo_missing = False
        print("  ✓ 仓库可达，%d 个文件" % len(have))
        print("    缺失 %d / 内容不同 %d / 多出 %d"
              % (len(missing), len(differ), len(extra)))
        for k in missing[:6]:
            print("      - 缺 %s" % k)
        for k in differ[:6]:
            print("      ~ 异 %s" % k)

    need = True if have is None else bool(
        (set(want) - set(have))
        or any(want[k] != have.get(k) for k in want))

    print("\n--- 2) Gitee 镜像（备份源）---")
    gurl, gtok = gitee_auth()
    ghave, gerr = survey(gurl, "gitee.com", gtok)
    if ghave is None:
        print("  ✗ Gitee 不可达：%s" % gerr)
        print("    → Gitee 镜像是 Codeup 的备份。备份也挂了就只能从本机主仓重建。")
    else:
        gbad = [k for k in sorted(want) if ghave.get(k) != want[k]]
        gmissing = [k for k in sorted(want) if k not in ghave]
        print("  %s Gitee 可达，%d 个文件" % ("✓" if not gbad else "✗", len(ghave)))
        if gbad:
            print("    内容不同 %d 个: %s" % (len(gbad), ", ".join(gbad[:6])))
        if gmissing:
            print("    缺失 %d 个: %s" % (len(gmissing), ", ".join(gmissing[:6])))
        if not gbad and not gmissing:
            print("    内容完全符合预期，可作为恢复源")

    print("\n--- 3) 结论 ---")
    if not need:
        print("  Codeup 仓库完整，**无需恢复**。")
        print("  但仍建议确认一下流水线本身还在（它存在云效数据库里，不在仓库）：")
        print("    打开云效 → 流水线 → 看得到列表且最近一次运行是成功")
        return 0

    if repo_missing:
        print("  需要恢复，但 Codeup 仓库当前不可达。")
        print("\n  若云效组织已被删除（欠费到期），**必须先手工重建**，脚本无能为力：")
        print("    1. 阿里云控制台 → 云效 → 重新创建组织（个人使用模式，0 元，5 人以内免费）")
        print("    2. 代码管理 → 新建代码仓库，路径必须是：%s" % RPATH)
        print("    3. 不要初始化 README（留空仓）")
        print("    4. 回到本脚本重跑 --apply")
        print("\n  若只是仓库被删、组织还在 → 直接 --apply")

    if not APPLY:
        print("\n  这是预演。加 --apply 实际执行。")
        if repo_missing:
            print("  （组织被删的话，先按上面 4 步重建，再跑）")
        print("\n  ⚠ 恢复完仓库后，**流水线还要手工重建**（配置在云效数据库里）：")
        print("     工具箱 → 流水线 → 新建 → 导入 %s" % os.path.join("tools", "ci_pipeline.yaml"))
        print("     或按 tools/CI_RECOVERY.md 手工配一遍")
        print("     cron: 每周日 04:23")
        return 0

    # ---------------- 实际恢复 ----------------
    print("\n--- 4) 执行恢复 ---")
    src = "Gitee 镜像" if FROM_GITEE else "本机主仓"
    print("  来源: %s" % src)

    stage = tempfile.mkdtemp(prefix="restore_stage_")
    work = tempfile.mkdtemp(prefix="restore_work_")
    try:
        if FROM_GITEE:
            rc, out = run(git_args("gitee.com") + ["clone", "--depth", "1",
                                                   gurl, stage],
                          timeout=900, secret=gtok)
            if rc != 0:
                print("  ✗ Gitee clone 失败: %s" % out[:200])
                return 1
            for rel, _, _ in probe_payload.payload_items():
                pass
            shutil.rmtree(os.path.join(stage, ".git"), ignore_errors=True)
        else:
            print("  从本机主仓组装内容（唯一来源）...")
            probe_payload.build(stage, README)

        print("  clone 目标仓库...")
        rc, out = run(git_args(HOST) + ["clone", curl, work],
                      timeout=900, secret=pw)
        if rc != 0:
            print("  ✗ Codeup clone 失败（仓库可能不存在）: %s" % out[:200])
            return 1

        print("  覆盖内容...")
        for name in os.listdir(stage):
            s, d = os.path.join(stage, name), os.path.join(work, name)
            if os.path.isdir(s):
                shutil.rmtree(d, ignore_errors=True)
                shutil.copytree(s, d, ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc"))
            else:
                shutil.copy2(s, d)

        for a in (["config", "user.name", "restore-bot"],
                  ["config", "user.email", "restore-bot@users.noreply.github.com"],
                  ["add", "-A"]):
            rc, out = run([GIT, "-c", "credential.helper="] + a, cwd=work)
            if rc != 0:
                print("  ✗ %s 失败: %s" % (a[0], out[:150]))
                return 1
        rc, out = run([GIT, "-c", "credential.helper=", "commit", "-q", "-m",
                       "restore: 灾难恢复，探针内容自 Gitee/主仓还原"],
                      cwd=work)
        if "nothing to commit" in out:
            print("  内容本就一致，无需提交")
        elif rc != 0:
            print("  ✗ commit 失败: %s" % out[:200])
            return 1

        rc, out = run(git_args(HOST) + ["push", "origin", "HEAD:master"],
                      cwd=work, timeout=900, secret=pw)
        print("  push exit=%d" % rc)
        if rc != 0:
            print("    " + out[:250])
            return 1

        print("\n--- 5) 校验 ---")
        final, err = survey(curl, HOST, pw)
        if final is None:
            print("  ✗ 恢复后仍不可达")
            return 1
        bad = [k for k in want if final.get(k) != want[k]]
        if bad:
            print("  ✗ 仍有 %d 个文件不符:" % len(bad))
            for k in bad[:8]:
                print("      %s" % k)
            return 1
        print("  ✓ %d 个文件全部与预期一致" % len(want))
        print("\n仓库恢复完成。**别忘了还有流水线要手工重建** —— 见 tools/CI_RECOVERY.md")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())


