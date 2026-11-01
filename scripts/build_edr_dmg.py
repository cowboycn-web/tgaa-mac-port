#!/usr/bin/env python3
"""Package the installed combined-display trial and verify the mounted image."""
import argparse,hashlib,json,plistlib,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--app',type=Path,default=Path.home()/'Applications/大逆转裁判 1&2 SDR-EDR体验版.app')
p.add_argument('--output',type=Path,default=ROOT/'release/大逆转裁判 1&2 4K60-EDR体验版.dmg')
a=p.parse_args();a.app=a.app.resolve();a.output=a.output.resolve()
if a.output.exists():raise SystemExit('Output exists; refusing to replace it')
def run(args,**kw):return subprocess.run([str(x) for x in args],check=True,**kw)
def verify_app(app):
 run(['codesign','--verify','--deep','--strict',app])
 info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
 if info.get('CFBundleIdentifier')!='org.nxnative.tgaa.japan.cn13.edrtrial':raise ValueError('Unexpected bundle')
 rules={s['env']:s for s in info['DMSettings']}
 for key,val in [('DM_TGAA_RESOLUTION','2160'),('DM_TGAA_FPS','60'),('DM_TGAA_DISPLAY','edr')]:
  if val not in rules[key]['values']:raise ValueError('Combined display option missing')
 return info
verify_app(a.app)
a.output.parent.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='tgaa-dmg-',dir='/private/tmp') as tmp:
 tmp=Path(tmp);stage=tmp/'content';stage.mkdir();mount=tmp/'mounted';mount.mkdir()
 run(['/bin/cp','-cR',a.app,stage/a.app.name])
 (stage/'Applications').symlink_to('/Applications',target_is_directory=True)
 notes=(ROOT/'release/SDR-EDR体验版说明.txt').read_text()
 intro='安装方法\n\n将应用拖入 Applications（应用程序）。如果同名版本位于个人 Applications 目录，请退出游戏后替换原位置，避免保留两个同名副本。原有其他版本可继续保留。\n\n此镜像只包含应用和说明，不包含个人存档、用户设置或 Switch 密钥。使用相同账户、相同应用标识时沿用原有独立存档；另一台 Mac 上从新存档开始。\n\n'
 (stage/'安装与使用说明.txt').write_text(intro+notes)
 verify_app(stage/a.app.name)
 image=tmp/a.output.name
 run(['hdiutil','create','-srcfolder',stage,'-volname','大逆转裁判 SDR-EDR体验版','-fs','HFS+','-format','UDZO','-imagekey','zlib-level=6',image])
 run(['hdiutil','verify',image])
 mounted=False
 try:
  run(['hdiutil','attach','-readonly','-nobrowse','-mountpoint',mount,image]);mounted=True
  verify_app(mount/a.app.name)
  for rel in ['Contents/Info.plist','Contents/Resources/dm/launcher.json','Contents/MacOS/dmhost','Contents/MacOS/nxnative','Contents/Resources/hdr/720e88a17ae787f6_b.metal']:
   if (a.app/rel).read_bytes()!=(mount/a.app.name/rel).read_bytes():raise ValueError('Mounted content mismatch: '+rel)
  if not (mount/'Applications').is_symlink():raise ValueError('Install shortcut missing')
 finally:
  if mounted:run(['hdiutil','detach',mount])
 shutil.move(str(image),a.output)
h=hashlib.sha256()
with a.output.open('rb') as f:
 for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
a.output.with_suffix('.dmg.sha256').write_text(f'{h.hexdigest()}  {a.output.name}\n')
print(json.dumps(dict(file=str(a.output),bytes=a.output.stat().st_size,sha256=h.hexdigest(),disk_image_verified=True,mounted_app_signature_verified=True),ensure_ascii=False,indent=2))
