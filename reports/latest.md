# clash-source 运行报告

- 生成时间：2026-11-01 17:23:17（UTC 记录：2026-11-01T17:23:14Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、clashdaily、leilaomi、ssrsub、ruk1ng001、shaoyouvip |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | autojiedian、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| autojiedian | 7.0% | 本机 7.0% 低于 8% |
| automerge | 26.1% | 本机 26.1% |
| clashdaily | 39.4% | 本机 39.4% |
| ermaozi | 8.8% | 本机 8.8% |
| leilaomi | 34.7% | 本机 34.7% |
| nomorewalls | 25.8% | 本机 25.8% |
| ruk1ng001 | 29.0% | 本机 29.0% |
| shaoyouvip | 26.9% | 本机 26.9% |
| snakem982 | 3.7% | 本机 3.7% 低于 8% |
| ssrsub | 34.0% | 本机 34.0% |
| yypool | 15.7% | 本机 15.7% |
| zhuhaiuk | 42.2% | 本机 42.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1205 | 838 | 25 簇 / 77 节点 | 否 | - | - |
| automerge | 372 | 94 | 1 簇 / 1 节点 | 否 | - | - |
| ermaozi | 499 | 388 | 34 簇 / 63 节点 | 否 | - | - |
| zhuhaiuk | 32 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 425 | 19 簇 / 44 节点 | 否 | auto | - |
| snakem982 | 62 | 53 | 3 簇 / 9 节点 | 否 | 观察 | - |
| nomorewalls | 375 | 85 | 2 簇 / 12 节点 | 否 | - | - |
| autojiedian | 379 | 356 | 4 簇 / 10 节点 | 否 | 观察 | - |
| shaoyouvip | 8 | 8 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 98 | 92 | 0 节点 | 否 | auto | - |

合计产出 **2634** 节点（合并池 2634）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- shaoyouvip AI 部分批次不可用（相关批次保留全部节点）：全部批次失败

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 542 节点，剔除 77 节点（25 个簇）；理由 TOP：订阅地址引流，伪装外国服务器，server为速度占位符，订阅地址本身，含服务器IP伪装
- **automerge**：审 95 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符Other_1
- **ermaozi**：审 418 节点，剔除 63 节点（34 个簇）；理由 TOP：占位符，群组引流，广告位引流，导航站，境内中转伪装
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 227 节点，剔除 44 节点（19 个簇）；理由 TOP：广告克隆节点，短域名，广告位，营销IP，拼写异常
- **snakem982**：审 62 节点，剔除 9 节点（3 个簇）；理由 TOP：伪装同服务器中转节点
- **nomorewalls**：审 97 节点，剔除 12 节点（2 个簇）；理由 TOP：广告位，占位符
- **autojiedian**：审 366 节点，剔除 10 节点（4 个簇）；理由 TOP：其他地区占位符
- **shaoyouvip**：审 0 节点，剔除 0 节点（全部批次失败）
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 92 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
