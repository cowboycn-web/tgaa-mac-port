"""Native regression checks for original-resource overlays; no game data needed."""
import ctypes
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'upstream/nxnative/dm/mac/button_atlas.c'


@unittest.skipUnless(sys.platform == 'darwin' and SOURCE.exists(), 'Requires patched nxnative source on macOS')
class OriginalOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='tgaa-overlay-regression-')
        cls.addClassCleanup(cls.build.cleanup)
        library = Path(cls.build.name) / 'overlay.dylib'
        subprocess.run(['xcrun', 'clang', '-dynamiclib', str(SOURCE), '-lz', '-o', str(library)],
                       check=True, capture_output=True)
        cls.library = ctypes.CDLL(str(library))
        cls.overlay = cls.library.dm_mac_button_overlay
        cls.overlay.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p]
        cls.overlay.restype = ctypes.c_int

    def test_original_switch_succeeds_and_removes_stale_chinese_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resources = root / 'resources'
            resources.mkdir()
            output = root / 'overlay'
            archive = output / 'nativeNXx64/archive'
            archive.mkdir(parents=True)
            for name in ('font_jpn.arc', 'font_eng.arc', 'msg_sys_jpn.arc'):
                (archive / name).write_bytes(b'stale overlay fixture')
            self.assertEqual(self.overlay(bytes(resources), bytes(output), 1, None), 1)
            self.assertEqual(list(archive.iterdir()), [])
            self.assertEqual(self.overlay(bytes(resources), bytes(output), 1, None), 1)

    def test_chinese_optional_message_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resources = root / 'resources'
            source = resources / 'button_source/msg_sys_jpn.arc'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'cleaned message fixture')
            output = root / 'overlay'
            self.assertEqual(self.overlay(bytes(resources), bytes(output), 1, None), 1)
            self.assertEqual((output / 'nativeNXx64/archive/msg_sys_jpn.arc').read_bytes(), source.read_bytes())

    def test_output_failure_is_not_reported_as_a_valid_empty_overlay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resources = root / 'resources'
            resources.mkdir()
            output = root / 'not-a-directory'
            output.touch()
            self.assertEqual(self.overlay(bytes(resources), bytes(output), 1, None), 0)


if __name__ == '__main__':
    unittest.main()
