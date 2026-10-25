# clash-source 运行报告

- 生成时间：2026-10-25 16:35:42（UTC 记录：2026-10-25T16:35:39Z）
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
| yypool | 1452 | 900 | 20 簇 / 54 节点 | 否 | - | - |
| anaer | 41 | 34 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 64 | 59 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 359 | 101 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 410 | 232 | 29 簇 / 117 节点 | 否 | 观察 | - |
| zhuhaiuk | 30 | 30 | 0 节点 | 否 | auto | - |
| ssrsub | 176 | 171 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 398 | 15 簇 / 57 节点 | 否 | auto | - |
| snakem982 | 63 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 380 | 97 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 336 | 315 | 0 节点 | 否 | - | - |
| shaoyouvip | 3 | 3 | 0 节点 | 否 | auto | - |

合计产出 **2402** 节点（合并池 2402）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1128 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 804 节点，剔除 54 节点（20 个簇）；理由 TOP：占位符示例，订阅地址本身，订阅地址引流，ProxyPool引流，伪装为中国节点
- **anaer**：审 35 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符/失效提示
- **passcro**：审 60 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **automerge**：审 111 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告位
- **ermaozi**：审 348 节点，剔除 117 节点（29 个簇）；理由 TOP：同簇广告，server为占位符，hysteria2占位，保加利亚广告位克隆，罗马尼亚广告位克隆
- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 171 节点，剔除 0 节点
- **ruk1ng001**：审 228 节点，剔除 57 节点（15 个簇）；理由 TOP：广告引流位，整簇剔除
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 107 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告节点
- **autojiedian**：审 315 节点，剔除 0 节点
- **shaoyouvip**：审 3 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
