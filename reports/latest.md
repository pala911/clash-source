# clash-source 运行报告

- 生成时间：2026-10-16 16:44:39（UTC 记录：2026-10-16T16:44:36Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、automerge、autojiedian |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 58.5% | 本机 58.5% |
| autojiedian | 17.8% | 本机 17.8% |
| automerge | 18.2% | 本机 18.2% |
| ermaozi | 6.8% | 本机 6.8% 低于 8% |
| nomorewalls | 12.9% | 本机 12.9% |
| passcro | 13.9% | 本机 13.9% |
| ruk1ng001 | 23.9% | 本机 23.9% |
| shaoyouvip | 11.9% | 本机 11.9% |
| snakem982 | 5.8% | 本机 5.8% 低于 8% |
| ssrsub | 41.3% | 本机 41.3% |
| yypool | 15.2% | 本机 15.2% |
| zhuhaiuk | 32.3% | 本机 32.3% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1777 | 900 | - | 否 | - | - |
| anaer | 39 | 32 | - | 否 | auto | - |
| passcro | 149 | 144 | - | 否 | - | - |
| automerge | 453 | 201 | - | 否 | auto | - |
| ermaozi | 484 | 351 | - | 否 | 观察 | - |
| zhuhaiuk | 28 | 26 | - | 否 | auto | - |
| ssrsub | 223 | 222 | - | 否 | auto | - |
| ruk1ng001 | 500 | 402 | - | 否 | auto | - |
| snakem982 | 63 | 61 | - | 否 | 观察 | - |
| nomorewalls | 455 | 188 | - | 否 | - | - |
| autojiedian | 952 | 887 | - | 否 | auto | - |
| shaoyouvip | 9 | 9 | - | 否 | - | - |

合计产出 **3423** 节点（合并池 3423）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1458 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要


## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
