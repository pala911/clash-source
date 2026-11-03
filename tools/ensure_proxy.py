# -*- coding: utf-8 -*-
"""推送前确保 Clash 代理可用（手动补推 / 运维脚本共用）。

2026-11-03 实踩：代理不可用时 local_probe 的 push 三连败，救援也因 fetch
失败告终，本机数据积压一天。现在 local_probe.push_to_github() 会自己调用
ensure_proxy()；这个 CLI 只是把同一逻辑暴露给手工操作，避免再靠人记。

用法：
    python tools/ensure_proxy.py            # 不通就拉起，最多等 90s
    python tools/ensure_proxy.py --wait 30  # 自定义等待
退出码：0=可用（或已拉起），1=仍不可用。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import local_probe  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="确保本机 Clash 代理（7897）可用")
    ap.add_argument("--wait", type=int, default=90, help="等待恢复的秒数")
    args = ap.parse_args()
    ok = local_probe.ensure_proxy(wait=args.wait)
    print("[ensure_proxy] %s" % ("可用" if ok else "仍不可用"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
