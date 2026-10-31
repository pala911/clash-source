# clash-source 运行报告

- 生成时间：2026-10-31 06:18:50（UTC 记录：2026-10-31T06:18:48Z）
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
| yypool | 1267 | 900 | 23 簇 / 88 节点 | 否 | - | - |
| automerge | 398 | 123 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 482 | 396 | 17 簇 / 38 节点 | 否 | - | - |
| zhuhaiuk | 28 | 21 | 1 簇 / 6 节点 | 否 | auto | - |
| ssrsub | 171 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 411 | 15 簇 / 59 节点 | 否 | auto | - |
| snakem982 | 63 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 367 | 118 | 3 簇 / 12 节点 | 否 | - | - |
| autojiedian | 355 | 340 | 2 簇 / 4 节点 | 否 | 备用 | - |
| shaoyouvip | 63 | 60 | 1 簇 / 3 节点 | 否 | auto | - |
| clashdaily | 80 | 77 | 1 簇 / 1 节点 | 否 | auto | - |
| leilaomi | 146 | 121 | 0 节点 | 否 | auto | - |

合计产出 **2797** 节点（合并池 2797）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- leilaomi AI 剔除超阈值，已整体回滚
- yypool 产出 921 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 599 节点，剔除 88 节点（23 个簇）；理由 TOP：广告位克隆，订阅地址本身，速度占位符，广告内容，疑似营销网站
- **automerge**：审 134 节点，剔除 11 节点（2 个簇）；理由 TOP：广告/宣传节点，server格式异常
- **ermaozi**：审 415 节点，剔除 38 节点（17 个簇）；理由 TOP：v2nodes.com广告位，广告位，server字段异常，频道引流配置，引流广告位
- **zhuhaiuk**：审 27 节点，剔除 6 节点（1 个簇）；理由 TOP：广告引流位
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 59 节点（15 个簇）；理由 TOP：占位符dokng.com示例节点
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 130 节点，剔除 12 节点（3 个簇）；理由 TOP：占位服务器，引流广告位
- **autojiedian**：审 344 节点，剔除 4 节点（2 个簇）；理由 TOP：占位符其他地区
- **shaoyouvip**：审 63 节点，剔除 3 节点（1 个簇）；理由 TOP：伪装：法国名但伊朗域名
- **clashdaily**：审 78 节点，剔除 1 节点（1 个簇）；理由 TOP：净0为失效提示
- **leilaomi**：审 121 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
