#!/usr/bin/env python3
"""Deprecated compatibility entrypoint for the single fail-closed site builder."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site69 import main as build_site69_main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(build_site69_main())
