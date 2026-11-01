#!/usr/bin/env python3
"""Rebuild the current trial DMG using the original Finder installation layout."""
import hashlib,plistlib,shutil,subprocess,tempfile,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=Path.home()/'Applications/大逆转裁判 1&2 SDR-EDR体验版.app'
reference=ROOT/'scripts/assets/dmg'
output=ROOT/'release/大逆转裁判 1&2 4K60-EDR体验版.dmg'
def run(args,**kw):return subprocess.run([str(x) for x in args],check=True,**kw)
def apple(text):return run(['osascript','-e',text])
run(['codesign','--verify','--deep','--strict',app])
with tempfile.TemporaryDirectory(prefix='tgaa-styled-',dir='/private/tmp') as tmp:
 tmp=Path(tmp);stage=tmp/'content';stage.mkdir();mount=tmp/'mounted';mount.mkdir()
 run(['/bin/cp','-cR',app,stage/app.name])
 (stage/'应用程序').symlink_to('/Applications',target_is_directory=True)
 shutil.copytree(reference/'.background',stage/'.background')
 shutil.copyfile(reference/'.DS_Store',stage/'.DS_Store')
 notes=(ROOT/'release/SDR-EDR体验版说明.txt').read_text()
 (stage/'安装说明.txt').write_text('将左侧游戏拖到右侧“应用程序”文件夹安装。若已有同名版本，请退出游戏后替换原位置；本镜像不包含个人存档或用户设置。\n\n'+notes)
 rw=tmp/'layout.dmg';final=tmp/'styled.dmg'
 run(['hdiutil','create','-srcfolder',stage,'-volname','大逆转裁判 1&2 EDR体验版','-fs','HFS+','-format','UDRW',rw])
 attached=False
 try:
  run(['hdiutil','attach','-readwrite','-nobrowse','-mountpoint',mount,rw]);attached=True
  # Finder writes background bookmark/alias for this volume, not the old volume.
  script='''tell application "Finder"
set diskFolder to POSIX file "%s" as alias
open diskFolder
delay 1
set w to container window of diskFolder
set current view of w to icon view
set toolbar visible of w to false
set statusbar visible of w to false
set pathbar visible of w to false
set bounds of w to {100, 162, 1060, 882}
set opts to icon view options of w
set arrangement of opts to not arranged
set icon size of opts to 128
set text size of opts to 14
set label position of opts to bottom
set shows item info of opts to false
set shows icon preview of opts to true
set background picture of opts to POSIX file "%s/.background/background.png"
set position of item "%s" of diskFolder to {190, 290}
set position of item "应用程序" of diskFolder to {760, 290}
set position of item "安装说明.txt" of diskFolder to {760, 555}
update diskFolder without registering applications
delay 3
try
close container window of diskFolder
end try
end tell''' % (mount,mount,app.name)
  apple(script)
  run(['sync'])
 finally:
  if attached:run(['hdiutil','detach',mount])
 run(['hdiutil','convert',rw,'-format','UDZO','-imagekey','zlib-level=6','-o',final])
 run(['hdiutil','verify',final])
 attached=False
 try:
  run(['hdiutil','attach','-readonly','-nobrowse','-mountpoint',mount,final]);attached=True
  run(['codesign','--verify','--deep','--strict',mount/app.name])
  for rel in ['Contents/Info.plist','Contents/Resources/dm/launcher.json','Contents/MacOS/dmhost','Contents/MacOS/nxnative']:
   if (app/rel).read_bytes()!=(mount/app.name/rel).read_bytes():raise ValueError('App differs from source')
  if (mount/'.background/background.png').read_bytes()!=(reference/'.background/background.png').read_bytes():raise ValueError('Background mismatch')
  # Save Finder's live layout for the mounted final artifact and expose it for visual QA.
  qa_script='''tell application "Finder"
set diskFolder to POSIX file "%s" as alias
open diskFolder
delay 1
activate
set w to container window of diskFolder
return {id of w, bounds of w, icon size of icon view options of w, position of item "%s" of diskFolder, position of item "应用程序" of diskFolder, position of item "安装说明.txt" of diskFolder}
end tell''' % (mount,mount,app.name)
  layout=run(['osascript','-e',qa_script],capture_output=True,text=True).stdout.strip();print('Final Finder layout:',layout,flush=True)
  window_id=int(layout.split(',')[0].strip())
  time.sleep(2)
  run(['screencapture','-x','-l',str(window_id),tmp/'screen.png'])
  shutil.copyfile(tmp/'screen.png',ROOT/'local-data/edr-package/dmg-layout-screen.png')
  apple('tell application "Finder" to close container window of (POSIX file "%s" as alias)' % mount)
 finally:
  if attached:run(['hdiutil','detach',mount])
 backup=ROOT/'local-data/edr-package/dmg-backups'/str(time.time_ns());backup.mkdir(parents=True)
 if output.exists():shutil.move(str(output),backup/output.name)
 checksum=output.with_suffix('.dmg.sha256')
 if checksum.exists():shutil.move(str(checksum),backup/checksum.name)
 shutil.move(str(final),output)
h=hashlib.sha256()
with output.open('rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
checksum.write_text(f'{h.hexdigest()}  {output.name}\n')
print(json.dumps(dict(file=str(output),bytes=output.stat().st_size,sha256=h.hexdigest(),backup=str(backup)),ensure_ascii=False,indent=2))
