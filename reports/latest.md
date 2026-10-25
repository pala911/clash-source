# clash-source 运行报告

- 生成时间：2026-10-25 05:00:58（UTC 记录：2026-10-25T05:00:55Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、passcro、ruk1ng001、shaoyouvip、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 83.1% | 本机 83.1% |
| autojiedian | 32.6% | 本机 32.6% |
| automerge | 24.8% | 本机 24.8% |
| ermaozi | 7.3% | 本机 7.3% 低于 8% |
| nomorewalls | 19.7% | 本机 19.7% |
| passcro | 42.0% | 本机 42.0% |
| ruk1ng001 | 37.8% | 本机 37.8% |
| shaoyouvip | 37.1% | 本机 37.1% |
| snakem982 | 4.3% | 本机 4.3% 低于 8% |
| ssrsub | 50.6% | 本机 50.6% |
| yypool | 19.3% | 本机 19.3% |
| zhuhaiuk | 33.0% | 本机 33.0% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1365 | 900 | 9 簇 / 29 节点 | 否 | - | - |
| anaer | 41 | 34 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 29 | 24 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 415 | 150 | 5 簇 / 6 节点 | 否 | - | - |
| ermaozi | 493 | 418 | 2 簇 / 18 节点 | 否 | 观察 | - |
| zhuhaiuk | 31 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 183 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 440 | 0 节点 | 否 | auto | - |
| snakem982 | 61 | 55 | 3 簇 / 6 节点 | 否 | 观察 | - |
| nomorewalls | 388 | 111 | 6 簇 / 26 节点 | 否 | - | - |
| autojiedian | 300 | 272 | 0 节点 | 否 | - | - |
| shaoyouvip | 79 | 79 | 0 节点 | 否 | auto | - |

合计产出 **2695** 节点（合并池 2695）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1042 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 727 节点，剔除 29 节点（9 个簇）；理由 TOP：订阅地址本身，staging测试环境，广告位引流，服务器非IP，引流广告链接
- **anaer**：审 35 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符说明
- **passcro**：审 25 节点，剔除 1 节点（1 个簇）；理由 TOP：说明占位符
- **automerge**：审 156 节点，剔除 6 节点（5 个簇）；理由 TOP：speednode占位符，占位符示例节点
- **ermaozi**：审 417 节点，剔除 18 节点（2 个簇）；理由 TOP：群组引流，广告引流
- **zhuhaiuk**：审 29 节点，剔除 0 节点
- **ssrsub**：审 183 节点，剔除 0 节点
- **ruk1ng001**：审 220 节点，剔除 0 节点
- **snakem982**：审 61 节点，剔除 6 节点（3 个簇）；理由 TOP：同服务器法国加拿大合并，伪装为伊朗服务器为内网
- **nomorewalls**：审 137 节点，剔除 26 节点（6 个簇）；理由 TOP：speed测试节点，引流广告占位符，占位符server，伪装为美国实际是广告
- **autojiedian**：审 272 节点，剔除 0 节点
- **shaoyouvip**：审 79 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
