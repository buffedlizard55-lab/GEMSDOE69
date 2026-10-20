#!/usr/bin/env python3
"""One fail-closed publication policy. Does not change the shared scientific template.

Archived measurements are never recomputed or silently reinterpreted here.
The literal user protocol takes precedence over stratified diagnostics.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(root, name):
    path = root / 'evidence' / name
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _finite_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _positive_ci(value):
    """True only for a finite paired mean with a fully positive 95% CI."""
    if not isinstance(value, dict):
        return False
    ci = value.get('ci95')
    mean = value.get('mean')
    if not isinstance(ci, list) or len(ci) != 2:
        return False
    lo, hi = ci
    return (_finite_number(mean) and _finite_number(lo) and _finite_number(hi)
            and mean > 0 and lo > 0 and hi >= lo)


def _holdout_protocol_ok(root, audit, gate, artifact_sha):
    """Verify a hash-bound audit of the required whole-segment holdout protocol."""
    if not isinstance(audit, dict) or not isinstance(artifact_sha, str) or len(artifact_sha) != 64:
        return False
    if (audit.get('evidence_class') != 'HOLDOUT-PROTOCOL-AUDIT'
            or audit.get('artifact_sha256') != artifact_sha
            or audit.get('evaluator') != gate.get('evaluator')
            or audit.get('compliant') is not True
            or audit.get('whole_fault_segments_withheld') is not True
            or audit.get('segment_chunking') is not False
            or audit.get('catalogue_features_from_visible_faults_only') is not True
            or audit.get('visible_fault_mask_pixel_exact') is not True
            or audit.get('pooled_dti') is not True
            or not _finite_number(audit.get('alpha')) or audit.get('alpha') != 0.2
            or not _finite_number(audit.get('beta')) or audit.get('beta') != 0.8
            or audit.get('kernel') != 'triangular'
            or audit.get('radius_m') != 300):
        return False
    buffer_px = audit.get('withheld_context_buffer_px')
    if not isinstance(buffer_px, int) or isinstance(buffer_px, bool) or buffer_px < 3:
        return False
    source_hashes = audit.get('source_sha256')
    if not isinstance(source_hashes, dict) or not source_hashes:
        return False
    root = Path(root).resolve()
    for rel, digest in source_hashes.items():
        if not isinstance(rel, str) or not isinstance(digest, str):
            return False
        source = (root / rel).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            return False
        try:
            if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                return False
        except OSError:
            return False
    return True


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
    evaluator = gate.get('evaluator')
    if gate.get('evidence_class') != 'HOLDOUT-DTI' or not isinstance(evaluator, str) or not evaluator.strip():
        reasons.append('A versioned HOLDOUT-DTI evaluator record is missing.')
    if not _positive_int(gate.get('withheld_positive_px_total')):
        reasons.append('The HOLDOUT-DTI withheld-positive count is missing or invalid.')
    if not _positive_int(gate.get('n_cells')):
        reasons.append('The HOLDOUT-DTI spatial-cell count is missing or invalid.')
    paired = gate.get('paired_cell_bootstrap')
    paired = paired if isinstance(paired, dict) else {}
    control_ci = (paired.get('candidate_minus_control')
                  or paired.get('transfer_minus_control'))
    current_best_ci = (paired.get('candidate_minus_current_best')
                       or paired.get('transfer_minus_current_best'))
    control_ci_ok = _positive_ci(control_ci)
    current_best_ci_ok = _positive_ci(current_best_ci)
    if not control_ci_ok:
        reasons.append('No positive paired HOLDOUT-DTI 95% CI is recorded against the no-prior control.')
    if not current_best_ci_ok:
        reasons.append('No positive paired HOLDOUT-DTI 95% CI is recorded against the current lane-best candidate.')
    literal = uniq.get('literal_gate', {})
    literal = literal if isinstance(literal, dict) else {}
    # The standing protocol says a literal rho OR dot-overlap threshold firing
    # means duplicate-and-stop. Stratified/dotlike diagnostics are useful for
    # explaining a firing, but are not authorized to override it.
    rho_ok = literal.get('rho_ok') is True
    overlap_ok = literal.get('overlap_ok') is True
    if not rho_ok:
        reasons.append('Registry rank-correlation gate failed (rho >0.90); duplicate-and-stop applies.')
    if not overlap_ok:
        reasons.append('Literal registry dot-overlap gate failed or is missing; duplicate-and-stop applies. Stratified/dotlike diagnostics cannot override the literal protocol.')
    expected = uniq.get('n_registry_blobs')
    compared = uniq.get('n_compared')
    errors = uniq.get('n_errors')
    if (not _positive_int(expected) or not isinstance(compared, int) or isinstance(compared, bool)
            or compared != expected or not isinstance(errors, int) or isinstance(errors, bool)
            or errors != 0):
        reasons.append('Registry scan is incomplete or contains errors.')
    if receipt.get('evidence_class') != 'SUBMISSION-RECEIPT':
        reasons.append('A correctly classified submission artifact receipt is missing.')
    receipt_raster = receipt.get('raster')
    receipt_raster = receipt_raster if isinstance(receipt_raster, dict) else {}
    raster = receipt_raster.get('zeros')
    raster = raster if isinstance(raster, dict) else {}
    relpath = raster.get('path')
    path = (root / relpath).resolve() if isinstance(relpath, str) else root / '__missing_artifact__'
    try:
        sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() and path.is_relative_to(root.resolve()) else None
    except OSError:
        sha = None
    if sha is None or sha != raster.get('sha256'):
        reasons.append('Artifact is missing or does not match its recorded SHA-256.')
    if sha is None or uniq.get('my_sha256') != sha:
        reasons.append('Registry result is not bound to the current artifact hash.')
    # Restored from merged H69-E policy: a holdout from another candidate
    # must never authorize these bytes (tests/test_release_gate.py).
    if sha is None or gate.get('artifact_sha256') != sha:
        reasons.append('Holdout comparison is missing or not bound to the current artifact hash.')
    protocol_audit = read(root, 'e2_holdout_protocol_audit.json')
    protocol_ok = _holdout_protocol_ok(root, protocol_audit, gate, sha)
    if not protocol_ok:
        reasons.append('A compliant, artifact-bound whole-segment holdout protocol audit is missing or failed.')
    manifest = read(root, 'e3_method_manifest.json')
    source_hashes = manifest.get('source_sha256', {})
    source_hashes = source_hashes if isinstance(source_hashes, dict) else {}
    source_ok = bool(source_hashes) and manifest.get('artifact_sha256') == sha and sha is not None
    for rel, digest in source_hashes.items():
        if not isinstance(rel, str) or not isinstance(digest, str):
            source_ok = False
            continue
        source = (root / rel).resolve()
        source_ok = source_ok and source.is_relative_to(root.resolve()) and source.is_file()
        if source_ok:
            try:
                source_ok = hashlib.sha256(source.read_bytes()).hexdigest() == digest
            except OSError:
                source_ok = False
    if not source_ok:
        reasons.append('Reproducible method source manifest is missing, stale, or not artifact-bound.')
    canaries = read(root, 'e1_canaries.json')
    features = manifest.get('feature_names', [])
    features = features if isinstance(features, list) and all(isinstance(f, str) for f in features) else []
    canary_ok = bool(features) and canaries.get('artifact_sha256') == sha and sha is not None
    for feature in features:
        feature_record = canaries.get(feature, {})
        auc = feature_record.get('auc') if isinstance(feature_record, dict) else None
        canary_ok = canary_ok and _finite_number(auc) and 0 <= auc <= 0.90
    if not canary_ok:
        reasons.append('Artifact-bound feature-alone leakage canaries are missing or flagged.')
    validator = receipt.get('validator')
    validator = validator if isinstance(validator, dict) else {}
    reports = validator.get('reports', [])
    reports = reports if isinstance(reports, list) else []
    report = next((r for r in reports if isinstance(r, dict) and r.get('sha256') == sha and sha is not None), {})
    checks = report.get('checks', {})
    checks = checks if isinstance(checks, dict) else {}
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
        phases = evidence.get('phases', {})
        phases = phases if isinstance(phases, dict) else {}
        phase_record = phases.get(phase, {})
        phase_record = phase_record if isinstance(phase_record, dict) else {}
        summary = phase_record.get('summary', {})
        summary = summary if isinstance(summary, dict) else {}
        if summary.get('candidate_file_sha256') != sha or sha is None:
            reasons.append(f'{phase} uniqueness phase is missing or not bound to the current artifact.')
        if summary.get('stop_required') is not False or summary.get('complete_accessible_scan') is not True:
            reasons.append(f'{phase} uniqueness phase failed or is incomplete.')
    return dict(verdict='negative' if reasons else 'eligible_for_selector', download_enabled=not reasons,
                reasons=reasons, artifact_sha256=sha, validator_report=report,
                paired_ci_control_passed=control_ci_ok,
                paired_ci_current_best_passed=current_best_ci_ok,
                holdout_protocol_compliant=protocol_ok,
                receipt_evidence_class=receipt.get('evidence_class'))


def write_card(root=ROOT, *, replace: bool = False):
    """Write a run card only for an explicitly bound, non-cross-candidate run.

    ``replace`` is intentionally opt-in: callers conducting a genuinely new,
    fully artifact-bound E2/E3 run must make the replacement decision explicit.
    """
    root = Path(root)
    card = read(root, 'run_card.json')
    decision = evaluate(root)
    gate = read(root, 'e2_gate.json')
    uniq = read(root, 'e3_uniqueness.json')
    receipt = read(root, 'e3_receipt.json')
    # A card generator must never silently replace one candidate's narrative
    # with another candidate's aggregate holdout. This was the historic
    # H69-J/H69-H2 merge failure. First bind E2 to the receipt bytes; then,
    # if an existing card names other bytes, require an explicit replacement.
    sha = decision.get('artifact_sha256')
    if sha is None or gate.get('artifact_sha256') != sha:
        raise ValueError(
            'Refusing to rewrite run_card.json: holdout is not bound to the receipt artifact SHA-256.'
        )
    existing_sha = card.get('raster', {}).get('zeros', {}).get('sha256')
    if existing_sha and existing_sha != sha and not replace:
        raise ValueError(
            'Refusing to rewrite run_card.json: existing run card identifies a different artifact; '
            'use an explicit artifact-bound replacement procedure.'
        )
    card.update(generated_utc=datetime.now(timezone.utc).isoformat(),
                verdict=decision['verdict'], banner='ok' if decision['download_enabled'] else 'stop',
                release_policy=decision,
                note='Literal protocol enforced. No submission slot used. Archived measurements are not organizer scores.')
    card['hypothesis'] = ('H69-J: convergent multi-scale HG+tilt edge phase across relay connectors (H1)')
    card['mechanism'] = ('Tip-graph corridor proposals scored by joint grav+mag HG and tilt coincidence (AND logic, min(E_grav,E_mag) 0.35), mag low gated by joint, lidar scarp, N-NE orientation, pull-apart prior; greedy marginal-DTI placement. Targets buried relay linkage between step-over tips separating basement blocks.')
    card['non_fault_mimic'] = ('Intrusive contacts and sedimentary basin margins can produce coincident gravity/magnetic edges without faulting; pluvial shorelines can mimic lidar scarps. Joint evidence does not rule out these processes.')
    mean, half = gate.get('corridor_mean_dti'), gate.get('corridor_ci95_half')
    card['holdout'] = dict(evidence_class='HOLDOUT-DTI', evaluator_version=gate.get('evaluator'),
        dti=mean, ci95=[mean-half, mean+half] if isinstance(mean, (int, float)) and isinstance(half, (int, float)) else None,
        withheld_positive_pixels=gate.get('withheld_positive_px_total'), n_cells=gate.get('n_cells'),
        comparator_dti=gate.get('control_mean_dti'), paired_delta=gate.get('paired_delta_mean'),
        paired_cell_bootstrap=gate.get('paired_cell_bootstrap'),
        uncertainty_note='Archived normal-approximation interval across repeated cells; not an independent block bootstrap. Paired 95% CIs are separately recorded above; not rerun this session.')
    card['correlation_overlap_vs_registry'] = uniq
    card['raster'] = receipt.get('raster', {})
    card['validator_output'] = decision['validator_report']
    card['submission_name'] = receipt.get('submission_name')
    card['submission_note'] = receipt.get('submission_note', '')[:140]
    (root / 'evidence' / 'run_card.json').write_text(json.dumps(card, indent=2) + '\n')
    return card


if __name__ == '__main__':
    # Audit-only command: never rewrite the committed run card from legacy inputs.
    # Rebuilding a card requires an explicit, artifact-bound evidence-generation run.
    print(json.dumps(evaluate(ROOT), indent=2))
