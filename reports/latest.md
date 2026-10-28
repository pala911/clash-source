# clash-source 运行报告

- 生成时间：2026-10-28 22:51:54（UTC 记录：2026-10-28T22:51:52Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、anaer、ssrsub、shaoyouvip、ruk1ng001、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982、clashdaily、leilaomi、wzmfree |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 55.1% | 本机 55.1% |
| autojiedian | 19.8% | 本机 19.8% |
| automerge | 27.5% | 本机 27.5% |
| clashdaily | - | 无本机探针数据 |
| ermaozi | 6.8% | 本机 6.8% 低于 8% |
| leilaomi | - | 无本机探针数据 |
| nomorewalls | 23.8% | 本机 23.8% |
| passcro | 63.3% | 本机 63.3% |
| ruk1ng001 | 28.8% | 本机 28.8% |
| shaoyouvip | 29.4% | 本机 29.4% |
| snakem982 | 2.7% | 本机 2.7% 低于 8% |
| ssrsub | 39.8% | 本机 39.8% |
| wzmfree | - | 无本机探针数据 |
| yypool | 15.5% | 本机 15.5% |
| zhuhaiuk | 27.7% | 本机 27.7% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1239 | 900 | 11 簇 / 42 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 347 | 114 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 338 | 259 | 10 簇 / 33 节点 | 否 | 观察 | - |
| zhuhaiuk | 30 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 171 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 426 | 15 簇 / 15 节点 | 否 | auto | - |
| snakem982 | 59 | 59 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 347 | 113 | 2 簇 / 11 节点 | 否 | - | - |
| autojiedian | 347 | 321 | 3 簇 / 9 节点 | 否 | - | - |
| shaoyouvip | 101 | 101 | 0 节点 | 否 | auto | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | 观察 | - |
| leilaomi | 66 | 49 | 3 簇 / 9 节点 | 否 | 观察 | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2620** 节点（合并池 2620）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- wzmfree AI 剔除超阈值，已整体回滚
- yypool 产出 946 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 627 节点，剔除 42 节点（11 个簇）；理由 TOP：订阅地址，群组引流广告位，占位符标记，订阅地址引流，伪装节点营销位
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 124 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告位
- **ermaozi**：审 292 节点，剔除 33 节点（10 个簇）；理由 TOP：广告位，伪装
- **zhuhaiuk**：审 29 节点，剔除 0 节点
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 202 节点，剔除 15 节点（15 个簇）；理由 TOP：名称含表情符号伪装
- **snakem982**：审 59 节点，剔除 0 节点
- **nomorewalls**：审 124 节点，剔除 11 节点（2 个簇）；理由 TOP：占位符节点名，引流广告节点
- **autojiedian**：审 330 节点，剔除 9 节点（3 个簇）；理由 TOP：免费VPN广告位，广告导航站，促销服务器占位
- **shaoyouvip**：审 101 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 58 节点，剔除 9 节点（3 个簇）；理由 TOP：占位符Channel，占位符EPODONIOS，占位符[80101]
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
