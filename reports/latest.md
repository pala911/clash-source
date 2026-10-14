# clash-source 运行报告

- 生成时间：2026-10-14 11:46:51（UTC 记录：2026-10-14T03:46:47Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 备注 |
|---|---:|---:|---:|---|---|
| yypool | 1767 | 900 | - | 否 | - |
| anaer | 21 | 14 | - | 否 | - |
| passcro | 149 | 144 | - | 否 | - |
| automerge | 534 | 262 | - | 否 | - |
| ermaozi | 598 | 548 | - | 否 | - |
| zhuhaiuk | 35 | 35 | - | 否 | - |
| ssrsub | 177 | 176 | - | 否 | - |
| ruk1ng001 | 500 | 479 | - | 否 | - |
| snakem982 | 60 | 59 | - | 否 | - |
| nomorewalls | 533 | 261 | - | 否 | - |
| autojiedian | 944 | 905 | - | 否 | - |
| shaoyouvip | 100 | 100 | - | 否 | - |

合计产出 **3883** 节点（合并池 3883）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1375 超过 max_nodes=900，已截断（考虑淘汰最差尾部）

## 硬过滤命中 TOP（按源）

- **yypool**：命名命中 exclude-filter×314，不支持的协议 hysteria×3
- **anaer**：不支持的协议 hysteria×2
- **automerge**：命名命中 exclude-filter×240，不支持的协议 hysteria×3
- **ermaozi**：命名命中 exclude-filter×11，不支持的协议 hysteria×3
- **ssrsub**：命名命中 exclude-filter×1
- **snakem982**：不支持的协议 hysteria×1
- **nomorewalls**：命名命中 exclude-filter×240，不支持的协议 hysteria×3
- **autojiedian**：有 obfs/plugin 但缺 obfs-password（会让整个 provider 加载失败）×7，不支持的协议 hysteria×1

## AI 处置摘要

- **yypool**：审 0，剔除 0；理由 TOP：广告位，同server，server字段异常，占位符，失效提示日期
- **anaer**：审 0，剔除 0；理由 TOP：占位符说明
- **passcro**：审 0，剔除 0；理由 TOP：占位符失效提示
- **automerge**：审 0，剔除 0；理由 TOP：广告引流节点
- **ermaozi**：审 0，剔除 0；理由 TOP：伪装，广告位，引流/广告/群组引流
- **zhuhaiuk**：审 0，剔除 0
- **ssrsub**：审 0，剔除 0
- **ruk1ng001**：审 0，剔除 0；理由 TOP：广告节点簇
- **snakem982**：审 0，剔除 0
- **nomorewalls**：审 0，剔除 0；理由 TOP：广告引流节点
- **autojiedian**：审 0，剔除 0
- **shaoyouvip**：审 0，剔除 0

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
