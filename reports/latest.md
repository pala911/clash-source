# clash-source 运行报告

- 生成时间：2026-11-10 07:30:16（UTC 记录：2026-11-10T07:30:15Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | ssrsub、leilaomi、zhuhaiuk、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、automerge |
| 观察 | 本机实测不达标 | Free-Nodes |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | - | 无本机探针数据 |
| automerge | 25.4% | 本机 25.4%（达标，但 AUTO 只取前 4） |
| leilaomi | 61.2% | 本机 61.2% |
| nomorewalls | 37.2% | 本机 37.2%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 51.9% | 本机 51.9% |
| ssrsub | 63.8% | 本机 63.8% |
| zhuhaiuk | 60.9% | 本机 60.9% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 418 | 78 | 3 簇 / 15 节点 | 否 | 备用 | 跨源去重 -99 |
| zhuhaiuk | 32 | 28 | 0 节点 | 否 | auto | 跨源去重 -3 |
| ssrsub | 353 | 347 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 227 | 60 簇 / 105 节点 | 否 | auto | 跨源去重 -134 |
| nomorewalls | 414 | 98 | 3 簇 / 16 节点 | 否 | 备用 | 跨源去重 -53 |
| leilaomi | 134 | 76 | 0 节点 | 否 | auto | 跨源去重 -44 |
| Free-Nodes | 37 | 18 | 2 簇 / 2 节点 | 否 | 观察 | 跨源去重 -7 |

合计产出 **872** 节点（合并池 872；跨源内容去重剔除 340）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- leilaomi AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 192 节点，剔除 15 节点（3 个簇）；理由 TOP：引流广告，群组广告引流
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 347 节点，剔除 0 节点
- **ruk1ng001**：审 210 节点，剔除 105 节点（60 个簇）；理由 TOP：引流，广告，伪装营销位，占位符，广告营销位
- **nomorewalls**：审 167 节点，剔除 16 节点（3 个簇）；理由 TOP：引流广告位，群组引流，引流
- **leilaomi**：审 120 节点，剔除 0 节点（超阈值已回滚）
- **Free-Nodes**：审 27 节点，剔除 2 节点（2 个簇）；理由 TOP：占位符未知地区，同服务器伪装

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
