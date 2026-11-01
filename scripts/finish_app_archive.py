#!/usr/bin/env python3
"""Revalidate remaining cloud-managed originals using durable local staging."""
from pathlib import Path
import json,os,time,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]; w=ROOT/'local-data/nas-archive'
while not (w/'collection-supplement-summary.json').exists():time.sleep(2)
p=json.loads((w/'plan.json').read_text()); cache=json.loads((w/'source-manifests.json').read_text())
report=json.loads((w/'collection-supplement-summary.json').read_text()); dst=report['archive']
verified=[json.loads(s) for s in (w/'events.jsonl').read_text().splitlines()]
assert any(e['event']=='collection_verified' and e['destination']==dst for e in verified)
journal=w/'app-final-journal.json';rows=json.loads(journal.read_text()) if journal.exists() else []
for i,item in enumerate(p['items']):
 src=Path(item['source'])
 row=next((r for r in rows if r['source']==str(src)),None)
 if item['kind']!='directory' or (not src.exists() and row is None) or (row and row['state']=='complete'):continue
 assert str(src)!=p['latest_app']
 stage=Path.home()/'Applications/.tgaa-app-nas-staging'/str(i)/src.name
 stage.parent.mkdir(parents=True,exist_ok=True)
 if row is None:
  row=dict(source=str(src),local_stage=str(stage),state='prepared');rows.append(row);journal.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 if src.exists():
  assert not stage.exists();os.rename(src,stage)
 row['state']='staged';journal.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 actual=json.loads(subprocess.check_output(['python3',str(ROOT/'scripts/archive_old_versions.py'),'--hash',str(stage)],text=True))
 match=next((e for e in verified if e['event']=='moved' and cache.get(e['source'])==actual),None)
 if match is None:
  (w/('remaining-app-'+str(i)+'.manifest.json')).write_text(json.dumps(actual,ensure_ascii=False))
  raise RuntimeError('No previously verified identical manifest; staged original retained')
 shutil.rmtree(stage);row['state']='complete';journal.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 e=dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event='moved',source=str(src),destination=match['destination'],restore_path=match.get('restore_path'),also_archived_in=dst,free_bytes=shutil.disk_usage(ROOT).free)
 with (w/'events.jsonl').open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 print(json.dumps(e,ensure_ascii=False),flush=True)
 stage.parent.rmdir()
base=Path.home()/'Applications/.tgaa-app-nas-staging'
if base.exists():base.rmdir()
print('App originals complete',flush=True)
