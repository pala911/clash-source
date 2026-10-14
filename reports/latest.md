# clash-source 运行报告

- 生成时间：2026-10-14 09:18:53（UTC 记录：2026-10-14T09:18:49Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 备注 |
|---|---:|---:|---:|---|---|
| yypool | 1700 | 900 | - | 否 | - |
| anaer | 21 | 14 | - | 否 | - |
| passcro | 149 | 144 | - | 否 | - |
| automerge | 524 | 248 | - | 否 | - |
| ermaozi | 598 | 459 | - | 否 | - |
| zhuhaiuk | 32 | 31 | - | 否 | - |
| ssrsub | 161 | 160 | - | 否 | - |
| ruk1ng001 | 500 | 480 | - | 否 | - |
| snakem982 | 61 | 60 | - | 否 | - |
| nomorewalls | 457 | 178 | - | 否 | - |
| autojiedian | 967 | 927 | - | 否 | - |
| shaoyouvip | 16 | 16 | - | 否 | - |

合计产出 **3617** 节点（合并池 3617）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1438 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要


## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
