# clash-source 运行报告

- 生成时间：2026-10-31 12:43:20（UTC 记录：2026-10-31T12:43:19Z）
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
| autojiedian | 8.4% | 位置敏感（本机 8.4%/云效 7.6%） |
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
| yypool | 1267 | 900 | 21 簇 / 49 节点 | 否 | - | - |
| automerge | 398 | 123 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 412 | 216 | 22 簇 / 123 节点 | 否 | - | - |
| zhuhaiuk | 31 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 171 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 454 | 4 簇 / 16 节点 | 否 | auto | - |
| snakem982 | 60 | 60 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 385 | 86 | 4 簇 / 17 节点 | 否 | - | - |
| autojiedian | 394 | 376 | 4 簇 / 7 节点 | 否 | 备用 | - |
| shaoyouvip | 12 | 12 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 77 | 1 簇 / 1 节点 | 否 | auto | - |
| leilaomi | 146 | 113 | 8 簇 / 8 节点 | 否 | auto | - |

合计产出 **2614** 节点（合并池 2614）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 960 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 599 节点，剔除 49 节点（21 个簇）；理由 TOP：广告位克隆，流量已用完，server非真实地址，server为域名，疑似占位，营销域名
- **automerge**：审 134 节点，剔除 11 节点（2 个簇）；理由 TOP：广告位，占位符服务器
- **ermaozi**：审 339 节点，剔除 123 节点（22 个簇）；理由 TOP：同源克隆，伪装为境内中转，群组引流，境内中转IP，占位符示例
- **zhuhaiuk**：审 29 节点，剔除 0 节点
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 16 节点（4 个簇）；理由 TOP：营销域名，marketplace广告位
- **snakem982**：审 60 节点，剔除 0 节点
- **nomorewalls**：审 103 节点，剔除 17 节点（4 个簇）；理由 TOP：速度占位符，广告引流/伪装
- **autojiedian**：审 373 节点，剔除 7 节点（4 个簇）；理由 TOP：日本节点伪装，占位符域名，server为占位域名
- **shaoyouvip**：审 12 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 1 节点（1 个簇）；理由 TOP：印度节点伪装为境内中转
- **leilaomi**：审 121 节点，剔除 8 节点（8 个簇）；理由 TOP：批量克隆营销位，伪装伊朗营销位，占位符示例

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
