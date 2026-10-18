# clash-source 运行报告

- 生成时间：2026-10-18 16:14:39（UTC 记录：2026-10-18T16:14:37Z）
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
| yypool | 1683 | 900 | 5 簇 / 28 节点 | 否 | - | - |
| anaer | 39 | 33 | 0 节点 | 否 | auto | - |
| passcro | 149 | 144 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 473 | 200 | 2 簇 / 14 节点 | 否 | - | - |
| ermaozi | 497 | 369 | 55 簇 / 85 节点 | 否 | 观察 | - |
| zhuhaiuk | 27 | 27 | 0 节点 | 否 | auto | - |
| ssrsub | 181 | 176 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 479 | 0 节点 | 否 | auto | - |
| snakem982 | 60 | 60 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 450 | 179 | 6 簇 / 25 节点 | 否 | - | - |
| autojiedian | 959 | 870 | 7 簇 / 44 节点 | 否 | auto | - |
| shaoyouvip | 4 | 4 | 0 节点 | 否 | auto | - |

合计产出 **3441** 节点（合并池 3441）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1385 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 1030 节点，剔除 28 节点（5 个簇）；理由 TOP：广告符号，引流链接
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 145 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符非真实节点
- **automerge**：审 214 节点，剔除 14 节点（2 个簇）；理由 TOP：广告内容，引流内容
- **ermaozi**：审 454 节点，剔除 85 节点（55 个簇）；理由 TOP：广告位克隆节点，同源克隆节点，广告位，订阅地址，营销账号
- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 176 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 0 节点
- **snakem982**：审 60 节点，剔除 0 节点
- **nomorewalls**：审 204 节点，剔除 25 节点（6 个簇）；理由 TOP：明显伪装，国家与IP不符，广告/引流，引流/广告
- **autojiedian**：审 731 节点，剔除 44 节点（7 个簇）；理由 TOP：server为域名疑似营销，同簇节点重复，伪装美国节点，server域名异常
- **shaoyouvip**：审 4 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
