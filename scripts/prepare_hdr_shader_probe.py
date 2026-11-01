#!/usr/bin/env python3
"""Prepare an isolated, explicitly experimental unclamped postprocess shader."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
chain='b-a78f966a7b38'
key='720e88a17ae787f6_b'
out=ROOT/'local-data/hdr-test/unclamp-msl'
out.mkdir(parents=True,exist_ok=True)
source=ROOT/'local-data/input/0100D7F00FB1A000_build/shader/cache'/chain/(key+'.metal')
s=source.read_text()
(out/'clamped-control.metal').write_text(s)
for v in (70,74,78):
 old=f'precise::clamp(_{v}, 0.0, 1.0)'
 if s.count(old)!=1: raise SystemExit('Unexpected shader source')
 s=s.replace(old,f'_{v}')
patched=out/(key+'.metal');patched.write_text(s)
(out/'experiment.json').write_text(json.dumps(dict(shader=key,change='Remove only three RGB output clamps; preserve exposure, alpha and all other shaders.',original_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),experimental=True,hdr_display=False),indent=2)+'\n')
print(out)
