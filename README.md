# clash-source

自建 Clash 节点源仓：**定时抓取多个免费源 → 归一去重 → 硬过滤 → AI 审核 → 按实测质量分桶 → 产出手机可直接订阅的完整 profile**，并用三个视角的真探针维护「源的健康档案」与「节点的稳定性档案」。

存在意义：免费通病是「池子大 = 死节点海」。同一个源在不同视角下通过率能差 **4~13 倍**（见 §7），所以「哪个源好」这件事本身就需要多视角交叉验证，不能靠单一测速。

而「哪个源好」也还不够 —— 同一个源里，快但一周只活 50% 的节点，会被 `url-test` 一直选中，因为它每次测都快。**长期稳定性**是 `url-test` 完全看不见的一维，本系统单独测它（见 §5）。

---

## 1. 日常怎么用

**手机订阅地址**（唯一一个你需要记的）：

```
https://pala911.github.io/clash-source/profile.yaml
```

在 Clash Verge / Clash Meta / Mihomo 里添加为「订阅」。

### 1.1 手机上会看到哪些组

| 组 | 类型 | 里面是什么 | 需要管吗 |
|---|---|---|---|
| `PROXY` | select | 默认选 `FAILOVER` | 平时不用动 |
| `FAILOVER` | fallback | 全部启用源，逐个兜底 | 不用动 |
| **`AUTO`** | url-test | **只有「达标源 × 稳节点」**，每 120 秒重测取最快 | **这是你用的那个** |
| `备用` | select | 未达标但有活的源 + `不稳定` 组 | 想换源时手动切 |
| `观察` | select | 本机实测通过率 < 8% 的源 | 基本不用管 |
| `不稳定` | url-test | 历史可用率偏低的节点 | 路由变了才需要 |
| `SRC-<源名>` | url-test | 单源的节点 | 排查单源时用 |
| `Claude` / `Gemini` | select | 全部启用源 | 不用动 |

**只有 `AUTO` 会自动竞速。** 差源和历史不稳的节点被排除在竞速之外 —— 不是删掉，仍然能从 `备用` 组手工切到。

profile 含两层，节点更新不必等 profile 刷新：

| 层 | 文件 | 更新频率 |
|---|---|---|
| 结构层 | `profile.yaml` | 每 6 小时（= L1 流水线一轮） |
| 节点层 | `nodes/*.yaml` | 每 6 小时（同一条流水线里一起产出） |

> ⚠ **两层是同一轮流水线一起重建的**，不是两个独立任务。
> 而 **L2（本机探针）只推 `state/`，从不碰 `dist/`** ——
> 所以「节点新不新鲜」完全取决于 L1 跑得勤不勤（见 §3）。

---

## 2. 系统怎么跑

```
    ┌────────────────────────────────────────────────────────────┐
    │  每 6 小时（自动）  GitHub Actions（美国 runner）            │
    │  抓取 12 源 → 硬过滤 → AI 审核 → build                     │
    │                                          │                  │
    │                              ┌───────────┴────────────┐     │
    │                              │ 按实测质量分桶          │     │
    │                              │ + 节点稳定性加权        │     │
    │                              └───────────┬────────────┘     │
    └──────────────────────────────────────────┼──────────────────┘
                                       提交 dist/
                                               ▼
                     gh-pages ──▶ 手机订阅（profile.yaml + nodes/*.yaml）
                                               │
       ┌───────────────────────────────────────┼────────────────────────┐
       ▼                                       ▼                        ▼
 source_health.json                 probe_latest.json            node_stability.json
 （源健康档案，含双视角分级）        （本机本轮全量探针）         （节点级可用率档案）
       ▲                                       ▲                        ▲
       │                    ┌──────────────────┴────────────┐           │
       │                    │  每日 12:30  本机全量探针      │───────────┘
       │                    │  scope=local（家用宽带）       │
       │                    │  与手机同源，唯一有权判优      │
       │                    └───────────────────────────────┘
       │
       │   ┌────────────────────────────────┐      ┌──────────────────────────────┐
       ├──▶│ 每日 04:23 云效杭州（第二视角）│      │ 每 6 小时 美国 CI（判死唯一）│
       │   │ scope=cnci，抽样 30/源，~75 秒 │      │ 连续 0 活且横跨 48h → 降级   │
       │   │ 结果推回主仓 state/            │      └──────────────────────────────┘
       │   │ 对回收有**否决权**（无决定权）  │
       │   └────────────────────────────────┘
```

