# clash-source 运行报告

- 生成时间：2026-10-29 13:16:05（UTC 记录：2026-10-29T13:16:03Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、anaer、clashdaily、leilaomi、ssrsub、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982、wzmfree |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 42.7% | 本机 42.7% |
| autojiedian | 16.0% | 本机 16.0% |
| automerge | 26.1% | 本机 26.1% |
| clashdaily | 37.7% | 本机 37.7% |
| ermaozi | 7.2% | 本机 7.2% 低于 8% |
| leilaomi | 36.4% | 本机 36.4% |
| nomorewalls | 23.7% | 本机 23.7% |
| passcro | 53.2% | 本机 53.2% |
| ruk1ng001 | 28.5% | 本机 28.5% |
| shaoyouvip | 26.5% | 本机 26.5% |
| snakem982 | 3.5% | 本机 3.5% 低于 8% |
| ssrsub | 36.2% | 本机 36.2% |
| wzmfree | 0.0% | 本机 0 活 |
| yypool | 15.1% | 本机 15.1% |
| zhuhaiuk | 30.9% | 本机 30.9% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1322 | 900 | 17 簇 / 70 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 327 | 83 | 2 簇 / 13 节点 | 否 | - | - |
| ermaozi | 374 | 245 | 10 簇 / 84 节点 | 否 | 观察 | - |
| zhuhaiuk | 30 | 30 | 0 节点 | 否 | auto | - |
| ssrsub | 135 | 134 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 433 | 7 簇 / 8 节点 | 否 | - | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 308 | 68 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 418 | 375 | 7 簇 / 21 节点 | 否 | - | - |
| shaoyouvip | 9 | 9 | 0 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 84 | 75 | 0 节点 | 否 | auto | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2495** 节点（合并池 2495）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- leilaomi AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- wzmfree AI 剔除超阈值，已整体回滚
- yypool 产出 1018 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 704 节点，剔除 70 节点（17 个簇）；理由 TOP：订阅地址本身，占位符服务器，占位符节点无端口，零带宽占位符，引流广告
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 96 节点，剔除 13 节点（2 个簇）；理由 TOP：引流广告位，伪装节点
- **ermaozi**：审 329 节点，剔除 84 节点（10 个簇）；理由 TOP：广告，广告位，tg频道引流，@ripaojiedian广告
- **zhuhaiuk**：审 30 节点，剔除 0 节点
- **ssrsub**：审 134 节点，剔除 0 节点
- **ruk1ng001**：审 202 节点，剔除 8 节点（7 个簇）；理由 TOP：生成域名，特殊字符广告，名称声称台湾服务器在中国，广告伪装节点
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 78 节点，剔除 10 节点（1 个簇）；理由 TOP：广告引流节点
- **autojiedian**：审 366 节点，剔除 21 节点（7 个簇）；理由 TOP：同server克隆，同IP段克隆，服务器为占位域名，占位符示例节点
- **shaoyouvip**：审 9 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 0 节点，剔除 0 节点（全部批次失败）
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
