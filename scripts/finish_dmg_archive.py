#!/usr/bin/env python3
"""Move remaining old images through durable local staging outside iCloud."""
from pathlib import Path
import os,json,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[1];W=ROOT/'local-data/nas-archive';plan=json.loads((W/'plan.json').read_text());nas=Path(plan['nas'])
staging=Path.home()/'Applications/.tgaa-nas-staging';staging.mkdir(exist_ok=True)
journal=W/'dmg-final-journal.json';rows=json.loads(journal.read_text()) if journal.exists() else []
def save():journal.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
def emit(event,**kw):
 d=dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**kw)
 with (W/'events.jsonl').open('a') as f:f.write(json.dumps(d,ensure_ascii=False)+'\n')
 print(json.dumps(d,ensure_ascii=False),flush=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
for i,item in enumerate(plan['items']):
 src=Path(item['source'])
 if item['kind']!='file' or src.suffix!='.dmg' or not src.exists():continue
 assert str(src)!=plan['latest_dmg']
 stage=staging/str(i)/src.name;stage.parent.mkdir(exist_ok=True)
 row=next((r for r in rows if r['source']==str(src)),None)
 if row is None:row=dict(source=str(src),local_stage=str(stage),destination=item['destination'],state='prepared');rows.append(row);save()
 assert not stage.exists();os.rename(src,stage);row['state']='local_staged';save()
 row['sha256']=sha(stage);row['bytes']=stage.stat().st_size;row['state']='ready';save()
 emit('dmg_staged',source=str(src),local_stage=str(stage),sha256=row['sha256'])
# Avoid competing large SMB streams; the app supplement has priority.
deadline=time.monotonic()+1800
while not (W/'collection-supplement-summary.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('App transfer still active; staged images are retained')
 time.sleep(2)
for row in rows:
 if row['state']=='complete':continue
 src=Path(row['source']);stage=Path(row['local_stage']);dst=Path(row['destination']);dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():
  emit('verify_existing_dmg',destination=str(dst))
  if sha(dst)!=row['sha256']:raise RuntimeError('Existing NAS image differs; both local and NAS retained')
 else:
  partial=dst.with_name(dst.name+'.partial');emit('copy_dmg',source=str(src),bytes=row['bytes'])
  shutil.copyfile(stage,partial)
  with partial.open('rb') as f:os.fsync(f.fileno())
  emit('verify_dmg',source=str(src))
  if sha(partial)!=row['sha256']:raise RuntimeError('NAS image checksum mismatch; local staging retained')
  partial.rename(dst)
 if sha(stage)!=row['sha256']:raise RuntimeError('Local staged image changed; not deleting')
 stage.unlink();row['state']='complete';save();emit('moved',source=str(src),destination=str(dst),sha256=row['sha256'],free_bytes=shutil.disk_usage(ROOT).free)
 for parent in [stage.parent]:
  try:parent.rmdir()
  except OSError:pass
shutil.copyfile(journal,nas/'旧DMG校验记录.json')
try:staging.rmdir()
except OSError:pass
emit('all_old_dmgs_complete')
