# clash-source 运行报告

- 生成时间：2026-11-02 16:09:52（UTC 记录：2026-11-02T16:09:51Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、clashdaily、ssrsub |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | - |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| automerge | 29.8% | 本机 29.8% |
| clashdaily | 39.2% | 本机 39.2% |
| leilaomi | 32.9% | 本机 32.9% |
| nomorewalls | 26.6% | 本机 26.6% |
| ruk1ng001 | 31.6% | 本机 31.6% |
| ssrsub | 36.4% | 本机 36.4% |
| zhuhaiuk | 41.2% | 本机 41.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| automerge | 425 | 160 | 5 簇 / 15 节点 | 否 | - | - |
| zhuhaiuk | 31 | 29 | 1 簇 / 1 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 413 | 14 簇 / 61 节点 | 否 | - | - |
| nomorewalls | 368 | 118 | 2 簇 / 2 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 41 | 40 | 0 节点 | 否 | - | - |

合计产出 **1024** 节点（合并池 1024）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- leilaomi AI 部分批次不可用（相关批次保留全部节点）：全部批次失败

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 175 节点，剔除 15 节点（5 个簇）；理由 TOP：广告引流，订阅地址本身，引流广告位克隆，占位符失效提示，群组引流
- **zhuhaiuk**：审 30 节点，剔除 1 节点（1 个簇）；理由 TOP：伪装境外节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 220 节点，剔除 61 节点（14 个簇）；理由 TOP：广告克隆节点，广告位克隆
- **nomorewalls**：审 120 节点，剔除 2 节点（2 个簇）；理由 TOP：群组引流，占位符示例
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 0 节点，剔除 0 节点（全部批次失败）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
