#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Re-render only the tray state icons (off/disabled marks, pause, record, badges)
of an already built layer, with build.py's current drawing code.

A full build.py run maps the build machine's installed Breeze and applications,
so rebuilding the whole layer elsewhere changes far more than the tray marks.
This keeps everything else byte for byte:

    python3 retouch-tray-states.py PACK.zip LAYER_DIR

LAYER_DIR is an extracted xplasma-xp-extended (e.g. from icons.tar.gz).
Re-run audit.py on it afterwards, as for a build.
"""
import json, re, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

SIZES = [16, 22, 24, 32, 48, 64, 128]


def main(pack, layer):
    layer = Path(layer)
    mappings = json.loads((layer / 'ALIAS-PROVENANCE.json').read_text())
    z = zipfile.ZipFile(pack)
    rendered, relinked, written = {}, 0, set()
    for name, item in mappings.items():
        if item['reason'] in {'control-glyph', 'xp-styled-kde-glyph', 'specialized-glyph'} or 'source' not in item:
            continue
        if not item['source'].startswith('Windows XP High Resolution Icon Pack/'):
            continue
        state = build.tray_state(name, item)
        normalized = re.sub(r'(-symbolic|-rtl)+$', '', name.lower())   # matches build.tray_variant()'s normalization
        old_off = bool(re.search(r'-(paused|stop)$', normalized)) and normalized in build.TRAY_ROLES
        if not any(state) and not old_off:
            continue   # a plain picture: untouched
        canonical = build.tray_canonical(item['source'], *state)
        for size in SIZES:
            for dest in (layer / f'{size}x{size}').glob(f'*/{name}.png'):
                path = dest.parent / canonical
                key = (item['source'], size) + state
                if key not in rendered:
                    rendered[key] = build.tray_image(z, item['source'], size, *state)
                if path not in written:
                    rendered[key].save(path)
                    written.add(path)
                if not dest.is_symlink() or dest.readlink().name != canonical:
                    dest.unlink()
                    dest.symlink_to(canonical)
                    relinked += 1
    # Canonical files nothing links to any more (e.g. the old slashed pause).
    linked = {p.resolve() for p in layer.rglob('*.png') if p.is_symlink()}
    removed = 0
    for p in layer.rglob('xp-*.png'):
        if not p.is_symlink() and p.resolve() not in linked:
            p.unlink()
            removed += 1
    print(f'{len(written)} tray images re-rendered, {relinked} names relinked, {removed} unused images removed')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
