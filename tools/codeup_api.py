# -*- coding: utf-8 -*-
"""Codeup(云效) API 探路：列出组织 / 仓库。

⚠ 下面这组 host 是**错的**（2026-10-16 实测）：`devops.cn-shenzhen.aliyuncs.com`
  在阿里 DNS / 114 上都是 NXDOMAIN。云效只有两套接入点：

    中心版 : https://openapi-rdc.aliyuncs.com
             /oapi/v1/flow/organizations/{organizationId}/pipelines/...
    Region版: https://{实例访问域名}      <- 就是控制台那个 host
             /oapi/v1/flow/pipelines/...    <- **不带 organizationId**

  我们是 Region 版：host = myxk-cn-shenzhen.devops.aliyuncs.com。
  鉴权头一律 `x-yunxiao-token: pt-...`。

  判据（找接口时极好用，省一整轮瞎猜）：
    401 InvalidToken -> 路由存在、鉴权没过
    404 NotFound     -> 这条路由不存在
    200 + HTML       -> 被控制台 SPA 兜底了，不是接口

  已经跑通的调用见 tools/cnci_trigger.py（触发流水线）
  与 tools/cnci_status.py（读回传留痕）。
"""
import json
import os
import urllib.error
import urllib.request

TOKEN = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "codeup.token"), encoding="utf-8").read().strip()
HOSTS = ["https://devops.cn-shenzhen.aliyuncs.com",
         "https://devops.aliyuncs.com"]


def api(host, path, method="GET", body=None):
    req = urllib.request.Request(host + path, method=method,
                                 data=body,
                                 headers={"x-yunxiao-token": TOKEN,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
        return json.loads(raw) if raw else {}, r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8", "replace")), e.code
        except Exception:
            return {}, e.code
    except Exception as e:
        return {"_err": str(e)}, 0


def show(tag, d, code):
    print("  [%s] HTTP %s" % (tag, code))
    if isinstance(d, dict) and "_err" in d:
        print("      %s" % d["_err"][:120])
        return
    s = json.dumps(d, ensure_ascii=False)
    print("      %s" % (s[:600] + ("..." if len(s) > 600 else "")))


def main():
    host = None
    for h in HOSTS:
        d, code = api(h, "/oapi/v1/codeup/organizations")
        print("=== %s ===" % h)
        show("organizations", d, code)
        if code == 200:
            host = h
            break
    if not host:
        print("\n两个接入点都没通，令牌或地域可能不对。")
        return 1

    orgs = None
    d, _ = api(host, "/oapi/v1/codeup/organizations")
    orgs = d if isinstance(d, list) else (d.get("organizations") or d.get("result") or [])
    print("\n=== 组织 ===")
    for o in (orgs if isinstance(orgs, list) else []):
        print("  id=%s  name=%s  path=%s" %
              (o.get("id"), o.get("name"), o.get("path") or o.get("webUrl")))

    for o in (orgs if isinstance(orgs, list) else []):
        oid = o.get("id")
        d, code = api(host, "/oapi/v1/codeup/organizations/%s/repositories"
                      % oid)
        print("\n=== 组织 %s(%s) 的仓库 === HTTP %s" % (o.get("path"), oid, code))
        if isinstance(d, dict) and "_err" in d:
            print("      %s" % d["_err"][:150])
            continue
        reps = d if isinstance(d, list) else []
        for r in reps:
            print("  id=%-6s name=%-20s defaultBranch=%-8s http=%s"
                  % (r.get("id"), r.get("name"), r.get("defaultBranch"),
                     r.get("httpUrlToRepo")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())