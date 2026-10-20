#!/usr/bin/env python3
"""Compatibility entry point for the single fail-closed run-card writer.

By default it refuses to replace a card for different bytes. A completed,
artifact-bound pipeline may make that intent explicit with
``--replace-artifact-bound-card``.
"""
import json
import sys

from release_gate import write_card

_ALLOWED = {"--replace-artifact-bound-card"}

if __name__ == "__main__":
    args = set(sys.argv[1:])
    if not args.issubset(_ALLOWED):
        print("Usage: make_run_card.py [--replace-artifact-bound-card]", file=sys.stderr)
        raise SystemExit(2)
    try:
        print(json.dumps(
            write_card(replace="--replace-artifact-bound-card" in args)["release_policy"],
            indent=2,
        ))
    except ValueError as exc:
        print(f"Run card unchanged: {exc}", file=sys.stderr)
        raise SystemExit(2)
