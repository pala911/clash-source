# clash-source 运行报告

- 生成时间：2026-10-24 16:15:05（UTC 记录：2026-10-24T16:15:02Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | anaer、ssrsub、passcro、ruk1ng001、shaoyouvip、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982 |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 83.1% | 本机 83.1% |
| autojiedian | 32.6% | 本机 32.6% |
| automerge | 24.8% | 本机 24.8% |
| ermaozi | 7.3% | 本机 7.3% 低于 8% |
| nomorewalls | 19.7% | 本机 19.7% |
| passcro | 42.0% | 本机 42.0% |
| ruk1ng001 | 37.8% | 本机 37.8% |
| shaoyouvip | 37.1% | 本机 37.1% |
| snakem982 | 4.3% | 本机 4.3% 低于 8% |
| ssrsub | 50.6% | 本机 50.6% |
| yypool | 19.3% | 本机 19.3% |
| zhuhaiuk | 33.0% | 本机 33.0% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1404 | 900 | 17 簇 / 67 节点 | 否 | - | - |
| anaer | 41 | 35 | 0 节点 | 否 | auto | - |
| passcro | 29 | 24 | 1 簇 / 1 节点 | 否 | auto | - |
| automerge | 376 | 96 | 4 簇 / 14 节点 | 否 | - | - |
| ermaozi | 410 | 324 | 6 簇 / 35 节点 | 否 | 观察 | - |
| zhuhaiuk | 29 | 29 | 0 节点 | 否 | auto | - |
| ssrsub | 187 | 183 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 418 | 11 簇 / 22 节点 | 否 | auto | - |
| snakem982 | 59 | 33 | 3 簇 / 26 节点 | 否 | 观察 | - |
| nomorewalls | 358 | 88 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 340 | 311 | 5 簇 / 9 节点 | 否 | - | - |
| shaoyouvip | 17 | 15 | 0 节点 | 否 | auto | - |

合计产出 **2456** 节点（合并池 2456）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1050 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 732 节点，剔除 67 节点（17 个簇）；理由 TOP：广告引流，订阅地址本身，失效，速度0.0，伪装：声称美国但服务器境内，伪装：声称韩国但服务器境内
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 25 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **automerge**：审 110 节点，剔除 14 节点（4 个簇）；理由 TOP：speednode营销位，占位符失效提示
- **ermaozi**：审 359 节点，剔除 35 节点（6 个簇）；理由 TOP：伪装节点，伪装为英国节点，广告引流节点，占位符，伪装为瑞典节点
- **zhuhaiuk**：审 29 节点，剔除 0 节点
- **ssrsub**：审 183 节点，剔除 0 节点
- **ruk1ng001**：审 220 节点，剔除 22 节点（11 个簇）；理由 TOP：国名与服务器不符，server为广告域名
- **snakem982**：审 59 节点，剔除 26 节点（3 个簇）；理由 TOP：server字段异常，伪装：server为营销域名，server疑似营销位
- **nomorewalls**：审 98 节点，剔除 10 节点（1 个簇）；理由 TOP：群组引流广告位
- **autojiedian**：审 320 节点，剔除 9 节点（5 个簇）；理由 TOP：Amazon广告位，server为test.wecantos.site，占位符，伪装个人名+免费代理域名，server为support.zoom.us，失效提示，占位符含完整IPv6
- **shaoyouvip**：审 15 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
