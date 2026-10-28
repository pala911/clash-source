# clash-source 运行报告

- 生成时间：2026-10-28 05:59:40（UTC 记录：2026-10-28T05:59:39Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、anaer、ssrsub、shaoyouvip、ruk1ng001、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 55.1% | 本机 55.1% |
| autojiedian | 19.8% | 本机 19.8% |
| automerge | 27.5% | 本机 27.5% |
| ermaozi | 6.8% | 本机 6.8% 低于 8% |
| nomorewalls | 23.8% | 本机 23.8% |
| passcro | 63.3% | 本机 63.3% |
| ruk1ng001 | 28.8% | 本机 28.8% |
| shaoyouvip | 29.4% | 本机 29.4% |
| snakem982 | 2.7% | 本机 2.7% 低于 8% |
| ssrsub | 39.8% | 本机 39.8% |
| yypool | 15.5% | 本机 15.5% |
| zhuhaiuk | 27.7% | 本机 27.7% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1279 | 900 | 18 簇 / 83 节点 | 否 | - | - |
| anaer | 39 | 30 | 2 簇 / 3 节点 | 否 | auto | - |
| passcro | 48 | 43 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 392 | 154 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 467 | 334 | 25 簇 / 85 节点 | 否 | 观察 | - |
| zhuhaiuk | 37 | 32 | 2 簇 / 2 节点 | 否 | auto | - |
| ssrsub | 171 | 168 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 438 | 0 节点 | 否 | auto | - |
| snakem982 | 64 | 64 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 350 | 96 | 4 簇 / 19 节点 | 否 | - | - |
| autojiedian | 309 | 292 | 1 簇 / 1 节点 | 否 | - | - |
| shaoyouvip | 45 | 45 | 0 节点 | 否 | auto | - |

合计产出 **2596** 节点（合并池 2596）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 909 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 630 节点，剔除 83 节点（18 个簇）；理由 TOP：订阅地址引流，广告地址，占位符，引流广告，引流广告位
- **anaer**：审 33 节点，剔除 3 节点（2 个簇）；理由 TOP：占位符示例节点，营销推广域名
- **passcro**：审 44 节点，剔除 1 节点（1 个簇）；理由 TOP：示例节点
- **automerge**：审 165 节点，剔除 11 节点（2 个簇）；理由 TOP：伪装英国服务器伊朗域名，广告内容
- **ermaozi**：审 402 节点，剔除 85 节点（25 个簇）；理由 TOP：广告位引流，占位符，占位符服务器，广告位，引流/群组
- **zhuhaiuk**：审 34 节点，剔除 2 节点（2 个簇）；理由 TOP：.xin域名疑似广告位，.bid域名疑似广告位
- **ssrsub**：审 168 节点，剔除 0 节点
- **ruk1ng001**：审 216 节点，剔除 0 节点
- **snakem982**：审 64 节点，剔除 0 节点
- **nomorewalls**：审 115 节点，剔除 19 节点（4 个簇）；理由 TOP：速度占位符，server格式异常，server伪装，广告引流节点
- **autojiedian**：审 293 节点，剔除 1 节点（1 个簇）；理由 TOP：promo字样引流
- **shaoyouvip**：审 45 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
