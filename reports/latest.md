# clash-source 运行报告

- 生成时间：2026-10-19 05:05:43（UTC 记录：2026-10-19T05:05:39Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
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
| yypool | 1330 | 900 | 0 节点 | 否 | - | - |
| anaer | 39 | 33 | 0 节点 | 否 | auto | - |
| passcro | 149 | 144 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 537 | 281 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 590 | 454 | 18 簇 / 97 节点 | 否 | 观察 | - |
| zhuhaiuk | 34 | 33 | 0 节点 | 否 | auto | - |
| ssrsub | 182 | 177 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 466 | 7 簇 / 13 节点 | 否 | auto | - |
| snakem982 | 63 | 63 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 556 | 281 | 2 簇 / 13 节点 | 否 | - | - |
| autojiedian | 943 | 870 | 3 簇 / 4 节点 | 否 | auto | - |
| shaoyouvip | 100 | 99 | 0 节点 | 否 | auto | - |

合计产出 **3801** 节点（合并池 3801）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1058 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 712 节点，剔除 0 节点
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 145 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例
- **automerge**：审 291 节点，剔除 10 节点（1 个簇）；理由 TOP：广告/引流节点
- **ermaozi**：审 535 节点，剔除 97 节点（18 个簇）；理由 TOP：www.v2nodes.com，广告位，营销域名，@符号广告，营销位
- **zhuhaiuk**：审 33 节点，剔除 0 节点
- **ssrsub**：审 177 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 13 节点（7 个簇）；理由 TOP：广告位，占位符，境内中转伪装
- **snakem982**：审 63 节点，剔除 0 节点
- **nomorewalls**：审 294 节点，剔除 13 节点（2 个簇）；理由 TOP：占位符测试节点，群组引流广告
- **autojiedian**：审 711 节点，剔除 4 节点（3 个簇）；理由 TOP：IP与名称重复，疑似占位符，server疑似营销位，server疑似Zoom广告
- **shaoyouvip**：审 99 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
