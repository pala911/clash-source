# clash-source 运行报告

- 生成时间：2026-11-16 22:12:40（UTC 记录：2026-11-16T22:12:39Z）
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
| 视频 | 本机实测高带宽（手动切） | 6 节点（≥ 0.6 MB/s） |

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
| zhuhaiuk | 36 | 36 | 0 节点 | 否 | auto | - |
| ssrsub | 405 | 293 | 0 节点 | 否 | auto | 跨源去重 -102 |
| ruk1ng001 | 590 | 313 | 48 簇 / 99 节点 | 否 | auto | 跨源去重 -4 |
| snakem982 | 62 | 45 | 0 节点 | 否 | 备用 | 跨源去重 -17 |
| nomorewalls | 374 | 66 | 2 簇 / 12 节点 | 否 | 备用 | 跨源去重 -63 |
| leilaomi | 51 | 39 | 0 节点 | 否 | auto | 跨源去重 -7 |
| Free-Nodes | 70 | 24 | 0 节点 | 否 | 观察 | 跨源去重 -10 |

合计产出 **816** 节点（合并池 816；跨源内容去重剔除 203）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 36 节点，剔除 0 节点
- **ssrsub**：审 395 节点，剔除 0 节点
- **ruk1ng001**：审 214 节点，剔除 99 节点（48 个簇）；理由 TOP：广告，伪装美国，伪装韩国，伪装意大利，引流广告
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 141 节点，剔除 12 节点（2 个簇）；理由 TOP：伪装，引流广告位
- **leilaomi**：审 46 节点，剔除 0 节点
- **Free-Nodes**：审 34 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
