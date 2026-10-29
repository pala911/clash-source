# clash-source 运行报告

- 生成时间：2026-10-29 23:01:51（UTC 记录：2026-10-29T23:01:48Z）
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
| yypool | 1065 | 760 | 30 簇 / 75 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 414 | 177 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 374 | 196 | 23 簇 / 133 节点 | 否 | 观察 | - |
| zhuhaiuk | 32 | 32 | 0 节点 | 否 | auto | - |
| ssrsub | 134 | 133 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 447 | 0 节点 | 否 | - | - |
| snakem982 | 64 | 64 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 322 | 83 | 2 簇 / 12 节点 | 否 | - | - |
| autojiedian | 366 | 352 | 2 簇 / 2 节点 | 否 | - | - |
| shaoyouvip | 100 | 95 | 4 簇 / 5 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 71 | 59 | 1 簇 / 1 节点 | 否 | auto | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2479** 节点（合并池 2479）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- snakem982 AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- wzmfree AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 497 节点，剔除 75 节点（30 个簇）；理由 TOP：订阅地址本身，广告/引流节点簇，广告位，占位符测试网地址，广告引流克隆位
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 187 节点，剔除 10 节点（1 个簇）；理由 TOP：广告
- **ermaozi**：审 329 节点，剔除 133 节点（23 个簇）；理由 TOP：广告位，广告网站引流，Telegram引流，群组引流/含用户名，IP伪装意大利
- **zhuhaiuk**：审 32 节点，剔除 0 节点
- **ssrsub**：审 133 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 0 节点
- **snakem982**：审 0 节点，剔除 0 节点（全部批次失败）
- **nomorewalls**：审 95 节点，剔除 12 节点（2 个簇）；理由 TOP：引流广告节点，server为速度指标失效
- **autojiedian**：审 345 节点，剔除 2 节点（2 个簇）；理由 TOP：占位符示例，staging失效提示
- **shaoyouvip**：审 100 节点，剔除 5 节点（4 个簇）；理由 TOP：营销位克隆
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 60 节点，剔除 1 节点（1 个簇）；理由 TOP：伪装美国节点
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
