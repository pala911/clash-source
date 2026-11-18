# clash-source 运行报告

- 生成时间：2026-11-18 20:37:53（UTC 记录：2026-11-18T20:37:53Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | shaoyouvip、Free-Nodes、nomorewalls |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 8 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 26.6% | 本机 26.6%（达标，但 AUTO 只取前 4） |
| leilaomi | 56.0% | 本机 56.0% |
| nomorewalls | 21.4% | 本机 21.4%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 63.0% | 本机 63.0% |
| shaoyouvip | 32.5% | 本机 32.5%（达标，但 AUTO 只取前 4） |
| ssrsub | 56.4% | 本机 56.4% |
| zhuhaiuk | 73.4% | 本机 73.4% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| zhuhaiuk | 29 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 371 | 357 | 0 节点 | 否 | auto | 跨源去重 -8 |
| ruk1ng001 | 93 | 58 | 15 簇 / 17 节点 | 否 | auto | 跨源去重 -1 |
| nomorewalls | 282 | 35 | 4 簇 / 17 节点 | 否 | 备用 | 跨源去重 -30 |
| shaoyouvip | 34 | 19 | 0 节点 | 否 | 备用 | 跨源去重 -11 |
| leilaomi | 45 | 33 | 0 节点 | 否 | auto | 跨源去重 -7 |
| Free-Nodes | 57 | 28 | 0 节点 | 否 | 备用 | 跨源去重 -6 |

合计产出 **559** 节点（合并池 559；跨源内容去重剔除 63）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 29 节点，剔除 0 节点
- **ssrsub**：审 365 节点，剔除 0 节点
- **ruk1ng001**：审 76 节点，剔除 17 节点（15 个簇）；理由 TOP：伪装意大利节点，广告，引流广告位，伪装新加坡节点，伪装美国节点
- **nomorewalls**：审 82 节点，剔除 17 节点（4 个簇）；理由 TOP：伪装，引流
- **shaoyouvip**：审 30 节点，剔除 0 节点
- **leilaomi**：审 40 节点，剔除 0 节点
- **Free-Nodes**：审 34 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
