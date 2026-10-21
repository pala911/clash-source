# clash-source 运行报告

- 生成时间：2026-10-21 05:06:44（UTC 记录：2026-10-21T05:06:41Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、zhuhaiuk、ruk1ng001、autojiedian、yypool |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 77.6% | 本机 77.6% |
| autojiedian | 26.1% | 本机 26.1% |
| automerge | 13.5% | 本机 13.5% |
| ermaozi | 8.3% | 本机 8.3% |
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
| yypool | 1354 | 900 | 16 簇 / 59 节点 | 否 | auto | - |
| anaer | 40 | 33 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 36 | 31 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 442 | 171 | 4 簇 / 13 节点 | 否 | - | - |
| ermaozi | 516 | 460 | 6 簇 / 6 节点 | 否 | - | - |
| zhuhaiuk | 26 | 26 | 0 节点 | 否 | auto | - |
| ssrsub | 191 | 185 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 482 | 0 节点 | 否 | auto | - |
| snakem982 | 63 | 63 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 446 | 165 | 6 簇 / 22 节点 | 否 | - | - |
| autojiedian | 996 | 937 | 3 簇 / 20 节点 | 否 | auto | - |
| shaoyouvip | 101 | 101 | 0 节点 | 否 | - | - |

合计产出 **3554** 节点（合并池 3554）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1037 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 720 节点，剔除 59 节点（16 个簇）；理由 TOP：订阅地址本身，广告位，服务器为伪装营销域名，服务器为占位符，服务器为速度占位符
- **anaer**：审 34 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符失效提示
- **passcro**：审 32 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符说明
- **automerge**：审 184 节点，剔除 13 节点（4 个簇）；理由 TOP：占位符节点，引流广告节点
- **ermaozi**：审 441 节点，剔除 6 节点（6 个簇）；理由 TOP：占位符示例节点，数字占位符，配置池营销，tg频道引流，代理服务引流
- **zhuhaiuk**：审 26 节点，剔除 0 节点
- **ssrsub**：审 185 节点，剔除 0 节点
- **ruk1ng001**：审 245 节点，剔除 0 节点
- **snakem982**：审 63 节点，剔除 0 节点
- **nomorewalls**：审 187 节点，剔除 22 节点（6 个簇）；理由 TOP：speednode占位符，占位符/失效提示
- **autojiedian**：审 776 节点，剔除 20 节点（3 个簇）；理由 TOP：营销域名伪装，Zoom官方域名伪装
- **shaoyouvip**：审 101 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
