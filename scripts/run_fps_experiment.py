#!/usr/bin/env python3
"""Run a bounded TGAA experiment with copied saves; never alter installed code.

Frame timing is performance evidence, not proof of correct animation speed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fps', type=int, choices=(30, 60), required=True)
    p.add_argument('--resolution', choices=('720', '1080', '1440', '2160'), default='1080')
    p.add_argument('--app', type=Path, default=Path.home() / 'Applications/大逆转裁判 1&2 SDR-EDR体验版.app')
    p.add_argument('--save', type=Path, default=ROOT / 'local-data/native4k-test/save')
    p.add_argument('--timeout', type=int, default=240)
    p.add_argument('--motion', action='store_true', help='Capture dialogue progression at matched wall-clock intervals')
    p.add_argument('--step-one', action='store_true', help='Experimental: halve the fixed engine update step (60 FPS only)')
    p.add_argument('--target-only', action='store_true', help='Keep the 30 Hz time base; change only the target render rate')
    args = p.parse_args()
    if (args.step_one or args.target_only) and args.fps != 60:
        p.error('Experimental rate options require --fps 60')
    resources = args.app / 'Contents/Resources'
    recipe = json.loads((ROOT / 'patches/tgaa-60fps-experiment.json').read_text())
    source = resources / 'dm/main.patched.bin'
    original = source.read_bytes()
    fixups = (resources / 'dm/main.fixups.tsv').read_text()
    if recipe['build_id'] not in fixups:
        raise SystemExit('Build ID does not match the experiment')
    offset = int(recipe['offset'], 16)
    before, after = bytes.fromhex(recipe['before']), bytes.fromhex(recipe['after'])
    if original[offset:offset + len(before)] != before:
        raise SystemExit('Original instructions differ; refusing to patch')
    if args.step_one and original[0x2eb4c8:0x2eb4cc] != bytes.fromhex('e8030232'):
        raise SystemExit('Unexpected update-step instruction')
    if not args.save.is_dir():
        raise SystemExit('An isolated test save directory is required')
    out = ROOT / 'local-data/fps-test' / f'{time.time_ns()}-{args.resolution}p-{args.fps}fps'
    out.mkdir(parents=True)
    shutil.copytree(resources / 'dm', out / 'dm')
    shutil.copytree(args.save, out / 'save')
    (out / 'temp').mkdir()
    patched = bytearray(original)
    if args.fps == 60:
        patched[offset:offset + len(after)] = after
        if args.target_only:
            patched[offset:offset + 4] = before[:4]
    if args.step_one:
        # The initializer writes 2.0f to engine+0x583c8; two call sites copy
        # that field to engine+0x84. Its timing semantics remain experimental.
        patched[0x2eb4c8:0x2eb4cc] = bytes.fromhex('08f0a752')
    (out / 'dm/main.patched.bin').write_bytes(patched)
    control = out / 'control.txt'
    control.touch()
    env = {k: v for k, v in os.environ.items() if not k.startswith('DM_')}
    env.update(DM_TGAA_RESOLUTION=args.resolution, DM_OPMODE='0',
               DM_ROMFS=str(resources / 'romfs.img'), DM_SAVE=str(out / 'save'),
               DM_TEMP=str(out / 'temp'), DM_MSL_DIR=str(resources / 'msl'),
               DM_NVN_SHMAP=str(out / 'dm/shader_map.tsv'), DM_CTL=str(control))
    # Match elapsed frame time between runs; startup pauses still require review.
    steps = [(700, '.5x.68'), (1100, '.5x.77'), (1500, '.5x.55'), (1700, '.37x.68')]
    factor = args.fps // 30
    env['DM_KEYS'] = ','.join(f'f{frame * factor}:T{xy}' for frame, xy in steps)
    screenshot = out / 'gameplay.png'
    env['DM_NVN_SHOT'] = f'{2200 * factor}:{screenshot}'
    log = out / 'run.log'
    print(out, flush=True)
    reason = 'timeout'
    motion_events = []
    with log.open('w') as stream:
        proc = subprocess.Popen([str(args.app / 'Contents/MacOS/dmhost'), str(out / 'dm')],
                                env=env, stdout=stream, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + args.timeout
            captured = None
            while proc.poll() is None and time.monotonic() < deadline:
                if screenshot.exists():
                    captured = captured or time.monotonic()
                    if time.monotonic() - captured > 15:
                        if args.motion:
                            start = time.monotonic()
                            with control.open('a', buffering=1) as commands:
                                commands.write('A\n')
                                for delay in (.25, .5, 1, 2, 4):
                                    time.sleep(max(0, start + delay - time.monotonic()))
                                    target = out / f'motion-{delay:g}s.png'
                                    commands.write(f'shot {target}\n')
                                    motion_events.append(dict(request_seconds=time.monotonic() - start,
                                                              screenshot=target.name))
                                time.sleep(1)
                        reason = 'capture-complete'
                        break
                time.sleep(1)
            if proc.poll() is not None:
                reason = 'process-exited'
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    unchanged = hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(original).digest()
    report = dict(fps=args.fps, resolution=args.resolution, step_one=args.step_one,
                  target_only=args.target_only, reason=reason,
                  returncode=proc.returncode, installed_binary_unchanged=unchanged,
                  screenshot_exists=screenshot.exists(), animation_speed_validated=False,
                  motion_events=motion_events)
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    if not unchanged or reason != 'capture-complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
