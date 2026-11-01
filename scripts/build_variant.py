#!/usr/bin/env python3
"""Prepare or pack isolated original (Japanese/English) and Chinese TGAA apps.

Requires previously built, matching nxnative host/modules/shaders. Does not
extract games, obtain keys, install apps, copy saves, or upload anything.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TITLE = '0100D7F00FB1A000'
MARKER = Path('nativeNXx64/sa/NX_64/root.arc')
VARIANTS = {
    'original': ('The Great Ace Attorney Chronicles - Original', 'org.nxnative.tgaa.japan.original', TITLE + '-original'),
    'chinese': ('大逆转裁判 1&2 汉化版', 'org.nxnative.tgaa.japan.cn13', TITLE + '-cn13'),
}


def ui_default(variant):
    return 'en' if variant == 'original' else 'zh-Hans'


def variant_name(variant, ui_language):
    if ui_language == 'en':
        return 'The Great Ace Attorney Chronicles - ' + ('Original' if variant == 'original' else 'Chinese')
    return '大逆转裁判 1&2 ' + ('原版' if variant == 'original' else '汉化版')


def localize_settings(rows, ui_language):
    # Replace presentation fields by setting ID, even if the input was already
    # translated. Never change the environment values consumed by the host.
    labels = {
        'DM_LANG': ('游戏语言', 'Game language'),
        'DM_OPMODE': ('操作模式', 'Input mode'),
        'DM_FULLSCREEN': ('显示模式', 'Window mode'),
        'DM_RUMBLE': ('游戏震动', 'Controller vibration'),
        'DM_RUMBLE_GAIN': ('震动强度', 'Vibration strength'),
        'DM_RUMBLE_MIN': ('震动触发阈值', 'Vibration threshold'),
        'DM_PRESENT_UPSCALE': ('画面放大', 'Upscaling'),
        'DM_METAL_HUD': ('性能监视器', 'Performance overlay'),
        'DM_TGAA_RESOLUTION': ('渲染分辨率', 'Render resolution'),
        'DM_TGAA_FPS': ('目标帧率', 'Target frame rate'),
        'DM_TGAA_DISPLAY': ('显示模式', 'Display output'),
    }
    options = {
        'DM_OPMODE': {'0': ('鼠标触控（推荐）', 'Mouse / touch (recommended)'), '1': ('电视模式（无鼠标触控）', 'TV mode (no mouse touch)')},
        'DM_FULLSCREEN': {'0': ('窗口', 'Windowed'), '1': ('全屏', 'Full screen')},
        'DM_PRESENT_UPSCALE': {'off': ('关闭', 'Off'), 'metalfx': ('MetalFX', 'MetalFX')},
        'DM_TGAA_RESOLUTION': {v: (label, label) for v, label in [('720', '1280 × 720'), ('1080', '1920 × 1080')]},
        'DM_TGAA_FPS': {'30': ('30 帧', '30 FPS'), '60': ('60 帧（实验）', '60 FPS (experimental)')},
        'DM_TGAA_DISPLAY': {'sdr': ('SDR', 'SDR'), 'edr': ('EDR（实验）', 'EDR (experimental)')},
    }
    for value, size in [('1440', '2560 × 1440'), ('2160', '3840 × 2160')]:
        options['DM_TGAA_RESOLUTION'][value] = (size + '（实验）', size + ' (experimental)')
    notes = {
        'DM_LANG': ('重启后生效。', 'Applied after restarting the game.'),
        'DM_OPMODE': ('鼠标触控跟随所选渲染分辨率。', 'Mouse touch coordinates follow the selected render resolution.'),
        'DM_PRESENT_UPSCALE': ('会增加 GPU 负载和设备发热。', 'May increase GPU load and heat.'),
        'DM_TGAA_RESOLUTION': ('重启后生效；高分辨率仍需完整流程验证。', 'Restart required. Higher resolutions still need full-game testing.'),
        'DM_TGAA_FPS': ('重启后生效；60 帧仍需验证剧情速度和音画同步。', 'Restart required. 60 FPS still needs timing and audio/video sync testing.'),
        'DM_TGAA_DISPLAY': ('重启后生效；EDR 是实验输出，并非已校准的原生 HDR。', 'Restart required. EDR is experimental, not calibrated native HDR.'),
    }
    index = 1 if ui_language == 'en' else 0
    for row in rows:
        env = row['env']
        row['label'] = labels[env][index]
        section = ('性能', 'Performance') if env in ('DM_METAL_HUD', 'DM_PRESENT_UPSCALE') else (('操作', 'Controls') if env.startswith('DM_RUMBLE') else ('游戏', 'Game'))
        row['section'] = section[index]
        row['note'] = notes.get(env, ('', ''))[index]
        for option in row.get('options', []):
            if env in options:
                if option[0] not in options[env]: raise ValueError(f'Unsupported option for {env}: {option[0]}')
                option[1] = options[env][option[0]][index]
    return rows


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def tree_files(root):
    """Reject symlinks and case collisions before copying untrusted resource trees."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f'Expected a real directory: {root}')
    files, seen = [], set()
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError(f'Symlinks are not supported: {p}')
        relative = p.relative_to(root)
        key = relative.as_posix().casefold()
        if key in seen:
            raise ValueError(f'Case-colliding resource paths: {relative}')
        seen.add(key)
        if p.is_file():
            files.append(relative)
        elif not p.is_dir():
            raise ValueError(f'Unsupported resource type: {p}')
    return files


