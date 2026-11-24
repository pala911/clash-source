# clash-source 运行报告

- 生成时间：2026-11-24 22:26:49（UTC 记录：2026-11-24T22:26:48Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | shaoyouvip、Free-Nodes、wzmfree |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 7 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 30.2% | 本机 30.2%（达标，但 AUTO 只取前 4） |
| leilaomi | 52.5% | 本机 52.5% |
| ruk1ng001 | 54.6% | 本机 54.6% |
| shaoyouvip | 41.0% | 本机 41.0%（达标，但 AUTO 只取前 4） |
| ssrsub | 53.2% | 本机 53.2% |
| wzmfree | 19.4% | 本机 19.4%（达标，但 AUTO 只取前 4） |
| zhuhaiuk | 58.9% | 本机 58.9% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| zhuhaiuk | 38 | 38 | 0 节点 | 否 | auto | - |
| ssrsub | 396 | 372 | 0 节点 | 否 | auto | 跨源去重 -16 |
| ruk1ng001 | 129 | 104 | 0 节点 | 否 | auto | 跨源去重 -1 |
| shaoyouvip | 100 | 57 | 0 节点 | 否 | 备用 | 跨源去重 -34 |
| leilaomi | 80 | 60 | 0 节点 | 否 | auto | 跨源去重 -12 |
| wzmfree | 134 | 1 | 0 节点 | 否 | 备用 | 跨源去重 -105 |
| Free-Nodes | 81 | 44 | 0 节点 | 否 | 备用 | 跨源去重 -10 |

合计产出 **676** 节点（合并池 676；跨源内容去重剔除 178）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- ssrsub AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- ruk1ng001 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- shaoyouvip AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- leilaomi AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- wzmfree AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- Free-Nodes AI 部分批次不可用（相关批次保留全部节点）：全部批次失败

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 0 节点，剔除 0 节点（全部批次失败）
- **ruk1ng001**：审 0 节点，剔除 0 节点（全部批次失败）
- **shaoyouvip**：审 0 节点，剔除 0 节点（全部批次失败）
- **leilaomi**：审 0 节点，剔除 0 节点（全部批次失败）
- **wzmfree**：审 0 节点，剔除 0 节点（全部批次失败）
- **Free-Nodes**：审 0 节点，剔除 0 节点（全部批次失败）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
