# clash-source 运行报告

- 生成时间：2026-10-30 22:43:00（UTC 记录：2026-10-30T22:42:57Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | leilaomi、clashdaily、zhuhaiuk、ssrsub、ruk1ng001、shaoyouvip |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| autojiedian | 12.6% | 本机 12.6% |
| automerge | 26.4% | 本机 26.4% |
| clashdaily | 37.2% | 本机 37.2% |
| ermaozi | 8.0% | 本机 8.0% 低于 8% |
| leilaomi | 41.7% | 本机 41.7% |
| nomorewalls | 25.2% | 本机 25.2% |
| ruk1ng001 | 31.0% | 本机 31.0% |
| shaoyouvip | 27.8% | 本机 27.8% |
| snakem982 | 3.9% | 本机 3.9% 低于 8% |
| ssrsub | 35.5% | 本机 35.5% |
| yypool | 16.0% | 本机 16.0% |
| zhuhaiuk | 36.6% | 本机 36.6% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1351 | 900 | 17 簇 / 86 节点 | 否 | - | - |
| automerge | 350 | 83 | 2 簇 / 12 节点 | 否 | - | - |
| ermaozi | 430 | 365 | 7 簇 / 16 节点 | 否 | 观察 | - |
| zhuhaiuk | 28 | 28 | 0 节点 | 否 | auto | - |
| ssrsub | 134 | 133 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 468 | 1 簇 / 2 节点 | 否 | auto | - |
| snakem982 | 62 | 61 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 409 | 158 | 1 簇 / 13 节点 | 否 | - | - |
| autojiedian | 347 | 329 | 3 簇 / 10 节点 | 否 | - | - |
| shaoyouvip | 100 | 100 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 80 | 40 | 1 簇 / 27 节点 | 否 | auto | - |

合计产出 **2743** 节点（合并池 2743）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1022 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 733 节点，剔除 86 节点（17 个簇）；理由 TOP：订阅地址，订阅地址本身，引流广告，ProxyPool 俄罗斯，ProxyPool 荷兰
- **automerge**：审 95 节点，剔除 12 节点（2 个簇）；理由 TOP：引流/境外势力渗透广告，server为占位符
- **ermaozi**：审 381 节点，剔除 16 节点（7 个簇）；理由 TOP：代理池推广，群组引流，VPN推广，免费VPN推广，Telegram频道引流
- **zhuhaiuk**：审 28 节点，剔除 0 节点
- **ssrsub**：审 133 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 2 节点（1 个簇）；理由 TOP：名称德国但服务器境内
- **snakem982**：审 61 节点，剔除 0 节点
- **nomorewalls**：审 171 节点，剔除 13 节点（1 个簇）；理由 TOP：引流广告位
- **autojiedian**：审 339 节点，剔除 10 节点（3 个簇）；理由 TOP：占位符域名
- **shaoyouvip**：审 100 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 67 节点，剔除 27 节点（1 个簇）；理由 TOP：批量克隆营销位

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
