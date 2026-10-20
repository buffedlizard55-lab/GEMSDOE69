#!/usr/bin/env python3
"""One fail-closed publication policy. Does not change the shared scientific template.

Archived measurements are never recomputed or silently reinterpreted here.
The literal user protocol takes precedence over stratified diagnostics.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(root, name):
    path = root / 'evidence' / name
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def evaluate(root=ROOT):
    root = Path(root)
    gate = read(root, 'e2_gate.json')
    uniq = read(root, 'e3_uniqueness.json')
    receipt = read(root, 'e3_receipt.json')
    reasons = []
    if gate.get('gate_passed') is not True:
        reasons.append('Holdout improvement gate failed or is missing.')
    if gate.get('current_best_beaten') is not True:
        reasons.append('No explicit same-evaluator evidence of beating the current holdout best.')
    literal = uniq.get('literal_gate', {})
    if literal.get('rho_ok') is not True or literal.get('overlap_ok') is not True:
        reasons.append('Literal registry uniqueness gate failed or is missing; duplicate-and-stop applies.')
    if not uniq.get('n_registry_blobs') or uniq.get('n_compared') != uniq.get('n_registry_blobs') or uniq.get('n_errors') != 0:
        reasons.append('Registry scan is incomplete or contains errors.')
    raster = receipt.get('raster', {}).get('zeros', {})
    path = (root / raster.get('path', '')).resolve()
    sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() and path.is_relative_to(root.resolve()) else None
    if sha is None or sha != raster.get('sha256'):
        reasons.append('Artifact is missing or does not match its recorded SHA-256.')
    if sha is None or uniq.get('my_sha256') != sha:
        reasons.append('Registry result is not bound to the current artifact hash.')
    # A successful holdout from another candidate must never authorize these
    # bytes (union port from merged H69-E session's stricter policy).
    if sha is None or gate.get('artifact_sha256') != sha:
        reasons.append('Holdout comparison is missing or not bound to the current artifact hash.')
    manifest = read(root, 'e3_method_manifest.json')
    source_hashes = manifest.get('source_sha256', {})
    source_ok = bool(source_hashes) and manifest.get('artifact_sha256') == sha and sha is not None
    for rel, digest in source_hashes.items():
        source = (root / rel).resolve()
        source_ok = source_ok and source.is_relative_to(root.resolve()) and source.is_file()
        if source_ok:
            source_ok = hashlib.sha256(source.read_bytes()).hexdigest() == digest
    if not source_ok:
        reasons.append('Reproducible method source manifest is missing, stale, or not artifact-bound.')
    canaries = read(root, 'e1_canaries.json')
    features = manifest.get('feature_names', [])
    canary_ok = bool(features) and canaries.get('artifact_sha256') == sha and sha is not None
    for feature in features:
        auc = canaries.get(feature, {}).get('auc')
        canary_ok = canary_ok and isinstance(auc, (int, float)) and 0 <= auc <= 0.90
    if not canary_ok:
        reasons.append('Artifact-bound feature-alone leakage canaries are missing or flagged.')
    reports = receipt.get('validator', {}).get('reports', [])
    report = next((r for r in reports if r.get('sha256') == sha and sha is not None), {})
    checks = report.get('checks', {})
    required = ('single_band', 'dtype_float32', 'crs_epsg_32611', 'shape_3730x3292',
                'transform_and_bounds_match_sample_submission', 'footprint_all_finite',
                'footprint_values_in_0_1', 'nan_only_outside_footprint', 'no_infinite_values',
                'all_finite_values_in_0_1', 'template_validator_passed')
    if report.get('all_checks_passed') is not True or not all(checks.get(k) is True for k in required):
        reasons.append('Hash-bound validator receipt is missing or failed.')
    # The separate phase files in this checkout refer to older candidates. Do not
    # let a newer aggregate receipt borrow their two-phase clearance.
    for phase in ('surface', 'dots'):
        evidence = read(root, f'e3_uniqueness_{phase}.json')
        summary = evidence.get('phases', {}).get(phase, {}).get('summary', {})
        if summary.get('candidate_file_sha256') != sha or sha is None:
            reasons.append(f'{phase} uniqueness phase is missing or not bound to the current artifact.')
        if summary.get('stop_required') is not False or summary.get('complete_accessible_scan') is not True:
            reasons.append(f'{phase} uniqueness phase failed or is incomplete.')
    return dict(verdict='negative' if reasons else 'promote', download_enabled=not reasons,
                reasons=reasons, artifact_sha256=sha, validator_report=report)


def write_card(root=ROOT):
    root = Path(root)
    card = read(root, 'run_card.json')
    decision = evaluate(root)
    gate = read(root, 'e2_gate.json')
    uniq = read(root, 'e3_uniqueness.json')
    receipt = read(root, 'e3_receipt.json')
    card.update(generated_utc=datetime.now(timezone.utc).isoformat(),
                verdict=decision['verdict'], banner='ok' if decision['download_enabled'] else 'stop',
                release_policy=decision,
                note='Literal protocol enforced. No submission slot used. Archived measurements are not organizer scores.')
    card['hypothesis'] = ('H69-H2 transfer-only: oblique-connector corridors at overlapping (transfer) '
                          'step-overs from the repaired catalogue tip graph (R1 interval offset, R2 546 px search) '
                          'rank hidden breaching faults; tested 2026-10-20 under preregistered Exp1+Exp2b.')
    card['mechanism'] = ('Repaired tip-graph pairs (W 0.1-15 km, separation <=3.5W) restricted to '
                         'non-dilatational transfer-overlap pairs; corridors scored v1 by gravity/magnetic HG+tilt, '
                         'magnetic lows, lidar scarp and N-NE orientation; greedy marginal-DTI dots >=200 m off catalogue.')
    card['non_fault_mimic'] = ('Restraining-overlap pressure ridges and pluvial shoreline scarps mimic breaching-fault '
                              'lineaments; lithologic contacts mimic subsurface steps. Slip sense/dip remain strike proxies.')
    mean, half = gate.get('corridor_mean_dti'), gate.get('corridor_ci95_half')
    card['holdout'] = dict(evidence_class='HOLDOUT-DTI', evaluator_version=gate.get('evaluator'),
        dti=mean, ci95=[mean-half, mean+half] if isinstance(mean, (int, float)) and isinstance(half, (int, float)) else None,
        withheld_positive_pixels=gate.get('withheld_positive_px_total'), n_cells=gate.get('n_cells'),
        comparator_dti=gate.get('control_mean_dti'), paired_delta=gate.get('paired_delta_mean'),
        uncertainty_note='Fresh 2026-10-20 run: pooled DTI primary (evidence/e2_gate.json pooled_dti + paired cell-bootstrap); mean+-half retained for site compatibility. Holdout is a screen, never a leaderboard projection.')
    card['correlation_overlap_vs_registry'] = uniq
    card['raster'] = receipt.get('raster', {})
    card['validator_output'] = decision['validator_report']
    card['submission_name'] = receipt.get('submission_name')
    card['submission_note'] = receipt.get('submission_note', '')[:140]
    (root / 'evidence' / 'run_card.json').write_text(json.dumps(card, indent=2) + '\n')
    return card


if __name__ == '__main__':
    print(json.dumps(write_card()['release_policy'], indent=2))
