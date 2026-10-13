# clash-source

自建 Clash 节点源仓：**定时抓取多个免费源 → 归一去重 → 硬过滤 → AI 审核 → 产出手机可直接订阅的完整 profile**。

存在意义：免费通病是「池子大 = 死节点海」。2026-10-13 实测（youtube 真探针）：

| 源 | 规模 | 通过率 |
|---|---:|---:|
| zhuhaiuk | 31 | 52% |
| ssrsub | 175 | 43% |
| ruk1ng001 | 500 | 38% |
| snakem982 | 61 | 21% |
| **ermaozi**（新） | 352 | **20%** |
| nomorewalls | 209 | 14% |
| autojiedian | 2137 | 12% |
| clashfree（新） | 611 | **0%** |
| Au1rxx（新） | 1745 | **~0%** |
| mahdibland Eternity（美机测速 200） | 201 | **0%** |

未过滤的源直接喂给手机 = 几千个死节点拖慢每次健康检查。本仓把这些收敛成几百个可用密度高的节点。

## 手机怎么用

**订阅地址（一行）**：

```
https://<你的GitHubID>.github.io/clash-source/profile.yaml
```

Clash Verge Rev（手机/PC）里新建订阅粘贴即可。备用地址（github.io 不达时）：

```
https://cdn.jsdelivr.net/gh/<你的GitHubID>/clash-source@gh-pages/profile.yaml
https://gh-proxy.com/raw.githubusercontent.com/<你的GitHubID>/clash-source/gh-pages/profile.yaml
```

**首次要在仓库设置里开一次 Pages**：Settings → Pages → Source = `gh-pages` 分支 / root。之后工作流每次会把 `dist/` 推到 gh-pages 分支根目录，URL 即上表。
不想开 Pages 也能用 —— 把工作流里的 `--ai-mode` 保留、并在 `run.py` 加 `--pages-base https://cdn.jsdelivr.net/gh/<ID>/clash-source@gh-pages` 即可（jsdelivr 免设置，国内直连实测可达）。

## profile 结构

`dist/profile.yaml` = 已实测验证过的组结构（9 月 26 日 L1~L4 降级切换测试全过的那套）：

```
PROXY → FAILOVER → [AUTO, SRC-zhuhaiuk, SRC-ruk1ng001, SRC-shaoyouvip, SRC-ssrsub,
                     SRC-nomorewalls, SRC-snakem982, SRC-autojiedian]
AUTO = [SRC-zhuhaiuk, SRC-ruk1ng001, SRC-ssrsub, SRC-nomorewalls, SRC-snakem982]
SRC-* = url-test，各挂一个本仓 dist/nodes/<源>.yaml
```

- **探针统一 `youtube.com/generate_204`**（不是 gstatic —— gstatic 国内可达会让境内中转节点假绿，见记忆坑 §27/§29）
- 每个 provider 带 `health-check`（youtube / 300s / timeout 5000）
- `rule-providers` 仍走 gh-proxy（手机侧 CN 直连可达，已验证）

## 目录

```
src/sources.yaml          上游源清单（唯一事实来源：加源/停源只改这里）
src/fetch.py              抓取（直连优先，失败自动回退 gh-proxy → jsdelivr）
src/filters.py            确定性硬过滤（协议白名单/必填字段/命名垃圾/同 server:port 去重）
src/ai_review.py          AI 审核（只输出 keep/drop 裁决，绝不改写节点字段）
src/build.py              产出 dist/（profile.yaml + nodes/*.yaml + all.yaml + manifest.json）
src/report.py             生成 reports/latest.md（漏斗统计 + 告警 + AI 摘要）
src/run.py                主入口
src/profile_template.yaml 手机 profile 模板（组结构/规则/dns，PC 专属键已剥离）
dist/                     产物（工作流提交到 main 并推 gh-pages）
reports/latest.md         每次运行的可审计报告
```

## AI 阶段的安全边界（重要）

- **AI 只做裁决，不做改写**：LLM 输出 `{序号: keep/drop, 理由}`，剔除动作由脚本按节点精确执行。改写 `server/port/uuid` 的幻觉会产出坏配置，比不过滤更糟。
- **fail-soft**：没配 key / 接口报错 / 解析失败 → 全部保留，只在报告里记警告。AI 挂了不会清空池子。
- **比例熔断**：单源 AI 剔除 > 60% 判定为模型误读 → 整体回滚该源剔除并告警。
- **双后端**：`AI_MODE=http`（任意 OpenAI 兼容接口：OpenAI/DeepSeek/通义/Moonshot）或 `opencode`（`opencode run` CLI，适合低频）。没配 `AI_BASE_URL`/`AI_API_KEY` 时自动关闭。

仓库 Secrets（Settings → Secrets）：

| 名称 | 说明 |
|---|---|
| `AI_BASE_URL` | 如 `https://api.deepseek.com`（自动补 `/v1`） |
| `AI_API_KEY` | 接口密钥 |
| `AI_MODEL` | 默认 `gpt-4o-mini` |

## 本地跑 / 验证

```powershell
python src/run.py --ai-mode off --keep-raw        # 纯规则，不需要任何 key
python src/run.py --ai-mode http --owner <你的ID>  # 带 AI 并把订阅地址填成真的
# 离线校验（-d 指向已有 geodata 目录，绕过 MMDB 联网下载）
& "C:\Program Files\Clash Verge\verge-mihomo.exe" -t -f dist\profile.yaml -d <geodata目录>
```

## 更新频率

工作流默认**每周一**（`schedule` cron），另有 `workflow_dispatch` 可随时手动触发。上游 churn 通常 2~12 小时一轮，想更鲜把 cron 改成 `'17 */6 * * *'`。注意 GitHub 会在仓库 60 天无活动后停用定时任务，而每次成功提交 `dist/` 即算活动。

## 踩过的坑（都已内置）

1. **「TCP 通」严重高估节点质量** —— Au1rxx 自测只保 TCP 存活，1745 个里 2 个能穿 youtube；所以 CI 只删明显垃圾，质量门禁永远是手机侧 youtube 探针。
2. **美机测速 ≠ 国内可用** —— mahdibland 用 GitHub Actions（美国）LiteSpeedTest 筛出的 200 个节点，国内 youtube 0% 通过。
3. **gstatic 探针假绿** —— 境内/中转节点 29ms 碾压真代理，导致「探针绿业务红」（手机 TikTok 卡顿的根因之一）。本仓探针只用 youtube。
4. **命名引流会绕过过滤** —— `ukn_dokng` 这种不含 `🇨🇳CN_` 字样的伪装出口，靠硬过滤抓不到，所以有 AI 语义复核这一层。
5. **raw.githubusercontent 手机不可达** —— 订阅与 provider 全走 `github.io`（Pages），避免 mobile 直连被墙。

## 声明

本仓仅聚合公开免费节点，供个人自用学习，请勿用于商业或违反当地法规的用途。