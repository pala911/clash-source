# clash-source 运行报告

- 生成时间：2026-10-18 11:22:27（UTC 记录：2026-10-18T11:22:24Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、shaoyouvip |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 76.2% | 本机 76.2% |
| autojiedian | 26.1% | 本机 26.1% |
| automerge | 15.9% | 本机 15.9% |
| ermaozi | 8.0% | 本机 8.0% 低于 8% |
| nomorewalls | 14.9% | 本机 14.9% |
| passcro | 15.0% | 本机 15.0% |
| ruk1ng001 | 32.5% | 本机 32.5% |
| shaoyouvip | 21.3% | 本机 21.3% |
| snakem982 | 6.3% | 本机 6.3% 低于 8% |
| ssrsub | 45.8% | 本机 45.8% |
| yypool | 17.5% | 本机 17.5% |
| zhuhaiuk | 43.1% | 本机 43.1% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1622 | 900 | 20 簇 / 77 节点 | 否 | - | - |
| anaer | 39 | 33 | 0 节点 | 否 | auto | - |
| passcro | 149 | 144 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 522 | 260 | 2 簇 / 14 节点 | 否 | - | - |
| ermaozi | 599 | 490 | 12 簇 / 66 节点 | 否 | 观察 | - |
| zhuhaiuk | 26 | 21 | 0 节点 | 否 | auto | - |
| ssrsub | 196 | 192 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 474 | 1 簇 / 1 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 473 | 200 | 2 簇 / 14 节点 | 否 | - | - |
| autojiedian | 1074 | 1004 | 1 簇 / 2 节点 | 否 | auto | - |
| shaoyouvip | 15 | 15 | 0 节点 | 否 | auto | - |

合计产出 **3795** 节点（合并池 3795）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- zhuhaiuk AI 剔除超阈值，已整体回滚
- yypool 产出 1298 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 1002 节点，剔除 77 节点（20 个簇）；理由 TOP：订阅地址本身，模板占位符，占位符标记，占位符服务器，本地地址占位符
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 145 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符失效提示
- **automerge**：审 274 节点，剔除 14 节点（2 个簇）；理由 TOP：引流/广告/群组引流，群组引流地址
- **ermaozi**：审 541 节点，剔除 66 节点（12 个簇）；理由 TOP：订阅地址克隆，订阅地址本身，占位符服务器名，付费VPN订阅，广告引流位
- **zhuhaiuk**：审 21 节点，剔除 0 节点（超阈值已回滚）
- **ssrsub**：审 192 节点，剔除 0 节点
- **ruk1ng001**：审 232 节点，剔除 1 节点（1 个簇）；理由 TOP：境内中转伪装
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 214 节点，剔除 14 节点（2 个簇）；理由 TOP：广告占位符，引流伪装节点
- **autojiedian**：审 802 节点，剔除 2 节点（1 个簇）；理由 TOP：可疑伪装域名
- **shaoyouvip**：审 15 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
