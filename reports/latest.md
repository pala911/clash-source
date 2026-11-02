# clash-source 运行报告

- 生成时间：2026-11-02 06:13:54（UTC 记录：2026-11-02T06:13:53Z）
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
| automerge | 448 | 159 | 3 簇 / 15 节点 | 否 | - | - |
| zhuhaiuk | 34 | 34 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 186 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 462 | 7 簇 / 7 节点 | 否 | - | - |
| nomorewalls | 476 | 180 | 7 簇 / 25 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 74 | 50 | 5 簇 / 16 节点 | 否 | - | - |

合计产出 **1149** 节点（合并池 1149）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **automerge**：审 174 节点，剔除 15 节点（3 个簇）；理由 TOP：引流广告节点，伪装新加坡服务器，台湾伪装服务器
- **zhuhaiuk**：审 34 节点，剔除 0 节点
- **ssrsub**：审 186 节点，剔除 0 节点
- **ruk1ng001**：审 227 节点，剔除 7 节点（7 个簇）；理由 TOP：占位符示例域名，同簇节点伪装
- **nomorewalls**：审 205 节点，剔除 25 节点（7 个簇）；理由 TOP：速度占位符，server重复疑似克隆，占位服务器，占位符服务器格式，群组引流
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 66 节点，剔除 16 节点（5 个簇）；理由 TOP：speednode命名疑似克隆营销

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
