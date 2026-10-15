# -*- coding: utf-8 -*-
"""云端探针仓库的**唯一**内容清单（Codeup 与 Gitee 共用）。

⚠ 为什么必须共用（2026-10-15 的教训）：
  云效那轮我犯过"门禁覆盖范围漏了 probe.py"这类错，根因就是**同一份清单
  在多处各自维护，改了一处忘了另一处**。两个远端仓库如果各写一份 FILES，
  迟早会漂移（推了 A 没推 B），而且漂移后极难发现 —— 因为两边都能正常跑，
  只是内容不一样。所以这里抽出唯一来源。

覆盖范围 = 会被推送到云端 CI 并在集群上执行的**每一个**文件：
  - tools/ci_*.py        能力判定 / 前置检查 / 探针执行器
  - src/probe.py         真探针主程序
  - src/health.py        健康档案
  - .tools/mihomo-linux-amd64.gz   预置内核（不现场下载 GitHub）
  - dist/nodes/*.yaml    已过滤的节点配置
  - .tools/yaml_vendor/yaml/*.py   vendor 的 PyYAML（不现场 pip）

改这个文件时，**必须同时跑** `python tools/check_ci_scripts.py`
（它按同样的范围做 Python 3.6 静态门禁）。
"""
import glob
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SCRIPTS = ["ci_check_paste.py", "ci_preflight.py", "ci_probe_run.py",
           "sync_and_probe.sh"]
SRC_MODULES = ["probe.py", "health.py"]


def _dest_name(name):
    """决定文件在云端仓库里的落地路径。

    ⚠ shell 脚本必须放 tools/，不能放根目录：
      sync_and_probe.sh 内部用 `dirname "$0"/..` 推算仓库根，
      放根目录就会指向仓库的上一级，逻辑全错。
      这个错的表现极难查 —— 流水线报
      `bash tools/sync_and_probe.sh: No such file or directory`，
      而文件明明就在仓库里（只是位置不对），看起来像"没推上去"。
    """
    return "tools/" + name if name.endswith(".sh") else name


def payload_items():
    """返回 [(相对路径, 绝对源路径, 说明)]，供各推送脚本使用。"""
    items = []
    for n in SCRIPTS:
        items.append((_dest_name(n), os.path.join(HERE, n), "脚本"))
    for n in SRC_MODULES:
        items.append((n, os.path.join(ROOT, "src", n), "主仓模块"))
    gz = os.path.join(ROOT, ".tools", "mihomo-linux-amd64.gz")
    if os.path.exists(gz):
        items.append(("mihomo-linux-amd64.gz", gz, "预置内核"))
    # ⚠ vendor 的 PyYAML 在 ROOT/.tools/ 下，不在 HERE/tools/ 下。
    #   这个路径我今天已经写错过一次（当时导致 3.6 门禁漏扫了 17 个文件），
    #   所以这里显式写全路径而不是用 HERE 拼。
    yv = os.path.join(ROOT, ".tools", "yaml_vendor", "yaml")
    for n in sorted(glob.glob(os.path.join(yv, "*.py"))):
        items.append(("yaml/" + os.path.basename(n), n, "vendor PyYAML"))
    return items


def node_files():
    """节点配置源文件列表（排除 all.yaml，它是合并产物）。"""
    return [f for f in sorted(glob.glob(os.path.join(ROOT, "dist", "nodes", "*.yaml")))
            if os.path.basename(f) != "all.yaml"]


def build(dest, readme=""):
    """把完整内容组装到 dest 目录。返回组装清单摘要（供打印）。"""
    os.makedirs(dest, exist_ok=True)
    log = []
    for rel, src, kind in payload_items():
        dst = os.path.join(dest, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            log.append((rel, kind, os.path.getsize(src)))
        else:
            log.append((rel, kind + "【缺失!】", 0))

    nd = os.path.join(dest, "nodes")
    os.makedirs(nd, exist_ok=True)
    nbytes = 0
    for f in node_files():
        shutil.copy2(f, os.path.join(nd, os.path.basename(f)))
        nbytes += os.path.getsize(f)
    log.append(("nodes/*.yaml", "节点配置", nbytes))

    if readme:
        with open(os.path.join(dest, "README.md"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(readme)
    return log