云效那一层的数据经 `tools/ci_push_main.py` 推到主仓（Contents API 优先，git 兜底）。**推失败不影响探针**，结果仍安全存在 Codeup 的 `results/`。

> ⚠ **截至 2026-10-16，这条回传管道一次都没真跑过。** 它 10-16 09:26 才随 payload
> 部署到 Codeup，而当天 04:24 那轮跑的是旧内容。主仓里现有的 `results/` 与
> `state/probe_cnci_latest.json` **全是本机手工补进去的**（历史里能看到
> 「删除误推的合成存档」这类提交），不能当回传成功的证据。
>
> 第一次真跑 = **2026-10-17 04:23** 那轮。判据很简单：主仓
> `state/probe_cnci_latest.json` 的 `probed_at` 自己变成当天。
> 前提是云效流水线的变量里有 `GH_PAT` —— 没有它脚本会**直接跳过且不报错**。

---

## 3. 三层各干什么、谁能改什么

| 层 | 位置 | 频率 | 规模 | **权限** | 成本 |
|---|---|---|---|---|---|
| **L1** | 美国 GitHub Actions | **每 6 小时** | 全量（~3800 节点） | **唯一有权判死**（降级） | public 仓免费 |
| **L2** | 你的 PC（计划任务） | **每日 12:30** | 全量 | **主判优**（排序分桶、节点加权） | 0 |
| **L3** | 云效杭州 | 每日 04:23 | 抽样 30/源，75s | **回收的否决权** | 3000 核分额度用 **3.0%** |
| 备份 | Gitee `andywx/ci-probe-test` | — | — | 内容与 Codeup 逐字节一致 | 0 |

权限分配的依据见 §7。

---

## 4. 各个模块的作用

### 主流程（`src/`，每 6 小时的 CI 跑）

| 模块 | 作用 | 关键点 |
|---|---|---|
| `fetch.py` | 抓 12 个源的原始订阅 | 走 GitHub API 取 base64（`raw.githubusercontent.com` 国内必墙） |
| `filters.py` | 硬过滤：明文协议放行、按簇聚类、`exclude_filter` | **明文 http/socks5 必须放行**（实测 545 明文通过 32%，733 加密协议只 1.9%）；`exclude_filter` **必须逐源取值** |
| `ai_review.py` | AI 审核，按「簇」而非按节点审 | 4831 节点 → 1683 簇。给 LLM 的协议是「只报要删的」 |
| `ai_backends.yaml` | 多后端故障转移链 | 腾讯 tokenhub / 硅基流动 / OpenRouter 三云冗余 |
| `build.py` | 产出 profile + 节点文件 | **代理组全部动态生成**（见 §5）；模板只提供规则/dns |
| `run.py` | 流水线主入口 | 两阶段并发：抓取+硬过滤 ‖ AI 审核 |
| `report.py` | 生成 `reports/` 审计留痕 | 含质量分桶表：每个源为什么在那组 |

### 健康档案（`src/health.py`）

维护 `state/source_health.json`，就地改写 `sources.yaml` 的 `enabled`。

- **降级**：CI 口径连续 3 轮 `alive == 0`，**且这些轮次横跨 >= 48 小时** → `enabled: false` + 移入 `archive/`
  （跨度这条是 2026-10-16 加的：cron 从每周提到每 6 小时后，只数轮数会把判死从 3 周变成 18 小时）
- **回收**：本机口径达标 2 轮 **且** 云效不否决 → `enabled: true`
- **双视角分级**：本机 × 云效交叉，分 T1/T2/T3（见 §7）
- 永不删除源本体，只改开关

### 真探针（`src/probe.py`）

用 mihomo 内核起 file provider，探测 `youtube.com/generate_204`。

| 参数 | 作用 | 注意 |
|---|---|---|
| `--sample N` | 每源分层抽样 N 个节点 | **按服务器 IP 网段分层**，不是随机抽 |
| `--scope` | `ci` / `local` / `cnci` | 决定这轮数据能参与什么决策 |
| `--hc-timeout` | 单节点探测超时，默认 8000ms | **直接线性偏置 alive**。调小它 = 批量制造假死亡 |

