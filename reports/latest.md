# clash-source 运行报告

- 生成时间：2026-11-22 06:59:09（UTC 记录：2026-11-22T06:59:08Z）
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
| 视频 | 本机实测高带宽（手动切） | 未生成：测速结果里没有 >= 0.6 MB/s 的节点 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 30.1% | 本机 30.1%（达标，但 AUTO 只取前 4） |
| automerge | 12.6% | 位置敏感（本机 12.6%/云效 7.9%） |
| leilaomi | 43.8% | 本机 43.8% |
| ruk1ng001 | 55.5% | 本机 55.5% |
| shaoyouvip | 38.6% | 本机 38.6%（达标，但 AUTO 只取前 4） |
| ssrsub | 48.8% | 本机 48.8% |
| zhuhaiuk | 62.2% | 本机 62.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 341 | 81 | 4 簇 / 19 节点 | 否 | 备用 | 跨源去重 -52 |
| zhuhaiuk | 33 | 32 | 0 节点 | 否 | auto | - |
| ssrsub | 362 | 251 | 0 节点 | 否 | auto | 跨源去重 -108 |
| ruk1ng001 | 421 | 276 | 32 簇 / 32 节点 | 否 | auto | - |
| shaoyouvip | 11 | 8 | 1 簇 / 1 节点 | 否 | 备用 | 跨源去重 -2 |
| leilaomi | 36 | 19 | 0 节点 | 否 | auto | 跨源去重 -7 |
| Free-Nodes | 42 | 16 | 0 节点 | 否 | 备用 | 跨源去重 -13 |

合计产出 **683** 节点（合并池 683；跨源内容去重剔除 182）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- 视频组未生成：测速结果里没有 >= 0.6 MB/s 的节点

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 152 节点，剔除 19 节点（4 个簇）；理由 TOP：占位符，防范境外势力渗透
- **zhuhaiuk**：审 32 节点，剔除 0 节点
- **ssrsub**：审 359 节点，剔除 0 节点
- **ruk1ng001**：审 187 节点，剔除 32 节点（32 个簇）；理由 TOP：引流/广告，明显伪装，引流，伪装，引流广告
- **shaoyouvip**：审 11 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符批量克隆
- **leilaomi**：审 26 节点，剔除 0 节点
- **Free-Nodes**：审 29 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
