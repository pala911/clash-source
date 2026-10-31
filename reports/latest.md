# clash-source 运行报告

- 生成时间：2026-10-31 21:52:56（UTC 记录：2026-10-31T21:52:54Z）
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
| yypool | 1198 | 876 | 19 簇 / 50 节点 | 否 | - | - |
| automerge | 399 | 94 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 412 | 323 | 7 簇 / 16 节点 | 否 | - | - |
| zhuhaiuk | 32 | 32 | 0 节点 | 否 | auto | - |
| ssrsub | 170 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 460 | 3 簇 / 3 节点 | 否 | auto | - |
| snakem982 | 63 | 63 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 484 | 172 | 4 簇 / 13 节点 | 否 | - | - |
| autojiedian | 359 | 347 | 6 簇 / 6 节点 | 否 | 备用 | - |
| shaoyouvip | 101 | 96 | 4 簇 / 5 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 146 | 117 | 4 簇 / 4 节点 | 否 | auto | - |

合计产出 **2826** 节点（合并池 2826）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 561 节点，剔除 50 节点（19 个簇）；理由 TOP：订阅地址，域名异常，广告引流，订阅地址本身，广告引流节点
- **automerge**：审 104 节点，剔除 10 节点（1 个簇）；理由 TOP：广告引流节点
- **ermaozi**：审 339 节点，剔除 16 节点（7 个簇）；理由 TOP：广告引流，tg频道引流，订阅地址本身，引流广告口号，营销位
- **zhuhaiuk**：审 32 节点，剔除 0 节点
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 223 节点，剔除 3 节点（3 个簇）；理由 TOP：国家代码伪装，广告/引流内容
- **snakem982**：审 63 节点，剔除 0 节点
- **nomorewalls**：审 185 节点，剔除 13 节点（4 个簇）；理由 TOP：server字段异常，引流广告位
- **autojiedian**：审 353 节点，剔除 6 节点（6 个簇）；理由 TOP：占位符域名，伪装：特拉维夫冒充美国，占位符/示例，域名含promo广告字样
- **shaoyouvip**：审 101 节点，剔除 5 节点（4 个簇）；理由 TOP：同簇克隆，广告节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 121 节点，剔除 4 节点（4 个簇）；理由 TOP：4FreeIran促销，twmoon引流，占位符节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
