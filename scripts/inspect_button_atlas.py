#!/usr/bin/env python3
"""Decode the single-mip BC7 button atlas in MT Framework Switch TEX files.

The byte order follows the Switch block-linear layout used by nxnative.
This is an inspection tool and does not alter game files.
"""
from pathlib import Path
import argparse
import struct

from build_controller_overlays import entries, plain


def deswizzle(tex):
    if tex[:4] != b'TEX\0' or tex[13] != 0x2a:
        raise ValueError('expected BC7 Switch TEX')
    info = struct.unpack_from('<I', tex, 8)[0]
    mipcount, width, height = info & 63, (info >> 6) & 8191, info >> 19
    if mipcount != 1 or width != 512 or height != 512:
        raise ValueError((mipcount, width, height))
    source = tex[24:]
    size = width * height
    if len(source) != size:
        raise ValueError('unexpected payload length')
    out = bytearray()
    indices = []
    start = 0
    step = height * 16 - 0x100
    blocknum = 0
    while start < step:
        pos = start
        while pos < size:
            for offset in (0, 0x20, 0x100, 0x120):
                out.extend(source[pos + offset:pos + offset + 16])
                indices.append(pos + offset)
            pos += 0x100 + step
        blocknum += 1
        start += (0x130 if blocknum == 8 else 0x10 if blocknum & 1 else 0x30)
        if blocknum == 8:
            blocknum = 0
    if len(out) != size:
        raise ValueError(f'deswizzle produced {len(out)} bytes, expected {size}')
    if len(set(indices)) != size // 16:
        raise ValueError('swizzle is not a permutation')
    return bytes(out)


def swizzle(blocks):
    """Reverse deswizzle, keeping the original file's 24-byte header separate."""
    if len(blocks) != 262144:
        raise ValueError('expected 512x512 BC7 payload')
    source = bytearray(len(blocks))
    read = 0
    start = 0
    step = 512 * 16 - 0x100
    blocknum = 0
    while start < step:
        pos = start
        while pos < len(source):
            for offset in (0, 0x20, 0x100, 0x120):
                source[pos + offset:pos + offset + 16] = blocks[read:read + 16]
                read += 16
            pos += 0x100 + step
        blocknum += 1
        start += (0x130 if blocknum == 8 else 0x10 if blocknum & 1 else 0x30)
        if blocknum == 8:
            blocknum = 0
    return bytes(source)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('name')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    entry = next(x for x in entries(args.archive.read_bytes()) if x[1].endswith(args.name))
    tex = plain(entry[2], entry[3])
    blocks = deswizzle(tex)
    # The TEX format byte 0x2a stores BC7 blocks for this game. A DX10 DDS
    # header lets Pillow inspect the actual pixels and glyph positions.
    header = bytearray(128)
    header[:4] = b'DDS '
    struct.pack_into('<I', header, 4, 124)
    struct.pack_into('<I', header, 8, 0x000A1007)
    struct.pack_into('<II', header, 12, 512, 512)
    struct.pack_into('<I', header, 20, len(blocks))
    struct.pack_into('<I', header, 76, 32)
    struct.pack_into('<I', header, 80, 4)
    header[84:88] = b'DX10'
    struct.pack_into('<I', header, 108, 0x1000)
    args.output.write_bytes(header + struct.pack('<5I', 98, 3, 0, 1, 0) + blocks)


if __name__ == '__main__':
    main()
