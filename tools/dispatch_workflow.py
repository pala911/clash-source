"""触发 clash-source 的 workflow_dispatch，带重试（本地代理 7897 偶发 SSL EOF）。"""
import json
import sys
import time
import urllib.error
import urllib.request

TOK = open(r'D:\work\agent\codebuddy\clash-source\.aikey-token').read().strip()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler(
    {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}))


def api(method, path, body=None, tries=4):
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            'https://api.github.com' + path, method=method, data=body,
            headers={'Authorization': 'Bearer ' + TOK,
                     'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28',
                     'Content-Type': 'application/json'})
        try:
            with OPENER.open(req, timeout=45) as r:
                raw = r.read()
            return (json.loads(raw) if raw else {}), r.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode('utf-8', 'replace')), e.code
        except Exception as e:          # URLError / SSLError / timeout
            last = e
            sys.stdout.write('  重试 %d/%d: %s\n' % (i + 1, tries, str(e)[:70]))
            time.sleep(2 + 2 * i)
    raise SystemExit('API 失败: %s' % last)


d, _ = api('GET', '/repos/pala911/clash-source/actions/workflows')
for w in d.get('workflows', []):
    print('workflow: %s (%s) state=%s' % (w['name'], w['path'], w['state']))
r, st = api('POST', '/repos/pala911/clash-source/actions/workflows/update.yml/dispatches',
            json.dumps({'ref': 'main'}).encode())
print('dispatch HTTP', st, r if st >= 300 else '(已排队)')