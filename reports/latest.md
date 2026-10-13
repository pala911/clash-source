# clash-source 运行报告

- 生成时间：2026-10-13 23:40:30（UTC 记录：2026-10-13T15:40:23Z）
- AI 模式：`off`
- 订阅入口：`https://YOUR_GITHUB_ID.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/YOUR_GITHUB_ID/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/YOUR_GITHUB_ID/clash-source@gh-pages/profile.yaml`

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 备注 |
|---|---:|---:|---:|---|---|
| yypool | 1725 | 900 | 0 | 是 | 直连失败走镜像 |
| anaer | 39 | 33 | 0 | 否 | - |
| passcro | 149 | 145 | 0 | 否 | - |
| automerge | 512 | 235 | 0 | 否 | - |
| ermaozi | 534 | 500 | 0 | 否 | - |
| zhuhaiuk | 34 | 34 | 0 | 否 | - |
| ssrsub | 176 | 175 | 0 | 否 | - |
| ruk1ng001 | 500 | 480 | 0 | 否 | - |
| snakem982 | 54 | 53 | 0 | 否 | - |
| nomorewalls | 477 | 203 | 0 | 否 | - |
| autojiedian | 2137 | 2093 | 0 | 否 | - |
| shaoyouvip | 1 | 1 | 0 | 否 | - |

合计产出 **4852** 节点（合并池 4852）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1433 超过 max_nodes=900，已截断（考虑淘汰最差尾部）
- 未指定 GitHub 用户名，profile 里的订阅地址是占位符 YOUR_GITHUB_ID（CI 上会自动取真实值；本地预览请传 --owner）

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

本轮未启用 AI（未配置 `AI_BASE_URL`/`AI_API_KEY`，或显式 `--ai-mode off`）。

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
