# clash-source 运行报告

- 生成时间：2026-10-14 07:01:46（UTC 记录：2026-10-14T07:01:42Z）
- AI 模式：`http`
- 订阅入口：`https://pala911.github.io/clash-source/profile.yaml`
- 备用入口（github.io 不达时）：`https://gh-proxy.com/raw.githubusercontent.com/pala911/gh-pages/profile.yaml`
- jsdelivr 备用：`https://cdn.jsdelivr.net/gh/pala911/clash-source@gh-pages/profile.yaml`

## 各源漏斗

| 源 | 原始 | 产出 | AI 剔除 | 镜像回退 | 备注 |
|---|---:|---:|---:|---|---|
| yypool | 1700 | 900 | - | 否 | - |
| anaer | 21 | 14 | - | 否 | - |
| passcro | 149 | 144 | - | 否 | - |
| automerge | 524 | 116 | - | 否 | - |
| ermaozi | 598 | 490 | - | 否 | - |
| zhuhaiuk | 32 | 31 | - | 否 | - |
| ssrsub | 161 | 160 | - | 否 | - |
| ruk1ng001 | 500 | 480 | - | 否 | - |
| snakem982 | 61 | 60 | - | 否 | - |
| nomorewalls | 533 | 271 | - | 否 | - |
| autojiedian | 944 | 905 | - | 否 | - |
| shaoyouvip | 16 | 16 | - | 否 | - |

合计产出 **3587** 节点（合并池 3587）。

> 注意：节点数 ≠ 可用性。真实质量门禁是 **youtube/generate_204 探针**（手机/PC 侧 mihomo 自己跑）；CI 在美国机，连通性检查只能删明显死的。

## ⚠ 本次告警

- yypool 产出 1154 超过 max_nodes=900，已截断（考虑淘汰最差尾部）
- ermaozi AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- zhuhaiuk AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- ssrsub AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- ruk1ng001 AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- snakem982 AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- nomorewalls AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- autojiedian AI 因墙钟预算耗尽被跳过（该源按纯规则产出）
- shaoyouvip AI 因墙钟预算耗尽被跳过（该源按纯规则产出）

## 硬过滤命中 TOP（按源）

- **yypool**：命名命中 exclude-filter×243，不支持的协议 hysteria×3
- **anaer**：不支持的协议 hysteria×2
- **automerge**：命名命中 exclude-filter×241，不支持的协议 hysteria×3
- **ermaozi**：命名命中 exclude-filter×11，不支持的协议 hysteria×3
- **ssrsub**：命名命中 exclude-filter×1
- **snakem982**：不支持的协议 hysteria×1
- **nomorewalls**：命名命中 exclude-filter×240，不支持的协议 hysteria×3
- **autojiedian**：有 obfs/plugin 但缺 obfs-password（会让整个 provider 加载失败）×7，不支持的协议 hysteria×1

## AI 处置摘要

- **yypool**：审 0，剔除 0；理由 TOP：广告位引流，广告位批量克隆，订阅地址本身，server为占位符，广告位
- **anaer**：审 0，剔除 0；理由 TOP：占位符示例节点
- **passcro**：审 0，剔除 0；理由 TOP：占位符示例节点
- **automerge**：审 0，剔除 0；理由 TOP：speednode测试节点，境外势力渗透广告，占位符节点
- **ermaozi**：审 0，剔除 0；理由 TOP：广告位，伪装境内中转，群组引流广告位，广告域名，占位符
- **zhuhaiuk**：审 0，剔除 0
- **ssrsub**：审 0，剔除 0
- **ruk1ng001**：审 0，剔除 0
- **snakem982**：审 0，剔除 0
- **nomorewalls**：审 0，剔除 0
- **autojiedian**：审 0，剔除 0
- **shaoyouvip**：审 0，剔除 0

## 产物

- `dist/profile.yaml` —— 手机订阅入口（组结构 + 规则 + providers）
- `dist/nodes/<源>.yaml` —— 各源过滤后节点池（provider 格式）
- `dist/nodes/all.yaml` —— 全源合并池（名字带源前缀）
- `dist/raw/<源>.yaml` —— 未过滤原始（仅当 `--keep-raw`，对比用，手机别订阅）
