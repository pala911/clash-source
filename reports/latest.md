# clash-source 运行报告

- 生成时间：2026-11-12 20:02:42（UTC 记录：2026-11-12T20:02:40Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ssrsub、leilaomi、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、yypool |
| 观察 | 本机实测不达标 | snakem982 |
| 视频 | 本机实测高带宽（手动切） | 9 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| leilaomi | 64.0% | 本机 64.0% |
| nomorewalls | 34.2% | 本机 34.2%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 52.4% | 本机 52.4% |
| snakem982 | 6.2% | 本机 6.2% 低于 8% |
| ssrsub | 64.2% | 本机 64.2% |
| yypool | 17.3% | 本机 17.3%（达标，但 AUTO 只取前 4） |
| zhuhaiuk | 66.7% | 本机 66.7% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1200 | 726 | 14 簇 / 50 节点 | 否 | 备用 | 跨源去重 -149 |
| zhuhaiuk | 39 | 34 | 0 节点 | 否 | auto | - |
| ssrsub | 368 | 360 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 197 | 79 | 1 簇 / 1 节点 | 否 | auto | 跨源去重 -55 |
| snakem982 | 47 | 10 | 0 节点 | 否 | 观察 | 跨源去重 -35 |
| nomorewalls | 325 | 41 | 4 簇 / 20 节点 | 否 | 备用 | 跨源去重 -20 |
| leilaomi | 79 | 69 | 1 簇 / 1 节点 | 否 | auto | 跨源去重 -5 |

合计产出 **1319** 节点（合并池 1319；跨源内容去重剔除 264）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- zhuhaiuk AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 643 节点，剔除 50 节点（14 个簇）；理由 TOP：伪装，占位符服务器，防范境外势力渗透，占位符示例节点，群组引流
- **zhuhaiuk**：审 34 节点，剔除 0 节点（超阈值已回滚）
- **ssrsub**：审 360 节点，剔除 0 节点
- **ruk1ng001**：审 135 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **snakem982**：审 45 节点，剔除 0 节点
- **nomorewalls**：审 81 节点，剔除 20 节点（4 个簇）；理由 TOP：群组引流广告，引流广告，引流广告占位符
- **leilaomi**：审 75 节点，剔除 1 节点（1 个簇）；理由 TOP：明显伪装

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
