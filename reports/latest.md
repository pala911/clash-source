# clash-source 运行报告

- 生成时间：2026-10-17 20:42:35（UTC 记录：2026-10-17T20:42:32Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、automerge |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 68.5% | 本机 68.5% |
| autojiedian | 23.0% | 本机 23.0% |
| automerge | 17.5% | 本机 17.5% |
| ermaozi | 7.8% | 本机 7.8% 低于 8% |
| nomorewalls | 14.1% | 本机 14.1% |
| passcro | 14.5% | 本机 14.5% |
| ruk1ng001 | 28.9% | 本机 28.9% |
| shaoyouvip | 15.9% | 本机 15.9% |
| snakem982 | 6.7% | 本机 6.7% 低于 8% |
| ssrsub | 44.1% | 本机 44.1% |
| yypool | 16.6% | 本机 16.6% |
| zhuhaiuk | 38.8% | 本机 38.8% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1599 | 900 | - | 否 | - | - |
| anaer | 39 | 31 | - | 否 | auto | - |
| passcro | 149 | 144 | - | 否 | - | - |
| automerge | 449 | 189 | - | 否 | auto | - |
| ermaozi | 510 | 392 | - | 否 | 观察 | - |
| zhuhaiuk | 30 | 24 | - | 否 | auto | - |
| ssrsub | 193 | 192 | - | 否 | auto | - |
| ruk1ng001 | 500 | 394 | - | 否 | auto | - |
| snakem982 | 62 | 62 | - | 否 | 观察 | - |
| nomorewalls | 543 | 278 | - | 否 | - | - |
| autojiedian | 956 | 905 | - | 否 | auto | - |
| shaoyouvip | 102 | 101 | - | 否 | - | - |

合计产出 **3612** 节点（合并池 3612）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1270 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要


## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
