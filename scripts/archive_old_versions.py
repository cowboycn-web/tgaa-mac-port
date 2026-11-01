#!/usr/bin/env python3
"""Verified NAS archive of an explicit local plan; never delete before verification."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'local-data/nas-archive'
plan=json.loads((WORK/'plan.json').read_text());nas=Path(plan['nas']);events=WORK/'events.jsonl'
latest={Path(plan['latest_app']),Path(plan['latest_dmg'])}
allowed=[ROOT,Path.home()/'Applications',Path('/private/tmp/tgaa-edr-combined'),Path('/private/tmp/tgaa-edr-release')]
def emit(event,**kw):
 record=dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event=event,**kw)
 with events.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
 print(json.dumps(record,ensure_ascii=False),flush=True)
def checksum(p):
 for attempt in range(3):
  before=p.stat();h=hashlib.sha256()
  with p.open('rb') as f:
   for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
  after=p.stat()
  if (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns):
   return dict(kind='file',bytes=after.st_size,sha256=h.hexdigest())
  time.sleep(0.2)
 raise RuntimeError(f'File keeps changing while hashing: {p}')

def tree(p):
 if p.is_symlink():return {'.':dict(kind='symlink',target=os.readlink(p))}
 if p.is_file():return {'.':checksum(p)}
 result={'.':dict(kind='directory')}
 for here,dirs,files in os.walk(p,followlinks=False):
  for name in dirs+files:
   f=Path(here)/name;rel=str(f.relative_to(p))
   if f.is_symlink():result[rel]=dict(kind='symlink',target=os.readlink(f))
   elif f.is_dir():result[rel]=dict(kind='directory')
   else:result[rel]=checksum(f)
 return result
def verify(expected,target):
 actual=tree(target)
 # SMB may create AppleDouble sidecars when preserving resource forks.
 actual={k:v for k,v in actual.items() if not any(part.startswith('._') for part in Path(k).parts) or k in expected}
 if expected!=actual:
  diff=[k for k in expected.keys()|actual.keys() if expected.get(k)!=actual.get(k)]
  raise RuntimeError(f'Archive verification failed for {target}: {diff[:8]}')
def free():return shutil.disk_usage(ROOT).free
import sys,zipfile
if len(sys.argv)>2 and sys.argv[1]=='--hash':
 source=Path(sys.argv[2])
 if source.is_relative_to(ROOT):
  # APFS cloning gives a stable data snapshot outside File Provider's read path.
  import tempfile
  with tempfile.TemporaryDirectory(prefix='tgaa-hash-snapshot-',dir='/private/tmp') as d:
   snapshot=Path(d)/'payload'
   subprocess.run(['/bin/cp','-cR',str(source),str(snapshot)],check=True)
   result=tree(snapshot)
 else:result=tree(source)
 print(json.dumps(result,ensure_ascii=False));sys.exit(0)
def remote_manifest(p,timeout=180):
 r=subprocess.run([sys.executable,__file__,'--hash',str(p)],capture_output=True,text=True,timeout=timeout,check=True)
 return json.loads(r.stdout)
def zip_manifest(p,basename):
 result={'.':dict(kind='directory')}
 with zipfile.ZipFile(p,metadata_encoding='utf-8') as z:
  for entry in z.infolist():
   name=entry.filename.rstrip('/')
   if name.startswith('__MACOSX/') or name=='__MACOSX':continue
   if name==basename:continue
   if not name.startswith(basename+'/'):raise RuntimeError('Unexpected ZIP root')
   key=name[len(basename)+1:]
   for parent in Path(key).parents:
    if str(parent)!='.':result.setdefault(str(parent),dict(kind='directory'))
   mode=entry.external_attr>>16
   if stat.S_ISLNK(mode):result[key]=dict(kind='symlink',target=z.read(entry).decode())
   elif entry.is_dir():result[key]=dict(kind='directory')
   else:
    h=hashlib.sha256()
    with z.open(entry) as f:
     for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    result[key]=dict(kind='file',bytes=entry.file_size,sha256=h.hexdigest())
 return result
if '--verify-latest' in sys.argv:
 for p in [Path(plan['latest_app']),Path(plan['latest_dmg']),Path(plan['latest_dmg']+'.sha256')]:
  emit('verify_latest',source=str(p));expected=remote_manifest(p);actual=remote_manifest(nas/'最新版本'/p.name,1800)
  actual={k:v for k,v in actual.items() if not any(c.startswith('._') for c in Path(k).parts) or k in expected}
  if expected!=actual:raise RuntimeError('Latest copy differs: '+str(p))
  (WORK/(p.name+'.manifest.json')).write_text(json.dumps(expected,ensure_ascii=False,indent=2))
 (WORK/'latest-verified.json').write_text(json.dumps(dict(time=time.time(),archive=str(nas))))
 emit('latest_verified');sys.exit(0)
start=free();emit('archive_start',free_bytes=start,items=len(plan['items']))
manifest_path=WORK/'source-manifests.json';manifests=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
pending=[];completed=[]
for item in plan['items']:
 src=Path(item['source']);dst=Path(item['destination'])
 if '--files-only' in sys.argv and item['kind']!='file':continue
 if src in latest or not any(src.is_relative_to(a) for a in allowed):raise RuntimeError(f'Unexpected source: {src}')
 if not src.exists():continue
 temp=None
 try:
  emit('hash_source',source=str(src))
  m=manifests.get(str(src)) or remote_manifest(src,90)
  manifests[str(src)]=m;manifest_path.write_text(json.dumps(manifests,ensure_ascii=False,indent=2))
  dst.parent.mkdir(parents=True,exist_ok=True)
  if src.is_dir():
   import tempfile
   temp=Path(tempfile.mkdtemp(prefix='tgaa-archive-',dir='/private/tmp'));payload=temp/(src.name+'.zip')
   emit('pack',source=str(src))
   subprocess.run(['ditto','-c','-k','--zlibCompressionLevel','1','--sequesterRsrc','--keepParent',str(src),str(payload)],check=True,timeout=300)
   if zip_manifest(payload,src.name)!=m:raise RuntimeError('ZIP differs from source manifest')
  else:
   import tempfile
   temp=Path(tempfile.mkdtemp(prefix='tgaa-archive-',dir='/private/tmp'));payload=temp/src.name
   subprocess.run(['/bin/cp','-c',str(src),str(payload)],check=True,timeout=90)
  want=checksum(payload)
  if dst.exists():
   if checksum(dst)!=want:raise RuntimeError('Existing destination differs; refusing overwrite')
  else:
   partial=dst.with_name(dst.name+'.partial');emit('copy',source=str(src),destination=str(dst),bytes=want['bytes'])
   shutil.copyfile(payload,partial)
   emit('verify_copy',source=str(src))
   if checksum(partial)!=want:raise RuntimeError('NAS checksum differs')
   partial.rename(dst)
  if remote_manifest(src,90)!=m:raise RuntimeError('Local source changed; retaining it')
  emit('verified',source=str(src),destination=str(dst),sha256=want['sha256'])
  if src.is_dir():shutil.rmtree(src)
  else:src.unlink()
  completed.append(item);emit('moved',source=str(src),free_bytes=free())
 except (subprocess.TimeoutExpired,subprocess.CalledProcessError,RuntimeError,OSError) as error:
  pending.append(dict(source=str(src),error=str(error)));emit('deferred',source=str(src),error=str(error))
 finally:
  if temp:shutil.rmtree(temp)
summary=dict(latest_retained=[str(p) for p in latest],archive=str(nas),free_before=start,free_after=free(),observed_free_increase=free()-start,completed=completed,pending=pending)
(WORK/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
for name in ['plan.json','source-manifests.json','events.jsonl','summary.json']:shutil.copyfile(WORK/name,nas/name)
emit('archive_pass_finished',moved=len(completed),pending=len(pending),free_bytes=free())
