#!/usr/bin/env python3
"""Record the verified archive inventory after all historical items are moved."""
from pathlib import Path
import json,shutil,time,hashlib
root=Path(__file__).resolve().parents[1]; w=root/'local-data/nas-archive'
p=json.loads((w/'plan.json').read_text()); nas=Path(p['nas'])
events=[json.loads(s) for s in (w/'events.jsonl').read_text().splitlines()]
moved={e['source']:e for e in events if e['event']=='moved'}
assert all(i['source'] in moved for i in p['items']), 'Historical transfers still pending'
assert all(not Path(i['source']).exists() for i in p['items']), 'Historical source remains'
for filename in ['app-final-journal.json','dmg-final-journal.json']:
 rows=json.loads((w/filename).read_text())
 assert all(r['state']=='complete' and not Path(r['local_stage']).exists() for r in rows)
assert (w/'latest-verified.json').exists()
assert Path(p['latest_app']).is_dir() and Path(p['latest_dmg']).is_file()
h=hashlib.sha256()
with Path(p['latest_dmg']).open('rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
expected=json.loads((w/(Path(p['latest_dmg']).name+'.manifest.json')).read_text())['.']['sha256']
assert h.hexdigest()==expected
start=next(e['free_bytes'] for e in events if e['event']=='start')
result=dict(completed_at=time.strftime('%Y-%m-%d %H:%M:%S'),archive=str(nas),latest=[dict(local=p[k],nas=str(nas/'最新版本'/Path(p[k]).name),retained_locally=True) for k in ['latest_app','latest_dmg']],history=[moved[i['source']] for i in p['items']],free_bytes=shutil.disk_usage(root).free,initial_free_bytes=start)
(w/'final-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
audit=nas/'校验记录';audit.mkdir(exist_ok=True)
for f in w.iterdir():
 if f.suffix in ['.json','.jsonl'] or f.name=='restore-check.txt':shutil.copyfile(f,audit/f.name)
text='''大逆转裁判 1&2 — 版本归档（2026-10-31）

最新版本：可直接复制到 Mac 的 App，以及对应 DMG；本机也保留这两份最新版。
历史版本：所有计划中的旧 App、构建副本和旧 DMG 已校验后迁移，本机旧副本已清理。

旧 App 保存在 Applications 内的 ZIP，以及“历史App合集-20261031.tar.gz”和“历史App补充-20261031.tar.gz”。在 Mac 解压后，按目录选择所需版本，并复制到“应用程序”后使用。合集对相同数据使用硬链接减少归档体积，请不要直接修改解压合集内的共享资源。
旧 DMG 保持原格式，在“历史版本/旧安装包”中按原目录区分。
最新版 App 不需要解压，位于“最新版本”。

每份归档均已核对 SHA-256；App 合集已解压并逐文件核对。旧 App 本地原件删除前也已再次核对。完整路径和校验记录见“校验记录/final-inventory.json”与 events.jsonl。早期过程报告可能列出曾经延后的项目，最终状态以 final-inventory.json 为准。
游戏源文件、源码、密钥与个人存档未迁移。
'''
(nas/'归档说明.txt').write_text(text)
r=root/'README.md';s=r.read_text();s=s.replace('本地旧版本正在迁往同目录的“历史版本”，只在副本校验成功后删除本地原件，进度记录见 `local-data/nas-archive/events.jsonl`。','本地旧版本已在校验后迁往同目录的“历史版本”，最终清单见 `local-data/nas-archive/final-inventory.json`。');r.write_text(s)
print(json.dumps(dict(history_count=len(result['history']),free_GiB=result['free_bytes']/2**30,increase_GiB=(result['free_bytes']-start)/2**30),ensure_ascii=False))
