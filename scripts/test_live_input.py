#!/usr/bin/env python3
"""Exercise immutable icon variants in a running game with isolated save data."""
from pathlib import Path
import os,shutil,subprocess,time,signal,json
root=Path(__file__).resolve().parents[1]
r=Path.home()/'Applications/大逆转裁判 1&2 SDR-EDR体验版.app/Contents/Resources'
out=root/'local-data/input-switch-test'/str(time.time_ns());out.mkdir()
shutil.copytree(root/'local-data/native4k-test/save',out/'save');(out/'temp').mkdir();ctl=out/'control.txt';ctl.touch()
env={k:v for k,v in os.environ.items() if not k.startswith('DM_')}
env.update(DM_WINDOW='1',DM_TGAA_RESOLUTION='1080',DM_TGAA_FPS='30',DM_OPMODE='0',DM_ROMFS=str(r/'romfs.img'),DM_SAVE=str(out/'save'),DM_TEMP=str(out/'temp'),DM_CTL=str(ctl),DM_MSL_DIR=str(r/'msl'),DM_NVN_SHMAP=str(r/'dm/shader_map.tsv'),DM_KEYS=','.join(f'f{f}:A' for f in [700,1100,1500,1700]),DM_CONTROLLER_STYLE='auto',DM_LIVE_ICONS=str(root/'local-data/input-switch-test/live'),DM_ROMFS_OVERLAY=str(root/'local-data/input-switch-test/overlay'),DM_TEST_ICON_STYLE='4',DM_TEST_KEEP_FOCUS='1',DM_EDR_READBACK=str(out/'present.raw'),DM_EDR_READBACK_FRAME='2400',DM_NVN_TEXINFO='512x512')
print(out,flush=True)
with (out/'run.log').open('w') as log:
 proc=subprocess.Popen([str(root/'upstream/nxnative/dm/host/dmhost'),str(r/'dm')],env=env,stdout=log,stderr=subprocess.STDOUT)
 try:
  deadline=time.monotonic()+200
  while proc.poll() is None and time.monotonic()<deadline:
   text=(out/'run.log').read_text(errors='replace')
   if 'EDR readback complete' in text:break
   time.sleep(1)
  else:raise RuntimeError('Game did not reach capture frame')
  if 'live input atlas matched' not in text:
   import re
   with ctl.open('a') as f:
    for ser,addr in re.findall(r'TEXINFO ser=(\d+).*?mem=(0x[0-9a-f]+)',text):f.write(f'memdump {addr} 262144 {out}/atlas-{ser}.bin\n')
   time.sleep(2)
   raise RuntimeError('Atlas did not match; captured candidate bytes')
  for style in [4,1,2,3,4,1]:
   with ctl.open('a') as f:f.write(f'env DM_TEST_ICON_STYLE={style}\n')
   time.sleep(1)
   with ctl.open('a') as f:f.write(f'shot {out}/style-{style}.png\n')
   time.sleep(2)
  text=(out/'run.log').read_text(errors='replace')
  assert all(f'live input atlas selected: {n}' in text for n in [1,2,3,4])
  assert all((out/f'style-{n}.png').exists() for n in [1,2,3,4])
  print('PASS: four runtime styles and return transitions; inspect captures',flush=True)
 finally:
  if proc.poll() is None:
   proc.send_signal(signal.SIGINT)
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
