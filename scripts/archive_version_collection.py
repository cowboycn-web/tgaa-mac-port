#!/usr/bin/env python3
"""Archive remaining app versions with verified hardlink deduplication."""
from pathlib import Path
import json,subprocess,tempfile,hashlib,shutil,os,time,stat,sys
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'local-data/nas-archive'
plan=json.loads((WORK/'plan.json').read_text());nas=Path(plan['nas']);events=WORK/'events.jsonl'
cache_path=WORK/'source-manifests.json';cache=json.loads(cache_path.read_text())
def emit(event,**kw):
 r=dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**kw)
 with events.open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 print(json.dumps(r,ensure_ascii=False),flush=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def tree(p,timeout=120):
 return json.loads(subprocess.check_output(['python3',str(ROOT/'scripts/archive_old_versions.py'),'--hash',str(p)],text=True,timeout=timeout))
def attrs(p):
 # Large data files are linked only when their extended attributes also match.
 return subprocess.check_output(['xattr','-lx',str(p)])
items=[];pending=[];protected={plan['latest_app'],plan['latest_dmg']}
start=shutil.disk_usage(ROOT).free
with tempfile.TemporaryDirectory(prefix='tgaa-version-collection-',dir='/private/tmp') as tmp:
 tmp=Path(tmp);stage=tmp/'历史App';stage.mkdir();seen={};shared=0
 for item in plan['items']:
  src=Path(item['source'])
  if item['kind']!='directory' or not src.exists():continue
  assert str(src) not in protected
  emit('collection_hash',source=str(src))
  dst=None
  try:
   m=cache.get(str(src)) or tree(src,90)
   cache[str(src)]=m;cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2))
   rel=Path(item['destination']).relative_to(nas/'历史版本').with_suffix('');dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True)
   subprocess.run(['/bin/cp','-cR',str(src),str(dst)],check=True,timeout=90)
   # Verify the APFS snapshot before deduplicating or archiving it.
   if tree(dst,90)!=m:raise RuntimeError('Snapshot does not match source')
   for name,v in m.items():
    if v['kind']!='file' or v['bytes']<1024*1024:continue
    p=dst/name;s=p.stat();key=(v['sha256'],v['bytes'],stat.S_IMODE(s.st_mode),s.st_mtime_ns,hashlib.sha256(attrs(p)).hexdigest())
    if key in seen:
     p.unlink();os.link(seen[key],p);shared+=v['bytes']
    else:seen[key]=p
   items.append(dict(source=str(src),restore_path=str(rel),manifest=m))
   emit('collection_staged',source=str(src),shared_bytes=shared)
  except (subprocess.TimeoutExpired,subprocess.CalledProcessError,RuntimeError,OSError) as e:
   pending.append(dict(source=str(src),error=str(e)));emit('deferred',source=str(src),error=str(e))
   if dst is not None and dst.exists():shutil.rmtree(dst)
 if items:
  (stage/'版本目录.json').write_text(json.dumps([{k:v for k,v in i.items() if k!='manifest'} for i in items],ensure_ascii=False,indent=2))
  archive=tmp/('历史App补充-20261031.tar.gz' if '--supplement' in sys.argv else '历史App合集-20261031.tar.gz');emit('collection_pack',versions=len(items),shared_bytes=shared)
  with archive.open('wb') as out:
   tar=subprocess.Popen(['tar','-cf','-','-C',str(tmp),'历史App'],stdout=subprocess.PIPE)
   gzip=subprocess.Popen(['gzip','-1'],stdin=tar.stdout,stdout=out);tar.stdout.close()
   if gzip.wait()!=0 or tar.wait()!=0:raise RuntimeError('Archive creation failed')
  restored=tmp/'restore';restored.mkdir()
  subprocess.run(['tar','-xf',str(archive),'-C',str(restored)],check=True)
  for i in items:
   if tree(restored/'历史App'/i['restore_path'],90)!=i['manifest']:raise RuntimeError('Restored version differs: '+i['source'])
  emit('collection_restore_verified',versions=len(items))
  sha=digest(archive);dst=nas/'历史版本'/archive.name;partial=dst.with_suffix('.gz.partial')
  assert not dst.exists(),'Collection already exists; inspect before replacing'
  emit('collection_copy',bytes=archive.stat().st_size);shutil.copyfile(archive,partial)
  if digest(partial)!=sha:raise RuntimeError('NAS archive checksum mismatch')
  partial.rename(dst);dst.with_suffix('.gz.sha256').write_text(sha+'  '+dst.name+'\n')
  emit('collection_verified',destination=str(dst),sha256=sha)
  for i in items:
   src=Path(i['source'])
   try:
    if tree(src,90)!=i['manifest']:raise RuntimeError('Source changed; keeping local copy')
    shutil.rmtree(src);emit('moved',source=str(src),destination=str(dst),restore_path=i['restore_path'],free_bytes=shutil.disk_usage(ROOT).free)
    # Remove only this run's interrupted per-version ZIP, now fully archived above.
    entry=next(x for x in plan['items'] if x['source']==i['source']);old=Path(entry['destination']);part=old.with_name(old.name+'.partial')
    if part.exists():part.unlink()
   except (subprocess.TimeoutExpired,subprocess.CalledProcessError,RuntimeError,OSError) as e:pending.append(dict(source=str(src),error=str(e)));emit('deferred',source=str(src),error=str(e))
 report=dict(archive=str(dst) if items else None,versions=len(items),pending=pending,free_before=start,free_after=shutil.disk_usage(ROOT).free)
 (WORK/('collection-supplement-summary.json' if '--supplement' in sys.argv else 'collection-summary.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 shutil.copyfile(WORK/('collection-supplement-summary.json' if '--supplement' in sys.argv else 'collection-summary.json'),nas/'历史版本'/('补充校验记录.json' if '--supplement' in sys.argv else '合集校验记录.json'))
 emit('collection_finished',**report)
