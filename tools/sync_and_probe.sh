#!/usr/bin/env bash
# ============================================================================
#  云端探针入口：同步代码 -> 跑探针 -> 提交结果
#
#  ⚠ 为什么必须重试同步（2026-10-15 实测踩到）：
#    云效 Codeup 的 git 端点**间歇性**对已鉴权请求回 302 跳 SSO 登录页。
#    实测存在「好窗口 / 坏窗口」快速交替，同一有效令牌、同样参数：
#      18:00 成功 → 18:21 连续 10 次全败 → 18:40 连续 4 次全成
#      → 18:42 连续 8 次全败 → 18:52 连续 3 次全成 → 18:53 连续 5 次全败
#    裸 git 报出来的是 `502 Bad Gateway` 或 `Failed to connect ... port 80`
#    （因为它跟着 302 跳到了 http://），**极具误导性** —— 真因是服务端抖动，
#    不是凭据问题、更不是网络问题。
#
#    所以：同步失败要**重试若干次**，而不是直接判失败。短窗口（比如 3 次）
#    骑不过一个坏窗口，会让定时任务随机红。
#
#  用法（流水线的执行命令填这一行即可）：
#      bash tools/sync_and_probe.sh
# ============================================================================
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

SYNC_TRIES="${SYNC_TRIES:-8}"
SYNC_GAP="${SYNC_GAP:-20}"      # 8 × 20s ≈ 最长 160 秒，足以骑过坏窗口
PROBE_ARGS="${*:-}"

echo "[sync] 同步代码（最多 ${SYNC_TRIES} 次，间隔 ${SYNC_GAP}s）"
ok=0
for i in $(seq 1 "$SYNC_TRIES"); do
  # 注意：不要把 git 放在 && 链里做守卫 —— `grep -c` 之类匹配数为 0 时
  # 退出码是 1，会把后面的命令掐死（这里踩过）。
  if git fetch origin && git reset --hard origin/master; then
    echo "[sync] 第 ${i} 次成功"
    ok=1
    break
  fi
  echo "[sync] 第 ${i} 次失败：云效 git 端点抖动（302→SSO），${SYNC_GAP}s 后重试"
  sleep "$SYNC_GAP"
done

if [ "$ok" -ne 1 ]; then
  echo "[sync] ${SYNC_TRIES} 次都失败。判定：云效服务不可用或凭据失效。"
  echo "[sync] 排查："
  echo "       1) 浏览器打开 https://myxk-cn-shenzhen.devops.aliyuncs.com 能登录吗"
  echo "       2) 本机跑 python tools/codeup_auth.py —— 成功=凭据没问题，纯抖动，等会儿再跑"
  echo "       3) 令牌真失效的信号：连续多次跑都失败，且网页端也登不上"
  exit 1
fi

# 顺带打一份"确实是新代码"的凭据，避免跑在旧副本上（云效复用带缓存的 workspace）
if grep -q capture_output probe.py 2>/dev/null; then
  echo "[sync] ⚠ probe.py 里仍有 capture_output=（Python 3.7+，而云效集群是 3.6.8）"
  echo "[sync]   说明拉到的是旧代码，探针会失败。检查是否忘了 git reset。"
  exit 1
fi

echo "[sync] 校验通过，开始探针"
exec python3 ci_probe_run.py $PROBE_ARGS