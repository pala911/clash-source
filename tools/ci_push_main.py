# -*- coding: utf-8 -*-
"""把云效探针结果推回**主仓**（pala911/clash-source），让云效数据真正参与判定。

## 为什么需要这个脚本

health.py 的双视角分级（2026-10-15 加的）要读 state/probe_cnci_latest.json，
而云效此前只把结果 commit 到**自己的 Codeup 仓**（ci-probe-test/results/）。
主仓一份都没有 —— 数据根本过不去，分级会永远显示「无云效口径数据」，
看起来就像「云效的数据没生效」。这条管道之前不存在，现在补上。

推两个文件：
    state/probe_cnci_latest.json     <- health.py 直接消费
    results/probe_cnci_<时间戳>.json <- 历史存档（两周后校准阈值要用）

## 三条不能省的约束

⚠ **绝不失败**：任何一步出错都只打印告警并 exit 0。
   探针本身已经跑完、结果也已经 commit 到 Codeup 了，推主仓失败不该让整条
   流水线变红 —— 而云效日志面板实测不渲染，**流水线状态就是唯一的告警信号**，
   把它染红只会掩盖真正的失败。

⚠ **不覆盖更新的数据**：若远端已有 probed_at 更晚的同名文件，本轮跳过。
   防时钟偏差 / 重跑旧结果把新数据盖回去。

⚠ **国内到 GitHub 的连通性未实测**：raw.githubusercontent.com 实测必墙，
   github.com 的 git 端点从云效杭州能不能打通**没有验证过**。所以带重试，
   失败只告警。真打不通就退回「本机中转」方案（见 tools/CI_RECOVERY.md）。

## 用法

云效流水线加一个环境变量 `GH_PAT`，值为一个 GitHub 细粒度令牌，
权限只要 **这一个仓库的 Contents: 写入**。没有这个变量时本脚本直接跳过。

## ⚠ 环境约束（栽过三次，别踩第四次）

云效集群是 **Python 3.6.8**：`capture_output=` / `text=` 是 3.7+，
海象运算符是 3.8+，f-string 与本项目 % 风格不一致。
本机 3.11 上全都正常，只有真机才炸，且报错极具误导性。
改完务必在主仓跑 `python tools/check_ci_scripts.py`。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import urllib.error
    import urllib.request
except ImportError:                                    # pragma: no cover
    urllib = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("MAIN_REPO", "pala911/clash-source")
BRANCH = os.environ.get("MAIN_BRANCH", "main")
TRIES = int(os.environ.get("PUSH_TRIES", "3"))
GAP = int(os.environ.get("PUSH_GAP", "15"))
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")


def find_git():
    """定位 git 可执行文件。

    ⚠ 云效集群上 `git` 在 PATH 里，直接用就行。但本机没装系统 git，
      只有 portable-git —— 一开始直接写 GIT="git"，结果 FileNotFoundError
      被下面的兜底 except 吞成「未预期的异常」，看起来像网络问题。
      那是**验证工具自己出错**的典型：它把「没找到 git」说成了「连不上」，
      会把人引到完全错误的方向去排查。

    所以这里按 GIT_BIN -> PATH -> portable-git 的顺序找，且**找不到时
    单独报一条能一眼看懂的告警**，不混进网络错误里。
    """
    cand = [os.environ.get("GIT_BIN", ""), "git"]
    for c in cand:
        if c and shutil.which(c):
            return shutil.which(c)
    # 往上找 portable-git（本机开发环境的位置约定）
    d = ROOT
    for _ in range(4):
        for rel in ("portable-git/bin/git.exe", "portable-git/bin/cmd/git.exe",
                    "portable-git/cmd/git.exe"):
            p = os.path.join(d, "..", "portable-git", *rel.split("/")[1:])
            if os.path.exists(p):
                return p
        d = os.path.dirname(d)
    return None


def say(msg):
    print("[push-main] %s" % msg)


def warn(msg):
    print("[push-main] ⚠ %s" % msg)


def run(args, cwd=None, timeout=300):
    # ⚠ 故意用 stdout/stderr=PIPE 而不是 capture_output=（3.7+）
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout, env=ENV)
    out = (p.stdout or b"").decode("utf-8", "replace")
    # ⚠ 必须脱敏。git 后备通道把令牌嵌在 URL 里
    #   （https://x-access-token:<PAT>@github.com/...），
    #   而 git 失败时的报错**经常把整个 URL 原样回显**。
    #   那些输出会进 warn() -> 流水线日志 -> 云效组织内任何有日志权限的人可见。
    #   codeup_push.py 早就做了这层（.replace(pw, "***")），这里漏了。
    pat = os.environ.get("GH_PAT", "").strip()
    if pat and pat in out:
        out = out.replace(pat, "***")
    return p.returncode, out


def stamp_of(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        return d.get("probed_at") or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 回传结果留痕（2026-10-16 新增）
# ---------------------------------------------------------------------------
# 问题：这条管道刻意「永不失败」（连异常都吞掉、不改流水线状态），因为云效的
#   日志面板实测渲染不全，把流水线染红只会掩盖真正的失败。于是「回传到底通没通」
#   在云效那边**没有任何信号** —— 只能靠人盯着主仓那个文件有没有自己变新。
#   实测后果：它从部署到被发现「一次都没真跑过」，中间隔了一天，谁都看不出来。
#
# 所以把结果落成仓库里的一个文件（`results/push_main_last.json`），由
#   `tools/sync_and_probe.sh` 提交 —— Codeup 的 git 是云端唯一稳定可读的通道。
#   看它 = `python tools/cnci_status.py`（本机），不用去翻流水线日志。
STATUS_REL = os.path.join("results", "push_main_last.json")


def status_dir():
    """留痕落点 = **仓库根**（云效上 probe_payload 把 .py 一律放在根目录）。

    本机开发时脚本在 `tools/` 下 —— 那就不留痕（本机跑这一趟，成败在终端里
    直接就能看到），免得往主仓塞一个只有本机才有意义的文件。
    """
    return None if os.path.basename(HERE).lower() == "tools" else HERE


def record_status(st):
    """把这一轮的回传结果写进工作区（永不抛异常）。"""
    d0 = status_dir()
    if not d0:
        say("本机（tools/）跳过留痕")
        return
    doc = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "probe_cnci_at": stamp_of(os.path.join(HERE, "probe_cnci.json")),
        "ok": bool(st.get("ok")),
        "status": st.get("status") or "unknown",
        "channel": st.get("channel") or "",
        "detail": (st.get("detail") or "")[:300],
        "repo": REPO,
        "branch": BRANCH,
        "py": sys.version.split()[0],
        # 每个文件的结果逐个记下来：
        #   实测踩过一次——state/ 写进去了、results/ 存档没进去，
        #   而留痕只说 ok-api，完全看不出来。
        "files": st.get("files") or [],
        # 回退到 git 之后，最终状态会覆盖掉 API 那次失败的原因 —— 而那个原因
        # 恰恰是最该看的（这次实测就吃了亏）。所以单独留一份。
        "api_why": st.get("api_why") or "",
    }
    try:
        path = os.path.join(d0, STATUS_REL)
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        say("回传结果已留痕: %s（status=%s）" % (STATUS_REL, doc["status"]))
    except Exception as e:                        # noqa: BLE001
        warn("留痕失败（不影响别的）：%r" % e)


def commit_status():
    """把留痕提交回 Codeup。

    ⚠ 为什么必须提交：工作区跑完就被回收，不提交等于没留。
      失败同样只告警 —— 这条链路的铁律是「绝不因回传而让流水线变红」。
      并发保护照抄 ci_probe_run.push_result（先 rebase 再推一次，绝不 --force）。

    ⚠ 用 find_git() 而不是 shutil.which("git")：本机没有系统 git，只有
      portable-git。原来那样写会让「本机彩排」直接跳过这一整段 ——
      于是最需要被验证的那部分代码，恰恰是**唯一没法在本机跑到的**。
    """
    d0 = status_dir()
    if not d0:
        return
    git = find_git()
    if not git:
        warn("留痕提交跳过：找不到 git（GIT_BIN / PATH / portable-git 都没有）")
        return

    def g(*a):
        return run([git] + list(a), cwd=d0, timeout=300)

    g("config", "user.name", "cnci-probe")
    g("config", "user.email", "cnci-probe@users.noreply.github.com")
    rc, out = g("add", "-A", STATUS_REL)
    rc, out = g("commit", "-m", "回传留痕 %s"
                % time.strftime("%Y%m%d-%H%M", time.gmtime()))
    if "nothing to commit" in out or "nothing added to commit" in out:
        say("留痕无变化，跳过提交")
        return
    if rc != 0:
        warn("留痕提交失败: %s" % out.strip()[:200])
        return
    rc, out = g("push", "origin", "HEAD:master")
    if rc != 0:
        g("pull", "--rebase", "--autostash", "origin", "master")
        rc, out = g("push", "origin", "HEAD:master")
    if rc == 0:
        say("留痕已提交到 Codeup（本机用 python tools/cnci_status.py 读）")
    else:
        warn("留痕推送失败: %s" % out.strip()[:200])


# ---------------------------------------------------------------------------
# 写入通道：Contents API（主） / git（后备）
# ---------------------------------------------------------------------------
# 为什么 API 优先：本机（国内）实测 **github.com:443 连不上**，云效在杭州、
# 同样在国内，git 端点大概率也被挡。但之前实测 **api.github.com 国内可直连 200**。
# 而 Contents API 还不必克隆（主仓 ~3MB，但克隆一次要传几十秒，还会撞上
# git 端点 302/超时那堆坑）。两个小请求就完事。
API = "https://api.github.com/repos/%s/contents/%s"


# API 是主通道（实测能通），git 从国内基本不通（Empty reply from server）。
# 所以多花点时间在 API 上重试划算：失败一轮的代价（一整轮探针白跑 +
# 双视角分级少一轮）远大于多等十几秒。
API_TRIES = int(os.environ.get("API_TRIES", "5"))
API_GAP = int(os.environ.get("API_GAP", "5"))


def api_call(url, pat, method="GET", body=None, timeout=60):
    """调一次 GitHub API。重试是必须的：

    ⚠ 2026-10-16 实测（本机 7897 代理）：urllib 会间歇性抛
      `ssl.SSLEOFError: EOF occurred in violation of protocol` / `URLError`，
      同一个 URL 立刻重试就成功。而单次抖动就会让
      **整条 API 通道失败**：这条通道是主选（国内可直连），
      退下去就是国内大概率也不通的 git 通道，这一轮就全废了。

    ⚠ `HTTPError` **不重试**：那是明确的业务答复（比如 404 = 文件不存在），
      重试只会把错误掩盖成慢。调用方按语义处理。
    """
    last = None
    for i in range(API_TRIES):
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", "token " + pat)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "clash-source-cnci")
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            req.add_header("Content-Type", "application/json; charset=utf-8")
        try:
            with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError:
            raise
        except Exception as e:                    # noqa: BLE001
            last = e
            if i + 1 < API_TRIES:
                warn("API 第 %d 次抖动：%r，%d 秒后重试" % (i + 1, e, API_GAP))
                time.sleep(API_GAP)
    raise last


def remote_stamp(repo, path_in_repo, pat):
    """读远端已有文件的 probed_at。取不到就返回 ""（当作「没有」）。

    只用于「别用旧数据盖掉新数据」这一道闸。任何失败都放行 ——
    宁可多推一次旧的，也不该因为读不到就卡住整条管道。
    """
    if urllib is None:
        return ""
    try:
        cur = api_call(API % (repo, path_in_repo), pat)
    except Exception:
        return ""
    if not cur.get("content"):
        return ""
    try:
        import base64
        raw = base64.b64decode(cur["content"]).decode("utf-8", "replace")
        return (json.loads(raw) or {}).get("probed_at") or ""
    except Exception:
        return ""


def api_put(repo, path_in_repo, local_path, message, branch, pat):
    """用 Contents API 写入一个文件。返回 (ok, 说明)。

    ⚠ 内容**完全相同**时不发 PUT。GitHub 的 contents API 即使内容一字不差
      也会生成一个新提交 —— 不比对的话，每天日更都会在主仓留下一条空提交，
      很快把提交历史冲成一堆噪音，反而让人看不出哪次是真的数据变了。
    """
    if urllib is None:
        return False, "urllib 不可用"
    url = API % (repo, path_in_repo)
    # 已存在就要带 sha，否则 GitHub 返回 422 Unprocessable Entity
    sha = None
    try:
        cur = api_call(url, pat)
        sha = cur.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return False, "GET %s -> HTTP %d" % (path_in_repo, e.code)
    except Exception as e:
        return False, "GET %s 失败: %r" % (path_in_repo, e)
    import base64
    with open(local_path, "rb") as f:
        raw = f.read()
    if sha and cur.get("content"):
        try:
            if base64.b64decode(cur["content"]) == raw:
                return True, "内容未变，跳过 %s" % path_in_repo
        except Exception:
            pass          # 比对不了就照常写，别因为解码问题卡住
    b64 = base64.b64encode(raw).decode("ascii")
    payload = {"message": message, "content": b64, "branch": branch}
    if sha:
        payload["sha"] = sha
    try:
        api_call(url, pat, method="PUT", body=payload)
        return True, "%s %s" % ("更新" if sha else "新建", path_in_repo)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        return False, "PUT %s -> HTTP %d %s" % (path_in_repo, e.code, detail)
    except Exception as e:
        return False, "PUT %s 失败: %r" % (path_in_repo, e)


def main(st=None):
    """跑一轮回传。结果记进 st（{"ok","status","channel","detail"}），供留痕。"""
    st = st if st is not None else {}
    src = os.path.join(HERE, "probe_cnci.json")
    if not os.path.exists(src):
        warn("没有 probe_cnci.json，跳过（探针没跑成功？）")
        st.update(status="no-probe", ok=False, detail="工作区没有 probe_cnci.json")
        return 0

    pat = os.environ.get("GH_PAT", "").strip()
    if not pat:
        warn("未设置 GH_PAT —— 云效数据不会进主仓，双视角分级会一直显示「无云效数据」")
        warn("  配法：云效流水线 -> 环境变量 -> GH_PAT = 只对 %s 有写权限的令牌" % REPO)
        st.update(status="no-pat", ok=False, channel="",
                  detail="流水线变量里没有 GH_PAT（脚本直接跳过、不报错）")
        return 0

    new_ts = stamp_of(src)
    if not new_ts:
        warn("probe_cnci.json 里没有 probed_at，不推送（无法判断新旧）")
        st.update(status="no-stamp", ok=False, detail="probe_cnci.json 缺 probed_at")
        return 0

    stamp = new_ts.split("#")[0].replace(":", "").replace("-", "")
    arch_rel = "results/probe_cnci_%s.json" % stamp
    latest_rel = "state/probe_cnci_latest.json"

    # ---- 不覆盖更新的数据（两条通道共用这个前置判断）----
    # ⚠ FORCE=1 可以强行覆盖。这个开关存在是因为**护栏会把自己锁死**：
    #   2026-10-16 测试时误推了一份 probed_at=2026-10-20 的伪造数据，
    #   结果之后 4 天所有真实数据都会被「远端更新」判据拒收 ——
    #   护栏正确地工作，却把管道彻底堵死了。必须留一把人工钥匙。
    #   平时绝不要设它。
    force = os.environ.get("PUSH_FORCE", "").strip() not in ("", "0", "false", "no")
    remote_ts = remote_stamp(REPO, latest_rel, pat)
    if remote_ts and remote_ts > new_ts and not force:
        say("主仓已有更新的数据（%s > %s），跳过，不覆盖" % (remote_ts, new_ts))
        st.update(status="skipped-newer", ok=False, channel="api",
                  detail="主仓已有更新数据 %s > %s（护栏，非故障）" % (remote_ts, new_ts))
        return 0
    if force and remote_ts and remote_ts > new_ts:
        warn("PUSH_FORCE=1：强行覆盖更新的数据（%s -> %s）" % (remote_ts, new_ts))

    # ---- 通道 1：Contents API（推荐，api.github.com 国内实测可直连）----
    ok, why = api_put(REPO, latest_rel, src, "cnci 探针 %s" % stamp, BRANCH, pat)
    if ok:
        say("API 写入 %s" % why)
        ok2, why2 = api_put(REPO, arch_rel, src, "cnci 探针存档 %s" % stamp,
                            BRANCH, pat)
        say("API 写入 %s" % why2 if ok2 else "API 存档跳过：%s" % why2)
        say("已推回主仓 %s:%s —— health.py 下一轮就能读它，分级会从「?」变 T1/T2/T3"
            % (REPO, BRANCH))
        st.update(status="ok-api", ok=True, channel="api", detail=why,
                  files=[{"path": latest_rel, "ok": True, "why": why},
                         {"path": arch_rel, "ok": bool(ok2), "why": why2}])
        return 0
    warn("Contents API 通道失败：%s" % why)
    warn("  回退到 git 通道（github.com:443 在国内常被挡，可能也不通）")
    # ⚠ 2026-10-16 实测证据（云效杭州 -> github.com）：
    #     fatal: unable to access ...：Empty reply from server
    #   → git 通道从云效这边基本没照（典型的国内出口行为），主通道只有 Contents API。
    #   这也是为什么要把 API 的重试预算调得比 git 多。
    st.update(status="fail-api", ok=False, channel="",
              detail="API: %s" % why, api_why=why)

    # ---- 通道 2：git clone + push ----
    git = find_git()
    if not git:
        warn("找不到 git 可执行文件（查过 GIT_BIN、PATH、portable-git）")
        warn("  这**不是 GitHub 连通性问题**，别顺着这条去查网络。")
        warn("  云效集群上 git 在 PATH 里；若在这里报错说明测试环境缺 git。")
        warn("  设 GIT_BIN=<git绝对路径> 可覆盖。")
        st.update(status="no-git", ok=False,
                  detail="找不到 git（不是网络问题）：%s" % (st.get("detail") or ""))
        return 0

    url = "https://x-access-token:%s@github.com/%s.git" % (pat, REPO)
    auth = ["-c", "credential.helper=", "-c", "core.askPass="]

    base = tempfile.gettempdir()
    work = os.path.join(base, "pushmain_%d_%d" % (os.getpid(), len(os.listdir(base))))
    shutil.rmtree(work, ignore_errors=True)

    # 先探连通性，别一上来就 clone 几百秒才发现连不上
    for i in range(TRIES):
        rc, out = run([git] + auth + ["ls-remote", url], timeout=90)
        if rc == 0:
            say("git ls-remote 第 %d 次成功" % (i + 1))
            break
        warn("git ls-remote 第 %d 次失败：%s" % (i + 1, out.strip()[:160]))
        if i + 1 < TRIES:
            time.sleep(GAP)
    else:
        warn("git 通道 %d 次都连不上 %s。" % (TRIES, REPO))
        warn("  结论：国内 -> GitHub 的两条通道（API / git）都断了。")
        warn("  这不阻塞探针：结果仍在 Codeup 的 results/ 里，")
        warn("  改用「本机中转」把数据搬到主仓即可（见 CI_RECOVERY.md）。")
        st.update(status="fail-both", ok=False,
                  detail="API 与 git 两条通道都不通 github.com")
        return 0

    rc, out = run([git] + auth + ["clone", "--depth", "1", "--branch", BRANCH,
                                  url, work], timeout=600)
    if rc != 0:
        warn("git clone 失败：%s" % out.strip()[:200])
        st.update(status="fail-git-clone", ok=False,
                  detail="git clone 失败：%s" % out.strip()[:200])
        return 0

    try:
        dst = os.path.join(work, "state", "probe_cnci_latest.json")
        old_ts = stamp_of(dst) if os.path.exists(dst) else ""
        if old_ts and old_ts > new_ts and not force:
            say("远端已有更新的数据（%s > %s），跳过，不覆盖" % (old_ts, new_ts))
            st.update(status="skipped-newer", ok=False, channel="git",
                      detail="主仓已有更新数据 %s > %s（护栏，非故障）" % (old_ts, new_ts))
            return 0

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        arch = os.path.join(work, "results", os.path.basename(arch_rel))
        os.makedirs(os.path.dirname(arch), exist_ok=True)
        shutil.copy2(src, arch)
        say("写入 %s + %s" % (latest_rel, arch_rel))

        run([git, "config", "user.name", "cnci-probe"], cwd=work)
        run([git, "config", "user.email", "cnci-probe@users.noreply.github.com"], cwd=work)
        rc, out = run([git, "add", "-A", "state", "results"], cwd=work)
        if rc != 0:
            warn("git add 失败：%s" % out.strip()[:160])
            st.update(status="fail-git-add", ok=False, detail=out.strip()[:200])
            return 0
        rc, out = run([git, "commit", "-m", "cnci 探针 %s" % stamp], cwd=work)
        if rc != 0:
            # 「无变化」不是错误：数据一模一样说明上一轮已经推上去了
            if "nothing to commit" in out or "无文件 to commit" in out \
                    or "nothing added to commit" in out:
                say("内容无变化，上一轮已推过")
                st.update(status="ok-git-dup", ok=True, channel="git",
                          detail="内容与主仓一致（上一轮已推过）")
                return 0
            warn("git commit 失败：%s" % out.strip()[:200])
            st.update(status="fail-git-commit", ok=False, detail=out.strip()[:200])
            return 0

        for i in range(TRIES):
            rc, out = run([git] + auth + ["push", "origin",
                                          "HEAD:%s" % BRANCH], cwd=work, timeout=300)
            if rc == 0:
                say("git 通道已推回主仓 %s:%s" % (REPO, BRANCH))
                st.update(status="ok-git", ok=True, channel="git", detail="push ok",
                          files=[{"path": latest_rel, "ok": True, "why": "git"},
                                 {"path": arch_rel, "ok": True, "why": "git"}])
                return 0
            warn("git push 第 %d 次失败：%s" % (i + 1, out.strip()[:160]))
            if i + 1 < TRIES:
                time.sleep(GAP)
        warn("git 通道推送失败，不影响本轮探针结果（已存在 Codeup 的 results/ 里）")
        st.update(status="fail-git-push", ok=False, channel="git",
                  detail=out.strip()[:200])
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    _st = {}
    try:
        sys.exit(main(_st))
    except Exception as e:
        # 这一层的存在意义就是「不因推主仓而让流水线变红」，所以连异常也要吞掉。
        # 但必须**分得清**两类失败，否则排查时会往错的方向跑：
        #   · 网络/鉴权失败 -> 该去查连通性、换令牌
        #   · 脚本自身 bug -> 该改代码（本文件曾栽过：调用点写成小写 repo，
        #     NameError 被这里吞掉，输出与「连不上」几乎一样）
        # 所以这里用醒目的前缀区分，并把 traceback 一起打出来。
        import traceback
        print("[push-main] " + "!" * 62)
        warn("脚本自身错误（不是网络问题、不是令牌问题）—— 请改代码：")
        print("[push-main] " + traceback.format_exc().replace("\n", "\n[push-main] "))
        print("[push-main] " + "!" * 62)
        _st.update(status="script-error", ok=False, detail=repr(e))
        sys.exit(0)
    finally:
        # ⚠ 留痕放在 finally：所有提前 `return 0` 的路径也要落文件，
        #   否则「没有留痕」会被误读成「脚本根本没跑」。
        record_status(_st)
        commit_status()