# clash-source 运行报告

- 生成时间：2026-10-19 22:37:04（UTC 记录：2026-10-19T22:37:01Z）
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
| yypool | 1294 | 891 | 39 簇 / 138 节点 | 否 | auto | - |
| anaer | 40 | 33 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 32 | 27 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 426 | 172 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 508 | 442 | 13 簇 / 29 节点 | 否 | - | - |
| zhuhaiuk | 35 | 34 | 0 节点 | 否 | auto | - |
| ssrsub | 190 | 185 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 433 | 10 簇 / 46 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 426 | 172 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 943 | 870 | 2 簇 / 4 节点 | 否 | auto | - |
| shaoyouvip | 102 | 96 | 1 簇 / 4 节点 | 否 | - | - |

合计产出 **3417** 节点（合并池 3417）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 679 节点，剔除 138 节点（39 个簇）；理由 TOP：广告/引流节点簇，广告订阅地址，订阅地址本身，广告伪装中转，明显伪装
- **anaer**：审 34 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符/失效提示
- **passcro**：审 28 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符/说明节点
- **automerge**：审 182 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告
- **ermaozi**：审 471 节点，剔除 29 节点（13 个簇）；理由 TOP：营销域名伪装，营销广告节点，引流广告营销位，Telegram频道引流，占位符示例节点
- **zhuhaiuk**：审 34 节点，剔除 0 节点
- **ssrsub**：审 185 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 46 节点（10 个簇）；理由 TOP：广告位，占位符示例节点
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 182 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告位
- **autojiedian**：审 711 节点，剔除 4 节点（2 个簇）；理由 TOP：占位符示例节点
- **shaoyouvip**：审 100 节点，剔除 4 节点（1 个簇）；理由 TOP：测速网站失效

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
