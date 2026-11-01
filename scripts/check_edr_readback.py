#!/usr/bin/env python3
"""Check a presentation readback against extended-sRGB decoding of its source."""
import argparse,json,struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--headroom',type=float,required=True)
a=p.parse_args()
def read(path):
 with path.open('rb') as f:
  w,h,pf,row=map(int,f.readline().split());data=f.read()
 if pf!=115 or row!=w*8 or len(data)!=row*h: raise ValueError('Expected packed RGBA16Float')
 return w,h,data
w,h,src=read(a.source);wo,ho,dst=read(a.output)
if (w,h)!=(wo,ho):raise ValueError('Sizes differ')
error=total=0.;n=0;bad=0
for s,d in zip(struct.iter_unpack('<4e',src),struct.iter_unpack('<4e',dst)):
 for v,out in zip(s[:3],d[:3]):
  v=max(0,v);expected=min(a.headroom,v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)
  delta=abs(expected-out);error=max(error,delta);total+=delta;n+=1;bad+=delta>.002
print(json.dumps(dict(width=w,height=h,max_error=error,mean_error=total/n,channels_error_above_002=bad,warning='Frame correspondence must be checked; mismatched animated frames are not shader conversion failures.'),indent=2))
