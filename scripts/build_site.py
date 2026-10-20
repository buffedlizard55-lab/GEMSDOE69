#!/usr/bin/env python3
"""Compatibility entry point for the fail-closed GEMSDOE69 site builder.

The older builder published an archived TIFF even for negative verdicts and
used stratified diagnostics to waive literal duplicate firings. Keep the
historical command name, but delegate every render to the current release-gated
builder so it cannot create a second, less strict publication path.
"""
from __future__ import annotations

from build_site69 import main


if __name__ == "__main__":
    raise SystemExit(main())
