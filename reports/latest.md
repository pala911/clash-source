# clash-source 运行报告

- 生成时间：2026-11-27 08:34:24（UTC 记录：2026-11-27T08:34:24Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、leilaomi、ssrsub |
| 备用 | 不自动竞速，手动切 | shaoyouvip、passcro、anaer |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 未生成：达标且能在本轮稳定池里对上的节点只有 3 个（< 4） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 23.9% | 本机 23.9%（达标，但 AUTO 只取前 4） |
| leilaomi | 53.4% | 本机 53.4% |
| passcro | 29.5% | 本机 29.5%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 54.4% | 本机 54.4% |
| shaoyouvip | 43.0% | 本机 43.0%（达标，但 AUTO 只取前 4） |
| ssrsub | 52.5% | 本机 52.5% |
| zhuhaiuk | 61.4% | 本机 61.4% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| anaer | 15 | 9 | 0 节点 | 否 | 备用 | 跨源去重 -1 |
| passcro | 32 | 15 | 0 节点 | 否 | 备用 | 跨源去重 -13 |
| zhuhaiuk | 31 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 405 | 383 | 0 节点 | 否 | auto | 跨源去重 -11 |
| ruk1ng001 | 54 | 44 | 0 节点 | 否 | auto | 跨源去重 -3 |
| shaoyouvip | 22 | 13 | 0 节点 | 否 | 备用 | 跨源去重 -3 |
| leilaomi | 63 | 60 | 0 节点 | 否 | auto | 跨源去重 -2 |

合计产出 **555** 节点（合并池 555；跨源内容去重剔除 33）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- passcro AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- ssrsub AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- ruk1ng001 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- shaoyouvip AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- leilaomi AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- 视频组未生成：达标且能在本轮稳定池里对上的节点只有 3 个（< 4）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 0 节点，剔除 0 节点（全部批次失败）
- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 0 节点，剔除 0 节点（全部批次失败）
- **ruk1ng001**：审 0 节点，剔除 0 节点（全部批次失败）
- **shaoyouvip**：审 0 节点，剔除 0 节点（全部批次失败）
- **leilaomi**：审 0 节点，剔除 0 节点（全部批次失败）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