def validate_resources(base, overlay, variant):
    files = tree_files(base)
    required = [MARKER] + [Path(f'nativeNXx64/archive/font_{lang}.arc') for lang in ('jpn', 'eng')]
    if not all((base / p).is_file() for p in required):
        raise ValueError('Base must be the complete, clean Japanese 1.0.0 RomFS, including both font archives')
    # Catch the known CN1.3 font archive used during this project's experiments.
    # This is a useful guard, not a proof of the origin of every supplied file.
    manifest = ROOT / 'docs/patch-manifest.tsv'
    for line in manifest.read_text().splitlines():
        cols = line.replace('\\t', '\t').split('\t')
        if len(cols) == 3 and cols[0] == 'romfs/nativeNXx64/archive/font_jpn.arc':
            if digest(base / 'nativeNXx64/archive/font_jpn.arc') == cols[2]:
                raise ValueError('Base contains the known Chinese font patch; supply the unmodified original RomFS')
    if variant == 'original' and overlay is not None:
        raise ValueError('Original builds must not receive a Chinese overlay')
    if variant == 'chinese' and overlay is None:
        raise ValueError('Chinese builds require --overlay-romfs pointing to the patch romfs directory')
    additions = tree_files(overlay) if overlay else []
    if overlay and (not additions or any(p.parts[0] != 'nativeNXx64' for p in additions)):
        raise ValueError('Overlay must be a nonempty romfs directory containing only nativeNXx64 resources')
    if overlay and (base == overlay or base in overlay.parents or overlay in base.parents):
        raise ValueError('Base and overlay must be separate, non-nested directories')
    # Avoid platform-dependent results when overlay casing differs from the base.
    casing = {p.relative_to(base).as_posix().casefold(): p.relative_to(base).as_posix()
              for p in base.rglob('*')}
    if overlay:
        for p in overlay.rglob('*'):
            rel = p.relative_to(overlay).as_posix()
            if rel.casefold() in casing and casing[rel.casefold()] != rel:
                raise ValueError(f'Overlay casing differs from base: {rel}')
            target = base / rel
            if target.exists() and target.is_dir() != p.is_dir():
                raise ValueError(f'Overlay file/directory conflict: {rel}')
    return files, additions


