#!/usr/bin/env python3
"""Configure an isolated SDR/EDR comparison bundle; sign after configuring."""
import argparse,json,plistlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('app',type=Path);a=p.parse_args()
res=a.app/'Contents/Resources';info_path=a.app/'Contents/Info.plist';config=res/'dm/launcher.json'
info=plistlib.loads(info_path.read_bytes());data=json.loads(config.read_text())
if data.get('game')!='0100D7F00FB1A000':raise SystemExit('Unexpected game')
name='大逆转裁判 1&2 SDR-EDR体验版'
info.update(CFBundleName=name,CFBundleDisplayName=name,CFBundleIdentifier='org.nxnative.tgaa.japan.cn13.edrtrial',DMDataID='0100D7F00FB1A000-edrtrial',DMDisplayExperiment='tgaa-edr-v1')
choice=dict(env='DM_TGAA_DISPLAY',kind='choice',section='游戏',label='显示模式',default='sdr',level='basic',options=[['sdr','SDR（标准）'],['edr','EDR（实验）']],note='重启游戏后生效。请优先在内置屏幕比较；EDR 保留部分高光，色彩与全章节表现仍待验证。')
rows=[choice]+[s for s in data['settings'] if s['env']!='DM_TGAA_DISPLAY']
for s in rows:
 if s['env']=='DM_TGAA_RESOLUTION':s.update(default='1080',options=[['720','1280 × 720'],['1080','1920 × 1080（标准）'],['1440','2560 × 1440'],['2160','3840 × 2160 · 4K（实验）']],note='重启生效。4K 会增加 GPU 与内存负载；性能不足时降低分辨率。')
 if s['env']=='DM_TGAA_FPS':s.update(default='30',options=[['30','30 帧（标准）'],['60','60 帧（实验）']],note='重启生效。可与分辨率、EDR 组合；60 帧为目标，不保证全程达到。')
 if s['env']=='DM_PRESENT_UPSCALE':s.update(default='off',options=[['off','关闭']],note='显示对比期间关闭额外缩放处理。')
 if s['env']=='DM_METAL_HUD':s['default']='0'
data['settings']=rows;data['name']=name
rules={r['env']:r for r in info['DMSettings']}
for s in rows:
 if 'options' in s: rules[s['env']]=dict(env=s['env'],values=[o[0] for o in s['options']])
info['DMSettings']=list(rules.values())
info_path.write_bytes(plistlib.dumps(info,sort_keys=False));config.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(res/'hdr').mkdir(exist_ok=True)
shutil.copyfile(ROOT/'local-data/hdr-test/unclamp-msl/720e88a17ae787f6_b.metal',res/'hdr/720e88a17ae787f6_b.metal')
print(a.app)
