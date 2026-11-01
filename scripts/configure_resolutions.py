#!/usr/bin/env python3
"""Add verified Japanese TGAA resolutions to a built Mac app's settings.

Requires the matching custom dmhost. Sign the app after applying this script.
"""
import argparse
import json
import plistlib
from pathlib import Path


def configure(app: Path):
    dm = app / 'Contents/Resources/dm'
    settings_path = dm / 'launcher.json'
    info_path = app / 'Contents/Info.plist'
    data = json.loads(settings_path.read_text())
    info = plistlib.loads(info_path.read_bytes())
    if data.get('game') != '0100D7F00FB1A000':
        raise ValueError('Only Japanese TGAA is supported')
    setting = {
        'env': 'DM_TGAA_RESOLUTION', 'kind': 'choice', 'section': '游戏',
        'label': '渲染分辨率', 'default': '1080', 'level': 'basic',
        'note': '重启游戏后生效。更高分辨率会增加内存和 GPU 负载。',
        'options': [['720', '1280 × 720'], ['1080', '1920 × 1080（推荐）'],
                    ['1440', '2560 × 1440（测试）'],
                    ['2160', '3840 × 2160 · 4K（测试）']],
    }
    settings = [s for s in data['settings'] if s['env'] != setting['env']]
    for s in settings:
        if s['env'] == 'DM_OPMODE':
            s.update(label='操作模式', note='鼠标触控模式支持上方选择的渲染分辨率。')
            s['options'] = [['0', '鼠标触控（推荐）'], ['1', '电视模式（无鼠标触控）']]
    data['settings'] = [setting] + settings
    rules = [r for r in info.get('DMSettings', []) if r['env'] != setting['env']]
    rules.append({'env': setting['env'], 'values': [v for v, _ in setting['options']]})
    info['DMSettings'] = rules
    settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    info_path.write_bytes(plistlib.dumps(info, sort_keys=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    configure(parser.parse_args().app)
