#!/usr/bin/env python3
"""Measure finite RGB ranges from Metal TEXDUMP raw output, excluding alpha."""
import argparse, json, math, struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('directory',type=Path)
a=p.parse_args()
results=[]
for f in sorted(a.directory.glob('*.raw')):
 with f.open('rb') as stream:
  w,h,pf,row=map(int,stream.readline().split()); data=stream.read()
 if pf not in (70,115): continue
 bpp=8 if pf==115 else 4
 if len(data)!=row*h: raise ValueError(f'Truncated raw file: {f}')
 low=float('inf'); high=-float('inf'); above=bad=0
 for y in range(h):
  for px in struct.iter_unpack('<4e' if pf==115 else '4B',data[y*row:y*row+w*bpp]):
   rgb=px[:3] if pf==115 else tuple(v/255 for v in px[:3])
   if not all(math.isfinite(v) for v in rgb): bad+=1; continue
   low=min(low,*rgb); high=max(high,*rgb); above+=max(rgb)>1.001
 results.append(dict(file=f.name,width=w,height=h,metal_format=pf,min_rgb=low,max_rgb=high,pixels_above_1=above,percent_above_1=100*above/(w*h),nonfinite_pixels=bad))
report=dict(targets=results,note='Raw shader-domain RGB; not a calibrated linear luminance or proof of HDR presentation.')
(a.directory/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
