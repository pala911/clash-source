# clash-source 运行报告

- 生成时间：2026-11-17 08:06:12（UTC 记录：2026-11-17T08:06:12Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | shaoyouvip、nomorewalls、Free-Nodes |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 未生成：达标且能在本轮稳定池里对上的节点只有 2 个（< 4） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 20.8% | 本机 20.8%（达标，但 AUTO 只取前 4） |
| leilaomi | 55.2% | 本机 55.2% |
| nomorewalls | 22.1% | 本机 22.1%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 61.9% | 本机 61.9% |
| shaoyouvip | 32.5% | 本机 32.5%（达标，但 AUTO 只取前 4） |
| ssrsub | 58.6% | 本机 58.6% |
| zhuhaiuk | 71.5% | 本机 71.5% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| zhuhaiuk | 37 | 37 | 0 节点 | 否 | auto | - |
| ssrsub | 444 | 410 | 2 簇 / 4 节点 | 否 | auto | 跨源去重 -21 |
| ruk1ng001 | 245 | 120 | 40 簇 / 40 节点 | 否 | auto | 跨源去重 -1 |
| nomorewalls | 277 | 43 | 0 节点 | 否 | 备用 | 跨源去重 -30 |
| shaoyouvip | 19 | 6 | 0 节点 | 否 | 备用 | 跨源去重 -12 |
| leilaomi | 27 | 24 | 0 节点 | 否 | auto | 跨源去重 -2 |
| Free-Nodes | 70 | 21 | 0 节点 | 否 | 备用 | 跨源去重 -13 |

合计产出 **661** 节点（合并池 661；跨源内容去重剔除 79）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- 视频组未生成：达标且能在本轮稳定池里对上的节点只有 2 个（< 4）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 37 节点，剔除 0 节点
- **ssrsub**：审 435 节点，剔除 4 节点（2 个簇）；理由 TOP：引流广告
- **ruk1ng001**：审 159 节点，剔除 40 节点（40 个簇）；理由 TOP：广告营销位，广告，广告克隆，引流广告位，引流广告
- **nomorewalls**：审 73 节点，剔除 0 节点
- **shaoyouvip**：审 18 节点，剔除 0 节点
- **leilaomi**：审 26 节点，剔除 0 节点
- **Free-Nodes**：审 34 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
