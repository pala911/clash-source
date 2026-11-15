# clash-source 运行报告

- 生成时间：2026-11-15 19:00:01（UTC 记录：2026-11-15T19:00:00Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ssrsub、leilaomi、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、automerge、snakem982 |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 4 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 20.3% | 本机 20.3%（达标，但 AUTO 只取前 4） |
| leilaomi | 62.6% | 本机 62.6% |
| nomorewalls | 28.1% | 本机 28.1%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 62.5% | 本机 62.5% |
| snakem982 | 13.7% | 本机 13.7%（达标，但 AUTO 只取前 4） |
| ssrsub | 67.7% | 本机 67.7% |
| zhuhaiuk | 73.6% | 本机 73.6% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 334 | 13 | 0 节点 | 否 | 备用 | 跨源去重 -72 |
| zhuhaiuk | 35 | 34 | 0 节点 | 否 | auto | - |
| ssrsub | 375 | 364 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 397 | 166 | 0 节点 | 否 | auto | 跨源去重 -72 |
| snakem982 | 64 | 24 | 0 节点 | 否 | 备用 | 跨源去重 -36 |
| nomorewalls | 332 | 48 | 3 簇 / 14 节点 | 否 | 备用 | 跨源去重 -26 |
| leilaomi | 67 | 55 | 0 节点 | 否 | auto | 跨源去重 -7 |

合计产出 **704** 节点（合并池 704；跨源内容去重剔除 213）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- automerge AI 剔除超阈值，已整体回滚
- snakem982 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- leilaomi AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 85 节点，剔除 0 节点（超阈值已回滚）
- **zhuhaiuk**：审 34 节点，剔除 0 节点
- **ssrsub**：审 364 节点，剔除 0 节点
- **ruk1ng001**：审 150 节点，剔除 0 节点
- **snakem982**：审 0 节点，剔除 0 节点（全部批次失败）
- **nomorewalls**：审 88 节点，剔除 14 节点（3 个簇）；理由 TOP：引流广告，占位符示例，引流广告节点
- **leilaomi**：审 62 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
