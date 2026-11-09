# clash-source 运行报告

- 生成时间：2026-11-09 22:34:18（UTC 记录：2026-11-09T22:34:17Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | leilaomi、ssrsub、zhuhaiuk、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、automerge |
| 观察 | 本机实测不达标 | free-nodes |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 29.7% | 本机 29.7%（达标，但 AUTO 只取前 4） |
| free-nodes | - | 无本机探针数据 |
| leilaomi | 59.4% | 本机 59.4% |
| nomorewalls | 35.5% | 本机 35.5%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 47.2% | 本机 47.2% |
| ssrsub | 57.2% | 本机 57.2% |
| zhuhaiuk | 56.8% | 本机 56.8% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 329 | 31 | 3 簇 / 15 节点 | 否 | 备用 | 跨源去重 -54 |
| zhuhaiuk | 35 | 30 | 0 节点 | 否 | auto | 跨源去重 -3 |
| ssrsub | 148 | 145 | 0 节点 | 否 | auto | 跨源去重 -1 |
| ruk1ng001 | 500 | 390 | 16 簇 / 16 节点 | 否 | auto | 跨源去重 -60 |
| nomorewalls | 418 | 124 | 3 簇 / 15 节点 | 否 | 备用 | 跨源去重 -53 |
| leilaomi | 44 | 39 | 0 节点 | 否 | auto | - |
| free-nodes | - | 0 | - | 否 | 观察 | 全部 URL 尝试均失败 |

合计产出 **759** 节点（合并池 759；跨源内容去重剔除 171）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- free-nodes 抓取失败：全部 URL 尝试均失败（本轮产出空文件，不影响其他源）
- leilaomi AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 100 节点，剔除 15 节点（3 个簇）；理由 TOP：群组引流
- **zhuhaiuk**：审 33 节点，剔除 0 节点
- **ssrsub**：审 146 节点，剔除 0 节点
- **ruk1ng001**：审 210 节点，剔除 16 节点（16 个簇）；理由 TOP：引流，广告，引流广告
- **nomorewalls**：审 192 节点，剔除 15 节点（3 个簇）；理由 TOP：引流群组推广，引流广告位整簇剔除
- **leilaomi**：审 39 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