### 节点稳定性（`src/node_stability.py`）

维护 `state/node_stability.json`：`{源, 轮次, 存活轮次, 最近 8 个存活延迟}`。

- **指纹取「整份配置去掉 name」的 sha1** —— 用节点名做键是错的，名字每天都在变（国家标签、序号重排）
- **只记录 `scope=local` 的全量轮次**（抽样会误伤未抽中的节点；`ci` 是美国视角）
- 剪掉 30 天未出现的

### 云端与运维（`tools/`）

| 文件 | 作用 |
|---|---|
| `local_probe.py` | 本机探针入口，供计划任务调用 |
| `run_local_probe.cmd` | 计划任务入口（**必须纯 ASCII + CRLF**） |
| `probe_payload.py` | 云端仓库内容的**唯一来源**（Codeup 与 Gitee 共用） |
| `sync_and_probe.sh` | 云端探针唯一入口：同步（带重试）→ 跑探针 → 推主仓 |
| `ci_probe_run.py` | 云端探针执行器：解压内核、vendor yaml、跑探针、commit 结果 |
| `ci_push_main.py` | 把云效结果推回主仓（Contents API 优先，git 兜底，**永不失败**） |
| `check_ci_scripts.py` | **Python 3.6 静态门禁**（28 个文件，交付前必跑） |
| `test_stability.py` / `test_build_groups.py` / `test_health_tiering.py` | 三组回归测试 |
| `verify_profile.py` | **用真 mihomo 内核校验生成的 profile**（见 §9） |
| `restore_codeup.py` / `CI_RECOVERY.md` | 云效组织被删后的灾难恢复 |
| `codeup_push.py` / `gitee_push.py` | 推送云端内容到两个远端 |

---

## 5. 「每次用都是多源中最优」是怎么实现的

这是三个维度分给三个执行者，**各管各的时间尺度**：

| 维度 | 谁负责 | 为什么不是别人 |
|---|---|---|
| **选哪个源** | 探针（多轮均值 + 云效否决） | 源质量是**天**级别的慢变量 |
| **选哪些节点进池子** | 探针（历史可用率） | 稳定性是**周**级别的慢变量 |
| **此刻选哪个节点** | Clash `url-test`（每 120 秒） | 节点状态是**秒**级别的快变量 |

三层探针**做不到**第三件事，也不该做 —— 每天跑一次的探针，用它选节点等于用昨天的信息挑今天的。

### 5.1 质量分桶（build.py 动态生成）

```
AUTO   url-test   只放达标源（本机多轮均值 ≥ 8%），前 6 名降序
备用   select     未达标但有活的 + 不稳定组
观察   select     本机 < 8%
FAILOVER fallback 保留全部启用源（安全网不被质量分桶削掉）
```

**排序只用国内口径。** 美国 CI 的 Spearman rho 仅 0.48，不可排序（shaoyouvip 美国 81.2% #4 / 国内 6.2% #11 垫底）。

达标源不足 3 个时**构建直接失败** —— 宁可不出也不给一个残缺的自动组。

### 5.2 节点稳定性加权

被判不稳的节点写进 `nodes/<源>--flaky.yaml`，从 `nodes/<源>.yaml` 里移出，
以 `SRCFL-*` provider 挂到「不稳定」组 —— **仍可用，只是不自动竞速**。

三重保险，每条对应一种「把池子砍空」的失败方式：

| # | 触发条件 | 行为 |
|---|---|---|
| 1 | 攒够 5 轮的节点 < 100 个 | **完全不加权** |
| 2 | 节点没有历史 | **一律保留**（新节点不该因「未知」被淘汰） |
| 3 | 单源保留数低于地板 | 该源整体不砍 |

**被移出的节点仍会被探针测量**（探针的发现逻辑是 `glob('*.yaml')`）——
不测就永远无法翻盘。`<源>--flaky` 这个伪源名在 `health.py` 里被过滤，不进健康档案。

---

## 6. 前置要求

| 组件 | 要求 | 备注 |
|---|---|---|
| GitHub Actions | 本仓 public，**Actions 分钟数免费** | job 超时 90 分钟 |
| 云效（L3） | **Python 3.6.8**、2 核、38GB 磁盘 | 内核与 vendor PyYAML **已预置进仓库**，不现场下载 |
| 云效环境变量 | `GH_PAT` = 对本仓有 Contents 写权限的令牌 | 不配也能跑，只是数据不回主仓 |
| 本机（L2） | Windows + Clash Verge 的 `verge-mihomo.exe` | 每日 12:30 |
| 开发 | portable-git（无系统 git）、Python 3.11 | GitHub 直连被墙，push/API 走 `127.0.0.1:7897` |