def make_settings(source, variant, language, edr=False, ui_language=None):
    ui_language = ui_language or ui_default(variant)
    data = json.loads(source.read_text())
    if data.get('game') != TITLE:
        raise ValueError('Launcher settings must target Japanese TGAA')
    allowed = {'DM_OPMODE', 'DM_LANG', 'DM_FULLSCREEN', 'DM_RUMBLE',
               'DM_RUMBLE_GAIN', 'DM_RUMBLE_MIN', 'DM_PRESENT_UPSCALE', 'DM_METAL_HUD'}
    rows = [s for s in data['settings'] if s['env'] in allowed]
    lang = next((s for s in rows if s['env'] == 'DM_LANG'), None)
    if lang is None:
        raise ValueError('Launcher settings are missing DM_LANG')
    lang.update(default=language, options=([['ja', '中文（汉化资源）']] if variant == 'chinese'
                else [['ja', 'Japanese' if ui_language == 'en' else '日语'], ['en-US', 'English (US)'], ['en-GB', 'English (UK)']]))
    if variant == 'chinese' and ui_language == 'en': lang['options'] = [['ja', 'Chinese (fan translation)']]
    for s in rows:
        if s['env'] == 'DM_OPMODE': s['default'] = '0'
        if s['env'] == 'DM_PRESENT_UPSCALE': s['default'] = 'off'
        if s['env'] == 'DM_METAL_HUD': s['default'] = '0'
    def choice(env, label, default, options):
        return dict(env=env, kind='choice', section='游戏', label=label,
                    default=default, level='basic', options=options, note='重启后生效；增强选项仍需完整流程验证。')
    rows.extend([
        choice('DM_TGAA_RESOLUTION', '渲染分辨率', '1080', [['720', '1280 × 720'],
               ['1080', '1920 × 1080'], ['1440', '2560 × 1440（实验）'], ['2160', '3840 × 2160（实验）']]),
        choice('DM_TGAA_FPS', '目标帧率', '30', [['30', '30 帧'], ['60', '60 帧（实验）']]),
    ])
    if edr:
        rows.append(choice('DM_TGAA_DISPLAY', '显示模式', 'sdr', [['sdr', 'SDR'], ['edr', 'EDR（实验）']]))
    data.update(name=variant_name(variant, ui_language), settings=localize_settings(rows, ui_language))
    return data


