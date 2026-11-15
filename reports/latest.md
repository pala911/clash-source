# clash-source 运行报告

- 生成时间：2026-11-15 03:30:59（UTC 记录：2026-11-15T03:30:58Z）
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
| 视频 | 本机实测高带宽（手动切） | 未生成：达标且能在本轮稳定池里对上的节点只有 3 个（< 4） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 19.6% | 本机 19.6%（达标，但 AUTO 只取前 4） |
| leilaomi | 61.9% | 本机 61.9% |
| nomorewalls | 28.9% | 本机 28.9%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 58.8% | 本机 58.8% |
| snakem982 | 9.5% | 本机 9.5%（达标，但 AUTO 只取前 4） |
| ssrsub | 66.2% | 本机 66.2% |
| zhuhaiuk | 73.1% | 本机 73.1% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 395 | 48 | 4 簇 / 14 节点 | 否 | 备用 | 跨源去重 -75 |
| zhuhaiuk | 33 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 360 | 349 | 0 节点 | 否 | auto | 跨源去重 -1 |
| ruk1ng001 | 397 | 165 | 3 簇 / 3 节点 | 否 | auto | 跨源去重 -70 |
| snakem982 | 62 | 37 | 0 节点 | 否 | 备用 | 跨源去重 -21 |
| nomorewalls | 393 | 89 | 2 簇 / 12 节点 | 否 | 备用 | 跨源去重 -40 |
| leilaomi | 89 | 68 | 5 簇 / 5 节点 | 否 | auto | 跨源去重 -5 |

合计产出 **787** 节点（合并池 787；跨源内容去重剔除 212）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- 视频组未生成：达标且能在本轮稳定池里对上的节点只有 3 个（< 4）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 137 节点，剔除 14 节点（4 个簇）；理由 TOP：群组引流，群组引流广告，placeholder，占位符无真实服务器
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 350 节点，剔除 0 节点
- **ruk1ng001**：审 150 节点，剔除 3 节点（3 个簇）；理由 TOP：占位符，引流
- **snakem982**：审 58 节点，剔除 0 节点
- **nomorewalls**：审 141 节点，剔除 12 节点（2 个簇）；理由 TOP：引流广告占位符，引流广告
- **leilaomi**：审 78 节点，剔除 5 节点（5 个簇）；理由 TOP：伪装伊朗代理服务器

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
