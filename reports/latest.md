# clash-source 运行报告

- 生成时间：2026-11-21 08:57:58（UTC 记录：2026-11-21T08:57:57Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | automerge、shaoyouvip、Free-Nodes |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 未生成：达标且能在本轮稳定池里对上的节点只有 2 个（< 4） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 31.7% | 本机 31.7%（达标，但 AUTO 只取前 4） |
| automerge | 16.7% | 位置敏感（本机 16.7%/云效 6.1%） |
| leilaomi | 50.4% | 本机 50.4% |
| ruk1ng001 | 59.4% | 本机 59.4% |
| shaoyouvip | 39.9% | 本机 39.9%（达标，但 AUTO 只取前 4） |
| ssrsub | 55.8% | 本机 55.8% |
| zhuhaiuk | 63.9% | 本机 63.9% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 320 | 69 | 2 簇 / 11 节点 | 否 | 备用 | 跨源去重 -49 |
| zhuhaiuk | 31 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 348 | 253 | 0 节点 | 否 | auto | 跨源去重 -91 |
| ruk1ng001 | 421 | 271 | 33 簇 / 33 节点 | 否 | auto | 跨源去重 -4 |
| shaoyouvip | 7 | 1 | 0 节点 | 否 | 备用 | 跨源去重 -6 |
| leilaomi | 52 | 41 | 0 节点 | 否 | auto | 跨源去重 -7 |
| Free-Nodes | 969 | 490 | 0 节点 | 否 | 备用 | 跨源去重 -10 |

合计产出 **1156** 节点（合并池 1156；跨源内容去重剔除 167）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- Free-Nodes 产出 638 超过 max_nodes=500，已截断
- 视频组未生成：达标且能在本轮稳定池里对上的节点只有 2 个（< 4）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 129 节点，剔除 11 节点（2 个簇）；理由 TOP：引流广告，群组引流
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 344 节点，剔除 0 节点
- **ruk1ng001**：审 187 节点，剔除 33 节点（33 个簇）；理由 TOP：占位符模板节点，引流/广告，占位符、示例，伪装，引流广告
- **shaoyouvip**：审 7 节点，剔除 0 节点
- **leilaomi**：审 48 节点，剔除 0 节点
- **Free-Nodes**：审 638 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
