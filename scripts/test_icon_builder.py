#!/usr/bin/env python3
from pathlib import Path
import ctypes,subprocess,tempfile
root=Path(__file__).resolve().parents[1];src=root/'upstream/nxnative/dm/mac/button_atlas.c'
subprocess.run(['clang','-shared','-fPIC',str(src),'-lz','-o','/private/tmp/tgaa-icon-builder.dylib'],check=True)
lib=ctypes.CDLL('/private/tmp/tgaa-icon-builder.dylib')
f=lib.dm_mac_button_overlay;f.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p]
g=lib.dm_mac_live_icons;g.argtypes=[ctypes.c_char_p]*3
res=str(Path.home()/'Applications/大逆转裁判 1&2 SDR-EDR体验版.app/Contents/Resources').encode()
out=root/'local-data/input-switch-test';out.mkdir(exist_ok=True)
assert f(res,str(out/'overlay').encode(),4,None)
font=out/'overlay/nativeNXx64/archive/font_jpn.arc';assert font.exists()
import struct,zlib

def members(path):
 data=path.read_bytes();count=struct.unpack_from('<H',data,6)[0];result={}
 for i in range(count):
  pos=8+i*0x90;name=data[pos:pos+128].split(b'\0')[0]
  size,marked,offset=struct.unpack_from('<III',data,pos+0x84)
  result[name]=data[offset:offset+size]
 return result
for lang in ['jpn','eng']:
 original=members(Path(res.decode())/'button_source'/f'font_{lang}.arc')
 changed=members(out/'overlay/nativeNXx64/archive'/f'font_{lang}.arc')
 assert original.keys()==changed.keys()
 assert all(changed[k]==v for k,v in original.items() if not k.endswith(b'button_swi_00_ID_HQ'))
assert f(res,str(out/'overlay').encode(),1,None);assert not font.exists()
assert g(res,str(out/'live').encode(),None)
for p in (out/'live').glob('*.icons'):
 data=p.read_bytes();assert len(data)==5*262144
 assert len({data[i*262144:(i+1)*262144] for i in range(1,5)})==4
print('PASS: stale overlay cleanup, four distinct complete live variants, both languages')
