# clash-source 运行报告

- 生成时间：2026-11-16 06:46:09（UTC 记录：2026-11-16T06:46:08Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | nomorewalls、snakem982 |
| 观察 | 本机实测不达标 | Free-Nodes |
| 视频 | 本机实测高带宽（手动切） | 8 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 0.0% | 本机 0 活 |
| leilaomi | 57.1% | 本机 57.1% |
| nomorewalls | 24.2% | 本机 24.2%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 65.6% | 本机 65.6% |
| snakem982 | 17.1% | 本机 17.1%（达标，但 AUTO 只取前 4） |
| ssrsub | 65.4% | 本机 65.4% |
| zhuhaiuk | 74.4% | 本机 74.4% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| zhuhaiuk | 34 | 34 | 0 节点 | 否 | auto | - |
| ssrsub | 403 | 267 | 0 节点 | 否 | auto | 跨源去重 -126 |
| ruk1ng001 | 590 | 386 | 6 簇 / 6 节点 | 否 | auto | 跨源去重 -1 |
| snakem982 | 64 | 55 | 0 节点 | 否 | 备用 | 跨源去重 -7 |
| nomorewalls | 366 | 64 | 7 簇 / 17 节点 | 否 | 备用 | 跨源去重 -51 |
| leilaomi | 44 | 28 | 2 簇 / 2 节点 | 否 | auto | 跨源去重 -8 |
| Free-Nodes | 105 | 33 | 0 节点 | 否 | 观察 | 跨源去重 -14 |

合计产出 **867** 节点（合并池 867；跨源内容去重剔除 207）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- zhuhaiuk AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 34 节点，剔除 0 节点（超阈值已回滚）
- **ssrsub**：审 393 节点，剔除 0 节点
- **ruk1ng001**：审 150 节点，剔除 6 节点（6 个簇）；理由 TOP：引流广告伪装，名称与server不符，speednode占位符，伪装国籍，占位符
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 132 节点，剔除 17 节点（7 个簇）；理由 TOP：占位符服务器，占位符示例，引流广告位，群组引流广告
- **leilaomi**：审 38 节点，剔除 2 节点（2 个簇）；理由 TOP：伪装意大利标伊朗名
- **Free-Nodes**：审 47 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
