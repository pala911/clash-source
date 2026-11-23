# clash-source 运行报告

- 生成时间：2026-11-23 07:46:57（UTC 记录：2026-11-23T07:46:56Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/clash-source/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 质量分桶（决定手机上 AUTO 组里有哪些源）

| 组 | 含义 | 源 |
|---|---|---|
| AUTO | 参与自动竞速 | zhuhaiuk、ruk1ng001、ssrsub、leilaomi |
| 备用 | 不自动竞速，手动切 | shaoyouvip、Free-Nodes、wzmfree |
| 观察 | 本机实测不达标 | - |
| 视频 | 本机实测高带宽（手动切） | 6 节点（≥ 0.6 MB/s） |

排序依据是**国内口径**（本机全量探针的多轮均值）。美国 CI 口径不用来排序 —— 实测 Spearman rho 仅 0.48，排名不可信。

| 源 | 多轮均值 | 分组依据 |
|---|---:|---|
| Free-Nodes | 36.0% | 本机 36.0%（达标，但 AUTO 只取前 4） |
| leilaomi | 45.5% | 本机 45.5% |
| ruk1ng001 | 52.5% | 本机 52.5% |
| shaoyouvip | 37.5% | 本机 37.5%（达标，但 AUTO 只取前 4） |
| ssrsub | 46.9% | 本机 46.9% |
| wzmfree | 13.3% | 本机 13.3%（达标，但 AUTO 只取前 4） |
| zhuhaiuk | 61.7% | 本机 61.7% |

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除(簇/节点) | 镜像回退 | 分组 | 备注 |
|---|---:|---:|---:|---|---|---|
| zhuhaiuk | 31 | 30 | 0 节点 | 否 | auto | - |
| ssrsub | 386 | 365 | 1 簇 / 2 节点 | 否 | auto | 跨源去重 -11 |
| ruk1ng001 | 129 | 91 | 14 簇 / 14 节点 | 否 | auto | - |
| shaoyouvip | 6 | 3 | 1 簇 / 3 节点 | 否 | 备用 | - |
| leilaomi | 41 | 39 | 0 节点 | 否 | auto | 跨源去重 -2 |
| wzmfree | 134 | 13 | 4 簇 / 6 节点 | 否 | 备用 | 跨源去重 -87 |
| Free-Nodes | 51 | 27 | 1 簇 / 4 节点 | 否 | 备用 | 跨源去重 -8 |

合计产出 **568** 节点（合并池 568；跨源内容去重剔除 108）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- leilaomi AI 剔除超阈值，已整体回滚

## 硬过滤命中 TOP（按源）

- 无记录

## AI 处置摘要

- **zhuhaiuk**：审 30 节点，剔除 0 节点
- **ssrsub**：审 378 节点，剔除 2 节点（1 个簇）；理由 TOP：引流广告
- **ruk1ng001**：审 105 节点，剔除 14 节点（14 个簇）；理由 TOP：广告位，引流广告
- **shaoyouvip**：审 6 节点，剔除 3 节点（1 个簇）；理由 TOP：伪装为德国实为境内中转
- **leilaomi**：审 41 节点，剔除 0 节点（超阈值已回滚）
- **wzmfree**：审 106 节点，剔除 6 节点（4 个簇）；理由 TOP：广告，占位符或说明，伪装
- **Free-Nodes**：审 39 节点，剔除 4 节点（1 个簇）；理由 TOP：广告

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
