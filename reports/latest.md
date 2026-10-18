# clash-source 运行报告

- 生成时间：2026-10-18 20:55:38（UTC 记录：2026-10-18T20:55:36Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、shaoyouvip |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 76.2% | 本机 76.2% |
| autojiedian | 26.1% | 本机 26.1% |
| automerge | 15.9% | 本机 15.9% |
| ermaozi | 8.0% | 本机 8.0% 低于 8% |
| nomorewalls | 14.9% | 本机 14.9% |
| passcro | 15.0% | 本机 15.0% |
| ruk1ng001 | 32.5% | 本机 32.5% |
| shaoyouvip | 21.3% | 本机 21.3% |
| snakem982 | 6.3% | 本机 6.3% 低于 8% |
| ssrsub | 45.8% | 本机 45.8% |
| yypool | 17.5% | 本机 17.5% |
| zhuhaiuk | 43.1% | 本机 43.1% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1630 | 900 | 38 簇 / 121 节点 | 否 | - | - |
| anaer | 39 | 33 | 0 节点 | 否 | auto | - |
| passcro | 149 | 144 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 450 | 188 | 3 簇 / 16 节点 | 否 | - | - |
| ermaozi | 497 | 418 | 13 簇 / 36 节点 | 否 | 观察 | - |
| zhuhaiuk | 31 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 181 | 176 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 413 | 13 簇 / 66 节点 | 否 | auto | - |
| snakem982 | 60 | 48 | 3 簇 / 12 节点 | 否 | 观察 | - |
| nomorewalls | 532 | 276 | 2 簇 / 14 节点 | 否 | - | - |
| autojiedian | 883 | 721 | 6 簇 / 130 节点 | 否 | auto | - |
| shaoyouvip | 100 | 98 | 1 簇 / 1 节点 | 否 | auto | - |

合计产出 **3444** 节点（合并池 3444）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- zhuhaiuk AI 剔除超阈值，已整体回滚
- yypool 产出 1248 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 1019 节点，剔除 121 节点（38 个簇）；理由 TOP：订阅地址本身，死节点，占位符，群组引流，引流链接
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 145 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例失效
- **automerge**：审 204 节点，剔除 16 节点（3 个簇）；理由 TOP：引流/境外势力渗透广告位，群组引流广告位，占位符示例节点
- **ermaozi**：审 454 节点，剔除 36 节点（13 个簇）；理由 TOP：订阅地址引流，群组引流，群组引流地址，名称含FreeVPN促销，伪装国家路由
- **zhuhaiuk**：审 29 节点，剔除 0 节点（超阈值已回滚）
- **ssrsub**：审 176 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 66 节点（13 个簇）；理由 TOP：广告位
- **snakem982**：审 60 节点，剔除 12 节点（3 个簇）；理由 TOP：广告域名可疑，占位符可疑
- **nomorewalls**：审 290 节点，剔除 14 节点（2 个簇）；理由 TOP：引流广告占位符，引流广告
- **autojiedian**：审 688 节点，剔除 130 节点（6 个簇）；理由 TOP：广告营销位，疑似引流域名
- **shaoyouvip**：审 99 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符节点名

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
