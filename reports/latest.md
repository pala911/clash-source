# clash-source 运行报告

- 生成时间：2026-11-13 19:52:25（UTC 记录：2026-11-13T19:52:24Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ssrsub、leilaomi、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、ermaozi、snakem982 |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 未生成：达标且能在本轮稳定池里对上的节点只有 3 个（< 4） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| ermaozi | 9.3% | 本机 9.3%（达标，但 AUTO 只取前 4） |
| leilaomi | 61.3% | 本机 61.3% |
| nomorewalls | 34.8% | 本机 34.8%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 54.4% | 本机 54.4% |
| snakem982 | 8.8% | 本机 8.8%（达标，但 AUTO 只取前 4） |
| ssrsub | 65.5% | 本机 65.5% |
| zhuhaiuk | 71.0% | 本机 71.0% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| ermaozi | 444 | 271 | 10 簇 / 23 节点 | 否 | 备用 | 跨源去重 -96 |
| zhuhaiuk | 34 | 34 | 0 节点 | 否 | auto | - |
| ssrsub | 369 | 357 | 0 节点 | 否 | auto | 跨源去重 -1 |
| ruk1ng001 | 287 | 121 | 4 簇 / 4 节点 | 否 | auto | 跨源去重 -46 |
| snakem982 | 64 | 32 | 2 簇 / 13 节点 | 否 | 备用 | 跨源去重 -17 |
| nomorewalls | 336 | 55 | 3 簇 / 14 节点 | 否 | 备用 | 跨源去重 -27 |
| leilaomi | 68 | 58 | 0 节点 | 否 | auto | 跨源去重 -6 |

合计产出 **928** 节点（合并池 928；跨源内容去重剔除 193）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- 视频组未生成：达标且能在本轮稳定池里对上的节点只有 3 个（< 4）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **ermaozi**：审 381 节点，剔除 23 节点（10 个簇）；理由 TOP：群组引流，明显伪装，占位符，引流/广告/伪装，引流广告
- **zhuhaiuk**：审 34 节点，剔除 0 节点
- **ssrsub**：审 358 节点，剔除 0 节点
- **ruk1ng001**：审 150 节点，剔除 4 节点（4 个簇）；理由 TOP：speed测试节点占位，伪装为德国实为境内中转，引流广告
- **snakem982**：审 62 节点，剔除 13 节点（2 个簇）；理由 TOP：意大利节点server为境内中转，新加坡节点server为境内中转
- **nomorewalls**：审 96 节点，剔除 14 节点（3 个簇）；理由 TOP：引流广告位，引流广告，群组引流
- **leilaomi**：审 64 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
