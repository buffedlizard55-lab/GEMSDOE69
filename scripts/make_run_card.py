#!/usr/bin/env python3
"""Compatibility entry point for the single fail-closed run-card writer.

It refuses, rather than mutates, when E2 and E3 refer to different artifacts.
"""
import json
import sys

from release_gate import write_card

if __name__ == "__main__":
    try:
        print(json.dumps(write_card()["release_policy"], indent=2))
    except ValueError as exc:
        print(f"Run card unchanged: {exc}", file=sys.stderr)
        raise SystemExit(2)
