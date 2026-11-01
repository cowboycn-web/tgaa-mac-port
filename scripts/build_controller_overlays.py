#!/usr/bin/env python3
"""Experimental button glyph overlay builder; do not package its output yet.

Input must be the Chinese-patched RomFS. Using the unpatched Japanese font ARC
as a whole-file overlay removes 11 Chinese-patched members from font_jpn.arc
and causes missing characters. Preserving those members fixes that symptom,
but the PC button GUI still does not produce correct keyboard prompts, and the
PlayStation candidate has not passed an in-game display check.
"""
from pathlib import Path
import argparse
import struct
import zlib


def entries(data):
    if data[:4] != b"ARC\0" or struct.unpack_from("<H", data, 4)[0] != 7:
        raise ValueError("expected MT Framework ARC version 7")
    count = struct.unpack_from("<H", data, 6)[0]
    result = []
    for i in range(count):
        pos = 8 + i * 0x90
        name = data[pos:pos + 128].split(b"\0")[0].decode("latin-1")
        csize, marked_size, offset = struct.unpack_from("<3I", data, pos + 0x84)
        size = marked_size & 0x1fffffff
        packed = data[offset:offset + csize]
        if len(packed) != csize:
            raise ValueError(f"truncated entry {name}")
        result.append((pos, name, packed, size, marked_size & ~0x1fffffff))
    return result


def plain(packed, size):
    result = packed if len(packed) == size else zlib.decompress(packed)
    if len(result) != size:
        raise ValueError("entry size mismatch")
    return result


