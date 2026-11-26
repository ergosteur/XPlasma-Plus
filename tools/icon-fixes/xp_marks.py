# SPDX-License-Identifier: GPL-3.0-or-later
"""XP's "disabled / disconnected" mark: a small red X in the bottom-right corner.

Drawn here (no artwork) after the X on XP's own disconnected icons: a plain
sans-serif X (two straight bars, ends cut level), a light-to-deep red vertical
gradient and a dark red outline. Used by tools/icon-expansion/build.py (tray off
states) and tools/icon-fixes/build.py (the notifications-off bell).
"""
from PIL import Image, ImageDraw

SCALE = 8
FILL_TOP, FILL_BOTTOM = (236, 84, 80), (196, 22, 26)
OUTLINE = (128, 14, 18, 255)
FRACTION = 0.5      # of the icon, bottom-right
STEM = 0.27         # horizontal width of each bar, of the X's box
EDGE = 0.07         # outline, of the X's box


def _x(mask, left, top, box, stem, grow=0):
    """The X's two bars on MASK; GROW > 0 widens them by that much all round (the outline)."""
    d = ImageDraw.Draw(mask)
    right, bottom = left + box, top + box
    # Each bar: a parallelogram from a top corner to the opposite bottom corner,
    # its ends cut level like a sans-serif X.
    for bar in ([(left, top), (left + stem, top), (right, bottom), (right - stem, bottom)],
                [(right - stem, top), (right, top), (left + stem, bottom), (left, bottom)]):
        d.polygon(bar, fill=255)
        if grow:
            d.line(bar + [bar[0]], fill=255, width=round(2 * grow), joint='curve')
            for x, y in bar:
                d.ellipse([x - grow, y - grow, x + grow, y + grow], fill=255)


def red_x(size, fraction=FRACTION):
    """An RGBA layer SIZE x SIZE with the X in its bottom-right FRACTION."""
    big = size * SCALE
    edge = max(SCALE, round(big * fraction * EDGE))
    box = big * fraction - 2 * edge
    left = top = big - box - edge
    inner = Image.new('L', (big, big), 0)
    _x(inner, left, top, box, box * STEM)
    outer = Image.new('L', (big, big), 0)
    _x(outer, left, top, box, box * STEM, grow=edge)
    gradient = Image.new('RGBA', (big, big))
    g = ImageDraw.Draw(gradient)
    for y in range(big):
        t = min(1, max(0, (y - top) / box))
        g.line([(0, y), (big, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(FILL_TOP, FILL_BOTTOM)) + (255,))
    layer = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    layer.paste(Image.new('RGBA', (big, big), OUTLINE), (0, 0), outer)
    layer.paste(gradient, (0, 0), inner)
    return layer.resize((size, size), Image.LANCZOS)


def with_red_x(image):
    """IMAGE (RGBA) with the X over its bottom-right corner, at full strength."""
    out = image.convert('RGBA').copy()
    out.alpha_composite(red_x(out.width))
    return out


def map_pin(size):
    """An XP-style map pin (location), SIZE x SIZE, styled like the red X: a
    light-to-deep red gradient, a dark red outline, and a white hole with a soft
    grey rim. XP had no location icon; this is drawn for the project."""
    import math
    big = size * SCALE
    u = big / 96
    cx, cy, r = 48 * u, 36 * u, 27 * u          # the head
    tip = (48 * u, 91 * u)                      # the point
    edge = 4.5 * u

    def pin(mask, grow):
        d = ImageDraw.Draw(mask)
        R = r + grow
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
        # the two lines from the tip tangent to the head
        dist = math.hypot(tip[0] - cx, tip[1] - cy)
        a = math.atan2(tip[1] - cy, tip[0] - cx)
        b = math.acos(R / dist)
        t1 = (cx + R * math.cos(a + b), cy + R * math.sin(a + b))
        t2 = (cx + R * math.cos(a - b), cy + R * math.sin(a - b))
        tx, ty = tip[0], tip[1] + grow * 1.2
        d.polygon([t1, (tx, ty), t2, (cx, cy)], fill=255)

    outer, inner = Image.new('L', (big, big), 0), Image.new('L', (big, big), 0)
    pin(outer, edge)
    pin(inner, 0)
    top, bottom = cy - r, tip[1]
    gradient = Image.new('RGBA', (big, big))
    g = ImageDraw.Draw(gradient)
    for y in range(big):
        t = min(1, max(0, (y - top) / (bottom - top)))
        g.line([(0, y), (big, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(FILL_TOP, FILL_BOTTOM)) + (255,))
    layer = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    layer.paste(Image.new('RGBA', (big, big), OUTLINE), (0, 0), outer)
    layer.paste(gradient, (0, 0), inner)
    d = ImageDraw.Draw(layer)
    # a soft highlight on the head's upper left, then the hole
    hl = Image.new('L', (big, big), 0)
    ImageDraw.Draw(hl).ellipse([cx - r * 0.78, cy - r * 0.86, cx + r * 0.2, cy - r * 0.05], fill=90)
    hl = Image.composite(hl, Image.new('L', (big, big), 0), inner)
    layer.paste(Image.new('RGBA', (big, big), (255, 255, 255, 255)), (0, 0), hl)
    h = 10.5 * u
    d.ellipse([cx - h - 2 * u, cy - h - 2 * u, cx + h + 2 * u, cy + h + 2 * u], fill=OUTLINE)
    d.ellipse([cx - h, cy - h, cx + h, cy + h], fill=(250, 250, 250, 255))
    return layer.resize((size, size), Image.LANCZOS)
