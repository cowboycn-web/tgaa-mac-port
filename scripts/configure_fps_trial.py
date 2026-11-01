#!/usr/bin/env python3
"""Configure a separately copied trial app; requires the matching custom host/launcher."""
import argparse
import json
import plistlib
from pathlib import Path
from configure_resolutions import configure


def configure_trial(app):
    configure(app)
    info_path = app / 'Contents/Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    name = '大逆转裁判 1&2 60帧体验版'
    info.update(CFBundleName=name, CFBundleDisplayName=name,
                CFBundleIdentifier='org.nxnative.tgaa.japan.cn13.fps60trial',
                DMDataID='0100D7F00FB1A000-fps60trial')
    rules = [r for r in info['DMSettings'] if r['env'] != 'DM_TGAA_FPS']
    rules.append({'env': 'DM_TGAA_FPS', 'values': ['30', '60']})
    info['DMSettings'] = rules
    info_path.write_bytes(plistlib.dumps(info, sort_keys=False))
    path = app / 'Contents/Resources/dm/launcher.json'
    data = json.loads(path.read_text())
    setting = {'env': 'DM_TGAA_FPS', 'kind': 'choice', 'section': '游戏',
               'label': '目标帧率', 'default': '30', 'level': 'basic',
               'options': [['30', '30 帧（标准）'], ['60', '60 帧（体验）']],
               'note': '重启生效。60 帧已测试部分法庭对话，其他场景仍需验证；异常时切回 30 帧。'}
    data['settings'] = [setting] + [s for s in data['settings'] if s['env'] != 'DM_TGAA_FPS']
    defaults = {'DM_OPMODE': '0', 'DM_LANG': 'ja', 'DM_TGAA_RESOLUTION': '1080',
                'DM_PRESENT_UPSCALE': 'off', 'DM_METAL_HUD': '0'}
    for row in data['settings']:
        if row['env'] in defaults:
            row['default'] = defaults[row['env']]
    # Launcher packs use name for the settings header.
    if 'name' in data:
        data['name'] = name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    configure_trial(parser.parse_args().app)
