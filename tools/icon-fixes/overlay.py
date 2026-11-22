#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run build.py and keep what it changed in XPlasma Primary as an overlay.

The native desktop apply writes XPlasma Primary (~/.local/share/icons/xplasma-icons)
from scratch on every look change, which would drop these fixes. So the changes
build.py makes there are captured into ~/.local/share/icons/xplasma-fixes:

  <size>/<context>/<name>.<ext>   files and symlinks to put in Primary (replacing
                                  that name in any extension)
  REMOVED.txt                     Primary paths to remove, one per line
  index.theme                     [<size>/<context>] sections Primary must list

The native apply merges it into Primary after writing it (icons.cpp
mergeIconOverlay). Symlinks keep their targets: the overlay sits beside Primary,
so relative links into xplasma-xp-extended resolve the same from both.
build.py's changes to xplasma-xp-extended stay where they are (the native apply
doesn't rewrite that layer).

  python3 -I overlay.py [build.py options]
"""
import configparser, hashlib, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICONS = Path.home() / '.local/share/icons'
PRIM, OVERLAY = ICONS / 'xplasma-icons', ICONS / 'xplasma-fixes'


def entries(root):
    """relative path -> ('link', target) | ('file', sha256) for every icon in an icon theme."""
    out = {}
    for path in root.glob('*x*/*/*'):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            out[rel] = ('link', os.readlink(path))
        elif path.is_file():
            out[rel] = ('file', hashlib.sha256(path.read_bytes()).hexdigest())
    return out


def sections(index):
    parser = configparser.RawConfigParser(strict=False)
    parser.optionxform = str
    parser.read(index)
    return parser


def main():
    if not (PRIM / 'index.theme').is_file():
        sys.exit('XPlasma Primary is not installed; nothing to fix')
    before = entries(PRIM)
    index_before = sections(PRIM / 'index.theme')
    subprocess.run([sys.executable, '-I', str(HERE / 'build.py'), *sys.argv[1:]], check=True)
    if '--dry-run' in sys.argv:
        return
    after = entries(PRIM)
    index_after = sections(PRIM / 'index.theme')

    # On a reinstall Primary already had the last overlay merged in, so build.py
    # finds less to change: what that overlay held and is still in place (or still
    # removed) stays in the new one.
    old = entries(OVERLAY) if OVERLAY.is_dir() else {}
    old_removed = set((OVERLAY / 'REMOVED.txt').read_text().split()) if (OVERLAY / 'REMOVED.txt').is_file() else set()

    fresh = OVERLAY.with_name(OVERLAY.name + '.new')
    if fresh.exists():
        shutil.rmtree(fresh)
    fresh.mkdir(parents=True)
    changed = sorted({rel for rel, value in after.items() if before.get(rel) != value} | (set(old) & set(after)))
    for rel in changed:
        src, dst = PRIM / rel, fresh / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
        else:
            shutil.copy2(src, dst)
    removed = sorted({rel for rel in before if rel not in after} | {rel for rel in old_removed if rel not in after})
    (fresh / 'REMOVED.txt').write_text(''.join(r + '\n' for r in removed))
    # Directory sections to carry: the ones Primary declares now (after build.py and the
    # pack's own repair added theirs) that changed files sit in. A file in a directory
    # Primary doesn't declare is never looked up; declaring it here would change that.
    import re
    match = re.search(r'^Directories=(.*)$', (PRIM / 'index.theme').read_text(), re.M)
    declared = set(match.group(1).split(',')) if match else set()
    out = configparser.RawConfigParser()
    out.optionxform = str
    dirs = sorted({str(Path(rel).parent) for rel in changed} & declared)
    for d in dirs:
        out.add_section(d)
        source = index_after[d] if index_after.has_section(d) else None
        size = d.split('x')[0]
        out.set(d, 'Size', source.get('Size', size) if source else size)
        out.set(d, 'Context', source.get('Context', d.split('/')[1].capitalize()) if source else d.split('/')[1].capitalize())
        out.set(d, 'Type', source.get('Type', 'Fixed') if source else 'Fixed')
    with (fresh / 'index.theme').open('w') as f:
        f.write('# XPlasma icon fixes: merged into XPlasma Primary by the desktop apply (see overlay.py)\n')
        out.write(f, space_around_delimiters=False)
    if OVERLAY.exists():
        shutil.rmtree(OVERLAY)
    fresh.rename(OVERLAY)
    print(f'icon fixes overlay: {len(changed)} icons, {len(removed)} removals, {len(dirs)} directories -> {OVERLAY}')


if __name__ == '__main__':
    main()
