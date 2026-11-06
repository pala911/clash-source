# clash-source 运行报告

- 生成时间：2026-11-06 07:00:42（UTC 记录：2026-11-06T07:00:41Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | clashdaily、zhuhaiuk、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | ruk1ng001、automerge、nomorewalls |
| 观察 | 本机实测不达标 | - |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 31.0% | 本机 31.0%（达标，但 AUTO 只取前 4） |
| clashdaily | 53.1% | 本机 53.1% |
| leilaomi | 44.2% | 本机 44.2% |
| nomorewalls | 27.1% | 本机 27.1%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 37.6% | 本机 37.6%（达标，但 AUTO 只取前 4） |
| ssrsub | 44.9% | 本机 44.9% |
| zhuhaiuk | 48.3% | 本机 48.3% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 372 | 99 | 3 簇 / 13 节点 | 否 | 备用 | 跨源去重 -44 |
| zhuhaiuk | 35 | 35 | 0 节点 | 否 | auto | - |
| ssrsub | 134 | 131 | 0 节点 | 否 | auto | 跨源去重 -1 |
| ruk1ng001 | 500 | 313 | 37 簇 / 83 节点 | 否 | 备用 | 跨源去重 -70 |
| nomorewalls | 381 | 27 | 7 簇 / 25 节点 | 否 | 备用 | 跨源去重 -116 |
| clashdaily | 80 | 80 | 0 节点 | 否 | auto | - |
| leilaomi | 34 | 28 | 0 节点 | 否 | auto | 跨源去重 -4 |

合计产出 **713** 节点（合并池 713；跨源内容去重剔除 235）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 156 节点，剔除 13 节点（3 个簇）；理由 TOP：群组引流广告位，广告位引流，群组引流
- **zhuhaiuk**：审 35 节点，剔除 0 节点
- **ssrsub**：审 132 节点，剔除 0 节点
- **ruk1ng001**：审 210 节点，剔除 83 节点（37 个簇）；理由 TOP：伪装广告节点，引流，server格式异常，日本名配境内服务器，引流广告
- **nomorewalls**：审 168 节点，剔除 25 节点（7 个簇）；理由 TOP：明显伪装，群组引流，伪装为法国但服务器为伊朗，引流，引流/广告
- **clashdaily**：审 80 节点，剔除 0 节点
- **leilaomi**：审 32 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
