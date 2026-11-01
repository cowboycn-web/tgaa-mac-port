#!/usr/bin/env python3
"""Isolated SDR/float measurements and optional experimental EDR presentation."""
import argparse, json, os, shutil, signal, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--resolution', choices=['720','1080','1440','2160'], default='1080')
p.add_argument('--fps', type=int, choices=[30,60], default=30)
p.add_argument('--window', action='store_true', help='Open a window for the SDR control')
p.add_argument('--edr', action='store_true', help='Open an experimental EDR window on the built-in display')
p.add_argument('--clamped-control', action='store_true', help='Runtime-compile unchanged shader for compiler-matched control')
p.add_argument('--unclamp', action='store_true', help='Use separately built experimental postprocess library')
p.add_argument('--float-targets', action='store_true')
p.add_argument('--frame', type=int, default=2200)
p.add_argument('--timeout', type=int, default=240)
a = p.parse_args()
factor=a.fps//30
a.frame *= factor
if a.edr and not (a.float_targets and a.unclamp): p.error('--edr requires --float-targets --unclamp')
if a.unclamp and a.clamped_control: p.error('Choose experiment or control')
if (a.unclamp or a.clamped_control) and not a.float_targets: p.error('--unclamp requires --float-targets')
r = Path.home() / 'Applications/大逆转裁判 1&2 SDR-EDR体验版.app/Contents/Resources'
if 'd871b992e95b71c541ddc834f63c664b' not in (r/'dm/main.fixups.tsv').read_text():
    raise SystemExit('Unexpected game build')
out = ROOT/'local-data/hdr-test'/f'{time.time_ns()}-{"float" if a.float_targets else "sdr"}'
out.mkdir(parents=True)
shutil.copytree(ROOT/'local-data/native4k-test/save',out/'save')
(out/'temp').mkdir()
(out/'control.txt').touch()
env={k:v for k,v in os.environ.items() if not k.startswith('DM_')}
env.update(DM_TGAA_RESOLUTION=a.resolution, DM_TGAA_FPS=str(a.fps), DM_OPMODE='0',
 DM_TGAA_FLOAT_PROBE='1' if a.float_targets else '0', DM_ROMFS=str(r/'romfs.img'),
 DM_SAVE=str(out/'save'),DM_TEMP=str(out/'temp'),DM_CTL=str(out/'control.txt'),
 DM_MSL_DIR=str(r/'msl'), DM_NVN_SHMAP=str(r/'dm/shader_map.tsv'),
 DM_KEYS=','.join(f'f{f*factor}:T{xy}' for f,xy in [(700,'0.5x0.68'),(1100,'0.5x0.77'),(1500,'0.5x0.55'),(1700,'0.37x0.68')]),
 DM_NVN_PASSDUMP=str(a.frame), DM_NVN_TEXDUMP=f'{a.frame}:{out}/target-%d.png',DM_NVN_SNAPRAW='1',
 DM_NVN_TEXSNAP_MSAA='1', DM_NVN_TEXSNAP=','.join(map(str,range(24))))
if a.unclamp: env['DM_TGAA_POSTPROCESS_SOURCE']=str(ROOT/'local-data/hdr-test/unclamp-msl/720e88a17ae787f6_b.metal')
if a.clamped_control: env['DM_TGAA_POSTPROCESS_SOURCE']=str(ROOT/'local-data/hdr-test/unclamp-msl/clamped-control.metal')
if a.window: env.update(DM_WINDOW='1',DM_TEST_KEEP_FOCUS='1',DM_EDR_READBACK=str(out/'present-linear.raw'),DM_EDR_READBACK_FRAME=str(a.frame),DM_KEYS=','.join(f'f{f*factor}:A' for f in [700,1100,1500,1700]))
if a.edr:
 env.update(DM_TEST_KEEP_FOCUS='1',DM_TGAA_EDR='1',DM_WINDOW='1',DM_EDR_BUILTIN='1',DM_PRESENT_UPSCALE='off',DM_EDR_READBACK=str(out/'present-linear.raw'),DM_EDR_READBACK_FRAME=str(a.frame),DM_KEYS=','.join(f'f{f*factor}:A' for f in [700,1100,1500,1700]))
print(out,flush=True)
reason='timeout'
with (out/'run.log').open('w') as log:
 proc=subprocess.Popen([str(ROOT/'upstream/nxnative/dm/host/dmhost'),str(r/'dm')],env=env,stdout=log,stderr=subprocess.STDOUT)
 try:
  deadline=time.monotonic()+a.timeout
  while proc.poll() is None and time.monotonic()<deadline:
   if ((not (a.edr or a.window) or 'EDR readback complete' in (out/'run.log').read_text(errors='replace')) and ('[texdump]' in (out/'run.log').read_text(errors='replace') and f'frame {a.frame + 1}' in (out/'run.log').read_text(errors='replace'))):
    reason='capture-complete'; time.sleep(12); break
   time.sleep(1)
  if proc.poll() is not None: reason='process-exited'
 finally:
  if proc.poll() is None:
   proc.send_signal(signal.SIGINT)
   try: proc.wait(timeout=10)
   except subprocess.TimeoutExpired: proc.kill(); proc.wait()
report=dict(resolution=a.resolution,fps=a.fps,clamped_control=a.clamped_control,unclamp=a.unclamp,frame=a.frame,float_targets=a.float_targets,reason=reason,returncode=proc.returncode,hdr_display_requested=a.edr)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
raise SystemExit(0 if reason=='capture-complete' else 1)
