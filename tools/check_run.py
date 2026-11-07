"""查 clash-source 最近一次 update-source 的分步状态与关键日志（带重试，代理不稳）。"""
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

TOK = open(r'D:\work\agent\codebuddy\clash-source\.aikey-token').read().strip()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler(
    {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}))
H = {'Authorization': 'Bearer ' + TOK, 'Accept': 'application/vnd.github+json'}


def get(path, raw=False, tries=6):
    last = None
    for i in range(tries):
        try:
            with OPENER.open(urllib.request.Request('https://api.github.com' + path,
                                                   headers=H), timeout=60) as r:
                return r.read() if raw else json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2 + 2 * i)
    print('API 失败 %s: %s' % (path, last))
    raise SystemExit(1)


runs = get('/repos/pala911/clash-source/actions/runs?per_page=8')['workflow_runs']
t = next((r for r in runs if r['name'].startswith('update')), None)
if not t:
    raise SystemExit('没找到 update-source 运行记录')
print('run %s  head=%s  %s/%s' % (t['id'], t['head_sha'][:7], t['status'], t['conclusion']))

MARK = {'success': 'OK ', 'skipped': '-- ', 'cancelled': '-- '}
for j in get('/repos/pala911/clash-source/actions/runs/%d/jobs' % t['id']).get('jobs', []):
    for s in j.get('steps', []):
        if s['status'] == 'pending':
            continue
        c = s.get('conclusion')
        m = MARK.get(c, '.. ' if s['status'] == 'in_progress' else 'XX ')
        print('  %s%-44s %s' % (m, s['name'][:44], c or s['status']))

if t['status'] != 'completed':
    raise SystemExit(0)

data = get('/repos/pala911/clash-source/actions/runs/%d/logs' % t['id'], raw=True)
z = zipfile.ZipFile(io.BytesIO(data))
txt = ''.join(z.read(n).decode('utf-8', 'replace') for n in z.namelist() if n.endswith('.txt'))
print('\n=== 关键日志（去重）===')
seen = set()
for ln in txt.splitlines():
    if not re.search(r'\[probe\]|\[health\]|AI 用量|后端 |完成：|::warning|::error', ln):
        continue
    ln = ln.split('Z ', 1)[-1].strip()
    if ln in seen:
        continue
    seen.add(ln)
    print('  ' + ln[:170])