def replace_gui(source, destination, target):
    data = source.read_bytes()
    catalog = entries(data)
    suffix = {"xbox": "button_one", "ps": "button_ps4", "keyboard": "button_pc"}[target]
    original = next((e for e in catalog if e[1].endswith("\\button_swi")), None)
    alternative = next((e for e in catalog if e[1].endswith("\\" + suffix)), None)
    if not original or not alternative:
        raise ValueError(f"missing button GUI in {source}")
    replacement = plain(alternative[2], alternative[3])
    if suffix.encode() not in replacement:
        raise ValueError(f"wrong texture reference in {source}")
    # Keep every original member at its original offset. Other resources in this
    # archive can refer to those offsets; repacking the whole archive made Chinese
    # text glyphs disappear even though every zlib stream still decompressed.
    out = bytearray(data)
    packed = zlib.compress(replacement)
    struct.pack_into("<3I", out, original[0] + 0x84, len(packed), original[4] | len(replacement), len(out))
    out.extend(packed)
    check = entries(out)
    changed = next(e for e in check if e[1] == original[1])
    if plain(changed[2], changed[3]) != replacement:
        raise ValueError("overlay verification failed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(out)


def replace_texture(source, destination, target):
    data = source.read_bytes()
    catalog = entries(data)
    suffix = {"xbox": "button_one", "ps": "button_ps4", "keyboard": "button_pc"}[target]
    original = next(e for e in catalog if e[1].endswith("\\button_swi_00_ID_HQ"))
    alternative = next(e for e in catalog if e[1].endswith("\\" + suffix + "_00_ID_HQ"))
    replacement = plain(alternative[2], alternative[3])
    if replacement[:24] != plain(original[2], original[3])[:24]:
        raise ValueError('texture header mismatch')
    out = bytearray(data)
    packed = zlib.compress(replacement)
    struct.pack_into("<3I", out, original[0] + 0x84, len(packed), original[4] | len(replacement), len(out))
    out.extend(packed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(out)


def replace_mapped_texture(source, destination, target):
    from inspect_button_atlas import deswizzle, swizzle
    data = source.read_bytes()
    catalog = entries(data)
    suffix = {"xbox": "button_one", "ps": "button_ps4"}[target]
    original = next(e for e in catalog if e[1].endswith("\\button_swi_00_ID_HQ"))
    alternative = next(e for e in catalog if e[1].endswith("\\" + suffix + "_00_ID_HQ"))
    orig_tex = plain(original[2], original[3])
    alt_tex = plain(alternative[2], alternative[3])
    if orig_tex[:24] != alt_tex[:24]:
        raise ValueError('texture header mismatch')
    # Game asks for the Switch semantic A/B/X/Y slots. Xbox and PlayStation
    # atlases put their face buttons in B/A/Y/X and circle/cross/triangle/square
    # order, so exchange each neighboring 64-pixel cell in the first row.
    blocks = bytearray(deswizzle(alt_tex))
    original_blocks = bytes(blocks)
    pitch = 512 // 4
    cell = 64 // 4
    for dst, src in ((0, 1), (1, 0), (2, 3), (3, 2)):
        for row in range(cell):
            a = (row * pitch + dst * cell) * 16
            b = (row * pitch + src * cell) * 16
            blocks[a:a + cell * 16] = original_blocks[b:b + cell * 16]
    replacement = orig_tex[:24] + swizzle(blocks)
    out = bytearray(data)
    packed = zlib.compress(replacement)
    struct.pack_into("<3I", out, original[0] + 0x84, len(packed), original[4] | len(replacement), len(out))
    out.extend(packed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(out)


def replace_keyboard_texture(source, destination, key_slots, pc_texture="button_pc_00_ID_HQ"):
    from inspect_button_atlas import deswizzle, swizzle
    data = source.read_bytes()
    catalog = entries(data)
    original = next(e for e in catalog if e[1].endswith("\\button_swi_00_ID_HQ"))
    alternative = next(e for e in catalog if e[1].endswith("\\" + pc_texture))
    orig_tex = plain(original[2], original[3])
    pc_tex = plain(alternative[2], alternative[3])
    if orig_tex[:24] != pc_tex[:24]:
        raise ValueError('texture header mismatch')
    blocks = bytearray(deswizzle(orig_tex))
    pc = deswizzle(pc_tex)
    pitch, cell = 512 // 4, 64 // 4
    for dest_row, dest_col, key_row, key_col in key_slots:
        for row in range(cell):
            a = ((dest_row * cell + row) * pitch + dest_col * cell) * 16
            b = ((key_row * cell + row) * pitch + key_col * cell) * 16
            blocks[a:a + cell * 16] = pc[b:b + cell * 16]
    replacement = orig_tex[:24] + swizzle(blocks)
    out = bytearray(data)
    packed = zlib.compress(replacement)
    struct.pack_into("<3I", out, original[0] + 0x84, len(packed), original[4] | len(replacement), len(out))
    out.extend(packed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("romfs", type=Path, help="extracted original RomFS directory")
    parser.add_argument("output", type=Path, help="output controller-overlays directory")
    args = parser.parse_args()
    for style in ("xbox", "ps", "keyboard"):
        for lang in ("jpn", "eng"):
            rel = Path("nativeNXx64/archive") / f"font_{lang}.arc"
            replace_gui(args.romfs / rel, args.output / style / rel, style)
            print(style, rel)
    for style in ("xbox", "ps", "keyboard"):
        for lang in ("jpn", "eng"):
            rel = Path("nativeNXx64/archive") / f"font_{lang}.arc"
            replace_texture(args.romfs / rel, args.output / (style + '-texture') / rel, style)
            print(style + '-texture', rel)
    for style in ("xbox", "ps"):
        for lang in ("jpn", "eng"):
            rel = Path("nativeNXx64/archive") / f"font_{lang}.arc"
            replace_mapped_texture(args.romfs / rel, args.output / (style + '-mapped') / rel, style)
            print(style + '-mapped', rel)
    # First-pass keyboard atlas for the default macOS mapping. Keep separate
    # from packaged builds until its in-game placement has been checked.
    keyboard_slots = [(0, 0, 3, 2), (0, 1, 3, 3), (0, 2, 2, 0), (0, 3, 2, 1)]
    for lang in ("jpn", "eng"):
        rel = Path("nativeNXx64/archive") / f"font_{lang}.arc"
        replace_keyboard_texture(args.romfs / rel, args.output / "keyboard-mapped" / rel, keyboard_slots)
        print('keyboard-mapped', rel)


if __name__ == "__main__":
    main()