**凭据**（全部在 `.gitignore` 内，仓库是 public 绝不能入库）：

```
.aikey-token        GitHub PAT（写 Actions secrets + 推云效结果）
codeup.token        云效个人访问令牌（原始）
codeup.https        登录账号 + 令牌（由 codeup_auth.py 生成）
gitee.token         Gitee 私人令牌
aliyun.token        阿里云账号密码
tx.aikey-token      腾讯 tokenhub
```

---

## 7. 三条铁律

### ① 判死（降级）只能由 L1（美国）做

国内发起探测时 `alive == 0` 是**歧义的** —— 节点真死了？还是它的 IP 被 GFW 阻断、我根本连不上？两者在数据上完全一样。

> 推论：**即使买国内服务器，也只能把「判优」搬过去，判死仍得留在美国。**

### ② 排序与节点加权以 L2（本机）为主，L3 只有否决权

**L2 是主排序依据**，因为家用宽带与手机同源。

L3（云效）**只有否决权、没有决定权**：

```
回收（enabled: false → true）要求「本机达标 且 云效不否决」
```

这样只会让回收更**保守**：否决的失败后果是多留一个源在历史库（可逆无害）；
若云效能单独放行，则会把差源捞回池子（不可逆污染）。

### ③ 为什么需要三个视角，而不是一个

假设「用户的手机在家宽上用」，则本机是唯一真值。但**手机位置是移动的** ——
跨运营商、跨地区、跨 4G/家宽。实测 `rho(云效, 本机)` 仅 **0.734**：
两个视角看的是不同的网络，各自成立但都不完整。

所以**分歧本身就是要用的信息**，据此分四档：

| 本机 | 云效 | 分级 | 含义 |
|---|---|---|---|
| 达标 | 达标 | **T1** | 到处能用 |
| 达标 | 不达标 | **T2** | 位置敏感，自动回收会排除它 |
| 不达标 | 达标 | **T3** | 机房友好，低优先级 |
| 不达标 | 不达标 | **T4** | 两视角都不行，该考虑降级 |

实测印证：`snakem982` 云效 0% / 本机 15.4% → **T2 位置敏感**（该源 63 个节点里 40 个是域名型免费中转，普遍封禁机房 IP）；`ermaozi` 云效 13.3% / 本机 2.9% → **T3 机房友好**。

> ⚠ **T4 这一格曾经根本不存在。** 代码只有三个分支，`else` 同时吃掉了
> 「本机差+云效达标」和「本机差+云效也差」，于是**到处都不行的源被标成
> 「机房友好」**——而 T3 按规划要用于降优先级，这个标签是主动误导。
> 更巧的是 12 个真实源里**没有一个落在第 4 格**，所以测试全绿也说明不了问题。
> 现在 `test_health_tiering.py` 用合成源 `demo_t4` 覆盖该格，并断言**四格全覆盖**。

> ⚠ 云效轮次不足 7 轮时分级显示 `?` 且**不参与回收判定**。
> 单轮噪声实测 avg 5.5pp / max 16.7pp，与 8% 阈值同量级，单轮不可用于判定。
> 分级在云效改日更后约一周内自然生效，届时再回来校准阈值。

---

## 8. 出问题的影响

| 故障 | 影响 | 严重度 | 表现 |
|---|---|---|---|
| **L1 挂了** | 订阅不更新；差源不下线 | **高**（唯一影响日常体验的） | 手机上节点越来越旧 |
| **L2 挂了** | 排序用旧数据、分桶退化；节点加权停更 | 中 | 分桶反映的是上次跑时的质量 |
| **L3 挂了** | 回收失去否决权（退回本机单视角）；订阅不受影响 | 低 | 主仓 `state/probe_cnci_latest.json` 停止更新 |
| **本机连不上 GitHub** | 云效结果进不了主仓 | 低 | 分级显示「无云效口径数据」，其余正常 |
| AI 后端全挂 | 不再剔除广告节点 | 中 | 节点名里出现引流信息 |
| 某个源挂了 | 连续 3 轮 0 活、横跨 >= 48h 后自动降级 | 无 | `sources.yaml` 里 `enabled: false` |
| **稳定性档案被污染** | 池子被误砍 | 中 | AUTO 里节点数骤减 |
| 云效组织被删 | L3 停摆 + Codeup 仓库丢失 | 中（有备份） | `restore_codeup.py --apply` + 按 `CI_RECOVERY.md` 重建 |

