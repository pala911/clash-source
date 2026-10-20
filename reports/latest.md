# clash-source 运行报告

- 生成时间：2026-10-20 05:15:25（UTC 记录：2026-10-20T05:15:22Z）
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
| yypool | 1292 | 900 | 1 簇 / 10 节点 | 否 | auto | - |
| anaer | 40 | 34 | 0 节点 | 否 | auto | - |
| passcro | 32 | 27 | 1 簇 / 1 节点 | 否 | - | - |
| automerge | 442 | 179 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 510 | 456 | 8 簇 / 17 节点 | 否 | - | - |
| zhuhaiuk | 29 | 28 | 0 节点 | 否 | auto | - |
| ssrsub | 190 | 185 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 471 | 8 簇 / 8 节点 | 否 | auto | - |
| snakem982 | 62 | 62 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 436 | 161 | 3 簇 / 27 节点 | 否 | - | - |
| autojiedian | 953 | 800 | 4 簇 / 90 节点 | 否 | auto | - |
| shaoyouvip | 88 | 85 | 2 簇 / 2 节点 | 否 | - | - |

合计产出 **3388** 节点（合并池 3388）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- yypool 产出 1026 超过 max_nodes=900，已截断

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 693 节点，剔除 10 节点（1 个簇）；理由 TOP：广告/中转IP
- **anaer**：审 0 节点，剔除 0 节点（全部批次失败）
- **passcro**：审 28 节点，剔除 1 节点（1 个簇）；理由 TOP：占位符示例失效提示
- **automerge**：审 190 节点，剔除 11 节点（2 个簇）；理由 TOP：广告引流/占位符，占位符示例节点
- **ermaozi**：审 452 节点，剔除 17 节点（8 个簇）；理由 TOP：@标签营销，数字编号伪装，@标签引流，Telegram引流，广告引流节点
- **zhuhaiuk**：审 28 节点，剔除 0 节点
- **ssrsub**：审 185 节点，剔除 0 节点
- **ruk1ng001**：审 243 节点，剔除 8 节点（8 个簇）；理由 TOP：名称声称境外，server为境内
- **snakem982**：审 62 节点，剔除 0 节点
- **nomorewalls**：审 188 节点，剔除 27 节点（3 个簇）；理由 TOP：伪装节点，境内中转IP，广告内容
- **autojiedian**：审 726 节点，剔除 90 节点（4 个簇）；理由 TOP：Zoom支持域名疑似失效，广告引流节点，测试域名疑似失效
- **shaoyouvip**：审 87 节点，剔除 2 节点（2 个簇）；理由 TOP：占位符服务器

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
