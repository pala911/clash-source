# clash-source 运行报告

- 生成时间：2026-11-20 20:28:01（UTC 记录：2026-11-20T20:28:00Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | Free-Nodes、shaoyouvip、snakem982 |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 7 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 37.9% | 本机 37.9%（达标，但 AUTO 只取前 4） |
| leilaomi | 51.1% | 本机 51.1% |
| ruk1ng001 | 61.8% | 本机 61.8% |
| shaoyouvip | 36.1% | 本机 36.1%（达标，但 AUTO 只取前 4） |
| snakem982 | 17.1% | 本机 17.1%（达标，但 AUTO 只取前 4） |
| ssrsub | 56.8% | 本机 56.8% |
| zhuhaiuk | 66.7% | 本机 66.7% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| zhuhaiuk | 38 | 35 | 0 节点 | 否 | auto | - |
| ssrsub | 332 | 314 | 1 簇 / 2 节点 | 否 | auto | 跨源去重 -12 |
| ruk1ng001 | 93 | 70 | 3 簇 / 5 节点 | 否 | auto | 跨源去重 -1 |
| snakem982 | 59 | 38 | 0 节点 | 否 | 备用 | 跨源去重 -21 |
| shaoyouvip | 101 | 59 | 0 节点 | 否 | 备用 | 跨源去重 -30 |
| leilaomi | 60 | 49 | 0 节点 | 否 | auto | 跨源去重 -6 |
| Free-Nodes | 969 | 490 | 1 簇 / 12 节点 | 否 | 备用 | 跨源去重 -10 |

合计产出 **1055** 节点（合并池 1055；跨源内容去重剔除 80）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- leilaomi AI 剔除超阈值，已整体回滚
- Free-Nodes 产出 626 超过 max_nodes=500，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 35 节点，剔除 0 节点
- **ssrsub**：审 328 节点，剔除 2 节点（1 个簇）；理由 TOP：引流广告
- **ruk1ng001**：审 76 节点，剔除 5 节点（3 个簇）；理由 TOP：广告
- **snakem982**：审 59 节点，剔除 0 节点
- **shaoyouvip**：审 89 节点，剔除 0 节点
- **leilaomi**：审 55 节点，剔除 0 节点（超阈值已回滚）
- **Free-Nodes**：审 638 节点，剔除 12 节点（1 个簇）；理由 TOP：引流广告

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
