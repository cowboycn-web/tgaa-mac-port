#!/usr/bin/env python3
"""Update a styled image through a shadow file, preserving its Finder metadata."""
import hashlib,subprocess,tempfile,time,shutil,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=Path.home()/'Applications/大逆转裁判 1&2 SDR-EDR体验版.app'
image=ROOT/'release/大逆转裁判 1&2 4K60-EDR体验版.dmg'
def run(args):subprocess.run([str(a) for a in args],check=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
run(['codesign','--verify','--deep','--strict',app])
with tempfile.TemporaryDirectory(prefix='tgaa-dmg-update-',dir='/private/tmp') as temp:
 temp=Path(temp);mount=temp/'volume';mount.mkdir();shadow=temp/'changes.shadow';final=temp/'updated.dmg'
 attached=False
 try:
  run(['hdiutil','attach','-nobrowse','-mountpoint',mount,'-shadow',shadow,image]);attached=True
  store=(mount/'.DS_Store').read_bytes();background=(mount/'.background/background.png').read_bytes()
  target=mount/app.name
  # Preserve the original signed resources; copy only files that actually differ.
  for p in app.rglob('*'):
   rel=p.relative_to(app);q=target/rel
   if p.is_symlink():
    if not q.is_symlink() or q.readlink()!=p.readlink():raise RuntimeError(f'Symlink differs: {rel}')
   elif p.is_file():
    if not q.is_file() or digest(p)!=digest(q):
     q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);shutil.copymode(p,q);print('Updated:',rel,flush=True)
  notes=(ROOT/'release/SDR-EDR体验版说明.txt').read_text()
  (mount/'安装说明.txt').write_text('将左侧游戏拖到右侧“应用程序”文件夹安装。若已有同名版本，请退出游戏后替换原位置；本镜像不包含个人存档或用户设置。\n\n'+notes)
  run(['codesign','--verify','--deep','--strict',target]);run(['sync'])
  assert store==(mount/'.DS_Store').read_bytes() and background==(mount/'.background/background.png').read_bytes()
 finally:
  if attached:run(['hdiutil','detach',mount])
 run(['hdiutil','convert',image,'-shadow',shadow,'-format','UDZO','-imagekey','zlib-level=6','-o',final])
 run(['hdiutil','verify',final]);attached=False
 try:
  run(['hdiutil','attach','-readonly','-nobrowse','-mountpoint',mount,final]);attached=True
  run(['codesign','--verify','--deep','--strict',mount/app.name])
  for rel in ['Contents/MacOS/dmhost','Contents/MacOS/nxnative']:
   assert digest(app/rel)==digest(mount/app.name/rel)
  assert store==(mount/'.DS_Store').read_bytes() and background==(mount/'.background/background.png').read_bytes()
 finally:
  if attached:run(['hdiutil','detach',mount])
 checksum=digest(final);backup=ROOT/'local-data/edr-package/dmg-backups'/str(time.time_ns());backup.mkdir(parents=True)
 image.rename(backup/image.name)
 side=image.with_suffix('.dmg.sha256')
 if side.exists():side.rename(backup/side.name)
 shutil.move(final,image);side.write_text(checksum+'  '+image.name+'\n')
 print(json.dumps(dict(path=str(image),bytes=image.stat().st_size,sha256=checksum,layout='original DS_Store and background verified identical'),ensure_ascii=False),flush=True)
