# clash-source 运行报告

- 生成时间：2026-11-03 17:16:40（UTC 记录：2026-11-03T17:16:39Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、clashdaily、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | - |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 28.6% | 本机 28.6% |
| clashdaily | 41.8% | 本机 41.8% |
| leilaomi | 34.5% | 本机 34.5% |
| nomorewalls | 28.6% | 本机 28.6% |
| ruk1ng001 | 31.3% | 本机 31.3% |
| ssrsub | 35.0% | 本机 35.0% |
| zhuhaiuk | 45.0% | 本机 45.0% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 391 | 85 | 2 簇 / 11 节点 | 否 | - | - |
| zhuhaiuk | 33 | 30 | 0 节点 | 否 | auto | - |
| ssrsub | 165 | 164 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 497 | 473 | 0 节点 | 否 | - | - |
| nomorewalls | 391 | 85 | 2 簇 / 11 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 34 | 27 | 0 节点 | 否 | auto | - |

合计产出 **942** 节点（合并池 942）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 96 节点，剔除 11 节点（2 个簇）；理由 TOP：群组引流，引流营销文案
- **zhuhaiuk**：审 30 节点，剔除 0 节点
- **ssrsub**：审 164 节点，剔除 0 节点
- **ruk1ng001**：审 225 节点，剔除 0 节点
- **nomorewalls**：审 96 节点，剔除 11 节点（2 个簇）；理由 TOP：群组引流广告，引流广告伪装节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 27 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
