# clash-source 运行报告

- 生成时间：2026-10-24 11:14:51（UTC 记录：2026-10-24T11:14:48Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、yypool |
| 备用 | 不自动竞速，手动切 | ermaozi |
| 观察 | 本机实测不达标 | snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 77.6% | 本机 77.6% |
| autojiedian | 26.1% | 本机 26.1% |
| automerge | 13.5% | 本机 13.5% |
| ermaozi | 8.3% | 位置敏感（本机 8.3%/云效 6.7%） |
| nomorewalls | 14.9% | 本机 14.9% |
| passcro | 13.6% | 本机 13.6% |
| ruk1ng001 | 37.3% | 本机 37.3% |
| shaoyouvip | 17.8% | 本机 17.8% |
| snakem982 | 4.4% | 本机 4.4% 低于 8% |
| ssrsub | 43.9% | 本机 43.9% |
| yypool | 18.3% | 本机 18.3% |
| zhuhaiuk | 42.2% | 本机 42.2% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1367 | 900 | 28 簇 / 147 节点 | 否 | auto | - |
| anaer | 41 | 34 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 29 | 24 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 419 | 138 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 515 | 438 | 3 簇 / 12 节点 | 否 | 备用 | - |
| zhuhaiuk | 25 | 25 | 0 节点 | 否 | auto | - |
| ssrsub | 279 | 274 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 443 | 2 簇 / 3 节点 | 否 | auto | - |
| snakem982 | 63 | 63 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 376 | 100 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 381 | 354 | 4 簇 / 6 节点 | 否 | auto | - |
| shaoyouvip | 54 | 53 | 0 节点 | 否 | - | - |

合计产出 **2846** 节点（合并池 2846）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 944 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 720 节点，剔除 147 节点（28 个簇）；理由 TOP：广告位克隆，订阅地址本身，广告引流，私有IP占位符，伪装营销占位域名
- **anaer**：审 35 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符/失效提示
- **passcro**：审 25 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符/失效提示
- **automerge**：审 148 节点，剔除 10 节点（1 个簇）；理由 TOP：占位符失效提示
- **ermaozi**：审 434 节点，剔除 12 节点（3 个簇）；理由 TOP：订阅配置通道，广告引流占位符，FreeVPN引流
- **zhuhaiuk**：审 25 节点，剔除 0 节点
- **ssrsub**：审 274 节点，剔除 0 节点
- **ruk1ng001**：审 219 节点，剔除 3 节点（2 个簇）；理由 TOP：伪装印度服务器境内，server为失效提示域名
- **snakem982**：审 63 节点，剔除 0 节点
- **nomorewalls**：审 110 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告
- **autojiedian**：审 347 节点，剔除 6 节点（4 个簇）；理由 TOP：同簇克隆节点，伪装马德里节点，服务器与节点名相同
- **shaoyouvip**：审 53 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
