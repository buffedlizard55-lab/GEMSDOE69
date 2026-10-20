#!/usr/bin/env python3
"""Retired entry point: do not synthesize validation evidence or rewrite history.

The former implementation could fill in missing feature AUCs, reuse an older
holdout and mark validators successful after a failed subprocess. That is not a
scientific experiment. Its artifacts are quarantined, not automatically rebased
onto new code. See evidence/integrity_review.json and HANDOFF.md.

This compatibility command deliberately does not import the model, read data,
write a TIFF, edit evidence, or spend a competition slot.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        'BLOCKED — unsafe legacy generator retired. No files changed. '
        'Literal duplicate-and-stop remains binding. Read HANDOFF.md and '
        'evidence/integrity_review.json; use scripts/release_gate.py to audit '
        'publication status. Missing holdout results or canaries must be '
        'measured, never filled in or borrowed from another artifact.',
        file=sys.stderr,
    )
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
