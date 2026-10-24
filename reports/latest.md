# clash-source 运行报告

- 生成时间：2026-10-24 04:53:18（UTC 记录：2026-10-24T04:53:16Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、yypool |
| 备用 | 不自动竞速，手动切 | ermaozi |
| 观察 | 本机实测不达标 | snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 77.6% | 本机 77.6% |
| autojiedian | 26.1% | 本机 26.1% |
| automerge | 13.5% | 本机 13.5% |
| ermaozi | 8.3% | 位置敏感（本机 8.3%/云效 6.7%） |
| nomorewalls | 14.9% | 本机 14.9% |
| passcro | 13.6% | 本机 13.6% |
| ruk1ng001 | 37.3% | 本机 37.3% |
| shaoyouvip | 17.8% | 本机 17.8% |
| snakem982 | 4.4% | 本机 4.4% 低于 8% |
| ssrsub | 43.9% | 本机 43.9% |
| yypool | 18.3% | 本机 18.3% |
| zhuhaiuk | 42.2% | 本机 42.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1297 | 900 | 4 簇 / 14 节点 | 否 | auto | - |
| anaer | 41 | 35 | 0 节点 | 否 | auto | - |
| passcro | 29 | 25 | 0 节点 | 否 | - | - |
| automerge | 450 | 169 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 515 | 443 | 2 簇 / 7 节点 | 否 | 备用 | - |
| zhuhaiuk | 25 | 24 | 0 节点 | 否 | auto | - |
| ssrsub | 279 | 274 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 445 | 1 簇 / 1 节点 | 否 | auto | - |
| snakem982 | 62 | 61 | 1 簇 / 1 节点 | 否 | 观察 | - |
| nomorewalls | 445 | 177 | 0 节点 | 否 | - | - |
| autojiedian | 325 | 305 | 0 节点 | 否 | auto | - |
| shaoyouvip | 81 | 80 | 0 节点 | 否 | - | - |

合计产出 **2938** 节点（合并池 2938）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1002 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 650 节点，剔除 14 节点（4 个簇）；理由 TOP：占位符服务器，伪装为国内节点server为营销域名
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 25 节点，剔除 0 节点
- **automerge**：审 179 节点，剔除 10 节点（1 个簇）；理由 TOP：群组引流广告位
- **ermaozi**：审 434 节点，剔除 7 节点（2 个簇）；理由 TOP：广告引流节点，伪装为美国服务器为伊朗
- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 274 节点，剔除 0 节点
- **ruk1ng001**：审 219 节点，剔除 1 节点（1 个簇）；理由 TOP：特殊符号可能广告
- **snakem982**：审 62 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **nomorewalls**：审 177 节点，剔除 0 节点
- **autojiedian**：审 305 节点，剔除 0 节点
- **shaoyouvip**：审 80 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
