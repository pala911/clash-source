# clash-source 运行报告

- 生成时间：2026-11-05 15:16:50（UTC 记录：2026-11-05T15:16:50Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、clashdaily、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | ruk1ng001、automerge、nomorewalls |
| 观察 | 本机实测不达标 | - |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 28.4% | 本机 28.4%（达标，但 AUTO 只取前 4） |
| clashdaily | 47.6% | 本机 47.6% |
| leilaomi | 38.1% | 本机 38.1% |
| nomorewalls | 27.1% | 本机 27.1%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 36.5% | 本机 36.5%（达标，但 AUTO 只取前 4） |
| ssrsub | 42.3% | 本机 42.3% |
| zhuhaiuk | 48.5% | 本机 48.5% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 340 | 55 | 12 簇 / 42 节点 | 否 | 备用 | 跨源去重 -20 |
| zhuhaiuk | 30 | 30 | 0 节点 | 否 | auto | - |
| ssrsub | 157 | 152 | 0 节点 | 否 | auto | 跨源去重 -4 |
| ruk1ng001 | 500 | 298 | 61 簇 / 107 节点 | 否 | 备用 | 跨源去重 -61 |
| nomorewalls | 340 | 20 | 2 簇 / 12 节点 | 否 | 备用 | 跨源去重 -85 |
| clashdaily | 80 | 79 | 0 节点 | 否 | auto | 跨源去重 -1 |
| leilaomi | 36 | 19 | 9 簇 / 9 节点 | 否 | auto | 跨源去重 -4 |

合计产出 **653** 节点（合并池 653；跨源内容去重剔除 175）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 117 节点，剔除 42 节点（12 个簇）；理由 TOP：占位符服务器，伪装国名带速度，引流广告，伪装美国服务器，speednode测速引流
- **zhuhaiuk**：审 30 节点，剔除 0 节点
- **ssrsub**：审 156 节点，剔除 0 节点
- **ruk1ng001**：审 210 节点，剔除 107 节点（61 个簇）；理由 TOP：引流，营销位伪装，广告，占位符，引流广告
- **nomorewalls**：审 117 节点，剔除 12 节点（2 个簇）；理由 TOP：引流广告，引流广告位
- **clashdaily**：审 80 节点，剔除 0 节点
- **leilaomi**：审 32 节点，剔除 9 节点（9 个簇）；理由 TOP：明显伪装

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
