# clash-source 运行报告

- 生成时间：2026-10-31 10:03:47（UTC 记录：2026-10-31T10:03:44Z）
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
| yypool | 1267 | 900 | 18 簇 / 39 节点 | 否 | - | - |
| automerge | 398 | 121 | 3 簇 / 13 节点 | 否 | - | - |
| ermaozi | 482 | 352 | 43 簇 / 82 节点 | 否 | - | - |
| zhuhaiuk | 28 | 23 | 4 簇 / 4 节点 | 否 | auto | - |
| ssrsub | 171 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 399 | 27 簇 / 71 节点 | 否 | auto | - |
| snakem982 | 63 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 367 | 116 | 5 簇 / 14 节点 | 否 | - | - |
| autojiedian | 394 | 375 | 4 簇 / 8 节点 | 否 | 备用 | - |
| shaoyouvip | 16 | 16 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 146 | 121 | 0 节点 | 否 | auto | - |

合计产出 **2731** 节点（合并池 2731）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- shaoyouvip AI 剔除超阈值，已整体回滚
- yypool 产出 970 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 599 节点，剔除 39 节点（18 个簇）；理由 TOP：广告引流位，广告/引流节点，关网占位符，IP疑似境内中转
- **automerge**：审 134 节点，剔除 13 节点（3 个簇）；理由 TOP：server字段为速度单位，server字段为占位符，广告引流节点
- **ermaozi**：审 415 节点，剔除 82 节点（43 个簇）；理由 TOP：广告位，同源克隆节点，营销伪装节点，广告引流信息，引流广告
- **zhuhaiuk**：审 27 节点，剔除 4 节点（4 个簇）；理由 TOP：伪装多国实为同地
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 71 节点（27 个簇）；理由 TOP：dokng.com广告引流，同簇克隆节点
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 130 节点，剔除 14 节点（5 个簇）；理由 TOP：speed节点为广告位，引流广告节点，占位符server
- **autojiedian**：审 373 节点，剔除 8 节点（4 个簇）；理由 TOP：占位符域名，占位符服务器地址，广告位/引流节点，含promo推广域名
- **shaoyouvip**：审 16 节点，剔除 0 节点（超阈值已回滚）
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 121 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
