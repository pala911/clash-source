# clash-source 运行报告

- 生成时间：2026-10-30 06:04:06（UTC 记录：2026-10-30T06:04:04Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、leilaomi、clashdaily、zhuhaiuk、ssrsub、anaer |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982、wzmfree |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 31.6% | 本机 31.6% |
| autojiedian | 12.6% | 本机 12.6% |
| automerge | 26.4% | 本机 26.4% |
| clashdaily | 37.2% | 本机 37.2% |
| ermaozi | 8.0% | 本机 8.0% 低于 8% |
| leilaomi | 41.7% | 本机 41.7% |
| nomorewalls | 25.2% | 本机 25.2% |
| passcro | 44.4% | 本机 44.4% |
| ruk1ng001 | 31.0% | 本机 31.0% |
| shaoyouvip | 27.8% | 本机 27.8% |
| snakem982 | 3.9% | 本机 3.9% 低于 8% |
| ssrsub | 35.5% | 本机 35.5% |
| wzmfree | 0.0% | 本机 0 活 |
| yypool | 16.0% | 本机 16.0% |
| zhuhaiuk | 36.6% | 本机 36.6% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1142 | 821 | 21 簇 / 75 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 401 | 151 | 2 簇 / 11 节点 | 否 | - | - |
| ermaozi | 390 | 296 | 22 簇 / 50 节点 | 否 | 观察 | - |
| zhuhaiuk | 29 | 27 | 0 节点 | 否 | auto | - |
| ssrsub | 135 | 134 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 443 | 2 簇 / 4 节点 | 否 | - | - |
| snakem982 | 62 | 61 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 401 | 150 | 3 簇 / 12 节点 | 否 | - | - |
| autojiedian | 404 | 389 | 2 簇 / 2 节点 | 否 | - | - |
| shaoyouvip | 77 | 73 | 3 簇 / 4 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 84 | 67 | 0 节点 | 否 | auto | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2693** 节点（合并池 2693）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- zhuhaiuk AI 部分批次不可用（相关批次保留全部节点）：全部批次失败
- wzmfree AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 561 节点，剔除 75 节点（21 个簇）；理由 TOP：广告位克隆，订阅地址本身，引流广告，订阅地址/占位符，占位符失效提示
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 162 节点，剔除 11 节点（2 个簇）；理由 TOP：server字段异常，占位符无效
- **ermaozi**：审 346 节点，剔除 50 节点（22 个簇）；理由 TOP：广告位克隆，Telegram频道引流，巴西节点占位域名，伪装台湾节点，俄罗斯节点web重定向
- **zhuhaiuk**：审 0 节点，剔除 0 节点（全部批次失败）
- **ssrsub**：审 134 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 4 节点（2 个簇）；理由 TOP：广告/引流节点，营销位/占位符
- **snakem982**：审 61 节点，剔除 0 节点
- **nomorewalls**：审 162 节点，剔除 12 节点（3 个簇）；理由 TOP：占位符格式，土耳其实为伊朗伪装，引流广告伪装节点
- **autojiedian**：审 377 节点，剔除 2 节点（2 个簇）；理由 TOP：server疑似境内中转，staging占位域名
- **shaoyouvip**：审 77 节点，剔除 4 节点（3 个簇）；理由 TOP：占位符节点，广告引流节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 67 节点，剔除 0 节点
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
