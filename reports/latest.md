# clash-source 运行报告

- 生成时间：2026-10-18 17:26:20（UTC 记录：2026-10-18T17:26:16Z）
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
| yypool | 1630 | 900 | 57 簇 / 188 节点 | 否 | - | - |
| anaer | 39 | 32 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 149 | 144 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 450 | 186 | 3 簇 / 18 节点 | 否 | - | - |
| ermaozi | 497 | 389 | 27 簇 / 65 节点 | 否 | 观察 | - |
| zhuhaiuk | 27 | 26 | 0 节点 | 否 | auto | - |
| ssrsub | 181 | 176 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 383 | 28 簇 / 96 节点 | 否 | auto | - |
| snakem982 | 60 | 51 | 2 簇 / 9 节点 | 否 | 观察 | - |
| nomorewalls | 450 | 182 | 4 簇 / 22 节点 | 否 | - | - |
| autojiedian | 959 | 914 | 0 节点 | 否 | auto | - |
| shaoyouvip | 29 | 29 | 0 节点 | 否 | auto | - |

合计产出 **3412** 节点（合并池 3412）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1181 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 1019 节点，剔除 188 节点（57 个簇）；理由 TOP：广告位引流，整簇剔除，广告位克隆，重复节点，广告克隆节点簇，营销域名
- **anaer**：审 33 节点，剔除 1 节点（1 个簇）；理由 TOP：本地地址占位符
- **passcro**：审 145 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例失效
- **automerge**：审 204 节点，剔除 18 节点（3 个簇）；理由 TOP：占位符信息，伪装节点，广告内容
- **ermaozi**：审 454 节点，剔除 65 节点（27 个簇）；理由 TOP：广告位，订阅地址，占位符，频道引流推广，伪装
- **zhuhaiuk**：审 26 节点，剔除 0 节点
- **ssrsub**：审 176 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 96 节点（28 个簇）；理由 TOP：广告位，广告/引流节点
- **snakem982**：审 60 节点，剔除 9 节点（2 个簇）；理由 TOP：名称声称香港但server为德国，server疑似营销位
- **nomorewalls**：审 204 节点，剔除 22 节点（4 个簇）；理由 TOP：无机场推荐，明显伪装，引流内容，广告内容
- **autojiedian**：审 731 节点，剔除 0 节点
- **shaoyouvip**：审 29 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
