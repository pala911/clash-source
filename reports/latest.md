# clash-source 运行报告

- 生成时间：2026-11-08 13:38:04（UTC 记录：2026-11-08T13:38:03Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | leilaomi、ssrsub、zhuhaiuk、ruk1ng001 |
| 备用 | 不自动竞速，手动切 | automerge、nomorewalls |
| 观察 | 本机实测不达标 | free-nodes |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 32.8% | 本机 32.8%（达标，但 AUTO 只取前 4） |
| free-nodes | - | 无本机探针数据 |
| leilaomi | 52.2% | 本机 52.2% |
| nomorewalls | 32.2% | 本机 32.2%（达标，但 AUTO 只取前 4） |
| ruk1ng001 | 44.0% | 本机 44.0% |
| ssrsub | 51.8% | 本机 51.8% |
| zhuhaiuk | 51.5% | 本机 51.5% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 343 | 71 | 2 簇 / 12 节点 | 否 | 备用 | 跨源去重 -32 |
| zhuhaiuk | 33 | 27 | 0 节点 | 否 | auto | 跨源去重 -5 |
| ssrsub | 148 | 138 | 0 节点 | 否 | auto | 跨源去重 -7 |
| ruk1ng001 | 500 | 363 | 36 簇 / 37 节点 | 否 | auto | 跨源去重 -66 |
| nomorewalls | 314 | 31 | 3 簇 / 14 节点 | 否 | 备用 | 跨源去重 -45 |
| leilaomi | 59 | 58 | 1 簇 / 1 节点 | 否 | auto | - |
| free-nodes | - | 0 | - | 否 | 观察 | 全部 URL 尝试均失败 |

合计产出 **688** 节点（合并池 688；跨源内容去重剔除 155）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- free-nodes 抓取失败：全部 URL 尝试均失败（本轮产出空文件，不影响其他源）

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 115 节点，剔除 12 节点（2 个簇）；理由 TOP：引流广告，引流广告位
- **zhuhaiuk**：审 32 节点，剔除 0 节点
- **ssrsub**：审 145 节点，剔除 0 节点
- **ruk1ng001**：审 210 节点，剔除 37 节点（36 个簇）；理由 TOP：广告，引流，server疑似占位符，引流广告，明显伪装
- **nomorewalls**：审 90 节点，剔除 14 节点（3 个簇）；理由 TOP：引流群组广告，群组引流，引流广告节点
- **leilaomi**：审 59 节点，剔除 1 节点（1 个簇）；理由 TOP：伪装：伊朗节点挂美国国旗

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