**共识：探针层的故障都是「保守失败」** —— 不会误杀源、不会让订阅变坏，只是少做事。真正不能挂的是 L1。

---

## 9. 运维

### 手动触发

```powershell
python tools\dispatch_workflow.py      # 触发 L1
python tools\check_run.py              # 看运行状态
tools\run_local_probe.cmd              # 跑 L2（+ --no-push / --scope-only）
```

云效 → 流水线 → 运行。命令行：

```bash
ok=0; for i in $(seq 1 8); do git fetch origin && git reset --hard origin/master && { ok=1; break; }; sleep 20; done; [ "$ok" = "1" ] && bash tools/sync_and_probe.sh || { echo "同步失败"; exit 1; }
```

### 交付前必跑（全部九道）

```powershell
python tools\check_ci_scripts.py      # Python 3.6 静态门禁
python tools\test_probe_wiring.py     # 探针 ↔ 稳定性档案 的接线
python tools\test_health_tiering.py   # 双视角分级（四格全覆盖）+ 判死轮数/跨度双闸门
python tools\test_build_groups.py     # 质量分桶
python tools\test_stability.py        # 节点稳定性加权
python tools\test_flaky_reprobe.py    # 被移出的节点能否翻盘
python tools\test_fault_injection.py  # 坏数据进来时是否明确报错
python tools\test_provider_load.py    # 一个畸形节点会不会让整源加载失败（真内核）
python tools\verify_profile.py        # 真 mihomo 内核校验
python tools\probe_field_types.py     # mihomo 接受哪些字段类型
```

> ⚠️ **`test_provider_load.py`** 补的是「**真内核跑起来整源消失**」这一类 ——
> 2026-10-16 实测：`dist/nodes/autojiedian.yaml` 里一个 `sni: false`（布尔塞进
> string 字段）让 mihomo 报 `'sni' expected type 'string'`，**892 个节点一个都没
> 加载进来**，而当时 7 道门禁全绿：
>
> | 为什么没抓到 | 它验的是什么 |
> |---|---|
> | `test_fault_injection.py` | 坏**数据**进不进来（这个是合法 YAML、字段名也在白名单里） |
> | `verify_profile.py` / `test_stability.py` 的 `mihomo -t` | **`-t` 不加载 provider** —— provider 的解析错误只在实例启动时才出现 |
> | `probe_field_types.py` | 逐类型规则本身对不对，不是「产出物能不能加载」 |
>
> 和坑 §33 同一类：**provider 级失败是全有全无、不报错、只少一个源**。
> 所以这个测试的**场景 A 必须复现基线**（原文件喂内核必须被拒），否则后面的
> 「修复后能加载」什么都不证明。

> ⚠️ **`test_fault_injection.py`** 逐个把输入搞坏（截断 JSON、字段类型漂移、
> 越界数值、空源清单），断言系统是**明确报错/明确降级**而不是静默按默认值走。
> 它逮到过三个静默失败：健康档案损坏会**静默从零开始**（丢光累积的多轮历史）、
> `sources: []` 会被**照单全收写回**（源清单进 git）、单源字段类型漂移会**崩掉整轮**。

> ⚠️ **`test_probe_wiring.py`** 补的是一个真实的、长期存在的静默失败：
> `probe.node_fingerprints()` 漏 `import yaml`，每次调用抛 `NameError` 被
> `except Exception: continue` 吞掉 → 稳定性档案**压根没生成**，而探针照常
> 打印正常结果、退出码 0。`test_stability.py` 那时是全绿的 —— 因为它测的是
> `node_stability.merge()` 这个**模块**，坏掉的是**模块与探针之间的连线**。
> **测模块不等于测接线。**

### ⚠ 为什么最后一道不能省

**真内核校验逮到过三个断言全绿但产出物坏掉的问题**：

