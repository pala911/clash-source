# -*- coding: utf-8 -*-
"""触发一次云效国内探针流水线，并盯到结束；完了自动读回传留痕给结论。

## 为什么需要它

L3（云效）的「跑没跑、通没通」以前只能靠翻流水线面板 —— 而那边**没有**像
L1 那样的可调用入口。这次是把云效 OpenAPI 摸清了才补上的：

  ⚠ 云效有两套接入点，用错必然 404/401（我在这上面栽了整整一轮）：

    中心版 : https://openapi-rdc.aliyuncs.com
             /oapi/v1/flow/organizations/{organizationId}/pipelines/...
    Region版: https://{实例访问域名}          <- 就是控制台那个 host
             /oapi/v1/flow/pipelines/...        <- **不带 organizationId**

  我们是 Region 版（控制台 host = myxk-cn-shenzhen.devops.aliyuncs.com），
  鉴权头一律是 `x-yunxiao-token: pt-...`。

  判据（找接口时很好用）：
    · 401 InvalidToken  -> 路由存在、鉴权没过
    · 404 NotFound      -> 这个路由不存在
    · 200 + HTML        -> 被控制台 SPA 兜底了，不是接口

## 用法

    python tools\\cnci_trigger.py            # 触发一轮，盯到结束，再读留痕
    python tools\\cnci_trigger.py --status   # 只看最近几次运行，不触发
    python tools\\cnci_trigger.py --triggers # 读定时触发配置（改完用它核对）
    python tools\\cnci_trigger.py --wait 900 # 自定义等待上限（秒）

⚠ 触发**不改**任何配置，只是让流水线跑一轮（和定时触发同一件事）。
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOST = os.environ.get("CNCI_HOST", "myxk-cn-shenzhen.devops.aliyuncs.com")
PIPELINE_ID = int(os.environ.get("CNCI_PIPELINE_ID", "1400185"))
DONE = ("SUCCESS", "FAIL", "FAILED", "CANCELED", "CANCELLED", "TERMINATED")


def token():
    for fn in ("codeup-clash20261016.token", "codeup.token"):
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read().strip()
            if t:
                return t
    print("✗ 找不到云效个人访问令牌（codeup.token / codeup-clash*.token）")
    sys.exit(2)


def call(path, method="GET", body=None, timeout=40):
    req = urllib.request.Request("https://%s%s" % (HOST, path), method=method)
    req.add_header("x-yunxiao-token", token())
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)[:180]


def bj(ms):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ms / 1000.0 + 8 * 3600)) \
        if ms else "-"


def list_runs(n=8):
    code, body = call("/oapi/v1/flow/pipelines/%d/runs?page=1&perPage=%d"
                      % (PIPELINE_ID, n))
    if code != 200:
        return None, "HTTP %s %s" % (code, body[:160])
    try:
        d = json.loads(body)
    except Exception as e:
        return None, "解析失败 %r" % e
    rs = d if isinstance(d, list) else (d.get("result") or d.get("pipelineRuns") or [])
    return rs, ""


def show(runs):
    for r in runs:
        print("  runId=%-4s %-9s trigger=%s  %s -> %s"
              % (r.get("pipelineRunId"), r.get("status"), r.get("triggerMode"),
                 bj(r.get("startTime")), bj(r.get("endTime"))))


def show_triggers():
    """把 pipelineConfig.triggers 翻译成人话。

    ⚠ 触发器没有 OpenAPI（只能控制台改），所以这是**改完核对**的唯一手段。
      云效定时触发有两种：
        周期触发 -> type=PERIOD，在 from~to 时间段内**每 interval 分钟触发一次**
                    （所以窗口不是"每天一次"，窗口越宽跑得越多）
        单次触发 -> 每天（勾周一~周日）某一个时间点一次
    """
    code, body = call("/oapi/v1/flow/pipelines/%d" % PIPELINE_ID)
    if code != 200:
        print("✗ 读流水线失败 HTTP %s %s" % (code, body[:160]))
        return 2
    d = json.loads(body)
    tr = (d.get("pipelineConfig") or {}).get("triggers")
    if isinstance(tr, str):
        try:
            tr = json.loads(tr)
        except Exception:
            pass
    print("流水线: %s（id=%d）" % (d.get("name"), PIPELINE_ID))
    print("定时触发配置：")
    if not tr:
        print("  （无触发器）")
        return 0
    for t in (tr if isinstance(tr, list) else [tr]):
        kind = t.get("type")
        print("  - 类型: %s" % kind)
        if kind == "SCHEDULED":
            s = t.get("scheduled") or {}
            st = s.get("type")
            days = s.get("daysOfWeek")
            print("      子类型: %s" % st)
            print("      星期  : %s（1..7 = 周一..周日）" % days)
            if st == "PERIOD":
                print("      时间段: %s -> %s" % (s.get("from"), s.get("to")))
                print("      间隔  : %s 分钟" % s.get("interval"))
                print("      ⇒ 周期触发：在这个时间段内**每 %s 分钟触发一次**，"
                      % s.get("interval"))
                print("        所以一天会跑多轮（不是一天一轮）")
            else:
                print("      时间  : %s" % s.get("fixedTime"))
                print("      ⇒ 单次触发：每天在固定时间跑一次")
            if s.get("timezone"):
                print("      时区  : %s" % s.get("timezone"))
        elif t.get("webhookUrl"):
            print("      webhook: %s" % t.get("webhookUrl"))
    return 0


def main():
    args = sys.argv[1:]
    wait = 900
    if "--wait" in args:
        wait = int(args[args.index("--wait") + 1])

    code, body = call("/oapi/v1/flow/pipelines/%d" % PIPELINE_ID)
    if code != 200:
        print("✗ 读流水线失败 HTTP %s %s" % (code, body[:160]))
        print("  （接入点是实例域名 %s 吗？中心版要用 openapi-rdc，路径也不同）" % HOST)
        return 2
    name = (json.loads(body) or {}).get("name")
    print("流水线: %s（id=%d，host=%s）" % (name, PIPELINE_ID, HOST))

    if "--triggers" in args:
        return show_triggers()

    runs, err = list_runs()
    if runs is None:
        print("✗ 读运行历史失败：%s" % err)
        return 2
    print("\n触发前最近几次：")
    show(runs[:3])

    if "--status" in args:
        return 0

    print("\n触发一轮 ...")
    code, body = call("/oapi/v1/flow/pipelines/%d/runs" % PIPELINE_ID, "POST", {})
    if code not in (200, 201):
        print("✗ 触发失败 HTTP %s %s" % (code, body[:200]))
        return 1
    print("  已排队（返回 %s）" % body.strip()[:40])

    before = {r.get("pipelineRunId") for r in runs}
    t0, last, done = time.time(), None, None
    while time.time() - t0 < wait:
        time.sleep(15)
        rs, _ = list_runs()
        new = [r for r in (rs or []) if r.get("pipelineRunId") not in before]
        if not new:
            continue
        r = new[0]
        st = r.get("status")
        if st != last:
            print("  [%3ds] runId=%s status=%s" % (int(time.time() - t0),
                                                   r.get("pipelineRunId"), st))
            last = st
        if st in DONE:
            done = r
            break
    if not done:
        print("⚠ 等了 %ds 还没结束 —— 去控制台看（云效日志面板有时不渲染）" % wait)
        return 1
    print("\n本轮 %s，用时 %ss（runId=%s）"
          % (done.get("status"),
             int((done.get("endTime", 0) - done.get("startTime", 0)) / 1000),
             done.get("pipelineRunId")))

    sys.stdout.flush()      # 否则子进程的输出会先冒出来，管道里看很乱
    print("\n" + "=" * 68)
    print("看回传结果（读 Codeup 里的留痕 push_main_last.json）：")
    print("=" * 68)
    subprocess.run([sys.executable, os.path.join(HERE, "cnci_status.py")], cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
