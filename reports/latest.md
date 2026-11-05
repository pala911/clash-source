# clash-source 运行报告

- 生成时间：2026-11-05 06:47:25（UTC 记录：2026-11-05T06:47:24Z）
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
| automerge | 297 | 77 | 0 节点 | 否 | 备用 | - |
| zhuhaiuk | 33 | 32 | 0 节点 | 否 | auto | - |
| ssrsub | 157 | 156 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 466 | 0 节点 | 否 | 备用 | - |
| nomorewalls | 297 | 77 | 0 节点 | 否 | 备用 | - |
| clashdaily | 80 | 80 | 0 节点 | 否 | auto | - |
| leilaomi | 40 | 36 | 0 节点 | 否 | auto | - |

合计产出 **924** 节点（合并池 924）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- automerge AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- ssrsub AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- ruk1ng001 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- nomorewalls AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- clashdaily AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- leilaomi AI 部分批次不可用（相关批次保留全部节点）：全部批次失败

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 0 节点，剔除 0 节点（全部批次失败）
- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 0 节点，剔除 0 节点（全部批次失败）
- **ruk1ng001**：审 0 节点，剔除 0 节点（全部批次失败）
- **nomorewalls**：审 0 节点，剔除 0 节点（全部批次失败）
- **clashdaily**：审 0 节点，剔除 0 节点（全部批次失败）
- **leilaomi**：审 0 节点，剔除 0 节点（全部批次失败）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
