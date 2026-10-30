# clash-source 运行报告

- 生成时间：2026-10-30 13:11:04（UTC 记录：2026-10-30T13:11:02Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、leilaomi、clashdaily、zhuhaiuk、ssrsub、anaer |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982、wzmfree |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 31.6% | 本机 31.6% |
| autojiedian | 12.6% | 本机 12.6% |
| automerge | 26.4% | 本机 26.4% |
| clashdaily | 37.2% | 本机 37.2% |
| ermaozi | 8.0% | 本机 8.0% 低于 8% |
| leilaomi | 41.7% | 本机 41.7% |
| nomorewalls | 25.2% | 本机 25.2% |
| passcro | 44.4% | 本机 44.4% |
| ruk1ng001 | 31.0% | 本机 31.0% |
| shaoyouvip | 27.8% | 本机 27.8% |
| snakem982 | 3.9% | 本机 3.9% 低于 8% |
| ssrsub | 35.5% | 本机 35.5% |
| wzmfree | 0.0% | 本机 0 活 |
| yypool | 16.0% | 本机 16.0% |
| zhuhaiuk | 36.6% | 本机 36.6% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1361 | 900 | 31 簇 / 197 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 384 | 114 | 4 簇 / 15 节点 | 否 | - | - |
| ermaozi | 430 | 360 | 13 簇 / 21 节点 | 否 | 观察 | - |
| zhuhaiuk | 26 | 25 | 0 节点 | 否 | auto | - |
| ssrsub | 135 | 134 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 414 | 19 簇 / 33 节点 | 否 | - | - |
| snakem982 | 63 | 63 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 354 | 89 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 406 | 385 | 3 簇 / 7 节点 | 否 | - | - |
| shaoyouvip | 6 | 5 | 1 簇 / 1 节点 | 否 | - | - |
| clashdaily | 80 | 77 | 1 簇 / 1 节点 | 否 | auto | - |
| leilaomi | 91 | 70 | 1 簇 / 3 节点 | 否 | auto | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2639** 节点（合并池 2639）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- snakem982 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- wzmfree AI 剔除超阈值，已整体回滚
- yypool 产出 918 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 727 节点，剔除 197 节点（31 个簇）；理由 TOP：订阅地址，订阅地址本身，占位符失效提示，群组引流广告位，占位符示例地址
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 129 节点，剔除 15 节点（4 个簇）；理由 TOP：政治宣传占位节点，占位符服务器地址，占位符节点名，荷兰节点域名可疑
- **ermaozi**：审 381 节点，剔除 21 节点（13 个簇）；理由 TOP：群组引流，伪装国家，芬兰节点服务器为伊朗IP，引流信息，Telegram引流
- **zhuhaiuk**：审 25 节点，剔除 0 节点
- **ssrsub**：审 134 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 33 节点（19 个簇）；理由 TOP：占位符dokng.com，引流广告域名，广告/引流节点簇
- **snakem982**：审 0 节点，剔除 0 节点（全部批次失败）
- **nomorewalls**：审 99 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告位
- **autojiedian**：审 377 节点，剔除 7 节点（3 个簇）；理由 TOP：同服务器不同城市名疑似批量，staging占位域名
- **shaoyouvip**：审 6 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符server
- **clashdaily**：审 78 节点，剔除 1 节点（1 个簇）；理由 TOP：净0为失效提示
- **leilaomi**：审 73 节点，剔除 3 节点（1 个簇）；理由 TOP：占位符Channel
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
