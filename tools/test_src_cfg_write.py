# -*- coding: utf-8 -*-
"""验证 health.write_src_cfg 只改 enabled、绝不整份重写。

## 为什么单独测这个

`src/sources.yaml` 里最值钱的东西不是 12 个 URL，而是那些注释
（「为什么 exclude_filter 必须逐源」「12% 通过率但 2100+ 节点」）。
原实现是 `yaml.safe_dump(cfg) + 4 行固定表头`，**一次降级就把注释从 23 行
抹到 4 行**（2026-10-16 实测）。这类丢失是静默的：git status 只显示
「已修改」，而结论一旦丢了就找不回来（没人会去翻 git 历史）。

## 六条用例

  A 基线：正常输入必须通过，且只动该动的那一行
  B 幂等：同一份 cfg 再写一次，文件逐字节不变
  C 归零守卫：sources: [] 必须拒绝
  D 暴跌守卫：源数掉到一半以下必须拒绝
  E 对不上：文本里的源与 cfg 对不上必须拒绝，**且文件原样不动**
  F 条目缺 enabled：补一行，缩进跟同条目其他字段一致

⚠ 全程只动临时文件（monkeypatch health.SOURCES），真 sources.yaml 一字不碰。
"""
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import yaml                                    # noqa: E402
import health                                  # noqa: E402

REAL = os.path.join(ROOT, "src", "sources.yaml")
TMPDIR = os.path.join(ROOT, ".tools", "_srccfg_test")
FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                        ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def comments(text):
    return sum(1 for ln in text.split("\n") if ln.lstrip().startswith("#"))


def target():
    return health.SOURCES


def read():
    return io.open(target(), encoding="utf-8").read()


