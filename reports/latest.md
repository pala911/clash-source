# clash-source 运行报告

- 生成时间：2026-10-15 02:50:37（UTC 记录：2026-10-15T02:50:33Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 备注 |
|---|---:|---:|---:|---|---|
| yypool | 1730 | 900 | - | 否 | - |
| anaer | 38 | 31 | - | 否 | - |
| passcro | 149 | 144 | - | 否 | - |
| automerge | 534 | 266 | - | 否 | - |
| ermaozi | 595 | 527 | - | 否 | - |
| zhuhaiuk | 34 | 34 | - | 否 | - |
| ssrsub | 161 | 160 | - | 否 | - |
| ruk1ng001 | 488 | 451 | - | 否 | - |
| snakem982 | 63 | 63 | - | 否 | - |
| nomorewalls | 515 | 254 | - | 否 | - |
| autojiedian | 927 | 892 | - | 否 | - |
| shaoyouvip | 101 | 101 | - | 否 | - |

合计产出 **3823** 节点（合并池 3823）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1429 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要


## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
