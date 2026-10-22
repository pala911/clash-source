# clash-source 运行报告

- 生成时间：2026-10-22 05:04:25（UTC 记录：2026-10-22T05:04:21Z）
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
| yypool | 1442 | 900 | 27 簇 / 115 节点 | 否 | auto | - |
| anaer | 41 | 34 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 36 | 31 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 461 | 179 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 523 | 430 | 15 簇 / 39 节点 | 否 | - | - |
| zhuhaiuk | 27 | 17 | 1 簇 / 9 节点 | 否 | auto | - |
| ssrsub | 190 | 188 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 448 | 5 簇 / 6 节点 | 否 | auto | - |
| snakem982 | 62 | 55 | 1 簇 / 7 节点 | 否 | 观察 | - |
| nomorewalls | 444 | 168 | 2 簇 / 11 节点 | 否 | - | - |
| autojiedian | 1023 | 965 | 3 簇 / 10 节点 | 否 | auto | - |
| shaoyouvip | 101 | 100 | 0 节点 | 否 | - | - |

合计产出 **3515** 节点（合并池 3515）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1058 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 803 节点，剔除 115 节点（27 个簇）；理由 TOP：广告位，server字段为带宽信息，广告位克隆，订阅地址本身，占位符服务器
- **anaer**：审 35 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例失效
- **passcro**：审 32 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **automerge**：审 190 节点，剔除 11 节点（2 个簇）；理由 TOP：占位符节点，广告引流节点
- **ermaozi**：审 440 节点，剔除 39 节点（15 个簇）；理由 TOP：伪装国家IP，订阅地址本身，伪装境内中转，占位符域名，域名可疑伪装
- **zhuhaiuk**：审 26 节点，剔除 9 节点（1 个簇）；理由 TOP：广告位
- **ssrsub**：审 188 节点，剔除 0 节点
- **ruk1ng001**：审 225 节点，剔除 6 节点（5 个簇）；理由 TOP：广告位，占位符节点，占位符，营销位域名
- **snakem982**：审 62 节点，剔除 7 节点（1 个簇）；理由 TOP：测试开发服务器
- **nomorewalls**：审 179 节点，剔除 11 节点（2 个簇）；理由 TOP：广告内容，占位符未命名
- **autojiedian**：审 777 节点，剔除 10 节点（3 个簇）；理由 TOP：server疑似引流，占位符测试域名，server疑似广告
- **shaoyouvip**：审 100 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
