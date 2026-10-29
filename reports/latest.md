# clash-source 运行报告

- 生成时间：2026-10-29 17:22:55（UTC 记录：2026-10-29T17:22:52Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | passcro、anaer、clashdaily、leilaomi、ssrsub、zhuhaiuk |
| 备用 | 不自动竞速，手动切 | - |
| 观察 | 本机实测不达标 | ermaozi、snakem982、wzmfree |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| anaer | 42.7% | 本机 42.7% |
| autojiedian | 16.0% | 本机 16.0% |
| automerge | 26.1% | 本机 26.1% |
| clashdaily | 37.7% | 本机 37.7% |
| ermaozi | 7.2% | 本机 7.2% 低于 8% |
| leilaomi | 36.4% | 本机 36.4% |
| nomorewalls | 23.7% | 本机 23.7% |
| passcro | 53.2% | 本机 53.2% |
| ruk1ng001 | 28.5% | 本机 28.5% |
| shaoyouvip | 26.5% | 本机 26.5% |
| snakem982 | 3.5% | 本机 3.5% 低于 8% |
| ssrsub | 36.2% | 本机 36.2% |
| wzmfree | 0.0% | 本机 0 活 |
| yypool | 15.1% | 本机 15.1% |
| zhuhaiuk | 30.9% | 本机 30.9% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| yypool | 1065 | 767 | 17 簇 / 68 节点 | 否 | - | - |
| anaer | 1 | 1 | 0 节点 | 否 | auto | - |
| passcro | 1 | 1 | 0 节点 | 否 | auto | - |
| automerge | 327 | 86 | 1 簇 / 10 节点 | 否 | - | - |
| ermaozi | 374 | 231 | 21 簇 / 98 节点 | 否 | 观察 | - |
| zhuhaiuk | 25 | 24 | 0 节点 | 否 | auto | - |
| ssrsub | 135 | 134 | 0 节点 | 否 | auto | - |
| ruk1ng001 | 500 | 431 | 16 簇 / 16 节点 | 否 | - | - |
| snakem982 | 64 | 64 | 0 节点 | 否 | 观察 | - |
| nomorewalls | 308 | 68 | 1 簇 / 10 节点 | 否 | - | - |
| autojiedian | 366 | 351 | 3 簇 / 3 节点 | 否 | - | - |
| shaoyouvip | 2 | 2 | 0 节点 | 否 | - | - |
| clashdaily | 80 | 78 | 0 节点 | 否 | auto | - |
| leilaomi | 71 | 59 | 1 簇 / 1 节点 | 否 | auto | - |
| wzmfree | 1 | 1 | 0 节点 | 否 | 观察 | - |

合计产出 **2298** 节点（合并池 2298）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- anaer AI 剔除超阈值，已整体回滚
- passcro AI 剔除超阈值，已整体回滚
- wzmfree AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **yypool**：审 497 节点，剔除 68 节点（17 个簇）；理由 TOP：广告位，订阅地址，占位符域名，保留地址示例，占位符示例
- **anaer**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **passcro**：审 1 节点，剔除 0 节点（超阈值已回滚）
- **automerge**：审 96 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告营销位
- **ermaozi**：审 329 节点，剔除 98 节点（21 个簇）；理由 TOP：广告位，新加坡server为境内IP，香港server为境内IP，免费VPN引流，境外势力渗透广告
- **zhuhaiuk**：审 24 节点，剔除 0 节点
- **ssrsub**：审 134 节点，剔除 0 节点
- **ruk1ng001**：审 222 节点，剔除 16 节点（16 个簇）；理由 TOP：广告/引流位，广告位
- **snakem982**：审 64 节点，剔除 0 节点
- **nomorewalls**：审 78 节点，剔除 10 节点（1 个簇）；理由 TOP：引流广告位
- **autojiedian**：审 345 节点，剔除 3 节点（3 个簇）；理由 TOP：占位符示例域名，占位staging域名
- **shaoyouvip**：审 2 节点，剔除 0 节点
- **clashdaily**：审 78 节点，剔除 0 节点
- **leilaomi**：审 60 节点，剔除 1 节点（1 个簇）；理由 TOP：疑似群组引流
- **wzmfree**：审 1 节点，剔除 0 节点（超阈值已回滚）

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
