# clash-source

自建 Clash 节点源仓：**定时抓取多个免费源 → 归一去重 → 硬过滤 → AI 审核 → 产出手机可直接订阅的完整 profile**，并用三个视角的真探针维护「源的健康档案」。

存在意义：免费通病是「池子大 = 死节点海」。2026-10-13 实测（youtube 真探针，12 个源）：

| 源 | 规模 | 国内通过率 |
|---|---:|---:|
| anaer | 14 | 79% |
| ssrsub | 160 | 35% |
| ruk1ng001 | 374 | 10% |
| shaoyouvip | 46 | 24% |
| **snakem982** | 63 | 25% |

同一个源在不同视角下通过率能差 **4~13 倍**（见 §6），所以「哪个源好」这件事本身就需要多视角交叉验证，不能靠单一测速。

---

## 1. 日常怎么用

**手机订阅地址**（唯一一个你需要记的）：

```
https://pala911.github.io/clash-source/profile.yaml
```

在 Clash Verge / Clash Meta / Mihomo 里添加为「订阅」，更新频率由订阅器决定。
profile 里含两层：

| 层 | 文件 | 更新频率 | 变化内容 |
|---|---|---|---|
| 结构层 | `profile.yaml` | 低频（每日） | 代理组、规则、provider 列表 |
| 节点层 | `nodes/*.yaml` | **每小时** | 节点本身 |

所以节点更新不需要等 profile 刷新，订阅器每小时会自动拉节点层。

---

## 2. 系统怎么跑

```
                    ┌─────────────────────────────────────────┐
   每日（自动）      │  GitHub Actions（美国 runner）           │
                    │  ┌──────┐ ┌──────┐ ┌───────┐ ┌──────┐  │
   抓取 12 个源 ────▶│  │fetch │▶filter│▶AI审核 │▶build │  │
                    │  └──────┘ └──────┘ └───────┘ └──────┘  │
                    └──────────────┬──────────────────────────┘
                                   │ 提交 dist/
                                   ▼
                    gh-pages ──▶ 手机订阅（profile.yaml + nodes/*.yaml）
                                   │
                    ┌──────────────┴──────────────────────────┐
                    ▼                                      ▼
        state/source_health.json              state/probe_latest.json
        （源健康档案，滚动历史）              （本轮真探针数据）
                    ▲                                      ▲
        ┌───────────┴──────────┐              ┌────────────┴────────────┐
        │ 每日：判死（唯一）    │              │ 每周一 20:07 全量        │
        │ scope=ci（美国）     │              │ scope=local（家用宽带）  │
        │ 连续 3 轮 0 活 → 降级 │              │ 达标 2 轮 → 回收         │
        └──────────────────────┘              └─────────────────────────┘

        ┌──────────────────────────────────────────────────────────┐
        │ 每周日 04:23  云效杭州（国内第三个视角）                    │
        │ scope=cnci，分层抽样 30/源，~75 秒                        │
        │ **只记录、只交叉验证，永不触发任何升降级**                  │
        │ 结果 commit 回 Codeup：results/probe_cnci_<时间戳>.json   │
        └──────────────────────────────────────────────────────────┘
```

---

## 3. 四层各干什么、谁能改什么

| 层 | 位置 | 频率 | 规模 | **权限** | 成本 |
|---|---|---|---|---|---|
| **L1** | 美国 GitHub Actions | 每日 | 全量（~3800 节点，2400s） | **唯一有权判死**（降级） | public 仓免费 |
| **L2** | 你的 PC（计划任务） | **周一 20:07** | 全量 | **唯一有权回收** | 0 |
| **L3** | 云效杭州 | 周日 04:23 | 抽样 30/源，75s | 只交叉验证 | 3000 核分额度用 **0.4%** |
| 备份 | Gitee `andywx/ci-probe-test` | — | — | 内容与 Codeup 逐字节一致 | 0 |

**权限这样分配是硬约束，不是随便定的**——理由见 §6 铁律。

---

## 4. 各个模块的作用

### 主流程（`src/`，L1 每日跑）

