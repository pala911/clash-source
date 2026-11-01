# clash-source 运行报告

- 生成时间：2026-11-01 18:14:22（UTC 记录：2026-11-01T18:14:20Z）
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
| yypool | 1205 | 866 | 15 簇 / 49 节点 | 否 | - | - |
| automerge | 372 | 51 | 5 簇 / 44 节点 | 否 | - | - |
| ermaozi | 499 | 391 | 8 簇 / 60 节点 | 否 | - | - |
| zhuhaiuk | 32 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 467 | 2 簇 / 2 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 375 | 79 | 5 簇 / 18 节点 | 否 | - | - |
| autojiedian | 379 | 348 | 6 簇 / 18 节点 | 否 | 观察 | - |
| shaoyouvip | 8 | 8 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 98 | 92 | 0 节点 | 否 | auto | - |

合计产出 **2659** 节点（合并池 2659）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- shaoyouvip AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 542 节点，剔除 49 节点（15 个簇）；理由 TOP：占位符域名，订阅地址本身，广告引流节点，伪装爱尔兰节点，占位符
- **automerge**：审 95 节点，剔除 44 节点（5 个簇）；理由 TOP：境外势力渗透广告，广告位/ piracy，伪装新加坡节点，伪装台湾节点，伪装香港节点
- **ermaozi**：审 418 节点，剔除 60 节点（8 个簇）；理由 TOP：新加坡伪装DNS解析器，境内中转伪装为爱尔兰，伪装美国，server为伊朗域名，境内中转伪装为中国，引流广告节点
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 227 节点，剔除 2 节点（2 个簇）；理由 TOP：美国节点伪装日本服务器
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 97 节点，剔除 18 节点（5 个簇）；理由 TOP：广告位克隆，占位符/失效提示，引流/广告/群组引流
- **autojiedian**：审 366 节点，剔除 18 节点（6 个簇）；理由 TOP：其他地区占位符，伪装广告位
- **shaoyouvip**：审 8 节点，剔除 0 节点（超阈值已回滚）
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 92 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
