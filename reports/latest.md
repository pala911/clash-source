# clash-source 运行报告

- 生成时间：2026-11-21 19:25:09（UTC 记录：2026-11-21T19:25:09Z）
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
| automerge | 254 | 35 | 1 簇 / 10 节点 | 否 | 备用 | 跨源去重 -30 |
| zhuhaiuk | 34 | 33 | 0 节点 | 否 | auto | - |
| ssrsub | 349 | 251 | 0 节点 | 否 | auto | 跨源去重 -94 |
| ruk1ng001 | 421 | 275 | 32 簇 / 32 节点 | 否 | auto | 跨源去重 -1 |
| shaoyouvip | 6 | 4 | 0 节点 | 否 | 备用 | 跨源去重 -2 |
| leilaomi | 52 | 40 | 0 节点 | 否 | auto | 跨源去重 -8 |
| Free-Nodes | 42 | 19 | 0 节点 | 否 | 备用 | 跨源去重 -10 |

合计产出 **657** 节点（合并池 657；跨源内容去重剔除 145）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- Free-Nodes AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- 视频组未生成：达标且能在本轮稳定池里对上的节点只有 2 个（< 4）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 75 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告位
- **zhuhaiuk**：审 33 节点，剔除 0 节点
- **ssrsub**：审 345 节点，剔除 0 节点
- **ruk1ng001**：审 187 节点，剔除 32 节点（32 个簇）；理由 TOP：引流/广告，明显伪装，名称声称意大利但IP境内，引流广告，同主机克隆广告位
- **shaoyouvip**：审 6 节点，剔除 0 节点
- **leilaomi**：审 48 节点，剔除 0 节点
- **Free-Nodes**：审 0 节点，剔除 0 节点（全部批次失败）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
