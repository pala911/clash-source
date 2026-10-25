# clash-source 运行报告

- 生成时间：2026-10-25 21:04:10（UTC 记录：2026-10-25T21:04:07Z）
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
| yypool | 1429 | 900 | 48 簇 / 106 节点 | 否 | - | - |
| anaer | 41 | 35 | 0 节点 | 否 | auto | - |
| passcro | 64 | 59 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 380 | 95 | 2 簇 / 12 节点 | 否 | - | - |
| ermaozi | 410 | 320 | 4 簇 / 29 节点 | 否 | 观察 | - |
| zhuhaiuk | 36 | 35 | 0 节点 | 否 | auto | - |
| ssrsub | 176 | 171 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 453 | 1 簇 / 2 节点 | 否 | auto | - |
| snakem982 | 63 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 433 | 151 | 3 簇 / 13 节点 | 否 | - | - |
| autojiedian | 307 | 279 | 1 簇 / 1 节点 | 否 | - | - |
| shaoyouvip | 100 | 98 | 0 节点 | 否 | auto | - |

合计产出 **2658** 节点（合并池 2658）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1064 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 822 节点，剔除 106 节点（48 个簇）；理由 TOP：订阅地址本身，缺端口，占位符，订阅地址引流，占位端口
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 60 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **automerge**：审 107 节点，剔除 12 节点（2 个簇）；理由 TOP：占位符速度，引流广告位
- **ermaozi**：审 348 节点，剔除 29 节点（4 个簇）；理由 TOP：订阅密钥节点，引流广告群组引流，政治口号伪装节点
- **zhuhaiuk**：审 35 节点，剔除 0 节点
- **ssrsub**：审 171 节点，剔除 0 节点
- **ruk1ng001**：审 228 节点，剔除 2 节点（1 个簇）；理由 TOP：伪装节点同域批量克隆
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 164 节点，剔除 13 节点（3 个簇）；理由 TOP：伪装为印度实为境内中转，引流广告位，名称波兰但服务器为伊朗
- **autojiedian**：审 280 节点，剔除 1 节点（1 个簇）；理由 TOP：广告营销节点
- **shaoyouvip**：审 98 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
