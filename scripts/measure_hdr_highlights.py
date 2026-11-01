#!/usr/bin/env python3
"""Locate over-range RGB in a float snapshot; no luminance calibration implied."""
import argparse,json,struct,math
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);a=p.parse_args()
with a.raw.open('rb') as f:
 w,h,pf,row=map(int,f.readline().split());data=f.read()
if pf!=115 or row!=w*8 or len(data)!=row*h: raise SystemExit('Expected packed RGBA16Float')
count=0; peak=0.;x0=w;y0=h;x1=y1=-1; quadrants=[0]*4
for i,px in enumerate(struct.iter_unpack('<4e',data)):
 v=max(px[:3]);peak=max(peak,v)
 if v>1.001:
  x=i%w;y=i//w;count+=1;x0=min(x0,x);y0=min(y0,y);x1=max(x1,x);y1=max(y1,y)
  quadrants[(y>=h//2)*2+(x>=w//2)]+=1
print(json.dumps(dict(file=a.raw.name,width=w,height=h,peak_rgb=peak,pixels_above_1=count,percent=100*count/(w*h),bounds=[x0,y0,x1,y1] if count else None,quadrants=quadrants),indent=2))
