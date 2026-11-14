# -*- coding: utf-8 -*-
"""实测：mihomo 到底拒绝哪些字段类型。

不能靠猜。已知 `sni: False` 让整源（892 节点）加载失败，
但 `password: null` 所在的 3 个源实测加载正常。
所以要逐类型试，不是一刀切丢弃。
"""
import os
import subprocess
import sys
import tempfile

MIHOMO = os.environ.get("MIHOMO_BIN", r"C:\Program Files\Clash Verge\verge-mihomo.exe")

CASES = [
    # (说明, 额外字段行, 要从基础节点里**替换掉**的字段)
    ("sni: false",          "    sni: false",   ()),
    ("sni: null",           "    sni: ~",       ()),
    ("sni: 123",            "    sni: 123",     ()),
    ("password: null",      "",                ("password",)),
    ("skip-cert-verify: str", '    skip-cert-verify: "yes"', ()),
    ("udp: 1",              "    udp: 1",       ()),
    ("alpn: str",           '    alpn: "h2"',   ()),
    ("无异常字段（基线）",    "",                ()),
]

BASE_HEAD = """mixed-port: 17890
mode: rule
log-level: silent
proxies:
  - name: t
    type: hysteria2
    server: example.invalid
    port: 443
"""

BASE_TAIL = """proxy-groups:
  - name: G
    type: select
    proxies:
      - t
rules:
  - MATCH,G
"""

vfd = r"C:\Program Files\Clash Verge\resources"
for fn, newname in (("Country.mmdb", "geoip.metadb"), ("geoip.dat", None),
                    ("geosite.dat", None)):
    src = os.path.join(vfd, fn)
    if os.path.exists(src):
        import shutil
        shutil.copy2(src, os.path.join(tempfile.gettempdir(), newname or fn))

print("%-24s %-8s %s" % ("字段", "结果", "内核原话"))
print("-" * 74)
for label, line, replace in CASES:
    p = os.path.join(tempfile.gettempdir(), "fieldtype.yaml")
    body = "    password: pw\n" if "password" not in replace else ""
    with open(p, "w", encoding="utf-8") as f:
        f.write(BASE_HEAD + body + (line + "\n" if line else "") + BASE_TAIL)
    r = subprocess.run([MIHOMO, "-t", "-f", p], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    out = (r.stdout or b"").decode("utf-8", "replace")
    if r.returncode == 0:
        verdict, msg = "接受", ""
    else:
        verdict = "拒绝"
        for ln in out.splitlines():
            if "level=error" in ln:
                msg = ln.split("msg=", 1)[-1][:44]
                break
    print("%-24s %-8s %s" % (label, verdict, msg))
    os.remove(p)