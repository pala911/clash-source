# -*- coding: utf-8 -*-
"""验证 src/refill.py 自动补员（CI 侧唯一的 sources.yaml 插入写者）。

## 用例（每条都有真实事故/拍板背景）

  A 基线补员：approved + 空位 -> 插 1 条；原有行序一字不动（子序列断言）、
     excluded 段逐字节不变、新条目带 auto_added/enabled/max_nodes=500；
     state/refill_last.json 落 last_refill_at/name/url
  A2 幂等：同一输入连跑两次，第二次必须无事可补（URL 已在清单 = 排重兜底）
  B cap 满（拍板：enabled=12 为稳态上限；现存 15 个不动，cap 只管未来）
     -> 不写入，且把「挂待用（pending-cap）」的人数说出来
  C 节流：距上次补员 < 24h -> 不写入（补员是慢系统，一次塞一串会让
     观察期失去意义 —— 10-19 拍板「每轮最多补 1」）
  D 排重：URL 已在 sources（含 enabled=false 的隔离源）/ excluded -> 一律跳过；
     excluded 是评估/人工的排除决定，自动补员绝不推翻
  E 选优：多条 approved -> 取 rate 最高者（同分再看 alive/best_ms）
  F 命名冲突：与既有源重名 -> 自动 -2 后缀（绝不覆盖别人）
  G 通道损坏：eval_verdicts.json 不是合法 JSON -> 大声说明、不写（游客身份，
     非关键消费者不红 CI；报警交给 eval 侧）
  H 节流状态损坏 -> 按「刚补过」保守处理，不写入
  I REFILL_DISABLE=1 紧急停用开关 -> 直接跳过
  J dry-run -> 全程不写任何文件
  K cap 内但通道无 approved -> 无事

⚠ 全程只动临时文件（monkeypatch refill.SOURCES/CHANNEL/STATE），
  真 src/sources.yaml / data/* / state/* 一字不碰。
"""
import contextlib
import io
import json
import os
import shutil
import sys
import time

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import refill                                   # noqa: E402

TMPDIR = os.path.join(ROOT, ".tools", "_refill_test")
FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                         ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def make_text(n_enabled=2, with_excluded=True):
    """造一份 sources.yaml 头（与真文件同构：条目 2 空格 / 字段 4 空格 / 尾部 excluded）。"""
    lines = ["# 头注释（补员测试的临时清单）", "sources:"]
    for i in range(n_enabled):
        lines += ["  - name: src%02d" % i,
                  "    url: https://example/s%02d" % i,
                  "    enabled: true",
                  "    note: n%d" % i]
    if with_excluded:
        lines += ["",
                  "# 已评估但未纳入（改 enabled: true 即恢复）",
                  "excluded:",
                  "  - name: gone",
                  "    url: https://example/gone",
                  "    reason: 空文件"]
    return "\n".join(lines) + "\n"


def cand(url="https://example/newone", verdict="approved", rate=10.0, alive=5,
         best=500, evaluated="2026-10-29T05:00:00Z", name="", repo="someone/NewOne"):
    d = {"url": url, "verdict": verdict, "note": "rate=%.1f%% alive=%d" % (rate, alive),
         "rate": rate, "alive": alive, "best_ms": best, "evaluated_at": evaluated}
    if repo:
        d["repo"] = repo
    if name:
        d["name"] = name
    return d


def write_channel(cands):
    with io.open(refill.CHANNEL, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"channel": "eval_verdicts", "generated_at":
                   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "candidates": cands}, f, ensure_ascii=False, indent=2)


