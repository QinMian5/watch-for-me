#!/usr/bin/env python3
"""Validate a bundle's source_map.json and project only its source_map.md reading copy."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_bundle import build_reader_copy, main

if __name__ == "__main__":
    raise SystemExit(main(build_artifacts=build_reader_copy, description=__doc__))