def prepare(base, overlay, variant, settings, language, destination, edr=False, ui_language=None):
    ui_language = ui_language or ui_default(variant)
    _, additions = validate_resources(base, overlay, variant)
    data = make_settings(settings, variant, language, edr, ui_language)
    if destination.exists():
        raise ValueError('Preparation destination must not exist; never reuse a variant resource tree')
    if any(destination == p or p in destination.parents or destination in p.parents
           for p in (base, overlay) if p):
        raise ValueError('Preparation output must be separate from input trees')
    destination.mkdir(parents=True)
    shutil.copytree(base, destination / 'romfs')
    if overlay:
        for relative in additions:
            target = destination / 'romfs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(overlay / relative, target)
    (destination / 'launcher.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (destination / 'env.txt').write_text('DM_TOUCH_1080=1\n')
    report = dict(title_id=TITLE, variant=variant, language=language, ui_language=ui_language,
                  bundle_id=VARIANTS[variant][1], data_id=VARIANTS[variant][2],
                  overlay_files={str(p): digest(overlay / p) for p in additions})
    (destination / 'build-variant.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', choices=VARIANTS, required=True)
    p.add_argument('--base-romfs', type=Path, required=True, help='Clean extracted original RomFS directory')
    p.add_argument('--overlay-romfs', type=Path, help='Chinese patch romfs directory; Chinese builds only')
    p.add_argument('--settings', type=Path, required=True, help='Generated launcher.json for this title')
    p.add_argument('--language', choices=('ja', 'en-US', 'en-GB'), help='Game language: defaults to en-US for original, ja for Chinese')
    p.add_argument('--ui-language', choices=('en', 'zh-Hans'), help='Launcher/menu language: defaults to en for original, zh-Hans for Chinese')
    p.add_argument('--upstream', type=Path, default=ROOT / 'upstream/nxnative')
    for flag in ('host', 'patched', 'msl', 'tables', 'font', 'icon', 'guide', 'edr-shader'):
        p.add_argument('--' + flag, type=Path)
    p.add_argument('--output', type=Path, help='New .app path (existing output is rejected)')
    p.add_argument('--prepare-only', type=Path, metavar='NEW_DIRECTORY', help='Prepare resource tree/settings only; no app compilation')
    p.add_argument('--dry-run', action='store_true', help='Validate inputs and print plan without writing files')
    return p


def main(argv=None):
    p = parser()
    a = p.parse_args(argv)
    a.language = a.language or ('en-US' if a.variant == 'original' else 'ja')
    a.ui_language = a.ui_language or ui_default(a.variant)
    try:
        for key, value in vars(a).items():
            if isinstance(value, Path):
                expanded = value.expanduser().absolute()
                if expanded.is_symlink(): raise ValueError(f'Symlink input/output is not supported: {expanded}')
                setattr(a, key, expanded.resolve())
        if a.variant == 'chinese' and a.language != 'ja':
            raise ValueError('Chinese patch replaces Japanese resources; use --language ja')
        if a.prepare_only and a.output:
            raise ValueError('Choose --prepare-only or --output')
        if not a.prepare_only and (not a.output or a.output.suffix != '.app'):
            raise ValueError('App builds require --output ending in .app')
        for target in (a.prepare_only, a.output):
            if target and (target.exists() or target.is_symlink()):
                raise ValueError(f'Output already exists: {target}')
            if target and any(target == source or source in target.parents or target in source.parents
                              for source in (a.base_romfs, a.overlay_romfs) if source):
                raise ValueError('Output must be separate from input trees')
        validate_resources(a.base_romfs, a.overlay_romfs, a.variant)
        make_settings(a.settings, a.variant, a.language, bool(a.edr_shader), a.ui_language)
        for key in ('guide', 'icon', 'edr_shader'):
            if getattr(a, key) and not getattr(a, key).is_file():
                raise ValueError(f'Missing --{key.replace("_", "-")} input')
        packer = a.upstream / 'dm/mac/pack_app.py'
        if not a.prepare_only:
            for key in ('host', 'patched', 'msl', 'tables', 'font'):
                value = getattr(a, key)
                if not value or not (value.is_file() if key == 'host' else value.is_dir()):
                    raise ValueError(f'Provide an existing --{key} input')
            if not packer.is_file() or any(flag not in packer.read_text() for flag in ('--resource-variant', '--ui-language')):
                raise ValueError('Apply all three nxnative patches before building')
        print(json.dumps(dict(variant=a.variant, language=a.language, ui_language=a.ui_language, name=variant_name(a.variant, a.ui_language),
                              bundle_id=VARIANTS[a.variant][1], data_id=VARIANTS[a.variant][2],
                              chinese_overlay=bool(a.overlay_romfs), guide=bool(a.guide), edr=bool(a.edr_shader)),
                         ensure_ascii=False, indent=2))
        if a.dry_run: return 0
        if a.prepare_only:
            prepare(a.base_romfs, a.overlay_romfs, a.variant, a.settings, a.language, a.prepare_only, bool(a.edr_shader), a.ui_language)
            return 0
        a.output.parent.mkdir(parents=True, exist_ok=True)
        # Stage beside output so the final rename also works on external volumes.
        with tempfile.TemporaryDirectory(prefix='.tgaa-' + a.variant + '-', dir=a.output.parent) as temp:
            stage = Path(temp) / 'prepared'
            report = prepare(a.base_romfs, a.overlay_romfs, a.variant, a.settings, a.language, stage, bool(a.edr_shader), a.ui_language)
            candidate = Path(temp) / a.output.name
            cmd = [sys.executable, str(packer), str(candidate)]
            for key in ('host', 'patched', 'msl', 'tables', 'font', 'icon', 'guide'):
                if getattr(a, key): cmd += ['--' + key, str(getattr(a, key))]
            cmd += ['--romfs', str(stage / 'romfs'), '--settings', str(stage / 'launcher.json'),
                    '--env-file', str(stage / 'env.txt'), '--title-id', TITLE, '--marker', str(MARKER),
                    '--name', variant_name(a.variant, a.ui_language), '--bundle-id', VARIANTS[a.variant][1],
                    '--data-id', VARIANTS[a.variant][2], '--resource-variant', a.variant, '--lang', a.language,
                    '--ui-language', a.ui_language]
            subprocess.run(cmd, check=True)
            # EDR is optional and never copied from an already patched app.
            resources = candidate / 'Contents/Resources'
            if a.edr_shader:
                import plistlib
                info_path = candidate / 'Contents/Info.plist'
                info = plistlib.loads(info_path.read_bytes())
                info['DMDisplayExperiment'] = 'tgaa-edr-v1'
                info_path.write_bytes(plistlib.dumps(info, sort_keys=False))
                (resources / 'hdr').mkdir()
                shutil.copy2(a.edr_shader, resources / 'hdr/720e88a17ae787f6_b.metal')
            (resources / 'build-variant.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            subprocess.run(['codesign', '--force', '--sign', '-', str(candidate)], check=True)
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(candidate)], check=True)
            # Rename only complete, verified app bundles; leave installed apps alone.
            if a.output.exists(): raise ValueError('Output appeared during build; refusing replacement')
            candidate.rename(a.output)
        print(f'app: {a.output}')
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        p.exit(1, f'build_variant: {e}\n')


if __name__ == '__main__':
    raise SystemExit(main())
