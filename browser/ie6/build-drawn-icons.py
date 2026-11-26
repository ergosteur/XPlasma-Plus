#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser icons drawn for this project rather than taken from the XP pack:
location.png, the map pin (tools/icon-fixes/xp_marks.py). Run
build-blocked-icons.py and build-icon-wrappers.py afterwards."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'tools/icon-fixes'))
import xp_marks  # noqa: E402

xp_marks.map_pin(96).save(ROOT / 'chrome/ie6-icons/location.png', optimize=True)
print('location.png: map pin')