| 模块 | 作用 | 关键点 |
|---|---|---|
| `fetch.py` | 抓 12 个源的原始订阅 | 走 GitHub API 取 base64（`raw.githubusercontent.com` 国内必墙） |
| `filters.py` | 硬过滤：明文协议放行、按簇聚类、`exclude_filter` | **明文 http/socks5 必须放行**（实测 545 明文通过 32%，733 加密协议只 1.9%）；`exclude_filter` **必须逐源取值**，统一化会让 ssrsub 归零 |
| `ai_review.py` | AI 审核，按「簇」而非按节点审 | 4831 节点 → 1683 簇，92 个 ≥8 节点的簇覆盖 2321 节点。**给 LLM 的协议是「只报要删的」**，让 pass 保持默认 |
| `ai_backends.yaml` | 多后端故障转移链 | 腾讯 tokenhub / 硅基流动 / OpenRouter 三云冗余 |
| `build.py` | 产出 profile.yaml + nodes/*.yaml | 两层刷新机制：结构低频 + 节点每小时 |
| `run.py` | 流水线主入口 | 两阶段并发：抓取+硬过滤 ‖ AI 审核 |
| `report.py` | 生成 `reports/` 审计留痕 | 含 `ai_dropped.md` 逐条记录 AI 剔了什么、为什么 |
| `sources.yaml` | 源清单（12 个），`enabled` 标志由 health.py 维护 | 唯一的源事实来源 |

### 健康档案（`src/health.py`）

维护 `state/source_health.json`（滚动历史），并就地改写 `sources.yaml` 的 `enabled`。

- **降级**：CI 口径连续 3 轮 `alive == 0` → `enabled: false` + 移入 `archive/sources.yaml`
- **回收**：本机口径连续 2 轮 `alive ≥ 5` 且 `rate ≥ 8%` → `enabled: true` 恢复
- **永不删除源本体**，只改开关

### 真探针（`src/probe.py`）

用 mihomo 内核起 file provider，探测 `youtube.com/generate_204`，给每个源打分。

| 参数 | 作用 | 注意 |
|---|---|---|
| `--sample N` | 每源分层抽样 N 个节点 | **按服务器 IP 网段分层**，不是随机抽（随机抽 30 个只有 15.2 个不同网段，分层是 30 个，偏差 0） |
| `--scope` | `ci` / `local` / `cnci` | 决定这轮数据能参与什么决策 |
| `--hc-timeout` | 单节点探测超时，默认 8000ms | **直接线性偏置 alive**（shaoyouvip 实测 3s→0活、8s→4活、15s→6活）。调小它=批量制造假死亡 |

### 云端与运维（`tools/`）

| 文件 | 作用 |
|---|---|
| `local_probe.py` | 本机（国内口径）探针入口，供计划任务调用 |
| `run_local_probe.cmd` | 计划任务的批处理入口（**纯 ASCII，见 §7 坑**） |
| `probe_payload.py` | 云端仓库内容的**唯一来源**（Codeup 与 Gitee 共用） |
| `sync_and_probe.sh` | 云端探针唯一入口：同步代码（带重试）→ 跑探针 → 提交结果 |
| `ci_probe_run.py` | 云端探针执行器：解压内核、vendor yaml、跑探针、打摘要、push 结果 |
| `ci_check_paste.py` | 平台能力判定（出网/DNS/端口/clone/回传路径） |
| `check_ci_scripts.py` | **Python 3.6 静态门禁**（覆盖 24 个文件，交付前必跑） |
| `restore_codeup.py` | 云效组织被删后的灾难恢复 |
| `CI_RECOVERY.md` | 手工恢复步骤（流水线配置存在云效数据库里，脚本救不了） |
| `codeup_push.py` / `gitee_push.py` | 推送云端内容到两个远端 |
| `dispatch_workflow.py` / `check_run.py` | 手动触发 CI / 查看运行状态与日志 |

---

## 5. 前置要求

| 组件 | 要求 | 备注 |
|---|---|---|
| GitHub Actions | 本仓 public，**Actions 分钟数免费** | job 超时设 90 分钟 |
| 云效（可选，L3） | **Python 3.6.8**、2 核、38GB 磁盘 | mihomo 内核与 vendor PyYAML **已预置进仓库**，不需要现场下载 |
| 本机计划任务（L2） | Windows + Clash Verge 的 `verge-mihomo.exe` | 周一 20:07 自动跑 |
| 本机（开发用） | portable-git（无系统 git）、Python 3.11 | GitHub 直连被墙，所有 push/API 走 `127.0.0.1:7897` |

**凭据**（全部在 `.gitignore` 内，仓库是 public 绝不能入库）：

```
.aikey-token        GitHub PAT（写 Actions secrets 用）
codeup.token        云效个人访问令牌（原始）
codeup.https        登录账号 + 令牌（由 codeup_auth.py 自动生成）
gitee.token         Gitee 私人令牌
aliyun.token        阿里云账号密码
tx.aikey-token      腾讯 tokenhub
```

---

## 6. 三条不可违反的铁律

### ① 判死（降级）只能由 L1（美国）做

**理由**：国内发起探测时 `alive == 0` 是**歧义的**——节点真死了？**还是它的 IP 被 GFW 阻断、我根本连不上**？两者在数据上完全一样。美国 runner 能直连全球节点 IP，它说 0 活才近似等于"节点真废了"。

> 推论：**即使买国内服务器，也只能把「判优」搬过去，判死仍得留在美国。**

### ② 判优（回收）只能由 L2（你的 PC）做

**理由**：你手机走的就是**你家宽带**。只有 L2 与业务同源。云 IDC 的国际出口与家用宽带不同（实测云效系统性偏高 +11.9pp）。

### ③ L3（云效 cnci）永不参与自动决策

**理由**（2026-10-15 实测，12 源对照）：

```
shaoyouvip   云效 66.7%   本机 24.4%
snakem982    云效  0.0%   本机 15.4%   ← 两次运行都是 0，稳定复现
```

`snakem982` 63 个节点里 40 个是域名型免费中转，**普遍封禁云厂商 IP 防滥用**。
只看云效会把这个源误判成死的。

**L3 的真实用途是一面对照镜子**：区分「源的问题」和「你网络的问题」。
云效 80% 而本机 24% → 那个源在你家宽带上被压着，不是它变差了。

---

## 7. 出问题的影响

| 故障 | 影响 | 严重度 | 表现 |
|---|---|---|---|
| **L1 挂了**（Actions 停了/额度耗尽） | 订阅不更新（节点变陈旧）；差源不下线，池子慢慢变肥 | **高**（唯一影响日常体验的） | 手机上节点越来越旧 |
| **L2 挂了**（PC 关太久/计划任务被禁） | 好源不被回收 —— 只是少收几个源，池子不会变坏 | 低（保守失败） | `state/` 里 good_streak 长期为 0 |
| **L3 挂了** | 无人在国内盯着；不影响订阅 | 极低 | Codeup 的 `results/` 停止更新 |
| **AI 后端全挂** | 不再剔除广告节点，节点名里出现引流信息 | 中 | 手机上看到「机场推荐/Telegram」等名字 |
| **某个源挂了**（上游消亡） | 该源连续 3 轮 0 活后自动降级 | 无（自动处理） | `sources.yaml` 里 `enabled: false` |
| **探针整体不可用** | 健康档案停更 | 低 | 订阅照常更新 |
| **云效组织被删**（欠费 15 天） | L3 停摆 + Codeup 仓库丢失 | 中（有备份） | `python tools/restore_codeup.py --apply` + 按 `CI_RECOVERY.md` 重建流水线 |

**重要共识：所有探针层的故障都是「保守失败」**——不会误杀源、不会让订阅变坏，只是少做事。真正不能挂的是 L1。

---

## 8. 运维手册

### 手动触发 L1

```powershell
python tools\dispatch_workflow.py      # 触发
python tools\check_run.py              # 看状态与关键日志
```

### 手动跑本机探针（L2）

```powershell
tools\run_local_probe.cmd              # 完整（探针+健康档案+推送）
tools\run_local_probe.cmd --scope-only # 只跑健康档案，用已有探针结果
tools\run_local_probe.cmd --no-push    # 不推回 GitHub
```

日志在 `logs/local_probe.log`。

### 手动触发云端（L3）

云效 → 流水线 → 运行。命令行是：

```bash
ok=0; for i in $(seq 1 8); do git fetch origin && git reset --hard origin/master && { ok=1; break; }; sleep 20; done; [ "$ok" = "1" ] && bash tools/sync_and_probe.sh || { echo "同步失败"; exit 1; }
```

### 云端内容改了要重新推

```powershell
python tools\check_ci_scripts.py    # 先过 3.6 门禁（必做）
python tools\codeup_push.py        # 推云效
python tools\gitee_push.py         # 推 Gitee 备份
```

### 交付前必跑的门禁

```powershell
python tools\check_ci_scripts.py
```

云效集群是 **Python 3.6.8**。以下四类错误在本机 3.11 上**完全正常**，只有真机才炸，且报错极具误导性（看起来像平台能力不足）：

1. `subprocess.run(capture_output=/text=)` —— 3.7+
2. 海象运算符 `:=` —— 3.8+
3. 引号不配平（漏一个右引号）
4. f-string（与本项目 `%%` 格式化风格不一致）

> **门禁的覆盖范围本身就是 bug 源**：第一版只扫 `tools/ci_*.py`，`probe.py` 不在范围内，
> 于是漏网。扩完又因为路径写错漏了 vendor 的 17 个文件。**漏扫的门禁比没门禁更危险**，
> 因为它给出虚假的安全感。

---

## 9. 已知限制与踩过的坑

| 坑 | 现象 | 真因 |
|---|---|---|
| 云效 workspace 不刷新 | 改了代码但流水线跑的还是旧的 | 复用带缓存的 workspace，增量同步漏文件 → **必须 `git reset --hard`** |
| 同步脚本无法自举 | 首次报 `No such file or directory` | 脚本在仓库里，而 workspace 太旧还没它 → **CI 第一条命令必须自包含** |
| 云效 git 端点抖动 | `502 Bad Gateway` / `port 80 连不上` | 未鉴权时返回 **302 跳 SSO**，git 跟到 `http://` 失败。**报错完全误导**，别去查网络或凭据 |
| 换令牌白折腾 | 换了新令牌问题依旧 | 上面那条是抖动不是凭据失效。**单次失败不能用来判断凭据** |
| `.cmd` 中文注释炸 cmd.exe | 报「xxx 不是内部或外部命令」，且后续命令也不执行 | cmd.exe 按 OEM 码页（936）读 `.cmd`。**必须纯 ASCII** |
| `.cmd` 用 LF 行尾 | 退出码永远传不出来（`%ERRORLEVEL%` 变空） | **必须 CRLF** |
| `grep -c` 掐死 `&&` 链 | 计数为 0 时退出码是 1，后面的命令不执行 | 守卫要写 `$(grep -c x f \|\| true)` |
| 云端日志面板不可靠 | 「执行命令」跑满 67 秒却只渲染出申请环境的输出 | 所以结果必须 commit 回仓库，**日志只用于排查** |

---

## 10. 目录结构

```
src/                  主流程模块（见 §4）
  sources.yaml        源清单（12 个），enabled 由 health.py 维护
  ai_backends.yaml    AI 后端链（顺序=优先级，只从环境变量读 key）
  profile_template.yaml  profile 模板
.github/workflows/update.yml   13 步流水线
dist/                 产物（profile.yaml + nodes/*.yaml），由 CI 生成
  archive/            历史库：曾启用但被判死的源
reports/              审计留痕（latest.md / ai_dropped.md）
state/                probe_latest.json / source_health.json（滚动历史）
data/                 discovered_pool.json（候选池，发现的新源只进这里）
archive/              历史库源清单
tools/                云端执行与运维脚本（见 §4）
probe_payload.py      云端内容清单唯一来源
```

---

## 11. 新增一个源

1. 把 URL 加进 `src/sources.yaml`
2. **必须真探针验证**——README 说的"测速筛选"不可信（Au1rxx 自测只保 TCP 存活，
   1745 个节点只有 2 个能穿 youtube）
3. `exclude_filter` **逐源取值**，不要复制粘贴
4. 跑一次 `python src\local_probe.py --no-push` 看真实国内通过率
5. 通过率 < 5% 且稳定的，别加

`tools/discover.py` 会定期从 GitHub 扫新共享源，但**只进 `data/discovered_pool.json` 候选池，
绝不自动入池**——源的结论必须来自真探针。