# clash-source 运行报告

- 生成时间：2026-10-20 12:02:51（UTC 记录：2026-10-20T12:02:47Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、yypool |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 77.6% | 本机 77.6% |
| autojiedian | 26.1% | 本机 26.1% |
| automerge | 13.5% | 本机 13.5% |
| ermaozi | 8.3% | 本机 8.3% |
| nomorewalls | 14.9% | 本机 14.9% |
| passcro | 13.6% | 本机 13.6% |
| ruk1ng001 | 37.3% | 本机 37.3% |
| shaoyouvip | 17.8% | 本机 17.8% |
| snakem982 | 4.4% | 本机 4.4% 低于 8% |
| ssrsub | 43.9% | 本机 43.9% |
| yypool | 18.3% | 本机 18.3% |
| zhuhaiuk | 42.2% | 本机 42.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1441 | 900 | 8 簇 / 32 节点 | 否 | auto | - |
| anaer | 40 | 31 | 2 簇 / 3 节点 | 否 | auto | - |
| passcro | 32 | 28 | 0 节点 | 否 | - | - |
| automerge | 367 | 110 | 0 节点 | 否 | - | - |
| ermaozi | 510 | 380 | 21 簇 / 93 节点 | 否 | - | - |
| zhuhaiuk | 30 | 25 | 2 簇 / 4 节点 | 否 | auto | - |
| ssrsub | 190 | 185 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 479 | 0 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 366 | 109 | 0 节点 | 否 | - | - |
| autojiedian | 984 | 752 | 5 簇 / 172 节点 | 否 | auto | - |
| shaoyouvip | 21 | 21 | 0 节点 | 否 | - | - |

合计产出 **3082** 节点（合并池 3082）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- passcro AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- automerge AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- snakem982 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- autojiedian AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- shaoyouvip AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1179 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 823 节点，剔除 32 节点（8 个簇）；理由 TOP：广告克隆位
- **anaer**：审 34 节点，剔除 3 节点（2 个簇）；理由 TOP：说明类占位符，本地测试地址
- **passcro**：审 0 节点，剔除 0 节点（全部批次失败）
- **automerge**：审 0 节点，剔除 0 节点（全部批次失败）
- **ermaozi**：审 452 节点，剔除 93 节点（21 个簇）；理由 TOP：广告克隆位，广告位，广告域名，广告网站引流，订阅地址本身
- **zhuhaiuk**：审 29 节点，剔除 4 节点（2 个簇）；理由 TOP：server域名异常
- **ssrsub**：审 185 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 0 节点
- **snakem982**：审 0 节点，剔除 0 节点（全部批次失败）
- **nomorewalls**：审 109 节点，剔除 0 节点
- **autojiedian**：审 752 节点，剔除 172 节点（5 个簇）（墙钟预算用尽，未审）；理由 TOP：广告营销位
- **shaoyouvip**：审 0 节点，剔除 0 节点（全部批次失败）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