def write_state(d):
    with io.open(refill.STATE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def read_state():
    with io.open(refill.STATE, encoding="utf-8") as f:
        return json.load(f)


def run():
    """跑一遍 main，抓回退出码+全部 stdout。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = refill.main([])
    return rc, buf.getvalue()


def iso_hours_ago(h):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600 * h))


def is_subsequence(old_lines, new_lines):
    """原文件的每一行都必须在新文件里**按原顺序**出现（允许在其间插入新行）。"""
    it = iter(new_lines)
    for ln in old_lines:
        for x in it:
            if x == ln:
                break
        else:
            return False
    return True


def setup():
    """重置临时目录与 monkeypatch。"""
    shutil.rmtree(TMPDIR, ignore_errors=True)
    os.makedirs(TMPDIR, exist_ok=True)
    refill.SOURCES = os.path.join(TMPDIR, "sources.yaml")
    refill.CHANNEL = os.path.join(TMPDIR, "eval_verdicts.json")
    refill.STATE = os.path.join(TMPDIR, "refill_last.json")


def teardown():
    shutil.rmtree(TMPDIR, ignore_errors=True)


setup()
try:
    # ---------------- A 基线补员 ----------------
    print("A 基线：approved + 空位 -> 恰好补 1 条，原有文本一字不动")
    base = make_text(2)
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(base)
    write_channel([cand(rate=10.0, alive=5, best=500)])
    rc, out = run()
    check(rc == 0 and "已补员" in out, "补员成功且说出来", out.strip().splitlines()[-1][:90])
    got = io.open(refill.SOURCES, encoding="utf-8").read()
    doc = yaml.safe_load(got)
    names = [s["name"] for s in doc["sources"]]
    check(names[-1] == "NewOne", "名字取 repo 尾段（与人工接入同调）", "、".join(names))
    e = doc["sources"][-1]
    check(e["auto_added"] is True and e["enabled"] is True
          and e["max_nodes"] == 500, "新条目带 auto_added/enabled/max_nodes=500")
    check(e["url"] == "https://example/newone", "URL 就是入选那条")
    check(len(doc["sources"]) == 3 and len(doc.get("excluded") or []) == 1,
          "源数 +1，excluded 段条目数没变")
    check("已评估但未纳入（改 enabled: true 即恢复）" in got,
          "excluded 段的横幅注释还在")
    old_lines = base.split("\n")
    check(is_subsequence(old_lines, got.split("\n")),
          "原有每一行都按原顺序保留（append-only，绝不整份重写）")
    check(got.split("excluded:")[1] == base.split("excluded:")[1],
          "excluded 段逐字节不变")
    st = read_state()
    check(st.get("last_refill_at") and st.get("last_name") == "NewOne"
          and st.get("last_url") == "https://example/newone",
          "state 落 last_refill_at/name/url",
          json.dumps({k: st.get(k) for k in ("last_name", "last_url")},
                     ensure_ascii=False)[:90])
    print()

    # ---------------- A2 幂等 ----------------
    print("A2 幂等：同一份通道/清单再跑一遍，必须无事可补")
    rc, out = run()
    check(rc == 0 and "已在 sources/excluded" in out, "排重兜底说清楚了原因",
          out.strip().splitlines()[-1][:90])
    check(io.open(refill.SOURCES, encoding="utf-8").read() == got,
          "第二个连跑没有造成第二次插入")
    print()

    # ---------------- B cap 满 ----------------
    print("B cap 满：enabled=12 -> 挂待用（pending-cap），不写入")
    setup()
    base12 = make_text(12)
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(base12)
    write_channel([cand(url="https://example/waiter")])
    rc, out = run()
    check(rc == 0 and "挂待用" in out and "12/12" in out,
          "cap 满 -> 挂待用且人数说了出来", out.strip().splitlines()[-1][:100])
    check(io.open(refill.SOURCES, encoding="utf-8").read() == base12,
          "cap 满时文件一字未动")
    print()

    # ---------------- C 节流 ----------------
    print("C 节流：1 小时前刚补过 -> 不补（补员是慢系统）")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    write_channel([cand()])
    write_state({"last_refill_at": iso_hours_ago(1), "v": 1})
    rc, out = run()
    check(rc == 0 and "节流" in out, "节流生效且说明原因", out.strip().splitlines()[-1][:90])
    check(not os.path.exists(refill.STATE) or read_state().get("last_name") is None,
          "节流轮里没写 state")
    print()

    # ---------------- D 排重 ----------------
    print("D 排重：excluded 段 / 已在 sources（隔离 enabled=false）的 URL 一律跳过")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    write_channel([cand(url="https://example/gone", name="gone"),
                   cand(url="https://example/newone")])
    rc, out = run()
    doc2 = yaml.safe_load(io.open(refill.SOURCES, encoding="utf-8").read())
    urls = {s["url"] for s in doc2["sources"]}
    check(rc == 0 and "https://example/gone" not in urls,
          "excluded 里的 URL 没有被翻案补回", "、".join(sorted(urls)))
    check("https://example/newone" in urls, "fresh 的候选正常补进")
    setup()
    # 隔离态条目走文本验证（确保 enabled=false 的 URL 也被 known_urls 记账）
    txt2 = make_text(2).replace(
        "  - name: src01\n    url: https://example/s01\n    enabled: true\n",
        "  - name: src01\n    url: https://example/isolated\n    enabled: false\n"
        "    note: 曾被判死\n")
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt2)
    write_channel([cand(url="https://example/isolated")])
    rc, out = run()
    check(rc == 0 and "全部已在" in out,
          "enabled=false 的旧 URL（含死过一次的）不会被重复补员",
          out.strip().splitlines()[-1][:90])
    print()

    # ---------------- E 选优 ----------------
    print("E 选优：两条 approved -> rate 最高的一条入选")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    write_channel([
        cand(url="https://example/weak", repo="w/Weak", rate=6.0, alive=4),
        cand(url="https://example/strong", repo="s/Strong", rate=21.0, alive=9, best=300),
    ])
    rc, out = run()
    doc3 = yaml.safe_load(io.open(refill.SOURCES, encoding="utf-8").read())
    check([s["name"] for s in doc3["sources"]][-1] == "Strong",
          "rate 最高者入选", "、".join(s["name"] for s in doc3["sources"]))
    print()

    # ---------------- F 命名冲突 ----------------
    print("F 命名冲突：重名 -> -2 后缀（绝不覆盖既有源）")
    setup()
    txt4 = make_text(2).replace("src00", "Strong").replace("src01", "StrongX")
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt4)
    write_channel([cand(url="https://example/strong2", repo="s/Strong",
                        rate=12.0, alive=6)])
    rc, out = run()
    doc4 = yaml.safe_load(io.open(refill.SOURCES, encoding="utf-8").read())
    nm = [s["name"] for s in doc4["sources"]]
    check("Strong-2" in nm, "冲突名变 Strong-2", "、".join(nm))
    check(len(nm) == len(set(nm)), "清单里没有重名")
    print()

    # ---------------- G 通道损坏 ----------------
    print("G 通道损坏：非法 JSON -> 大声说明、不写（不红 CI，报警归 eval 侧）")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    with io.open(refill.CHANNEL, "w", encoding="utf-8") as f:
        f.write("{bad json")
    rc, out = run()
    check(rc == 0 and "解析失败" in out, "坏通道被说出来", out.strip().splitlines()[-1][:90])
    check(open(refill.SOURCES, encoding="utf-8").read() == make_text(2),
          "坏通道时清单一字未动")
    print()

    # ---------------- H 节流状态损坏 ----------------
    print("H 节流状态损坏 -> 按「刚补过」保守处理")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    write_channel([cand()])
    with io.open(refill.STATE, "w", encoding="utf-8") as f:
        f.write("[[not json")
    rc, out = run()
    check(rc == 0 and ("节流" in out or "损坏" in out),
          "坏 state 被「刚补过」逻辑接住", out.strip().splitlines()[-1][:90])
    check(open(refill.SOURCES, encoding="utf-8").read() == make_text(2),
          "坏 state 时清单一字未动")
    print()

    # ---------------- I 紧急停用 ----------------
    print("I REFILL_DISABLE=1 紧急停用开关")
    setup()
    saved = os.environ.pop("REFILL_DISABLE", None)
    os.environ["REFILL_DISABLE"] = "1"
    try:
        with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
            f.write(make_text(2))
        write_channel([cand()])
        rc, out = run()
        check(rc == 0 and "停用" in out, "开关生效并说明", out.strip().splitlines()[-1][:80])
        check(open(refill.SOURCES, encoding="utf-8").read() == make_text(2),
              "停用时清单一字未动")
    finally:
        if saved is None:
            os.environ.pop("REFILL_DISABLE", None)
        else:
            os.environ["REFILL_DISABLE"] = saved
    print()

    # ---------------- J dry-run ----------------
    print("J dry-run：决策照做，但任何文件都不写")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    write_channel([cand()])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = refill.main(["--dry-run"])
    check(rc == 0 and "dry-run" in buf.getvalue(),
          "dry-run 说清楚了没写")
    check(open(refill.SOURCES, encoding="utf-8").read() == make_text(2),
          "清单一字未动")
    check(not os.path.exists(refill.STATE), "state 也没写")
    print()

    # ---------------- K 通道没有 approved ----------------
    print("K 通道只有 rejected/uncertain -> 无事")
    setup()
    with io.open(refill.SOURCES, "w", encoding="utf-8", newline="\n") as f:
        f.write(make_text(2))
    write_channel([cand(url="https://example/r1", verdict="rejected"),
                   cand(url="https://example/u1", verdict="uncertain")])
    rc, out = run()
    check(rc == 0 and "无 approved" in out, "无候选时明确说无事可做",
          out.strip().splitlines()[-1][:90])
finally:
    teardown()

print("=" * 66)
if FAILS:
    print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
    sys.exit(1)
print("结果：全部通过（cap/节流/排重/选优/命名/损坏/停用/dry-run 九路守卫 + "
      "append-only 子序列断言）")
sys.exit(0)
