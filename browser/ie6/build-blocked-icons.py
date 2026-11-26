#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blocked-permission icons: each NAME-blocked.png is NAME.png with a red slash.

The slash is drawn here (GPL code, no artwork): a red bar with a white border,
bottom-left to top-right, anti-aliased by drawing at 8x and scaling down. Run
build-icon-wrappers.py afterwards for the sized/*.svg wrappers.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ICONS = ROOT / 'chrome/ie6-icons'
RED, WHITE = (212, 0, 0, 255), (255, 255, 255, 255)
SCALE = 8


def slash(size):
    """The slash as an RGBA layer of SIZE x SIZE (designed on a 96 px grid)."""
    big = size * SCALE
    u = big / 96
    layer = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    start, end = (20 * u, 79 * u), (78 * u, 21 * u)
    for colour, width in ((WHITE, 14 * u), (RED, 8 * u)):
        draw.line([start, end], fill=colour, width=round(width))
        for x, y in (start, end):   # round ends
            r = width / 2
            draw.ellipse([x - r, y - r, x + r, y + r], fill=colour)
    return layer.resize((size, size), Image.LANCZOS)


def main():
    made = []
    for blocked in sorted(ICONS.glob('*-blocked.png')):
        base = ICONS / blocked.name.replace('-blocked', '')
        if not base.is_file():
            continue
        image = Image.open(base).convert('RGBA')
        image.alpha_composite(slash(image.width))
        image.save(blocked, optimize=True)
        made.append(blocked.name)
    print(f'{len(made)} blocked icons: ' + ', '.join(made))


if __name__ == '__main__':
    main()
