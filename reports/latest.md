# clash-source 运行报告

- 生成时间：2026-10-29 02:08:49（UTC 记录：2026-10-29T02:08:46Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、anaer、ssrsub、shaoyouvip、ruk1ng001、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982、clashdaily、leilaomi、wzmfree |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 55.1% | 本机 55.1% |
| autojiedian | 19.8% | 本机 19.8% |
| automerge | 27.5% | 本机 27.5% |
| clashdaily | - | 无本机探针数据 |
| ermaozi | 6.8% | 本机 6.8% 低于 8% |
| leilaomi | - | 无本机探针数据 |
| nomorewalls | 23.8% | 本机 23.8% |
| passcro | 63.3% | 本机 63.3% |
| ruk1ng001 | 28.8% | 本机 28.8% |
| shaoyouvip | 29.4% | 本机 29.4% |
| snakem982 | 2.7% | 本机 2.7% 低于 8% |
| ssrsub | 39.8% | 本机 39.8% |
| wzmfree | - | 无本机探针数据 |
| yypool | 15.5% | 本机 15.5% |
| zhuhaiuk | 27.7% | 本机 27.7% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1309 | 900 | 30 簇 / 81 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 380 | 149 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 408 | 283 | 27 簇 / 72 节点 | 否 | 观察 | - |
| zhuhaiuk | 30 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 171 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 441 | 0 节点 | 否 | auto | - |
| snakem982 | 57 | 57 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 380 | 138 | 3 簇 / 21 节点 | 否 | - | - |
| autojiedian | 393 | 361 | 5 簇 / 6 节点 | 否 | - | - |
| shaoyouvip | 93 | 92 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | 观察 | - |
| leilaomi | 76 | 50 | 2 簇 / 20 节点 | 否 | 观察 | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2749** 节点（合并池 2749）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- wzmfree AI 剔除超阈值，已整体回滚
- yypool 产出 981 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 684 节点，剔除 81 节点（30 个簇）；理由 TOP：订阅地址，订阅地址本身，伪装：境内服务器，server为速度，server字段为占位符
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 159 节点，剔除 10 节点（1 个簇）；理由 TOP：广告/占位符
- **ermaozi**：审 355 节点，剔除 72 节点（27 个簇）；理由 TOP：广告来源标记，同源引流节点，占位符，群组引流，伪装
- **zhuhaiuk**：审 29 节点，剔除 0 节点
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 202 节点，剔除 0 节点
- **snakem982**：审 57 节点，剔除 0 节点
- **nomorewalls**：审 159 节点，剔除 21 节点（3 个簇）；理由 TOP：引流广告节点，伪装意大利节点，伪装美国节点
- **autojiedian**：审 351 节点，剔除 6 节点（5 个簇）；理由 TOP：占位符域名，广告域名，伪装国家
- **shaoyouvip**：审 92 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 70 节点，剔除 20 节点（2 个簇）；理由 TOP：批量克隆营销位
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
