# clash-source 运行报告

- 生成时间：2026-10-19 13:33:14（UTC 记录：2026-10-19T13:33:11Z）
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
| yypool | 1275 | 850 | 13 簇 / 175 节点 | 否 | - | - |
| anaer | 39 | 32 | 1 簇 / 1 节点 | 否 | auto | - |
| passcro | 149 | 144 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 544 | 128 | 7 簇 / 154 节点 | 否 | - | - |
| ermaozi | 508 | 452 | 3 簇 / 19 节点 | 否 | 观察 | - |
| zhuhaiuk | 34 | 33 | 0 节点 | 否 | auto | - |
| ssrsub | 182 | 177 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 464 | 13 簇 / 15 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 495 | 102 | 6 簇 / 145 节点 | 否 | - | - |
| autojiedian | 943 | 786 | 3 簇 / 88 节点 | 否 | auto | - |
| shaoyouvip | 43 | 43 | 0 节点 | 否 | auto | - |

合计产出 **3273** 节点（合并池 3273）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## 本次告警

无。

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 667 节点，剔除 175 节点（13 个簇）；理由 TOP：广告克隆位，占位符节点，占位符，广告位，明显伪装
- **anaer**：审 33 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例节点
- **passcro**：审 145 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符失效
- **automerge**：审 282 节点，剔除 154 节点（7 个簇）；理由 TOP：占位符示例节点，占位符，引流广告节点，引流广告
- **ermaozi**：审 471 节点，剔除 19 节点（3 个簇）；理由 TOP：订阅广告引流，广告引流占位服务器，群组池名非节点
- **zhuhaiuk**：审 33 节点，剔除 0 节点
- **ssrsub**：审 177 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 15 节点（13 个簇）；理由 TOP：伪装节点名，广告位批量克隆
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 247 节点，剔除 145 节点（6 个簇）；理由 TOP：占位符节点，引流广告节点，占位符
- **autojiedian**：审 711 节点，剔除 88 节点（3 个簇）；理由 TOP：无描述，疑似广告，server疑似营销位，server疑似Zoom广告
- **shaoyouvip**：审 43 节点，剔除 0 节点

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
