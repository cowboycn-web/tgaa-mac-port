#!/usr/bin/env python3
"""Bounded launcher acceptance using the isolated EDR trial namespace."""
import argparse,json,os,shutil,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['sdr','edr']);p.add_argument('--resolution',choices=['720','1080','1440','2160'],default='1080');p.add_argument('--fps',type=int,choices=[30,60],default=30);p.add_argument('--isolated',action='store_true');p.add_argument('--app',type=Path);a=p.parse_args()
factor=a.fps//30;frame=2200*factor
bundle='org.nxnative.tgaa.japan.cn13.edrtrial'
app=a.app or Path.home()/'Applications/大逆转裁判 1&2 SDR-EDR体验版.app'
out=ROOT/'local-data/edr-package'/f'{time.time_ns()}-{a.mode}';out.mkdir()
log=Path.home()/'Library/Logs/nxnative/0100D7F00FB1A000-edrtrial.log'
if not a.isolated: subprocess.run(['defaults','write',bundle,'launcher.DM_TGAA_DISPLAY','-string',a.mode],check=True)
env={k:v for k,v in os.environ.items() if not k.startswith('DM_')}
env.update(DM_TGAA_RESOLUTION=a.resolution,DM_TGAA_FPS=str(a.fps),DM_KEYS=','.join(f'f{f*factor}:A' for f in [700,1100,1500,1700]),DM_EDR_READBACK=str(out/'present.raw'),DM_EDR_READBACK_FRAME=str(frame),DM_TEST_KEEP_FOCUS='1',DM_EDR_BUILTIN='1',DM_NVN_TEXDUMP=f'{frame}:{out}/target-%d.png',DM_NVN_SNAPRAW='1')
if a.isolated:
 shutil.copytree(ROOT/'local-data/native4k-test/save',out/'save');(out/'temp').mkdir();env.update(DM_TGAA_DISPLAY=a.mode,DM_SAVE=str(out/'save'),DM_TEMP=str(out/'temp'))
print(out,flush=True)
proc=None;reason='timeout'
try:
 proc=subprocess.Popen([str(app/'Contents/MacOS/nxnative'),'--no-launcher'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 deadline=time.monotonic()+240
 while proc.poll() is None and time.monotonic()<deadline:
  text=log.read_text(errors='replace') if log.exists() else ''
  if (out/'present.raw').exists() and str(out/'present.raw') in text and 'EDR readback complete' in text and '[texdump]' in text and f'frame {frame+1}' in text:reason='capture-complete';time.sleep(12);break
  time.sleep(1)
 if proc.poll() is not None:reason='process-exited'
finally:
 if proc and proc.poll() is None:
  proc.send_signal(signal.SIGTERM)
  try:proc.wait(timeout=12)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
 if log.exists():shutil.copyfile(log,out/'run.log')
 if not a.isolated: subprocess.run(['defaults','write',bundle,'launcher.DM_TGAA_DISPLAY','-string','sdr'],check=True)
text=(out/'run.log').read_text(errors='replace')
checks=dict(mode_logged=f'launcher: display mode {a.mode.upper()}' in text,readback_complete='EDR readback complete' in text,overlay_loaded='version tag hidden' in text)
report=dict(resolution=a.resolution,fps=a.fps,isolated=a.isolated,mode=a.mode,reason=reason,checks=checks,preferences='unchanged' if a.isolated else 'restored SDR')
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
raise SystemExit(0 if reason=='capture-complete' and all(checks.values()) else 1)
