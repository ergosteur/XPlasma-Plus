#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a testable installer bundle from this checkout, optionally push it to a test VM.

The public repo lacks the private inputs a release carries (prebuilt runtimes,
Windows artwork, crisp fonts, user pictures). So start from an extracted official
release bundle, refresh it from this checkout with installer/sync-payload.py,
and regenerate SHA256SUMS.json so backend.verify() accepts the modified files.

  tools/dev-bundle.py --base ~/Downloads/XPlasma-Plus-1.0.3 --out /tmp/xp-dev
  tools/dev-bundle.py --base ... --out ... --push 192.168.122.59:xp-dev

Prebuilt runtimes in the base stay in place but only match the base's own native
source; a native change makes the installer build locally (build deps get installed).
"""
import argparse, importlib.util, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / 'installer'))
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', type=Path, required=True, help='extracted official release bundle (left untouched)')
    p.add_argument('--out', type=Path, required=True, help='bundle directory to (re)create')
    p.add_argument('--push', metavar='HOST:DIR', help='rsync the bundle to HOST:DIR (DIR relative to the remote home)')
    a = p.parse_args()
    base, out = a.base.resolve(), a.out.resolve()
    if not (base / 'SHA256SUMS.json').is_file() or not (base / 'payload/assets').is_dir():
        sys.exit(f'{base} is not an extracted release bundle')
    if out == base or out.is_relative_to(base) or out.is_relative_to(ROOT):
        sys.exit('--out must be outside both the base bundle and this checkout')
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(base, out, symlinks=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    load('sync_payload', ROOT / 'installer/sync-payload.py').sync(out)
    count = load('prepare_release', ROOT / 'public-alpha/prepare-release.py').inventory(out)
    commit = subprocess.run(['git', 'describe', '--always', '--dirty'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f'dev bundle {out} ({count} files) from {commit}')
    if a.push:
        host, _, remote = a.push.partition(':')
        remote = remote or 'xp-dev'
        subprocess.run(['rsync', '-a', '--delete', '--exclude', '__pycache__', f'{out}/', f'{host}:{remote}/'], check=True)
        print(f'pushed to {host}:{remote}')


if __name__ == '__main__':
    main()
