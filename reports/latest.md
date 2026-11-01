# clash-source 运行报告

- 生成时间：2026-11-01 19:44:58（UTC 记录：2026-11-01T19:44:57Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、clashdaily、leilaomi |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | - |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 26.1% | 本机 26.1% |
| clashdaily | 39.4% | 本机 39.4% |
| leilaomi | 34.7% | 本机 34.7% |
| nomorewalls | 25.8% | 本机 25.8% |
| ruk1ng001 | 29.0% | 本机 29.0% |
| ssrsub | 34.0% | 本机 34.0% |
| zhuhaiuk | 42.2% | 本机 42.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 372 | 92 | 3 簇 / 3 节点 | 否 | - | - |
| zhuhaiuk | 26 | 25 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | - | - |
| ruk1ng001 | 500 | 432 | 26 簇 / 37 节点 | 否 | - | - |
| nomorewalls | 431 | 162 | 4 簇 / 13 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 82 | 78 | 1 簇 / 1 节点 | 否 | auto | - |

合计产出 **1053** 节点（合并池 1053）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 95 节点，剔除 3 节点（3 个簇）；理由 TOP：伪装为其他server，伪装为韩国server，伪装为巴西server
- **zhuhaiuk**：审 25 节点，剔除 0 节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 227 节点，剔除 37 节点（26 个簇）；理由 TOP：广告位，广告克隆位，占位符
- **nomorewalls**：审 175 节点，剔除 13 节点（4 个簇）；理由 TOP：占位符，群组引流，境外渗透节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 79 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
