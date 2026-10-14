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

## AI 阶段：多后端 + 簇级审核

### 为什么按「簇」审而不是按「节点」审

免费源里同一条目会有几十到几百个克隆位。实测 12 源 4831 个节点归一后只有 **1683 个簇**（2.9x），
其中 **92 个 ≥8 节点的簇覆盖了 2321 个节点（一半）**：

```
passcro / ermaozi / automerge / nomorewalls / yypool   "ro speednode"  ×118
autojiedian   "美国 reston cloudflare, inc. claude"    ×104
autojiedian   "claude"                                 ×76
yypool        "[free ] 未知"                           ×63
```

单节点审要 165 次调用；簇级审（`--ai-unit cluster`，默认）约 **26 次**——AI 判一次整簇清掉。

### 多后端故障转移

`src/ai_backends.yaml` 里配顺序，某个后端连续失败（429 / 超时 / 非 JSON）自动切下一个：

| 顺序 | 后端 | 实测 |
|---|---|---|
| 1 | 硅基流动 `Qwen/Qwen3-8B` | 首选，非推理模型，0.7s 级响应 |
| 2 | 硅基流动 `XingChenAGI/Xing4.0-29B` | 推理模型，思维链吃 token，`finish_reason=length` 会截断 JSON → 自动放大 max_tokens 重试 |
| 3 | OpenRouter `google/gemma-4-31b-it:free` | 末位备份，免费共享池常 429；国内可直连 |

### AI 能做什么、不能做什么

| | |
|---|---|
| ✅ 抓正则抓不到的语义垃圾 | `防范境外势力渗透` ×290 —— 正则在这些名字上一个关键词都匹配不上，AI 一次识别整簇清掉 |
| ✅ 删同族冗余克隆位 | `RO 02` = `RO 01` 的克隆（IP 差 1） |
| ✅ 不被「广告字样」骗 | prompt 里写死了反例：`🇮🇩 机场推荐:dafei.de 印尼 01` 是**可用节点**（实测 44% 通过率），必须保留 |
| ❌ **不能提高可用率** | 连通性只能靠真探针测，CI 跑在美国机。AI 只减冗余、不增供给 |

### 安全护栏（都实测触发过）

- **只输出要删的**：`{"drop":[{"c":簇号,"why":"≤12字"}]}`。让 pass 保持默认——早期协议让模型逐条输出 keep，一批 4.5k token，90s 超时直接全废（真烧钱且零效果）
- **比例熔断**：单源判掉 >60% 节点 → 整体回滚，防模型误读
- **fail-soft 到单 chunk**：某批失败只影响那批，其余照常；全部批次都失败才算「AI 不可用」
- **逐条留痕**：`reports/ai_dropped.md` 记录每簇节点名/类型/server/理由/簇大小。发现误杀就把节点名贴回来，针对性收窄 prompt

### 调参

```bash
AI_UNIT=cluster|node      # 簇级(默认) / 单节点(对照)
AI_MAX_CLUSTERS=150       # 每源送审簇数上限（按簇大小降序取前 N）
AI_CLUSTER_CHUNK=30       # 每批簇数
AI_CONCURRENCY=3          # 并发路数
AI_TIMEOUT / AI_RETRIES   # 全局覆盖后端自带配置
```

额度参考：L0（TPM 50k / RPM 1000）下簇级方案约占 TPM **4%**。**瓶颈从来不是 token，是上游延迟**
（实测故障全是 `RemoteDisconnected` / `read timeout` / `429 shared pool`），所以优化方向是并发 + 快速换后端。

### 接新后端

编辑 `src/ai_backends.yaml` 加一条，`env_key` 指定环境变量名，key **只放环境变量 / Actions secrets，不进仓库**。

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