#!/usr/bin/env python3
"""Exercise the actual loader patch against the independently tested 4K recipe."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'upstream/nxnative/dm/host/loader.c').read_text()
function = source[source.index('static void tgaa_resolution('):source.index('// Seal the code area')]
prefix = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define LOG(...) ((void)0)
#define die(...) exit(17)
typedef struct { char *name, *build_id; } module_t;
static unsigned tw, th;
void dm_touch_resolution(unsigned w, unsigned h) { tw=w; th=h; }
'''
main = r'''
int main(int argc, char **argv) {
    FILE *f=fopen(argv[1], "rb"); if (!f) return 1;
    fseek(f,0,SEEK_END); size_t n=ftell(f); rewind(f);
    uint8_t *b=malloc(n); if (fread(b,1,n,f)!=n) return 2; fclose(f);
    module_t m={"main","d871b992e95b71c541ddc834f63c664b"};
    tgaa_resolution(&m,b,n);
    f=fopen(argv[2],"wb"); fwrite(b,1,n,f); fclose(f);
    printf("%u %u", tw, th);
}
'''
binary = Path.home() / 'Applications/大逆转裁判 1&2 SDR-EDR体验版.app/Contents/Resources/dm/main.patched.bin'
pristine = binary.read_bytes()
recipe = json.loads((ROOT / 'patches/tgaa-4k-experiment.json').read_text())
expected = bytearray(pristine)
for cut in recipe['cuts']:
    off = int(cut['offset'], 16)
    before, after = bytes.fromhex(cut['before']), bytes.fromhex(cut['after'])
    assert expected[off:off+len(before)] == before
    expected[off:off+len(after)] = after
with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    c, exe, out = folder/'check.c', folder/'check', folder/'out.bin'
    c.write_text(prefix + function + main)
    subprocess.run(['clang', str(c), '-o', str(exe)], check=True)
    for choice, dimensions in [('720','1280 720'),('1080','1920 1080'),
                               ('1440','2560 1440'),('2160','3840 2160')]:
        env = dict(os.environ, DM_TGAA_RESOLUTION=choice)
        result = subprocess.check_output([exe, binary, out], env=env).decode()
        assert result == dimensions
        patched = out.read_bytes()
        if choice == '2160':
            assert patched == expected, '4K patch differs from the tested experiment'
        else:
            for off in [0x603b68, 0x603b78, 0x1c8a0]:
                assert patched[off:off+4] == pristine[off:off+4]
    corrupt = folder/'corrupt.bin'
    damaged = bytearray(pristine)
    damaged[0x603b68] ^= 1
    corrupt.write_bytes(damaged)
    assert subprocess.run([exe, corrupt, out], env=env).returncode == 17
print('PASS: 4K matches tested recipe; all touch sizes match; lower modes preserve allocation code; unexpected bytes rejected')
