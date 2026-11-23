#!/usr/bin/python3
"""Plasma's own lock screen on the XP desktop: XP's Welcome screen as its background.

Used when the wallpaper feature is chosen and the XP lock screen isn't. Plasma's
lock screen otherwise keeps the distribution's wallpaper (Fedora's is so light
that its white text was unreadable). Only settings are written: Plasma's files are
not modified. (Its blur and tint when the prompt appears stay; the XP taskbar
theme's colours keep the tint a darkening one, see panel.cpp.)

The background is XP's Welcome screen as logonui.exe's UIFILE lays it out: the dark
top band with its light edge, the blue with its glow, the gradient bottom band with
its orange edge, composed from the bitmaps the installer ships, or plain Welcome
blue without Pillow.
"""
from pathlib import Path

WELCOME_BLUE = (0x5a, 0x7e, 0xdc)


def welcome_background(assets, out, size=(1920, 1080)):
    """XP's Welcome screen as an image. False without Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return False
    w, h = size
    top, bottom = 80, 72
    img = Image.new('RGBA', (w, h), WELCOME_BLUE + (255,))
    assets = Path(assets)
    if (assets / '100.png').is_file():
        img.alpha_composite(Image.open(assets / '100.png').convert('RGBA'), (0, top))
    img.paste((0x00, 0x30, 0x9c, 255), (0, 0, w, top))
    if (assets / '125.png').is_file():
        img.alpha_composite(Image.open(assets / '125.png').convert('RGBA').resize((w, 2), Image.Resampling.NEAREST), (0, top - 2))
    for x in range(w):   # #3934ad -> #00309c, left to right
        t = x / max(w - 1, 1)
        img.paste((round(0x39 * (1 - t)), round(0x34 - 4 * t), round(0xad - 0x11 * t), 255), (x, h - bottom, x + 1, h))
    if (assets / '126.png').is_file():
        edge = Image.open(assets / '126.png').convert('RGBA')
        img.alpha_composite(edge.crop((0, 0, edge.width, 2)).resize((w, 2), Image.Resampling.NEAREST), (0, h - bottom))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.convert('RGB').save(out)
    return True


def apply(home, templates, writer, run, log=print):
    """Point Plasma's lock screen at XP's Welcome screen. writer: kwriteconfig6."""
    image = Path(home) / '.local/share/xplasma/assets/wallpapers/xp-welcome-lock.png'

    def lock(*keys):
        *groups, key, value = keys
        args = [writer, '--file', 'kscreenlockerrc']
        for g in groups:
            args += ['--group', g]
        run(args + ['--key', key, value])

    if welcome_background(Path(templates) / 'sddm/assets', image):
        lock('Greeter', 'WallpaperPlugin', 'org.kde.image')
        lock('Greeter', 'Wallpaper', 'org.kde.image', 'General', 'Image', image.as_uri())
        lock('Greeter', 'Wallpaper', 'org.kde.image', 'General', 'FillMode', '0')   # stretched: the bands stay whole
    else:
        lock('Greeter', 'WallpaperPlugin', 'org.kde.color')
        lock('Greeter', 'Wallpaper', 'org.kde.color', 'General', 'Color', ','.join(map(str, WELCOME_BLUE)))
    log('Lock screen: XP Welcome background.')
