# SPDX-License-Identifier: GPL-3.0-or-later
"""XP's "disabled / disconnected" mark: a small red X in the bottom-right corner.

Drawn here (no artwork) after the X on XP's own disconnected icons: chunky arms
that flare slightly toward their ends, a bright-to-deep red fill and a dark red
outline. Used by tools/icon-expansion/build.py (tray off states) and
tools/icon-fixes/build.py (the notifications-off bell).
"""
from PIL import Image, ImageDraw

SCALE = 8
FILL_TOP, FILL_BOTTOM = (240, 72, 64), (190, 16, 16)
OUTLINE = (110, 8, 8, 255)


def _arm(cx, cy, length, near, far, angle):
    """A bar through (cx, cy) at ANGLE, NEAR wide in the middle and FAR at the ends."""
    import math
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = -dy, dx
    half = length / 2
    pts = []
    for end, side in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        x = cx + dx * half * end + px * far / 2 * side
        y = cy + dy * half * end + py * far / 2 * side
        pts.append((x, y))
    mid = [(cx + px * near / 2, cy + py * near / 2), (cx - px * near / 2, cy - py * near / 2)]
    # end1-left, end1-right, mid-right, end2-right, end2-left, mid-left
    return [pts[0], pts[1], mid[1], pts[2], pts[3], mid[0]]


def red_x(size, fraction=0.56):
    """An RGBA layer SIZE x SIZE with the X in its bottom-right FRACTION."""
    import math
    big = size * SCALE
    box = big * fraction
    left, top = big - box, big - box
    cx, cy = left + box / 2, top + box / 2
    length = box * 0.98
    near, far = box * 0.22, box * 0.30
    edge = max(SCALE * 1.0, box * 0.07)

    def shape(grow):
        mask = Image.new('L', (big, big), 0)
        d = ImageDraw.Draw(mask)
        for angle in (math.pi / 4, -math.pi / 4):
            d.polygon(_arm(cx, cy, length + grow, near + grow, far + grow, angle), fill=255)
        return mask

    outer, inner = shape(edge * 2), shape(0)
    gradient = Image.new('RGBA', (big, big))
    gd = ImageDraw.Draw(gradient)
    for y in range(big):
        t = min(1, max(0, (y - top) / box))
        gd.line([(0, y), (big, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(FILL_TOP, FILL_BOTTOM)) + (255,))
    layer = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    layer.paste(Image.new('RGBA', (big, big), OUTLINE), (0, 0), outer)
    layer.paste(gradient, (0, 0), inner)
    return layer.resize((size, size), Image.LANCZOS)


def with_red_x(image):
    """IMAGE (RGBA) with the X over its bottom-right corner, at full strength."""
    out = image.convert('RGBA').copy()
    out.alpha_composite(red_x(out.width))
    return out
