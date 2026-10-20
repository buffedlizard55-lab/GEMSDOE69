#!/usr/bin/env python3
"""Enforce recorded duplicate stops before legacy model/generation commands.

Audits, validators, source research and site regeneration remain available. This
is not a new evaluator and has no --force escape hatch. A changed interpretation
of the user's protocol cannot be introduced as a silent density exemption.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stop_reasons(root=ROOT):
    root = Path(root)
    reasons = []
    for filename in ('e3_uniqueness.json', 'registry-blocker.json'):
        try:
            doc = json.loads((root / 'evidence' / filename).read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        literal = doc.get('literal_gate', {})
        if (isinstance(literal, dict) and (literal.get('overlap_ok') is False or literal.get('rho_ok') is False)) or doc.get('stop_required') is True:
            reasons.append(f'{filename}: literal duplicate-and-stop is recorded')
    try:
        review = json.loads((root / 'evidence' / 'integrity_review.json').read_text())
    except (OSError, ValueError):
        review = {}
    if isinstance(review, dict) and review.get('status') == 'quarantined':
        reasons.append('integrity_review.json: scientific evidence is quarantined')
    return reasons


def require_open_lane(root=ROOT):
    reasons = stop_reasons(root)
    if reasons:
        raise SystemExit('BLOCKED before model work: ' + '; '.join(reasons) + '. See HANDOFF.md. No new raster or experiment was produced.')


if __name__ == '__main__':
    require_open_lane()
    print('No recorded stop. This is not a holdout or publication clearance.')
