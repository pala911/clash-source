# clash-source 运行报告

- 生成时间：2026-11-11 19:45:43（UTC 记录：2026-11-11T19:45:41Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | ssrsub、zhuhaiuk、leilaomi、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、automerge、yypool |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 9 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 22.8% | 本机 22.8%（达标，但 AUTO 只取前 4） |
| leilaomi | 60.8% | 本机 60.8% |
| nomorewalls | 34.1% | 本机 34.1%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 51.7% | 本机 51.7% |
| ssrsub | 64.5% | 本机 64.5% |
| yypool | 17.3% | 本机 17.3%（达标，但 AUTO 只取前 4） |
| zhuhaiuk | 62.9% | 本机 62.9% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1477 | 690 | 10 簇 / 44 节点 | 否 | 备用 | 跨源去重 -210 |
| automerge | 326 | 40 | 7 簇 / 25 节点 | 否 | 备用 | 跨源去重 -40 |
| zhuhaiuk | 35 | 28 | 0 节点 | 否 | auto | 跨源去重 -5 |
| ssrsub | 347 | 338 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 129 | 57 | 2 簇 / 2 节点 | 否 | auto | 跨源去重 -27 |
| nomorewalls | 308 | 45 | 10 簇 / 33 节点 | 否 | 备用 | 跨源去重 -14 |
| leilaomi | 92 | 57 | 0 节点 | 否 | auto | 跨源去重 -31 |

合计产出 **1255** 节点（合并池 1255；跨源内容去重剔除 327）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1171 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 775 节点，剔除 44 节点（10 个簇）；理由 TOP：订阅地址本身，群组引流，广告位，服务器占位符，server为占位符free-nodes
- **automerge**：审 105 节点，剔除 25 节点（7 个簇）；理由 TOP：占位符，server非IP，占位符，伪装，引流
- **zhuhaiuk**：审 33 节点，剔除 0 节点
- **ssrsub**：审 338 节点，剔除 0 节点
- **ruk1ng001**：审 86 节点，剔除 2 节点（2 个簇）；理由 TOP：占位符示例节点，引流广告
- **nomorewalls**：审 92 节点，剔除 33 节点（10 个簇）；理由 TOP：占位符，伪装，伪装境外，引流
- **leilaomi**：审 88 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
