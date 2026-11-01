# clash-source 运行报告

- 生成时间：2026-11-01 18:42:51（UTC 记录：2026-11-01T18:42:49Z）
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
| yypool | 1205 | 877 | 12 簇 / 38 节点 | 否 | - | - |
| automerge | 372 | 68 | 3 簇 / 27 节点 | 否 | - | - |
| ermaozi | 499 | 422 | 8 簇 / 29 节点 | 否 | - | - |
| zhuhaiuk | 32 | 26 | 1 簇 / 5 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 468 | 1 簇 / 1 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 375 | 87 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 379 | 365 | 1 簇 / 1 节点 | 否 | 观察 | - |
| shaoyouvip | 100 | 91 | 3 簇 / 7 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 82 | 76 | 2 簇 / 3 节点 | 否 | auto | - |

合计产出 **2806** 节点（合并池 2806）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 542 节点，剔除 38 节点（12 个簇）；理由 TOP：伪装海外节点，引流，伪装，广告位，名称含D🔴及广告标识
- **automerge**：审 95 节点，剔除 27 节点（3 个簇）；理由 TOP： piracy引流，占位符示例节点， 境外势力渗透营销位
- **ermaozi**：审 418 节点，剔除 29 节点（8 个簇）；理由 TOP：导航站，失效提示占位符，广告引流节点，群组引流
- **zhuhaiuk**：审 31 节点，剔除 5 节点（1 个簇）；理由 TOP：伪装营销位
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 227 节点，剔除 1 节点（1 个簇）；理由 TOP：广告位克隆节点
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 97 节点，剔除 10 节点（1 个簇）；理由 TOP：国内广告/中转节点
- **autojiedian**：审 366 节点，剔除 1 节点（1 个簇）；理由 TOP：promo为广告引流域名
- **shaoyouvip**：审 98 节点，剔除 7 节点（3 个簇）；理由 TOP：节点名为占位符Other，server为占位符格式，伪装为HK但用携程服务器
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 79 节点，剔除 3 节点（2 个簇）；理由 TOP：server为境内IP，同簇节点数为2

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
