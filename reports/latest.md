# clash-source 运行报告

- 生成时间：2026-11-07 06:06:34（UTC 记录：2026-11-07T06:06:33Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ssrsub、leilaomi、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | nomorewalls、automerge |
| 观察 | 本机实测不达标 | free-nodes |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 30.1% | 本机 30.1%（达标，但 AUTO 只取前 4） |
| free-nodes | - | 无本机探针数据 |
| leilaomi | 45.0% | 本机 45.0% |
| nomorewalls | 30.9% | 本机 30.9%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 39.3% | 本机 39.3% |
| ssrsub | 46.4% | 本机 46.4% |
| zhuhaiuk | 49.0% | 本机 49.0% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 400 | 5 | 1 簇 / 10 节点 | 否 | 备用 | 跨源去重 -141 |
| zhuhaiuk | 32 | 31 | 0 节点 | 否 | auto | - |
| ssrsub | 134 | 132 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 313 | 30 簇 / 75 节点 | 否 | auto | 跨源去重 -78 |
| nomorewalls | 400 | 88 | 4 簇 / 17 节点 | 否 | 备用 | 跨源去重 -51 |
| leilaomi | 123 | 105 | 0 节点 | 否 | auto | 跨源去重 -18 |
| free-nodes | - | 0 | - | 否 | 观察 | 全部 URL 尝试均失败 |

合计产出 **674** 节点（合并池 674；跨源内容去重剔除 288）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- free-nodes 抓取失败：全部 URL 尝试均失败（本轮产出空文件，不影响其他源）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 156 节点，剔除 10 节点（1 个簇）；理由 TOP：广告引流位
- **zhuhaiuk**：审 31 节点，剔除 0 节点
- **ssrsub**：审 132 节点，剔除 0 节点
- **ruk1ng001**：审 210 节点，剔除 75 节点（30 个簇）；理由 TOP：引流，广告，引流广告
- **nomorewalls**：审 156 节点，剔除 17 节点（4 个簇）；理由 TOP：防范境外势力渗透，引流广告，引流群地址，🇬🇧 GB_1 4.0MB/s 明显伪装
- **leilaomi**：审 123 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
