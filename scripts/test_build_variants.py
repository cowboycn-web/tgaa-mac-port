"""Resource isolation and build orchestration tests; no game data required."""
import contextlib
import io
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

import build_variant as build


class VariantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'base'
        for rel in (build.MARKER, Path('nativeNXx64/archive/font_jpn.arc'),
                    Path('nativeNXx64/archive/font_eng.arc')):
            p = self.base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'original')
        self.overlay = self.root / 'patch'
        p = self.overlay / 'nativeNXx64/archive/font_jpn.arc'
        p.parent.mkdir(parents=True)
        p.write_bytes(b'chinese')
        self.settings = self.root / 'settings.json'
        self.settings.write_text(json.dumps(dict(game=build.TITLE, settings=[
            dict(env='DM_LANG', kind='choice', default='ja', options=[['ja', 'Japanese']]),
            dict(env='DM_TGAA_DISPLAY', kind='choice', default='edr'),
        ])))

    def test_separate_resources_and_languages(self):
        for variant in build.VARIANTS:
            destination = self.root / variant
            overlay = self.overlay if variant == 'chinese' else None
            build.prepare(self.base, overlay, variant, self.settings, 'ja', destination)
            arc = destination / 'romfs/nativeNXx64/archive/font_jpn.arc'
            self.assertEqual(arc.read_bytes(), b'chinese' if overlay else b'original')
            self.assertEqual((destination / 'romfs/nativeNXx64/archive/font_eng.arc').read_bytes(), b'original')
            data = json.loads((destination / 'launcher.json').read_text())
            language = next(s for s in data['settings'] if s['env'] == 'DM_LANG')
            self.assertEqual([o[0] for o in language['options']], ['ja'] if overlay else ['ja', 'en-US', 'en-GB'])
            self.assertNotIn('DM_TGAA_DISPLAY', [s['env'] for s in data['settings']])
        self.assertEqual((self.base / 'nativeNXx64/archive/font_jpn.arc').read_bytes(), b'original')
        self.assertNotEqual(build.VARIANTS['original'][1:], build.VARIANTS['chinese'][1:])

    def test_english_settings_replace_previously_chinese_presentation(self):
        data = json.loads(self.settings.read_text())
        for env, kind, options in [
            ('DM_OPMODE', 'choice', [['0', '掌机'], ['1', '电视']]),
            ('DM_FULLSCREEN', 'choice', [['0', '窗口'], ['1', '全屏']]),
            ('DM_PRESENT_UPSCALE', 'choice', [['off', '标准'], ['metalfx', '放大']]),
            ('DM_METAL_HUD', 'toggle', None), ('DM_RUMBLE', 'toggle', None),
            ('DM_RUMBLE_GAIN', 'range', None), ('DM_RUMBLE_MIN', 'range', None),
        ]:
            row = dict(env=env, kind=kind, label='中文标签', note='中文提示', section='中文分组', default='0')
            if options: row['options'] = options
            data['settings'].append(row)
        self.settings.write_text(json.dumps(data, ensure_ascii=False))
        for edr in (False, True):
            settings = build.make_settings(self.settings, 'original', 'en-US', edr=edr)
            text = json.dumps(settings, ensure_ascii=False)
            self.assertFalse(any('\u4e00' <= ch <= '\u9fff' for ch in text))
            rows = {s['env']: s for s in settings['settings']}
            self.assertEqual(rows['DM_OPMODE']['options'][0][0], '0')
            self.assertEqual(rows['DM_TGAA_FPS']['default'], '30')
            self.assertEqual('DM_TGAA_DISPLAY' in rows, edr)

    def test_ui_and_game_languages_are_independent(self):
        settings = build.make_settings(self.settings, 'original', 'ja', ui_language='en')
        language = next(s for s in settings['settings'] if s['env'] == 'DM_LANG')
        self.assertEqual(language['default'], 'ja')
        self.assertEqual(language['label'], 'Game language')
        settings = build.make_settings(self.settings, 'chinese', 'ja', ui_language='en')
        language = next(s for s in settings['settings'] if s['env'] == 'DM_LANG')
        self.assertEqual(language['options'], [['ja', 'Chinese (fan translation)']])
        settings = build.make_settings(self.settings, 'chinese', 'ja')
        self.assertEqual(next(s['label'] for s in settings['settings'] if s['env'] == 'DM_LANG'), '游戏语言')

    def test_cli_variant_language_defaults(self):
        for variant, game, ui in [('original', 'en-US', 'en'), ('chinese', 'ja', 'zh-Hans')]:
            args = ['--variant', variant, '--base-romfs', str(self.base), '--settings', str(self.settings),
                    '--prepare-only', str(self.root / variant), '--dry-run']
            if variant == 'chinese': args += ['--overlay-romfs', str(self.overlay)]
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(build.main(args), 0)
            report = json.loads(output.getvalue())
            self.assertEqual((report['language'], report['ui_language']), (game, ui))

    def test_reject_overlay_in_original_and_missing_in_chinese(self):
        for variant, overlay in [('original', self.overlay), ('chinese', None)]:
            with self.assertRaises(ValueError):
                build.validate_resources(self.base, overlay, variant)

    def test_reject_symlinks_and_case_collision(self):
        link = self.overlay / 'nativeNXx64/link'
        link.symlink_to(self.base)
        with self.assertRaises(ValueError):
            build.validate_resources(self.base, self.overlay, 'chinese')
        link.unlink()
        renamed = self.overlay / 'nativeNXx64/archive/FONT_JPN.arc'
        (renamed.parent / 'font_jpn.arc').rename(renamed)
        with self.assertRaises(ValueError):
            build.validate_resources(self.base, self.overlay, 'chinese')

    def test_reject_known_chinese_base(self):
        arc = self.base / 'nativeNXx64/archive/font_jpn.arc'
        arc.write_bytes(b'chinese')
        # Read the project's real fingerprint without any copyrighted input.
        rows = (build.ROOT / 'docs/patch-manifest.tsv').read_text().replace('\\t', '\t').splitlines()
        fingerprint = next(r.split('\t')[2] for r in rows if r.startswith('romfs/nativeNXx64/archive/font_jpn.arc\t'))
        with patch.object(build, 'digest', return_value=fingerprint):
            with self.assertRaises(ValueError):
                build.validate_resources(self.base, None, 'original')

    def test_no_reuse_or_nested_output(self):
        for output in (self.base, self.base / 'nested'):
            with self.assertRaises(ValueError):
                build.prepare(self.base, None, 'original', self.settings, 'ja', output)

    def test_dry_run_and_invalid_chinese_language(self):
        output = self.root / 'prepared'
        args = ['--variant', 'original', '--base-romfs', str(self.base), '--settings', str(self.settings),
                '--language', 'en-US', '--prepare-only', str(output), '--dry-run']
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(args), 0)
        self.assertFalse(output.exists())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build.main(['--variant', 'chinese', '--base-romfs', str(self.base), '--settings', str(self.settings),
                        '--overlay-romfs', str(self.overlay), '--language', 'en-US', '--prepare-only', str(output)])

    def test_pack_commands_and_bundle_metadata(self):
        upstream = self.root / 'upstream'
        packer = upstream / 'dm/mac/pack_app.py'
        packer.parent.mkdir(parents=True)
        packer.write_text('# --resource-variant --ui-language')
        host = self.root / 'host'
        host.touch()
        shader = self.root / 'experimental.metal'
        shader.write_text('// fixture')
        inputs = []
        for key in ('patched', 'msl', 'tables', 'font'):
            directory = self.root / key
            directory.mkdir()
            inputs += ['--' + key, str(directory)]
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[1] == str(packer.resolve()):
                candidate = Path(cmd[2])
                resources = candidate / 'Contents/Resources'
                resources.mkdir(parents=True)
                settings = json.loads(Path(cmd[cmd.index('--settings') + 1]).read_text())
                self.assertEqual(next(s['default'] for s in settings['settings'] if s['env'] == 'DM_LANG'), 'en-US')
                (candidate / 'Contents/Info.plist').write_bytes(plistlib.dumps({}))
                self.assertIn('--data-id', cmd)
                self.assertEqual(cmd[cmd.index('--resource-variant') + 1], 'original')
                self.assertEqual(cmd[cmd.index('--ui-language') + 1], 'en')
        output = self.root / 'original.app'
        with patch.object(build.subprocess, 'run', side_effect=fake_run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(['--variant', 'original', '--base-romfs', str(self.base),
                '--settings', str(self.settings), '--language', 'en-US', '--output', str(output),
                '--upstream', str(upstream), '--host', str(host), '--edr-shader', str(shader)] + inputs), 0)
        self.assertTrue((output / 'Contents/Resources/hdr/720e88a17ae787f6_b.metal').exists())
        info = plistlib.loads((output / 'Contents/Info.plist').read_bytes())
        self.assertEqual(info['DMDisplayExperiment'], 'tgaa-edr-v1')
        self.assertFalse((output / 'Contents/Resources/guide.json').exists())
        self.assertEqual(calls[-1][1:4], ['--verify', '--deep', '--strict'])


if __name__ == '__main__':
    unittest.main()
