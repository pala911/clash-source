# clash-source 运行报告

- 生成时间：2026-10-27 22:31:55（UTC 记录：2026-10-27T22:31:52Z）
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
| yypool | 1232 | 900 | 20 簇 / 63 节点 | 否 | - | - |
| anaer | 39 | 30 | 2 簇 / 3 节点 | 否 | auto | - |
| passcro | 48 | 43 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 307 | 62 | 2 簇 / 13 节点 | 否 | - | - |
| ermaozi | 379 | 318 | 2 簇 / 11 节点 | 否 | 观察 | - |
| zhuhaiuk | 33 | 33 | 0 节点 | 否 | auto | - |
| ssrsub | 172 | 169 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 377 | 15 簇 / 61 节点 | 否 | auto | - |
| snakem982 | 60 | 54 | 1 簇 / 6 节点 | 否 | 观察 | - |
| nomorewalls | 392 | 155 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 309 | 277 | 8 簇 / 16 节点 | 否 | - | - |
| shaoyouvip | 101 | 101 | 0 节点 | 否 | auto | - |

合计产出 **2519** 节点（合并池 2519）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 926 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 642 节点，剔除 63 节点（20 个簇）；理由 TOP：订阅地址本身，订阅地址，引流广告订阅地址，占位符，占位符失效提示
- **anaer**：审 33 节点，剔除 3 节点（2 个簇）；理由 TOP：占位符/示例
- **passcro**：审 44 节点，剔除 1 节点（1 个簇）；理由 TOP：占位说明节点非可用节点
- **automerge**：审 75 节点，剔除 13 节点（2 个簇）；理由 TOP：伪装/境内中转，广告/引流
- **ermaozi**：审 329 节点，剔除 11 节点（2 个簇）；理由 TOP：群组引流地址，广告引流节点
- **zhuhaiuk**：审 33 节点，剔除 0 节点
- **ssrsub**：审 169 节点，剔除 0 节点
- **ruk1ng001**：审 216 节点，剔除 61 节点（15 个簇）；理由 TOP：广告引流节点
- **snakem982**：审 60 节点，剔除 6 节点（1 个簇）；理由 TOP：伪装：德国名但伊朗服务器
- **nomorewalls**：审 165 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告伪装节点
- **autojiedian**：审 293 节点，剔除 16 节点（8 个簇）；理由 TOP：占位符，占位符节点，占位域名，Lease广告占位，server含promo
- **shaoyouvip**：审 101 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