def seed(text=None):
    """把（真的或指定的）源清单复制成待改的临时文件，返回文本。"""
    os.makedirs(TMPDIR, exist_ok=True)
    t = text if text is not None else io.open(REAL, encoding="utf-8").read()
    with io.open(target(), "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    return t


def cfg_of(text, **overrides):
    """从文本解析出 cfg，按 overrides 改 enabled（name -> bool）。"""
    cfg = yaml.safe_load(text)
    for s in cfg["sources"]:
        if s["name"] in overrides:
            s["enabled"] = overrides[s["name"]]
    return cfg


def expect_exit(fn, label):
    try:
        fn()
    except SystemExit as e:
        return check(True, label, str(e).splitlines()[0][:80])
    except Exception as e:                       # noqa: BLE001
        return check(False, label, "抛的是 %r 而不是 SystemExit" % (e,))
    return check(False, label, "居然没拒绝")


def main():
    # monkeypatch：所有读写都打到临时文件
    health.SOURCES = os.path.join(TMPDIR, "sources.yaml")
    shutil.rmtree(TMPDIR, ignore_errors=True)

    # ---------- A 基线 ----------
    print("A 基线：正常输入必须通过，且只动该动的那一行")
    base = seed()
    n_before = comments(base)
    lines_before = base.split("\n")
    check(n_before >= 15, "真源清单里确实有足够多的注释（基线成立）",
          "%d 行注释" % n_before)

    cfg = cfg_of(base, autojiedian=False)
    health.write_src_cfg(cfg, prev_count=12)
    after = read()
    lines_after = after.split("\n")
    check(comments(after) == n_before, "注释行数一行没少",
          "%d -> %d" % (n_before, comments(after)))
    check("逐源" in after and after.lstrip().startswith("#"),
          "关键注释文本还在（含「逐源」那段）")
    check(len(lines_after) == len(lines_before), "行数不变（没有重排/丢字段）",
          "%d -> %d" % (len(lines_before), len(lines_after)))

    diff = [i for i in range(len(lines_before))
            if lines_before[i] != lines_after[i]]
    check(len(diff) == 1, "只有 1 行被改动", "实际 %d 行：%s" % (len(diff), diff))
    if len(diff) == 1:
        check("enabled" in lines_after[diff[0]] and "false" in lines_after[diff[0]],
              "改的正是 autojiedian 的 enabled", lines_after[diff[0]].strip())

    parsed = yaml.safe_load(after)
    got = {s["name"]: s.get("enabled", True) for s in parsed["sources"]}
    check(got.get("autojiedian") is False, "解析后 autojiedian.enabled = false")
    check(all(v is True for k, v in got.items() if k != "autojiedian"),
          "其余源一律没被动过",
          "；".join("%s=%s" % (k, v) for k, v in got.items() if k != "autojiedian" and v is not True))
    check([s["name"] for s in parsed["sources"]] ==
          [s["name"] for s in yaml.safe_load(base)["sources"]],
          "源的数量与顺序不变")
    check(len(parsed.get("excluded") or []) ==
          len(yaml.safe_load(base).get("excluded") or []),
          "excluded: 段（候选排除清单）没被碰过")
    check(comments(after) == comments(base), "注释仍然完整（同前，二次确认）")
    print()

    # ---------- B 幂等 ----------
    print("B 幂等：同一份 cfg 再写一次，文件逐字节不变")
    health.write_src_cfg(cfg_of(read(), autojiedian=False), prev_count=12)
    again = read()
    check(again == after, "第二次写入后内容与第一次完全一致",
          "长度 %d vs %d" % (len(again), len(after)))
    print()

    # ---------- C 归零守卫 ----------
    print("C 归零守卫：sources: [] 必须拒绝")
    seed(base)
    before_c = read()
    expect_exit(lambda: health.write_src_cfg({"sources": []}, prev_count=12),
                "空清单被拒绝（SystemExit）")
    check(read() == before_c, "拒绝后文件原样不动")
    print()

    # ---------- D 暴跌守卫 ----------
    print("D 暴跌守卫：源数掉到一半以下必须拒绝")
    seed(base)
    small = {"sources": cfg_of(base)["sources"][:2]}
    expect_exit(lambda: health.write_src_cfg(small, prev_count=12),
                "12 -> 2 被拒绝（SystemExit）")
    check(read() == base, "拒绝后文件原样不动")
    print()

    # ---------- E 对不上 ----------
    print("E 文本与 cfg 对不上：必须拒绝，且不写")
    seed(base)
    full = cfg_of(base)
    # 造一个「文本里有、cfg 里没有」的场景：cfg 少一个源（但数量还是一半以上）
    short = {"sources": [s for s in full["sources"] if s["name"] != "zhuhaiuk"]}
    before_e = read()
    expect_exit(lambda: health.write_src_cfg(short, prev_count=12),
                "cfg 比文本少一个源 -> 拒绝")
    check(read() == before_e, "拒绝后文件原样不动（没退化成整份重写）")
    print()

    # ---------- F 条目缺 enabled / 不许碰 excluded ----------
    print("F 条目缺 enabled：补一行；且绝不碰 excluded: 段")
    mini = ("# 头注释：这个文件是唯一事实来源\n"
            "sources:\n"
            "  - name: alpha\n"
            "    url: https://example/alpha\n"
            "    enabled: false\n"
            "    note: 说明A\n"
            "  - name: beta\n"
            "    url: https://example/beta\n"
            "    note: 说明B（没有 enabled 字段）\n"
            "\n"
            "# 已评估但未纳入（改 enabled: true 即恢复）\n"
            "excluded:\n"
            "  - name: gamma\n"
            "    url: https://example/gamma\n"
            "    reason: 空文件\n")
    seed(mini)
    n0 = comments(mini)
    health.write_src_cfg(cfg_of(mini), prev_count=2)
    got = read()
    parts = got.split("- name: beta")
    beta_block = parts[1].split("- name:")[0] if len(parts) > 1 else ""
    check("enabled: true" in beta_block, "beta 缺的 enabled 被补上了",
          beta_block.strip().replace("\n", " | ")[:70])
    check("\n    enabled: true\n" in got,
          "补出来的行缩进是 4 空格（跟同条目其他字段一致）")
    check("  - name: alpha\n    url: https://example/alpha\n    enabled: false\n" in got,
          "alpha 的 enabled: false 原样保留（没被解析再序列化搞成别的写法）")
    gamma_block = got.split("- name: gamma")[1] if "- name: gamma" in got else ""
    check("enabled" not in gamma_block,
          "excluded: 里的 gamma 没有被塞进 enabled")
    check(got.split("excluded:")[1] == mini.split("excluded:")[1],
          "excluded: 段逐字节未变（连注释一起）")
    check(comments(got) == n0, "注释行数不变", "%d -> %d" % (n0, comments(got)))
    check(yaml.safe_load(got)["excluded"][0]["reason"] == "空文件",
          "解析后 excluded 内容仍然正确")
    print()

    shutil.rmtree(TMPDIR, ignore_errors=True)
    print("=" * 66)
    if FAILS:
        print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
        return 1
    print("结果：全部通过（注释零丢失 / 只改目标行 / 幂等 / 三道守卫都还在）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
