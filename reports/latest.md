# clash-source 运行报告

- 生成时间：2026-10-25 11:46:18（UTC 记录：2026-10-25T11:46:16Z）
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
| yypool | 1472 | 900 | 30 簇 / 190 节点 | 否 | - | - |
| anaer | 41 | 34 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 29 | 24 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 379 | 110 | 3 簇 / 14 节点 | 否 | - | - |
| ermaozi | 493 | 432 | 2 簇 / 4 节点 | 否 | 观察 | - |
| zhuhaiuk | 30 | 30 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 183 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 440 | 0 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 359 | 99 | 2 簇 / 12 节点 | 否 | - | - |
| autojiedian | 353 | 324 | 2 簇 / 2 节点 | 否 | - | - |
| shaoyouvip | 28 | 28 | 0 节点 | 否 | auto | - |

合计产出 **2666** 节点（合并池 2666）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1028 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 855 节点，剔除 190 节点（30 个簇）；理由 TOP：广告引流位，广告引流节点，广告位，占位符，流量为0.0MB
- **anaer**：审 35 节点，剔除 1 节点（1 个簇）；理由 TOP：失效提示占位符
- **passcro**：审 25 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **automerge**：审 124 节点，剔除 14 节点（3 个簇）；理由 TOP：speednode广告位，群组引流广告位
- **ermaozi**：审 417 节点，剔除 4 节点（2 个簇）；理由 TOP：引流网站，名称声称美国，域名为伊朗
- **zhuhaiuk**：审 30 节点，剔除 0 节点
- **ssrsub**：审 183 节点，剔除 0 节点
- **ruk1ng001**：审 220 节点，剔除 0 节点
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 111 节点，剔除 12 节点（2 个簇）；理由 TOP：广告引流节点，伪装节点server异常
- **autojiedian**：审 326 节点，剔除 2 节点（2 个簇）；理由 TOP：占位符示例节点
- **shaoyouvip**：审 28 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
