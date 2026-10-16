# -*- coding: utf-8 -*-
"""验证云效回传的「留痕」：回传的成败必须在 Codeup 仓里看得见。

## 为什么需要它

`tools/ci_push_main.py` 刻意「永不失败」（连异常都吞、不改流水线状态），
因为云效的日志面板实测渲染不全，把流水线染红只会掩盖真失败。
代价是：**回传到底通没通，在云效那边没有任何信号**。
实测后果：这条管道从部署到被发现「一次都没真跑过」，隔了一天没人看出来。

所以它现在往仓库里落一个 `results/push_main_last.json`。
这个测试保证：留痕一定会落、字段够用、且**本机开发时不往主仓塞文件**。

## 四条用例

  A 没有 probe_cnci.json   -> status=no-probe，且 exit 0（不许失败）
  B 有数据但没 GH_PAT      -> status=no-pat（这是最可能的真实故障）
  C 留痕是合法 JSON 且字段齐全（ok/status/channel/detail/probe_cnci_at）
  D 脚本在 tools/ 下（= 本机开发）-> 不留痕，别的仓库文件一字不动
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ci_push_main as C                    # noqa: E402

WORK = os.path.join(ROOT, ".tools", "_pushstatus_test")
FAILS = []


def check(ok, label, detail=""):
    print("  %s %s%s" % ("✓" if ok else "✗", label,
                        ("  —— %s" % detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def setup(with_probe):
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(os.path.join(WORK, "results"))
    if with_probe:
        with io.open(os.path.join(WORK, "probe_cnci.json"), "w",
                     encoding="utf-8") as f:
            json.dump({"scope": "cnci", "probed_at": "2026-10-17T04:24:00Z",
                       "sources": {}}, f)
    C.HERE = WORK                              # 假装自己是云效上的仓库根
    os.environ.pop("GH_PAT", None)


def status_file():
    return os.path.join(WORK, "results", "push_main_last.json")


def read_status():
    with io.open(status_file(), encoding="utf-8") as f:
        return json.load(f)


def main():
    real_here = C.HERE

    # ---------- A 没有探针结果 ----------
    print("A 没有 probe_cnci.json")
    setup(with_probe=False)
    st = {}
    rc = C.main(st)
    check(rc == 0, "退出码 0（这条链路的铁律是永不失败）", "rc=%d" % rc)
    check(st.get("status") == "no-probe", "status=no-probe", str(st))
    C.record_status(st)
    check(os.path.exists(status_file()), "仍然留痕了（没跑成功也是信息）")
    check(read_status()["ok"] is False, "ok=false")
    print()

    # ---------- B 没有 GH_PAT ----------
    print("B 有探针结果但没有 GH_PAT")
    setup(with_probe=True)
    st = {}
    rc = C.main(st)
    check(rc == 0, "退出码 0")
    check(st.get("status") == "no-pat", "status=no-pat", str(st))
    check("GH_PAT" in (st.get("detail") or ""), "detail 里点名了 GH_PAT",
          st.get("detail", ""))
    print()

    # ---------- C 字段齐全 ----------
    print("C 留痕内容")
    C.record_status(st)
    doc = read_status()
    need = ["at", "probe_cnci_at", "ok", "status", "channel", "detail", "py"]
    miss = [k for k in need if k not in doc]
    check(not miss, "必备字段都在", "缺 %s" % miss)
    check(doc["probe_cnci_at"] == "2026-10-17T04:24:00Z",
          "记录了这轮探针的数据时刻（能判断是不是陈旧数据）",
          doc.get("probe_cnci_at"))
    check(doc["status"] == "no-pat", "status 与运行时一致")
    check(isinstance(doc["ok"], bool), "ok 是布尔（方便一眼看）")
    print()

    # ---------- D 本机不留痕 ----------
    print("D 脚本在 tools/ 下（本机开发）不留痕")
    C.HERE = os.path.join(ROOT, "tools")
    check(C.status_dir() is None, "status_dir() 返回 None（明确不留痕）")
    st2 = {"status": "no-probe", "ok": False}
    C.record_status(st2)
    C.commit_status()
    check(not os.path.exists(os.path.join(ROOT, "tools", "results")),
          "没有在 main 仓里造出 tools/results/")
    check(not os.path.exists(os.path.join(ROOT, "results", "push_main_last.json")),
          "也没有在 main 仓的 results/ 里塞文件")
    print()

    C.HERE = real_here
    shutil.rmtree(WORK, ignore_errors=True)
    print("=" * 66)
    if FAILS:
        print("结果：失败 %d 项 —— %s" % (len(FAILS), "；".join(FAILS)))
        return 1
    print("结果：全部通过（留痕必落 / 字段够用 / 本机不往主仓塞文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
