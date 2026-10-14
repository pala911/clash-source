# clash-source 运行报告

- 生成时间：2026-10-14 01:00:49（UTC 记录：2026-10-13T17:00:37Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 备注 |
|---|---:|---:|---:|---|---|
| yypool | 1725 | 900 | 0 | 否 | - |
| anaer | 39 | 33 | 0 | 否 | - |
| passcro | 149 | 145 | 0 | 否 | - |
| automerge | 512 | 235 | 0 | 否 | - |
| ermaozi | 534 | 500 | 0 | 否 | - |
| zhuhaiuk | 31 | 31 | 0 | 否 | - |
| ssrsub | 176 | 175 | 0 | 否 | - |
| ruk1ng001 | 500 | 480 | 0 | 否 | - |
| snakem982 | 54 | 53 | 0 | 否 | - |
| nomorewalls | 477 | 203 | 0 | 否 | - |
| autojiedian | 2137 | 2093 | 0 | 否 | - |
| shaoyouvip | 1 | 1 | 0 | 否 | - |

合计产出 **4849** 节点（合并池 4849）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool AI 调用失败（已保留全部节点）：The read operation timed out
- yypool 产出 1433 超过 max_nodes=900，已截断（考虑淘汰最差尾部）
- anaer AI 调用失败（已保留全部节点）：The read operation timed out
- passcro AI 调用失败（已保留全部节点）：The read operation timed out
- automerge AI 调用失败（已保留全部节点）：The read operation timed out
- ermaozi AI 调用失败（已保留全部节点）：The read operation timed out
- zhuhaiuk AI 调用失败（已保留全部节点）：The read operation timed out
- ssrsub AI 调用失败（已保留全部节点）：The read operation timed out
- ruk1ng001 AI 调用失败（已保留全部节点）：The read operation timed out
- snakem982 AI 调用失败（已保留全部节点）：The read operation timed out
- nomorewalls AI 调用失败（已保留全部节点）：The read operation timed out
- autojiedian AI 调用失败（已保留全部节点）：The read operation timed out
- shaoyouvip AI 调用失败（已保留全部节点）：The read operation timed out

## 硬过滤命中 TOP（按源）

- **yypool**：命名命中 exclude-filter×289，不支持的协议 hysteria×3
- **anaer**：不支持的协议 hysteria×2
- **automerge**：命名命中 exclude-filter×257，不支持的协议 hysteria×3
- **ermaozi**：命名命中 exclude-filter×12，不支持的协议 hysteria×3
- **ssrsub**：命名命中 exclude-filter×1
- **snakem982**：不支持的协议 hysteria×1
- **nomorewalls**：命名命中 exclude-filter×254，不支持的协议 hysteria×3
- **autojiedian**：有 obfs/plugin 但缺 obfs-password（会让整个 provider 加载失败）×8，不支持的协议 hysteria×1

## AI 处置摘要

- **yypool**：审 0，剔除 0
- **anaer**：审 0，剔除 0
- **passcro**：审 0，剔除 0
- **automerge**：审 0，剔除 0
- **ermaozi**：审 0，剔除 0
- **zhuhaiuk**：审 0，剔除 0
- **ssrsub**：审 0，剔除 0
- **ruk1ng001**：审 0，剔除 0
- **snakem982**：审 0，剔除 0
- **nomorewalls**：审 0，剔除 0
- **autojiedian**：审 0，剔除 0
- **shaoyouvip**：审 0，剔除 0

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
