# clash-source 运行报告

- 生成时间：2026-11-01 06:23:33（UTC 记录：2026-11-01T06:23:31Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、clashdaily、leilaomi、ssrsub、ruk1ng001、shaoyouvip |
| 备用 | 不自动竞速，手动切 | autojiedian |
| 观察 | 本机实测不达标 | snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| autojiedian | 8.4% | 位置敏感（本机 8.4%/云效 5.2%） |
| automerge | 25.6% | 本机 25.6% |
| clashdaily | 38.0% | 本机 38.0% |
| ermaozi | 8.2% | 本机 8.2% |
| leilaomi | 37.7% | 本机 37.7% |
| nomorewalls | 25.8% | 本机 25.8% |
| ruk1ng001 | 29.6% | 本机 29.6% |
| shaoyouvip | 26.9% | 本机 26.9% |
| snakem982 | 3.7% | 本机 3.7% 低于 8% |
| ssrsub | 33.7% | 本机 33.7% |
| yypool | 15.7% | 本机 15.7% |
| zhuhaiuk | 42.2% | 本机 42.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1250 | 900 | 9 簇 / 26 节点 | 否 | - | - |
| automerge | 494 | 171 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 558 | 449 | 5 簇 / 16 节点 | 否 | - | - |
| zhuhaiuk | 33 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 384 | 30 簇 / 79 节点 | 否 | auto | - |
| snakem982 | 60 | 29 | 4 簇 / 31 节点 | 否 | 观察 | - |
| nomorewalls | 427 | 147 | 2 簇 / 11 节点 | 否 | - | - |
| autojiedian | 410 | 397 | 2 簇 / 2 节点 | 否 | 备用 | - |
| shaoyouvip | 13 | 13 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 76 | 1 簇 / 2 节点 | 否 | auto | - |
| leilaomi | 99 | 66 | 4 簇 / 4 节点 | 否 | auto | - |

合计产出 **2849** 节点（合并池 2849）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 928 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 586 节点，剔除 26 节点（9 个簇）；理由 TOP：广告位克隆，订阅地址本身，广告引流节点，占位符节点
- **automerge**：审 182 节点，剔除 11 节点（2 个簇）；理由 TOP：广告引流节点，群组引流节点
- **ermaozi**：审 429 节点，剔除 16 节点（5 个簇）；理由 TOP：引流广告节点，意大利节点servervisa，疑似伪装，群组引流，伪装美国代理池，每日配置频道引流
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 223 节点，剔除 79 节点（30 个簇）；理由 TOP：广告引流簇，广告/引流节点
- **snakem982**：审 60 节点，剔除 31 节点（4 个簇）；理由 TOP：域名含营销特征，server疑似境内，server非IP地址
- **nomorewalls**：审 158 节点，剔除 11 节点（2 个簇）；理由 TOP：广告节点，广告引流
- **autojiedian**：审 379 节点，剔除 2 节点（2 个簇）；理由 TOP：promo促销域名，staging测试域名
- **shaoyouvip**：审 13 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 2 节点（1 个簇）；理由 TOP：Cloudflare CDN占位符
- **leilaomi**：审 70 节点，剔除 4 节点（4 个簇）；理由 TOP：免费伊朗营销位，占位符名

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
