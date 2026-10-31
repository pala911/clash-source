# clash-source 运行报告

- 生成时间：2026-10-31 05:57:21（UTC 记录：2026-10-31T05:57:18Z）
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
| yypool | 1388 | 900 | 24 簇 / 90 节点 | 否 | - | - |
| automerge | 409 | 159 | 3 簇 / 12 节点 | 否 | - | - |
| ermaozi | 482 | 420 | 5 簇 / 14 节点 | 否 | - | - |
| zhuhaiuk | 28 | 27 | 0 节点 | 否 | auto | - |
| ssrsub | 171 | 153 | 7 簇 / 15 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 462 | 4 簇 / 8 节点 | 否 | auto | - |
| snakem982 | 63 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 367 | 118 | 3 簇 / 12 节点 | 否 | - | - |
| autojiedian | 355 | 337 | 5 簇 / 7 节点 | 否 | 备用 | - |
| shaoyouvip | 63 | 62 | 1 簇 / 1 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 107 | 80 | 0 节点 | 否 | auto | - |

合计产出 **2858** 节点（合并池 2858）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1011 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 706 节点，剔除 90 节点（24 个簇）；理由 TOP：广告位克隆，订阅伪装，广告订阅引流，失效占位符，伪装营销位
- **automerge**：审 171 节点，剔除 12 节点（3 个簇）；理由 TOP：域名疑似营销，广告引流位，server格式异常
- **ermaozi**：审 415 节点，剔除 14 节点（5 个簇）；理由 TOP：广告引流节点，疑似引流广告，群组引流
- **zhuhaiuk**：审 27 节点，剔除 0 节点
- **ssrsub**：审 168 节点，剔除 15 节点（7 个簇）；理由 TOP：广告位，境内IP，营销域名，随机域名
- **ruk1ng001**：审 222 节点，剔除 8 节点（4 个簇）；理由 TOP：新加坡名但Cloudflare服务器，德国名但境内中转服务器，新加坡名但AWS服务器
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 130 节点，剔除 12 节点（3 个簇）；理由 TOP：营销位域名，占位符server，广告引流节点
- **autojiedian**：审 344 节点，剔除 7 节点（5 个簇）；理由 TOP：占位符其他地区，占位符示例域名，可疑域名，疑似占位，Zoom支持页，疑似占位
- **shaoyouvip**：审 63 节点，剔除 1 节点（1 个簇）；理由 TOP：server非IP地址
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 80 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
