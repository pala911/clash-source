# -*- coding: utf-8 -*-
"""用真 mihomo 内核校验 build 生成的 profile 配置。

为什么非它不可：断言只能验证「我以为的结构对不对」，
而 mihomo -t 验证的是「内核真的吃不吃得下」。
组结构写错、引用了不存在的成员、类型与字段不匹配 —— 这些只有内核知道。

用法：verge-mihomo.exe -t -f <profile>
"""
import os
import shutil
import subprocess
import tempfile
import sys
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIHOMO = os.environ.get("MIHOMO_BIN", r"C:\Program Files\Clash Verge\verge-mihomo.exe")
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

import yaml                      # noqa: E402
import build                     # noqa: E402

NAMES = ["anaer", "autojiedian", "automerge", "ermaozi", "nomorewalls",
         "passcro", "ruk1ng001", "shaoyouvip", "snakem982", "ssrsub",
         "yypool", "zhuhaiuk"]

enabled = [{"name": n, "url": "https://example/%s" % n} for n in NAMES]
profile, base, ranking = build.build_profile(enabled, {}, "pala911", "clash-source")

out = os.path.join(tempfile.gettempdir(), "profile_build_test.yaml")
with open(out, "w", encoding="utf-8") as f:
    yaml.safe_dump(profile, f, allow_unicode=True, sort_keys=False, width=4096)
print("  生成 %s（%d 字节）" % (out, os.path.getsize(out)))

# ⚠ 内核校验时 GEOIP/GEOSITE 规则会去 download MMDB，而本机连不上 GitHub
#   （dial tcp 20.205.243.166:443 超时），会报「can't initial GeoIP」——
#   那是**网络问题，不是配置问题**，但 exit code 同样是 1，会把真失败掩盖掉。
#   所以先把 Clash Verge 自带的 geodata 拷到配置旁边，喂给它。
VFDATA = r"C:\Program Files\Clash Verge\resources"
copied = []
for fn, newname in (("Country.mmdb", "geoip.metadb"), ("geoip.dat", None),
                    ("geosite.dat", None)):
    src = os.path.join(VFDATA, fn)
    if os.path.exists(src):
        dst = os.path.join(tempfile.gettempdir(), newname or fn)
        shutil.copy2(src, dst)
        copied.append(newname or fn)
print("  已备好 geodata: %s" % "、".join(copied))

print("")
print("  AUTO   = %s" % "、".join(ranking["auto"]))
print("  备用   = %s" % "、".join(ranking["备用"]))
print("  观察   = %s" % "、".join(ranking["观察"]))
print("")
print("  分桶依据：")
for n in NAMES:
    d = ranking["detail"][n]
    print("    %-14s 均值 %5.1f%%  %s" % (n, d["rate"] or 0, d["why"]))

print("")
print("  === mihomo -t 真校验 ===")
p = subprocess.run([MIHOMO, "-t", "-f", out], cwd=ROOT,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
out_s = (p.stdout or b"").decode("utf-8", "replace").strip()
for ln in out_s.splitlines()[-15:]:
    print("    " + ln)
print("    exit=%d %s" % (p.returncode, "✓ 内核接受这个配置" if p.returncode == 0
                         else "✗ 内核拒绝"))
os.remove(out)
sys.exit(p.returncode)