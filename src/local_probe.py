# -*- coding: utf-8 -*-
"""本机（国内）真探针 —— 提供**可信口径**的质量数据，然后推回仓里。

为什么必须是「国内」（2026-10-14 实测校准；频率见第 3 点）：

  1) 国内口径不可替代。CI runner 在美国，同一批节点从美国看通过率系统性虚高
     1.8~13 倍，Spearman 秩相关只有 0.48，排名基本不可信：

         源            美国     国内     倍数    名次变化
         shaoyouvip   81.2%    6.2%    13.0x   #4  -> #11（垫底）
         yypool       84.3%   13.1%     6.4x   #2  -> #7
         anaer        78.6%   42.9%     1.8x   #5  -> #1（最好）

  2) 但国内口径**只能判优、不能判死**。从国内发起的 alive=0 是歧义的：
     节点真死了？或者它的 IP 被 GFW 阻断、我根本连不上？数据上一模一样。
     所以「降级」永远交给美国 CI（它能直连全球节点 IP）。
     —— 推论：**即使买台国内服务器，也只能把判优搬过去，判死仍得留在 CI。**

  3) 频率：计划任务是**每天 12:30**（2026-10-16 核对 schtasks）。
     早先（10-14）曾论证「每周一次足够」，理由是源质量是周/月尺度变量 ——
     但现在分级、AUTO 排序、节点稳定性档案全都吃本机口径的多轮均值，
     每天一轮才让这些数据保持新鲜；sni 修掉后全量一轮约 9 分钟，成本可忽略。

  4) **hc_timeout 一律保持 8000ms 默认值，别为了快调小**。
     它直接线性偏置 alive（shaoyouvip 实测：3s->0 活、8s->4 活、15s->6 活），
     调小等于批量制造假死亡。国内全量一轮约 9 分钟（2026-10-16 实测 8.7 分钟、
     12/12 源全测完）。真要省时间就用 `--sample 30`（实测 76 秒跑完 12 源且全部
     settle），那是「少测点」而不是「测得不实」。

用法：
    python src/local_probe.py                # 探针 + 健康档案 + 推回 GitHub
    （计划任务 \clash-source-local-probe 用 pythonw 直跑本脚本，无窗；
      run_local_probe.cmd 仅剩手动用途，效果相同）
    python src/local_probe.py --no-push      # 只探针，不推送
    python src/local_probe.py --scope-only   # 跳过探针，只把已有结果存档/推送

自愈能力（2026-10-24）：
  - 静默化：所有子进程挂 CREATE_NO_WINDOW，pythonw 计划任务时段不再弹窗。
  - 推送三连败 -> rescue_push()：积压轮次留证 -> 临时克隆里逐轮重放
    health.py（is_dup_run 去重，幂等）-> 补推 -> 真实工作区对齐远端。
    成功前真实工作区一动不动；失败大声退出、下轮探针自动再试
    （背景：10-21~10-24 推送竞态连堵四天，最老积压提交永远重放不上去的死锁）。

产出：state/probe_latest.json (scope=local) + state/source_health.json + reports/
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GIT = r"D:\work\agent\codebuddy\portable-git\bin\cmd\git.exe"

# ⚠ 静默化（2026-10-24 用户反馈「推送时段弹窗刷屏，影响工作」）：
#   计划任务是 pythonw（GUI 子系统，无控制台），但它起的**每个控制台子进程**
#   （git.exe / python.exe / verge-mihomo.exe）Windows 都会给它新开一个控制台
#   窗口 —— 探针时的 mihomo、健康档案时的 python、推送撞车重试时的 3×N 个
#   git，全是弹窗来源。CREATE_NO_WINDOW 让所有子进程继承无窗状态。
#   用 getattr 兜底：非 Windows（CI 的 Linux runner）没有这个常量，取 0 正好
#   等于默认值，POSIX 上 creationflags=0 合法。
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ⚠ pythonw（计划任务静默跑）下 sys.stdout/stderr 是 None，print 直接炸。
#   接到文件上：本脚本的 print 与子进程（probe.py 继承句柄）都落到这里。
if sys.stdout is None or sys.stderr is None:
    _d = os.path.join(ROOT, "logs")
    os.makedirs(_d, exist_ok=True)
    _f = open(os.path.join(_d, "local_probe_stdout.log"), "a",
         encoding="utf-8", buffering=1)   # 文本+行缓冲：print 写 str 才不炸
    sys.stdout = _f
    sys.stderr = _f
PROXY = "http://127.0.0.1:7897"          # github.com 直连被墙，push 必须走代理


def run_probe(args):
    """真探针。注意每次先清空装置目录 —— mihomo 的 -d 会残留上次文件。"""
    probe_dir = os.path.join(ROOT, ".probe")
    if os.path.isdir(probe_dir):
        shutil.rmtree(probe_dir, ignore_errors=True)
    env = dict(os.environ)
    env["PROBE_SCOPE"] = "local"
    # ⚠ 子进程 probe.py 没有守卫 —— 把父进程重定向后的句柄递给它，
    #   否则计划任务（pythonw）下子进程的 print 会直接炸掉整轮。
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "probe.py"),
         "--mihomo", args.mihomo, "--scope", "local",
         "--budget", str(args.budget),
         "--out", os.path.join(ROOT, "state", "probe_latest.json")],
        env=env, cwd=ROOT, creationflags=NOWIN,
        stdout=sys.stdout, stderr=subprocess.STDOUT).returncode


def _nothing_to_commit(out):
    """git 的「无内容可提交」有两种措辞，漏挡一种就会把正常当失败。"""
    low = out.lower()
    return ("nothing to commit" in low
            or "no changes added to commit" in low
            or "working tree clean" in low)


PUSH_TRIES = 3      # 与 CI 侧 tools/ci_git_push.sh 保持一致
PUSH_GAP = 5        # 重试间隔（秒）；测试里设成 0


def _rebase_abort():
    """清掉可能残留的 rebase 中间态；真清掉了才返回 True（没有时是 no-op）。

    ⚠ 为什么每轮尝试前都要清（§75 #9）：`git pull --rebase` 撞冲突会停在
    rebase-merge/ 中间态，此时 `git add -A`（下一轮的第一步）会把冲突标记
    （<<<<<<<）当内容暂存，或直接以 "cannot commit" 失败 ——
    **本机数据从此再也推不上去**，而日志里只剩一句「rebase 失败」看不出真因。
    失败方向必须是「这轮推不上去、下轮还能推」，绝不能是「仓库卡死」。
    """
    p = subprocess.run([GIT, "rebase", "--abort"], cwd=ROOT,
                       capture_output=True, text=True, timeout=60,
                       creationflags=NOWIN)
    return p.returncode == 0


# ── 三连败后的自动救援：「克隆-合并-补推」，成功前不动真实工作区 ─────────
# 背景（2026-10-24 实撞四连堵）：push 被拒 -> pull --rebase 重放最老的积压提交
# -> state/source_health.json 是「两边各自追加行」的文件，文本合并必冲突 ->
# abort。于是最老那个积压提交**永远**重放不上去，之后每天的探针都从它开始撞
# —— 积压一天天滚大（10-21~10-24 四天四轮全是这个死法，人工逐轮合并才解）。
#
# 解法照搬人工剧本，但有两处关键差异：
#   ① 在 **--depth 1 的临时克隆**里做，成功前真实工作区与本地提交一动不动，
#     （失败方向只能是「这轮没救成」，绝不可能是「仓库被拆」——这也是
#      tools/test_local_probe_push.py 能把失败路径测准的原因）；
#   ② health.py 的 is_dup_run 按 (ts, scope) 去重，逐轮重放天然幂等。
# 成功后再把真实工作区 reset --hard 到远端：内容已全部进入远端树。
RESCUE_TRIES = 2        # 整条「克隆-合并-补推」链的尝试轮数（远端中途又动了就再来一轮）
STASH_DIR = os.path.join(tempfile.gettempdir(), "clash_source_rescue")


def _run_health(cwd):
    """在指定仓库目录里跑 health.py，返回 (exit, 合并输出)。

    ⚠ 独立成模块级函数是为了护住测试的地基：tools/test_local_probe_push.py
    测试环境没有真实探针数据，把僵尸依赖绑在 health 的容错行为上会让用例
    结果变得不可预测；换桩后（测试里替换 local_probe._run_health）救援的
    git 编排可以独立测真。
    """
    p = subprocess.run([sys.executable, os.path.join(cwd, "src", "health.py")],
                       cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600,
                       creationflags=NOWIN)
    return p.returncode, ((p.stdout or "") + (p.stderr or ""))


def _stash_stuck(stuck):
    """把积压提交里真正有用的材料留证到 STASH_DIR（系统临时目录，reset 不砸）。

    返回 (days, ns_path)：
      days    = [(sha7, 留证文件路径, 短标), ...]（从老到新；短标优先用
                probe 文件里的 probed_at 日期，取不到就用 sha 前 7 位）
      ns_path = 最新一版 node_stability.json 的留证（本机口径专属，远端
                从不写它 -> 本地版必是全量真相；不存在时为 None）
    单轮损坏（JSON 解析不了）只跳过那轮并大声说明 —— 绝不因一轮坏了
    放弃全部：剩下的轮次在 health 合并里同样有价值。
    """
    os.makedirs(STASH_DIR, exist_ok=True)
    days = []
    for sha in stuck:
        bp = subprocess.run([GIT, "cat-file", "blob",
                             "%s:state/probe_latest.json" % sha],
                            cwd=ROOT, capture_output=True, timeout=60,
                            creationflags=NOWIN)
        if bp.returncode != 0:
            print("[rescue]   ⚠ %s 里没有 state/probe_latest.json：这轮只能放弃" % sha[:7])
            continue
        try:
            j = json.loads(bp.stdout.decode("utf-8"))
        except Exception as e:
            print("[rescue]   ⚠ %s 的探针文件不是合法 JSON（%s）：只能放弃该轮" % (sha[:7], type(e).__name__))
            continue
        fp = os.path.join(STASH_DIR, "probe_%s.json" % sha[:7])
        try:
            with open(fp, "wb") as f:
                f.write(bp.stdout)
        except Exception as e:
            print("[rescue] ✗ 留证写盘失败（%s）：%s" % (fp, str(e)[:80]))
            return [], None
        ts = str(j.get("probed_at") or "")
        stamp = ts[:10].replace("-", "") if ts else sha[:7]
        days.append((sha[:7], fp, stamp))
        print("[rescue]   留证 %s -> %s（%d B）" % (stamp, os.path.basename(fp), len(bp.stdout)))
    np = subprocess.run([GIT, "cat-file", "blob", "HEAD:state/node_stability.json"],
                        cwd=ROOT, capture_output=True, timeout=60, creationflags=NOWIN)
    if np.returncode != 0:
        print("[rescue]   ⚠ 本地没有 node_stability.json（老版本仓库？跳过稳定性档案恢复）")
        return days, None
    ns_path = os.path.join(STASH_DIR, "node_stability_newest.json")
    with open(ns_path, "wb") as f:
        f.write(np.stdout)
    return days, ns_path


def rescue_push():
    """推送三连败后的自动救援。返回 0=救成；None=无事可救/没救成。

    每一步失败都**大声**说明并把材料留在原地：真实工作区不动、本地积压提交
    还在，下一轮探针一来材料齐整，可以从头再救（health 的去重保证重救不脏）。
    """
    try:
        fetched = False
        for i in range(4):
            cmd = ([GIT] + (["-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY]
                            if i < 3 else []) + ["fetch", "origin", "main"])
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               timeout=120, creationflags=NOWIN)
            if p.returncode == 0:
                fetched = True
                break
            time.sleep(2)
        if not fetched:
            print("[rescue] ✗ 远端基点拿不到（fetch 4 连败）：先不救，材料留在本地")
            return None
        p = subprocess.run([GIT, "rev-list", "--reverse", "origin/main..HEAD"],
                           cwd=ROOT, capture_output=True, text=True,
                           timeout=60, creationflags=NOWIN)
        stuck = p.stdout.split()
        if not stuck:
            print("[rescue] 无积压提交（这轮推送失败另有原因，不涉及历史冲突）")
            return None
        print("[rescue] 积压 %d 个提交，开始自动救援（留证 -> 克隆 -> 逐轮合并 -> 补推）" % len(stuck))
        days, ns_path = _stash_stuck(stuck)
        if not days:
            print("[rescue] ✗ 找不出任何一轮可解析的探针数据，放弃（需人工从 git 对象抠）")
            return None
        up = subprocess.run([GIT, "config", "--get", "remote.origin.url"], cwd=ROOT,
                            capture_output=True, text=True, timeout=60, creationflags=NOWIN)
        url = (up.stdout or "").strip()
        if not url:
            print("[rescue] ✗ 拿不到 remote.origin.url，放弃")
            return None
        stamps = [d[2] for d in days]
        rng = (stamps[0] if len(stamps) == 1
               else "%s~%s" % (stamps[0], stamps[-1]))
        IDENT = ["-c", "user.name=local-probe-bot",
                 "-c", "user.email=local-probe-bot@users.noreply.github.com"]
        for attempt in range(1, RESCUE_TRIES + 1):
            clone_dir = tempfile.mkdtemp(prefix="clash_rescue_%d_" % attempt)
            cp = subprocess.run(
                [GIT, "-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
                 "clone", "--depth", "1", "-b", "main", url, clone_dir],
                cwd=ROOT, capture_output=True, text=True, timeout=600,
                creationflags=NOWIN)
            if cp.returncode != 0:
                print("[rescue] 第 %d/%d 轮 clone 失败: %s"
                      % (attempt, RESCUE_TRIES, (cp.stderr or "?").strip().splitlines()[-1][:120]))
                continue
            print("[rescue] 第 %d/%d 轮：克隆就绪，开始逐轮合并" % (attempt, RESCUE_TRIES))
            ok = True
            for sha7, fp, stamp in days:
                shutil.copyfile(fp, os.path.join(clone_dir, "state", "probe_latest.json"))
                rc, out = _run_health(clone_dir)
                if rc != 0:
                    print("[rescue] ✗ 克隆里 health.py 对 %s 失败（exit=%d）：%s"
                          % (stamp, rc, ("\n".join((out or "").splitlines()[-2:]))[:200]))
                    ok = False
                    break
                print("[rescue]   并入 %s（%s）" % (stamp, sha7))
            if not ok:
                continue
            if ns_path:
                shutil.copyfile(ns_path, os.path.join(clone_dir, "state", "node_stability.json"))
            add = [GIT, "add", "-A", "state", "archive", "src/sources.yaml", "reports"]
            commit = ([GIT] + IDENT
                      + ["commit", "-m", "chore: 本机探针(国内口径)补推 %s（%d 轮合并，"
                                         "推送竞态自动救援）" % (rng, len(days))])
            for c in (add, commit):
                p = subprocess.run(c, cwd=clone_dir, capture_output=True, text=True,
                                   timeout=180, creationflags=NOWIN)
                out = (p.stdout + p.stderr).strip()
                if p.returncode != 0 and not _nothing_to_commit(out):
                    print("[rescue] ✗ 克隆里步骤失败: %s %s"
                          % (" ".join(c[:2]), out.splitlines()[-1][:120] if out else ""))
                    ok = False
                    break
            if not ok:
                continue
            cpush = [GIT, "-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
                     "push", "origin", "HEAD:main"]
            cpull = ([GIT] + IDENT
                     + ["-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
                        "pull", "--rebase", "--autostash", "origin", "main"])
            pushed = False
            for pt in (1, 2):
                p = subprocess.run(cpush, cwd=clone_dir, capture_output=True,
                                   text=True, timeout=180, creationflags=NOWIN)
                if p.returncode == 0:
                    pushed = True
                    break
                print("[rescue]   补推第 %d/2 次被拒: %s"
                      % (pt, (p.stdout + p.stderr).strip().splitlines()[-1][:120]))
                if pt == 1:
                    pr = subprocess.run(cpull, cwd=clone_dir, capture_output=True,
                                        text=True, timeout=180, creationflags=NOWIN)
                    if pr.returncode != 0:
                        subprocess.run([GIT, "rebase", "--abort"], cwd=clone_dir,
                                       capture_output=True, timeout=60, creationflags=NOWIN)
                        print("[rescue]   克隆里 rebase 失败：换新一轮重试")
                        break
            if not pushed:
                continue
            # 远端已接受补推：把真实工作区对齐远端（若这步失败也只是下轮多救一次，
            # health 的去重保证重救不会产生重复行 —— 死锁已破）。
            _rebase_abort()
            sf = subprocess.run([GIT, "fetch", "origin", "main"], cwd=ROOT,
                                capture_output=True, text=True, timeout=120,
                                creationflags=NOWIN)
            if sf.returncode != 0:
                sf = subprocess.run([GIT, "-c", "http.proxy=" + PROXY,
                                     "fetch", "origin", "main"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=120,
                                    creationflags=NOWIN)
            if sf.returncode == 0:
                subprocess.run([GIT, "reset", "--hard", "origin/main"], cwd=ROOT,
                               capture_output=True, timeout=60, creationflags=NOWIN)
            print("[rescue] ✅ 自动救援成功：%d 轮（%s）已并档补推%s"
                  % (len(days), rng,
                     "，工作区已对齐远端" if sf.returncode == 0
                     else "；⚠ 工作区对齐失败（下轮会靠去重重救，不产生重复数据）"))
            return 0
        print("[rescue] ✗ 自动救援 %d 轮未成：真实工作区未动、本地提交还在、留证在 %s"
              "（下轮探针会再试）" % (RESCUE_TRIES, STASH_DIR))
        return None
    except Exception as e:
        print("[rescue] ✗ 救援内部异常（绝不波及主流程）：%s: %s" % (type(e).__name__, str(e)[:120]))
        return None


def push_to_github():
    """把健康数据推回 main。CI 也会推 dist，两边并发时 push 会失败 -> rebase 重试。"""
    if not os.path.exists(GIT):
        print("[local] 未找到 portable-git，跳过推送: %s" % GIT)
        return 0
    stamp = time.strftime("%Y%m%d-%H%M")
    add = [GIT, "add", "-A", "state", "archive", "src/sources.yaml", "reports"]
    # ⚠ 身份必须随身带（不只给 commit 用）：`pull --rebase` **重放**提交时同样
    #   需要 committer 身份。只靠仓库/全局 user.* 的话，换机器、重克隆、或用别的
    #   账号跑计划任务时，rebase 会 `fatal: unable to auto-detect email address`
    #   —— 重试三次全废，而最后的提示指向「代理没开或 PAT 过期」，完全指错方向。
    #   （2026-10-18 由 tools/test_local_probe_push.py 的真竞态用例抓到。）
    IDENT = ["-c", "user.name=local-probe-bot",
             "-c", "user.email=local-probe-bot@users.noreply.github.com"]
    commit = [GIT] + IDENT + ["commit", "-m", "chore: 本机探针(国内口径) %s" % stamp]
    push = [GIT, "-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
            "push", "origin", "main"]
    # ⚠ --autostash 是必需的（2026-10-15 实踩）：
    #   工作区只要有**未暂存**改动，`git pull --rebase` 就会直接拒绝
    #   （cannot pull with rebase: You have unstaged changes），
    #   于是「push 被拒 -> rebase -> 重试」的重试链必然二次失败，
    #   结果本地健康数据永远传不上去，而且日志里看不出真正原因。
    pull = ([GIT] + IDENT
            + ["-c", "http.proxy=" + PROXY, "-c", "https.proxy=" + PROXY,
               "pull", "--rebase", "--autostash", "origin", "main"])
    for c in (add, commit):
        p = subprocess.run(c, cwd=ROOT, capture_output=True, text=True,
                           timeout=180, creationflags=NOWIN)
        out = (p.stdout + p.stderr).strip()
        if out:
            print("  " + out.splitlines()[-1][:150])
        # ⚠ git 说「没东西可提交」有两种措辞，少挡一种就会把正常情况当失败：
        #    nothing to commit, working tree clean          （连改动都没有）
        #    no changes added to commit (use "git add" ...) （有改动但没 add）
        # 2026-10-15 实踩：只挡了前一种，计划任务每轮都误报 exit=1。
        if p.returncode != 0 and not _nothing_to_commit(out):
            print("[local] 步骤失败: %s" % " ".join(c[:3]))
            return p.returncode
    rc = 1
    last = ""
    for attempt in range(1, PUSH_TRIES + 1):
        # 每轮尝试前先清中间态：上一轮可能在 pull --rebase 撞冲突时停住过。
        # 这是「仓库卡死」的唯一入口，必须每次进门先打扫（§75 #9）。
        if _rebase_abort():
            print("  （清掉了上一轮遗留的 rebase 中间态）")
        p = subprocess.run(push, cwd=ROOT, capture_output=True, text=True,
                           timeout=180, creationflags=NOWIN)
        out = (p.stdout + p.stderr).strip()
        rc = p.returncode
        if rc == 0:
            print("  push: OK%s" % ("" if attempt == 1
                                    else "（第 %d 次尝试，重试生效）" % attempt))
            return 0
        last = out or last
        print("  push 第 %d/%d 次被拒: %s"
              % (attempt, PUSH_TRIES, out.splitlines()[-1][:150] if out else "?"))
        if attempt == PUSH_TRIES:
            break
        # 最常见原因：CI 刚推过，远端领先 -> rebase 后重试
        pr = subprocess.run(pull, cwd=ROOT, capture_output=True, text=True,
                            timeout=180, creationflags=NOWIN)
        if pr.returncode != 0:
            pout = (pr.stdout + pr.stderr).strip()
            last = pout or last
            print("  rebase 失败: %s" % (pout.splitlines()[-1][:150] if pout else "?"))
            _rebase_abort()
            print("  已 rebase --abort：工作区回到干净状态，数据仍在本地，下一轮还能推")
        if PUSH_GAP:
            time.sleep(PUSH_GAP)
    # 常规重试用完 -> 最后的自动手段：克隆-合并-补推（四连堵的教训，见 rescue_push）
    r = rescue_push()
    if r == 0:
        return 0
    # ⚠ 提示里必须带上**最后一条真实错误**：以前这里只有「多半是代理没开或 PAT
    #   过期」这一句，rebase 身份缺失/冲突这类原因会被这句话指到错误方向。
    print("[local] ⚠ 推送失败（已试 %d 次）：本地数据仍在 state/，但远端不会更新。" % PUSH_TRIES)
    print("       最后一条错误：%s" % (last.splitlines()[-1][:150] if last else "?"))
    print("       常见原因：代理(%s)没开 / PAT 过期 / rebase 身份缺失或冲突" % PROXY)
    return rc


def main():
    ap = argparse.ArgumentParser(description="本机（国内口径）真探针，计划任务每天 12:30 跑")
    ap.add_argument("--no-push", action="store_true", help="只探针，不推回 GitHub")
    ap.add_argument("--scope-only", action="store_true",
                    help="跳过探针，只跑健康档案并推送（用已有的 probe_latest.json）")
    ap.add_argument("--mihomo", default=r"C:\Program Files\Clash Verge\verge-mihomo.exe")
    ap.add_argument("--budget", type=int, default=3600, help="探针墙钟预算（秒）")
    # ⚠ 3600 的由来：2026-10-17 中午轮实测，3549 节点在中午网络下
    #   1800 秒不够（autojiedian 744/868、yypool 741/900 未测完），
    #   而机器中午闲着 —— 宁可多给一小时，也别让大源掉出当日判定。
    args = ap.parse_args()

    oplog = os.path.join(ROOT, "logs", "local_probe.log")
    os.makedirs(os.path.dirname(oplog), exist_ok=True)

    def _oplog(msg):
        # 原 run_local_probe.cmd 的职责：往 local_probe.log 记 start/done。
        # 任务改 pythonw 直跑后 .cmd 不再参与，这里接手（格式保持一致）。
        with io.open(oplog, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y/%m/%d %H:%M:%S] ") + msg + "\n")

    _oplog("start local probe (scope=local)%s"
           % ((" " + " ".join(sys.argv[1:])) if sys.argv[1:] else ""))
    if not args.scope_only:
        print("[local] 本机真探针（scope=local，国内口径）…")
        if run_probe(args) != 0:
            print("[local] 探针失败，退出（不改动健康档案）")
            return 1
    else:
        print("[local] --scope-only：复用现有 state/probe_latest.json")

    print("[local] 健康档案（国内口径只判优/回收，判死留给 CI）…")
    # ⚠ 必须**显式**把父进程（可能已被重定向到日志文件）的句柄递过去。
    #   `contextlib.redirect_stdout(buf)` 抓不到子进程 —— 它只改父进程的
    #   Python 级 sys.stdout，子进程写的是继承来的 OS 句柄，buf 恒空
    #   （那个转发循环是死代码，2026-10-18 全量审查实锤）。
    #   但**光删掉 redirect 不够**：pythonw（计划任务）下子进程继承的句柄
    #   是无效的，输出会静默消失。实测 2026-10-18 12:41 那轮
    #   logs/local_probe_stdout.log 里一个 [health] 行都没有，
    #   而 probe.py 因为 run_probe() 显式传了 stdout= 就正常 —— 同一个坑。
    # ⚠ 还要**查退出码**：health.py 崩了（例如回收分支的 NameError）
    #   会让整轮数据白丢，而原来这里不看返回码、输出又丢了 => 完全不可观测。
    hp = subprocess.run([sys.executable, os.path.join(HERE, "health.py")],
                        cwd=ROOT, stdout=sys.stdout, stderr=subprocess.STDOUT,
                        creationflags=NOWIN)
    health_rc = hp.returncode
    if health_rc != 0:
        print("[local] ⚠ health.py 失败（exit=%d）：健康档案本轮**未更新**。"
              "探针结果仍在 state/probe_latest.json，下轮探针会重跑。"
              % health_rc)

    rc = 0
    if args.no_push:
        print("[local] --no-push，跳过推送")
    else:
        rc = push_to_github()
    if health_rc != 0 and rc == 0:
        rc = health_rc                 # 健康档案失败必须反映到退出码，不能静默
    _oplog("done, exit=%d" % rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())