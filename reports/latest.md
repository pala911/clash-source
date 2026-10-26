# clash-source 运行报告

- 生成时间：2026-10-26 05:03:44（UTC 记录：2026-10-26T05:03:41Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、passcro、ruk1ng001、shaoyouvip、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 83.1% | 本机 83.1% |
| autojiedian | 32.6% | 本机 32.6% |
| automerge | 24.8% | 本机 24.8% |
| ermaozi | 7.3% | 本机 7.3% 低于 8% |
| nomorewalls | 19.7% | 本机 19.7% |
| passcro | 42.0% | 本机 42.0% |
| ruk1ng001 | 37.8% | 本机 37.8% |
| shaoyouvip | 37.1% | 本机 37.1% |
| snakem982 | 4.3% | 本机 4.3% 低于 8% |
| ssrsub | 50.6% | 本机 50.6% |
| yypool | 19.3% | 本机 19.3% |
| zhuhaiuk | 33.0% | 本机 33.0% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1457 | 878 | 40 簇 / 308 节点 | 否 | - | - |
| anaer | 41 | 34 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 64 | 59 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 433 | 160 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 508 | 397 | 15 簇 / 48 节点 | 否 | 观察 | - |
| zhuhaiuk | 31 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 178 | 172 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 413 | 18 簇 / 42 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 412 | 147 | 3 簇 / 12 节点 | 否 | - | - |
| autojiedian | 319 | 295 | 13 簇 / 13 节点 | 否 | - | - |
| shaoyouvip | 100 | 98 | 1 簇 / 1 节点 | 否 | auto | - |

合计产出 **2746** 节点（合并池 2746）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 823 节点，剔除 308 节点（40 个簇）；理由 TOP：订阅地址本身，广告位，占位域名，订阅地址引流，伪装
- **anaer**：审 35 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符说明
- **passcro**：审 60 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符说明非真实节点
- **automerge**：审 171 节点，剔除 11 节点（2 个簇）；理由 TOP：占位符server，广告/引流
- **ermaozi**：审 416 节点，剔除 48 节点（15 个簇）；理由 TOP：广告位，广告位克隆节点，引流广告， Telegram引流，群组引流广告位
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 172 节点，剔除 0 节点
- **ruk1ng001**：审 228 节点，剔除 42 节点（18 个簇）；理由 TOP：占位符示例节点，广告克隆节点，server重复
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 159 节点，剔除 12 节点（3 个簇）；理由 TOP：server格式异常，广告位
- **autojiedian**：审 308 节点，剔除 13 节点（13 个簇）；理由 TOP：Datacamp营销，Melbikomas营销，GNC-Alfa营销，Oracle伪装，Web营销位
- **shaoyouvip**：审 99 节点，剔除 1 节点（1 个簇）；理由 TOP：伪装批量克隆

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
