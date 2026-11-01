# clash-source 运行报告

- 生成时间：2026-11-01 13:42:00（UTC 记录：2026-11-01T13:41:57Z）
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
| yypool | 1297 | 900 | 14 簇 / 39 节点 | 否 | - | - |
| automerge | 366 | 98 | 0 节点 | 否 | - | - |
| ermaozi | 499 | 445 | 3 簇 / 6 节点 | 否 | - | - |
| zhuhaiuk | 32 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 439 | 15 簇 / 24 节点 | 否 | auto | - |
| snakem982 | 60 | 31 | 4 簇 / 29 节点 | 否 | 观察 | - |
| nomorewalls | 375 | 87 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 400 | 387 | 0 节点 | 否 | 观察 | - |
| shaoyouvip | 14 | 6 | 6 簇 / 8 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 98 | 88 | 4 簇 / 4 节点 | 否 | auto | - |

合计产出 **2776** 节点（合并池 2776）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- automerge AI 剔除超阈值，已整体回滚
- yypool 产出 960 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 594 节点，剔除 39 节点（14 个簇）；理由 TOP：订阅地址本身，广告位克隆，广告/占位符，剩余流量0.0MB，引流广告位
- **automerge**：审 98 节点，剔除 0 节点（超阈值已回滚）
- **ermaozi**：审 418 节点，剔除 6 节点（3 个簇）；理由 TOP：同簇重复，伪装境内，广告位
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 223 节点，剔除 24 节点（15 个簇）；理由 TOP：伪装名称非真实国名
- **snakem982**：审 60 节点，剔除 29 节点（4 个簇）；理由 TOP：伪装伊朗服务器为破解站，伪装美国但服务器为携程，伪装台湾但服务器为携程，伪装西班牙但服务器为携程
- **nomorewalls**：审 97 节点，剔除 10 节点（1 个簇）；理由 TOP：占位符失效
- **autojiedian**：审 380 节点，剔除 0 节点
- **shaoyouvip**：审 14 节点，剔除 8 节点（6 个簇）；理由 TOP：广告位
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 92 节点，剔除 4 节点（4 个簇）；理由 TOP：Cloudflare IP伪装

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
