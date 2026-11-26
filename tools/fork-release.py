#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build this fork's release installer from the checked-out commit.

  tools/fork-release.py --base ~/Downloads/XPlasma-Plus-1.0.3 --out DIR

The base is upstream's extracted *generic* 1.0.3 release (it carries the private
inputs: Windows artwork, fonts, the Firefox payload). The version comes from
installer/edition.json and the notes from public-alpha/RELEASE-NOTES-<version>.md.
The checkout must be clean, so the archive is exactly a commit you can tag.

Writes DIR/bundle (the release tree) and DIR/out (the .tar.gz and SHA256SUMS),
using tools/dev-bundle.py, prepare-release.py's inventory and package.py, which
verifies every file inside the archive. Then: test DIR/out/*.tar.gz with
tools/vm-test.sh --bundle, tag the commit, and publish both files.
"""
import argparse, importlib.util, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / 'installer'))
    spec.loader.exec_module(module)
    return module


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True, text=True).stdout.strip()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', type=Path, required=True, help="upstream's extracted generic release")
    p.add_argument('--out', type=Path, required=True, help='work directory (bundle/ and out/ are replaced)')
    p.add_argument('--allow-dirty', action='store_true', help='for a trial build only: the archive will not match a commit')
    a = p.parse_args()
    if git('status', '--porcelain', '--untracked-files=no') and not a.allow_dirty:
        sys.exit('The checkout has uncommitted changes; commit them (or pass --allow-dirty for a trial build).')
    edition = json.loads((ROOT / 'installer/edition.json').read_text())
    version, repository = edition['version'], edition['repository']
    notes = ROOT / f'public-alpha/RELEASE-NOTES-{version}.md'
    if not notes.is_file():
        sys.exit(f'{notes.relative_to(ROOT)} is missing.')
    commit = git('rev-parse', 'HEAD')
    out = a.out.resolve()
    bundle = out / 'bundle'

    subprocess.run([sys.executable, str(ROOT / 'tools/dev-bundle.py'), '--base', str(a.base), '--out', str(bundle)], check=True)
    (bundle / 'RELEASE-NOTES.md').write_text(notes.read_text())
    (bundle / 'BUILD-PROVENANCE.json').write_text(json.dumps({
        'release': version, 'variant': 'generic', 'source_commit': commit, 'source_repository': repository,
        'base_release': 'andymenard/XPlasma-Plus 1.0.3 generic (assets and Firefox payload)',
        'prebuilt': [], 'compatibility_validations': [], 'ota_included': False}, indent=2) + '\n')
    (bundle / 'RELEASE-STAGING.json').write_text(json.dumps({'version': version, 'variant': 'generic'}, indent=2) + '\n')
    print('manifest entries:', load('prepare_release', ROOT / 'public-alpha/prepare-release.py').inventory(bundle))
    load('package', ROOT / 'public-alpha/package.py').package(bundle, out / 'out', 'generic')
    print(f'{version} from {commit[:7]}: {out / "out"}')


if __name__ == '__main__':
    main()
