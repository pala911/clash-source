#!/usr/bin/env bash
# 提交并推送产物到 main —— 带重试。workflow 里四处（产物 / 健康档案 / 候选池 / 自动补员）共用。
#
# 用法: bash tools/ci_git_push.sh "<提交信息>" <路径> [<路径> ...]
#
# ⚠ 为什么必须有重试（2026-10-18 04:41 UTC 实测，不是理论风险）：
#   L2 本机探针（每天 12:30 北京时间）也在推 main。两边撞上时，一次裸
#   `git push` 会被 non-fast-forward 直接拒掉：
#       04:41:07  本机推上 078d4e7
#       04:41:32  CI 拿着 04:34:48 检出的旧基点推 -> 秒失败（exit 1）
#   而「提交产物到 main」这一步失败会让**后面 9 个步骤全部 skip**：
#       · gh-pages 不发布        -> 手机订阅最多 6 小时不更新
#       · 美国口径真探针不跑      -> **唯一有判死权的那层整层缺失**
#       · 健康档案不算不提交      -> CI 口径少攒一轮（判死要攒轮数）
#   也就是说：一次推送撞车 = 那一轮 L1 层静默消失，只看 Actions 上的红叉
#   完全看不出是「撞车」还是「探针挂了」。
#
# 策略（与 src/local_probe.py 的 push_to_github 同一套）：
#   被拒就 `git pull --rebase --autostash` 再推，最多 CI_PUSH_TRIES 次（默认 3）。
#   ⚠ 绝不 --force：远端可能有别人（本机探针）的提交，force 会把它抹掉。
#   ⚠ rebase 撞冲突时会停在中间态（§75 #9 同一个坑）：下一轮尝试前先 --abort，
#     否则后面的 `git add -A` 会把冲突标记当内容暂存，整仓从此推不上去。
#   ⚠ 三次都失败时**不让流水线变红**，改成 ::warning:: 注解 ——
#     红只会连带 skip 下游（正是上面那个后果），而这个提交还留在 workspace 里，
#     后面的步骤推的时候会把它一起带上，下一轮也会重算。
#     失败方向是「晚一轮」，不是「丢一轮」。
#
# 例行核对：本机没装 bash 也能测这条重试路径 —— tools/test_ci_workflow.py
# 会用 portable-git 的 sh.exe + 临时 git 仓库真跑一遍「先被拒、再成功」。
set -u

msg="${1:-}"
shift || true
if [ -z "$msg" ] || [ "$#" -eq 0 ]; then
  echo "[ci-push] 用法: $0 <提交信息> <路径> [<路径> ...]" >&2
  exit 2
fi

if ! command -v git >/dev/null 2>&1; then
  echo "[ci-push] 找不到 git，无法提交（这属于环境问题，不是数据问题）" >&2
  echo "::warning::找不到 git，本轮产物留在 workspace"
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# ⚠ 不能对可能不存在的目录直接 git add（2026-10-14 实测：
#   `git add -A dist reports state` 在 state/ 尚未生成时会
#   fatal: pathspec 'state' did not match any files -> 整步失败 -> 后续全 skip）
for p in "$@"; do
  git add -A -- "$p" 2>/dev/null || true
done

if git diff --cached --quiet; then
  echo "[ci-push] 本轮无变化，跳过提交"
  exit 0
fi

git commit -q -m "$msg"
branch="${GITHUB_REF_NAME:-main}"
tries="${CI_PUSH_TRIES:-3}"
gap="${CI_PUSH_GAP:-15}"

n=0
while [ "$n" -lt "$tries" ]; do
  n=$((n + 1))

  # 上一轮 rebase 可能停在中间态 —— 先回退干净再继续（否则整仓推不上去）
  if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    git rebase --abort >/dev/null 2>&1 || true
  fi

  # rebase 到远端最新再推；失败不致命，留给本轮末尾的 push 判定
  git pull --rebase --autostash origin "$branch" >/dev/null 2>&1 || true

  if git push origin "HEAD:$branch" >/dev/null 2>&1; then
    echo "[ci-push] 已推送（第 $n 次尝试）: $(git log --oneline -1)"
    exit 0
  fi

  echo "[ci-push] 推送被拒（第 $n 次 / 共 $tries 次；常见原因：本机探针同时在推 main）"
  if [ "$n" -lt "$tries" ] && [ "$gap" != "0" ]; then
    sleep "$gap"
  fi
done

echo "::warning::main 推送失败（常见原因：与本机探针撞车，或两边改了同一批生成文件而 rebase 冲突）。提交仍留在 workspace，当前/下一轮的后续步骤会把它带上；这里刻意不让流水线变红 —— 红会连带 skip 掉 gh-pages 发布与判死探针，损失比晚一轮大得多。"
exit 0