| 症状 | 断言为什么没抓到 |
|---|---|
| `rules[43] [RULE-SET,claude,Claude] error: proxy [Claude] not found` | 只验了「组之间自洽」，没验「rules 的目标存在」 |
| `proxy group[14]: 备用: 'SRCFL-xxx' not found` | 断言写成 `p in gp or p in providers` —— provider 名也满足，而内核不接受 |
| 停用任一源导致构建失败 | 模板把 `SRC-*` 写死，断言没覆盖「源被停用」这个状态 |

> **断言只能验证你想到的东西。** 每次改组结构都必须让真 mihomo 吃一遍。

另外：`mihomo -t` 会试图从 GitHub 下 MMDB，国内连不上时 exit 也是 1，**会把真失败掩盖掉**。`verify_profile.py` 已先拷 Clash Verge 自带的 geodata 规避。

### 已知坑

| 坑 | 现象 | 真因 |
|---|---|---|
| 云效 workspace 不刷新 | 改了代码但跑的还是旧的 | 复用带缓存 workspace → **必须 `git reset --hard`** |
| 同步脚本无法自举 | 首次 `No such file or directory` | 脚本在仓库里而 workspace 太旧 → **CI 首条命令必须自包含** |
| 云效 git 端点抖动 | `502` / `port 80 连不上` | 未鉴权返回 **302 跳 SSO**，报错极具误导性，**不是凭据问题** |
| `probe_payload` 落地路径 | `bash tools/sync_and_probe.sh` 找不到 | `*.sh` 落 `tools/`，`*.py` 落根目录 |
| `.cmd` 中文注释炸 cmd.exe | 报「xxx 不是内部或外部命令」 | 按 OEM 码页读 → **必须纯 ASCII** |
| `.cmd` 用 LF 行尾 | 退出码传不出来 | **必须 CRLF** |
| `grep -c` 掐死 `&&` 链 | 计数为 0 时后续不执行 | 写 `$(grep -c x f \|\| true)` |
| 云端日志面板不可靠 | 跑满 67 秒只渲染部分输出 | 所以结果必须 commit 回仓库，**日志只用于排查** |
| `mihomo -t` 不校验 provider | 配置校验 exit=0，实例一启动整源消失 | provider 的解析错误**只在实例启动时**才打进日志；`-t` 只验配置结构 |
| 一个畸形节点毁掉整源 | 892 个节点 0 加载，日志只有一行 error | provider 级失败**全有全无**；字段**类型**不在白名单检查范围内（坑 §33） |
| 测试把源清单改坏 | 跑一次 `test_health_tiering`，`src/sources.yaml` 变成历史库的内容 | 备份文件名用了 `os.path.basename` → `src/` 与 `archive/` 的 `sources.yaml` **撞名**互盖 |
| 测试往源清单里追加合成源 | 报 `mapping values are not allowed here` | `sources:` 的条目缩进 2 格，且文件末尾是另一个顶层键 `excluded:` |

---

## 10. 新增一个源

1. 把 URL 加进 `src/sources.yaml`
2. **必须真探针验证** —— README 说的"测速筛选"不可信
3. `exclude_filter` **逐源取值**，不要复制粘贴
4. 跑 `python src\local_probe.py --no-push` 看真实国内通过率
5. 通过率 < 5% 且稳定的，别加

`src/discover.py` 每轮（schedule 触发时）自动从 GitHub 扫新共享源，但**只进 `data/discovered_pool.json` 候选池，绝不自动入池** —— 源的结论必须来自真探针。

---

## 11. 目录结构

```
src/
  sources.yaml          源清单（12 个），enabled 由 health.py 维护
  probe.py              真探针（含分层抽样、settle 检测、节点级留档）
  health.py             源健康档案（双口径 + 双视角分级）
  node_stability.py     节点级稳定性档案
  build.py              产出 profile + 节点文件（组结构动态生成）
  ai_review.py          AI 审核      filters.py  硬过滤
  fetch.py  discover.py  run.py  report.py
.github/workflows/update.yml   13 步流水线
dist/                   产物：profile.yaml + nodes/*.yaml（含 *--flaky.yaml）
reports/                审计留痕（含质量分桶表）
state/                  probe_latest.json / probe_cnci_latest.json
                        source_health.json / node_stability.json
results/                云效探针历史存档
tools/                  云端执行、运维、测试、校验（见 §4）
```