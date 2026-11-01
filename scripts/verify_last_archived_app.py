from pathlib import Path
import json,tarfile,hashlib,shutil,time,subprocess
root=Path(__file__).resolve().parents[1];w=root/'local-data/nas-archive'
p=json.loads((w/'plan.json').read_text());rows=json.loads((w/'app-final-journal.json').read_text());row=next(r for r in rows if r['state']!='complete');stage=Path(row['local_stage'])
i=next(i for i in p['items'] if i['source']==row['source']);rel=str(Path(i['destination']).relative_to(Path(p['nas'])/'历史版本').with_suffix(''));prefix='历史App/'+rel
archive=Path(p['nas'])/'历史版本/历史App补充-20261031.tar.gz'
expected=json.loads((w/'remaining-app-15.manifest.json').read_text());actual={};seen={}
print('Reading verified NAS archive for '+prefix,flush=True)
with tarfile.open(archive,mode='r|gz') as t:
 for e in t:
  name=e.name.removeprefix('./').rstrip('/')
  if e.isdir():v=dict(kind='directory')
  elif e.issym():v=dict(kind='symlink',target=e.linkname)
  elif e.islnk():v=seen[e.linkname.removeprefix('./')]
  elif e.isfile():
   h=hashlib.sha256();f=t.extractfile(e)
   for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
   v=dict(kind='file',bytes=e.size,sha256=h.hexdigest())
  else:continue
  seen[name]=v
  if name==prefix:actual['.']=v
  elif name.startswith(prefix+'/'):
   key=name[len(prefix)+1:]
   if key in expected or not any(x.startswith('._') for x in Path(key).parts):actual[key]=v
assert actual==expected, 'NAS version differs; local staged app retained'
fresh=json.loads(subprocess.check_output(['python3',str(root/'scripts/archive_old_versions.py'),'--hash',str(stage)],text=True))
assert fresh==expected,'Local version changed; retained'
(w/'standard-nas-verified-manifest.json').write_text(json.dumps(actual,ensure_ascii=False))
shutil.rmtree(stage);row['state']='complete';(w/'app-final-journal.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
e=dict(time=time.strftime('%Y-%m-%d %H:%M:%S'),event='moved',source=row['source'],destination=str(archive),restore_path=rel,free_bytes=shutil.disk_usage(root).free)
with (w/'events.jsonl').open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
stage.parent.rmdir();stage.parent.parent.rmdir();print(json.dumps(e,ensure_ascii=False),flush=True)
