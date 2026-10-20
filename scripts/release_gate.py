#!/usr/bin/env python3
"""Single fail-closed publication policy; never reinterpret the literal protocol.

This is orchestration, not a replacement for the pinned scientific evaluator.
Receipts are evidence to check, not permission to invent missing measurements.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CHECKS = (
    'single_band', 'dtype_float32', 'crs_epsg_32611', 'shape_3730x3292',
    'transform_and_bounds_match_sample_submission', 'footprint_all_finite',
    'footprint_values_in_0_1', 'nan_only_outside_footprint', 'no_infinite_values',
    'all_finite_values_in_0_1', 'template_validator_passed',
    'no_positive_outside_footprint', 'zero_positive_on_mapped_catalogue', 'no_sentinel_values',
)


def read(root, name):
    try:
        obj = json.loads((Path(root) / 'evidence' / name).read_text())
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def finite_number(value, low=0.0, high=1.0):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def positive_count(value):
    return type(value) is int and value > 0


def interval(value, *, positive=False):
    return (isinstance(value, list) and len(value) == 2
            and all(finite_number(x, -1.0 if positive else 0.0) for x in value)
            and value[0] <= value[1] and (not positive or value[0] > 0))


def local_file(root, relative):
    if not isinstance(relative, str) or not relative:
        return None
    try:
        path = (root / relative).resolve()
        return path if path.is_relative_to(root) and path.is_file() else None
    except (OSError, ValueError, RuntimeError):
        return None


def object_dict(value):
    return value if isinstance(value, dict) else {}


def evaluate(root=ROOT):
    root = Path(root).resolve()
    gate = read(root, 'e2_gate.json')
    uniq = read(root, 'e3_uniqueness.json')
    receipt = read(root, 'e3_receipt.json')
    reasons = []
    if gate.get('gate_passed') is not True:
        reasons.append('Holdout improvement gate failed or is missing.')
    if gate.get('current_best_beaten') is not True:
        reasons.append('No explicit same-evaluator evidence of beating the current holdout best.')

    # Do not accept a pass flag in contradiction to its numeric evidence.
    statistics = gate.get('release_statistics', {})
    stats_ok = (isinstance(statistics, dict)
                and statistics.get('aggregation') == 'pooled_tp_fp_fn'
                and isinstance(statistics.get('evaluator_version'), str)
                and bool(statistics.get('evaluator_version'))
                and positive_count(statistics.get('withheld_positive_pixel_evaluations')))
    if stats_ok:
        for arm in ('candidate', 'control', 'current_best'):
            value, ci = statistics.get(arm + '_dti'), statistics.get(arm + '_ci95')
            stats_ok = stats_ok and finite_number(value) and interval(ci)
            if finite_number(value) and interval(ci):
                stats_ok = stats_ok and ci[0] <= value <= ci[1]
        stats_ok = (stats_ok and statistics['candidate_dti'] > statistics['control_dti']
                    and statistics['candidate_dti'] > statistics['current_best_dti']
                    and interval(statistics.get('delta_vs_control_ci95'), positive=True)
                    and interval(statistics.get('delta_vs_current_best_ci95'), positive=True)
                    and statistics.get('uncertainty_unit') == 'spatial_block')
    if not stats_ok:
        reasons.append('Pooled HOLDOUT-DTI, spatial-block confidence intervals, or a positive current-best contrast are unverified.')

    literal = object_dict(uniq.get('literal_gate'))
    if not isinstance(literal, dict) or literal.get('rho_ok') is not True or literal.get('overlap_ok') is not True:
        reasons.append('Literal registry uniqueness gate failed or is missing; duplicate-and-stop applies. Stratified diagnostics cannot clear it.')
    rho = uniq.get('worst_abs_spearman')
    overlap = uniq.get('worst_dot_overlap_all', {})
    overlap = overlap.get('dot_overlap_3px') if isinstance(overlap, dict) else None
    if not finite_number(rho, 0, .90) or not finite_number(overlap, 0, .70):
        reasons.append('Measured full-registry correlation/overlap is missing, non-finite, or exceeds the literal limits.')
    expected = uniq.get('n_registry_blobs')
    if (not positive_count(expected) or uniq.get('n_compared') != expected
            or type(uniq.get('n_compared')) is not int
            or uniq.get('n_errors') != 0 or type(uniq.get('n_errors')) is not int):
        reasons.append('Registry scan is incomplete or contains errors.')
    if object_dict(uniq.get('local_prior_overlap')).get('ok') is False:
        reasons.append('A local prior emission triggers duplicate-and-stop.')

    raster = object_dict(object_dict(receipt.get('raster')).get('zeros'))
    path = local_file(root, raster.get('path'))
    sha = sha256_file(path) if path else None
    if sha is None or sha != raster.get('sha256'):
        reasons.append('Artifact is missing or does not match its recorded SHA-256.')
    if sha is None or uniq.get('my_sha256') != sha:
        reasons.append('Registry result is not bound to the current artifact hash.')
    if sha is None or gate.get('artifact_sha256') != sha:
        reasons.append('Holdout comparison is missing or not bound to the current artifact hash.')

    manifest = read(root, 'e3_method_manifest.json')
    hashes = manifest.get('source_sha256', {})
    source_ok = isinstance(hashes, dict) and bool(hashes) and sha is not None and manifest.get('artifact_sha256') == sha
    if source_ok:
        for rel, digest in hashes.items():
            source = local_file(root, rel)
            if source is None or sha256_file(source) != digest:
                source_ok = False
                break
    if not source_ok:
        reasons.append('Reproducible method source manifest is missing, stale, or not artifact-bound.')
    if manifest.get('catalogue_features_visible_only') is not True:
        reasons.append('Visible-only catalogue derivation is not certified; full-catalogue holdout flank masks are not allowed.')
    geology = manifest.get('geological_requirements', {})
    if not isinstance(geology, dict) or not all(geology.get(k) is True for k in (
            'source_polylines_used', 'same_dip_verified', 'releasing_slip_sense_verified')):
        reasons.append('Source polylines, same-dip pairing, and releasing slip sense are not verified for this artifact.')

    canaries = read(root, 'e1_canaries.json')
    features = manifest.get('feature_names', [])
    canary_ok = (isinstance(features, list) and bool(features)
                 and canaries.get('artifact_sha256') == sha and sha is not None
                 and canaries.get('measurement_origin') == 'computed_holdout')
    if canary_ok:
        for feature in features:
            row = canaries.get(feature, {}) if isinstance(feature, str) else {}
            if not isinstance(row, dict) or not finite_number(row.get('auc'), 0, .90):
                canary_ok = False
                break
    if not canary_ok:
        reasons.append('Computed, artifact-bound feature-alone leakage canaries are missing, unverified, or flagged.')

    reports = object_dict(receipt.get('validator')).get('reports', [])
    report = next((r for r in reports if isinstance(r, dict) and r.get('sha256') == sha and sha is not None), {}) if isinstance(reports, list) else {}
    checks = report.get('checks', {})
    if (report.get('all_checks_passed') is not True or not isinstance(checks, dict)
            or not all(checks.get(k) is True for k in REQUIRED_CHECKS)):
        reasons.append('Hash-bound validator receipt is missing or failed.')

    for phase in ('surface', 'dots'):
        evidence = read(root, f'e3_uniqueness_{phase}.json')
        data = object_dict(object_dict(evidence.get('phases')).get(phase))
        summary = object_dict(data.get('summary'))
        if summary.get('candidate_file_sha256') != sha or sha is None:
            reasons.append(f'{phase} uniqueness phase is missing or not bound to the current artifact.')
        literal_phase = object_dict(object_dict(data.get('two_phase')).get('literal_reading'))
        phase_rho, phase_overlap = summary.get('worst_spearman_full_footprint'), summary.get('worst_dot_overlap')
        # Older receipts contain internally contradictory summaries. Inspect the
        # literal measurements too; an edited stop_required flag cannot clear them.
        phase_ok = (summary.get('stop_required') is False and summary.get('unique') is True
                    and summary.get('complete_accessible_scan') is True
                    and summary.get('registry_rasters_expected') == expected
                    and summary.get('registry_rasters_checked') == expected
                    and type(summary.get('registry_rasters_expected')) is int
                    and type(summary.get('registry_rasters_checked')) is int
                    and summary.get('missing_or_invalid') == 0
                    and type(summary.get('missing_or_invalid')) is int
                    and positive_count(expected)
                    and finite_number(phase_rho, -.90, .90)
                    and finite_number(phase_overlap, 0, .70)
                    and literal_phase.get('duplicate') is not True)
        if 'worst_forward_overlap' in literal_phase:
            phase_ok = phase_ok and finite_number(literal_phase['worst_forward_overlap'], 0, .70)
        if not phase_ok:
            reasons.append(f'{phase} uniqueness phase failed, contradicts its literal measurements, or is incomplete.')
    surface = read(root, 'e3_uniqueness_surface.json')
    if surface.get('completed_before_placement') is not True:
        reasons.append('The surface uniqueness check is not evidenced as completed before placement.')

    fresh = read(root, 'registry-blocker.json')
    if fresh.get('stop_required') is True and (fresh.get('candidate_sha256') == sha
            or fresh.get('registry_covers_entire_footprint') is True):
        reasons.append('Fresh pinned-prior measurement reproduces the literal duplicate-and-stop counterexample.')
    local = read(root, 'local-prior-audit.json')
    if local.get('candidate_sha256') == sha and sha:
        for row in local.get('rows', []) if isinstance(local.get('rows'), list) else []:
            if isinstance(row, dict) and (row.get('exact_bytes_equal') is True
                    or row.get('exact_footprint_pixels_equal') is True
                    or (finite_number(row.get('dots_within_3px')) and row['dots_within_3px'] > .70)):
                reasons.append('Fresh local-prior comparisons independently fail the literal overlap or identity rule, including sparse fields.')
                break
    for field in ('submission_name', 'submission_note'):
        value = receipt.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 140:
            reasons.append(f'{field} is missing or exceeds 140 characters; no silent truncation is allowed.')

    review = read(root, 'integrity_review.json')
    reviewed_hashes = review.get('artifact_sha256', [])
    if review.get('status') == 'quarantined' and isinstance(reviewed_hashes, list) and sha in reviewed_hashes:
        reasons.append('Artifact evidence is quarantined by the integrity review; a new hash or rebinding old receipts cannot clear it.')

    return dict(policy_version='gems69-literal-release-v3', verdict='negative' if reasons else 'promote',
                download_enabled=not reasons, reasons=reasons, artifact_sha256=sha, validator_report=report)


def write_card(root=ROOT, *, replace=False):
    """Refresh one artifact's audit card; never silently cross-bind candidates.

    A deliberate cross-candidate replacement first archives the complete prior
    card. Explicit replacement never changes any scientific release gate.
    """
    root = Path(root).resolve()
    decision = evaluate(root)
    gate, uniq, receipt = (read(root, n) for n in ('e2_gate.json', 'e3_uniqueness.json', 'e3_receipt.json'))
    sha = decision['artifact_sha256']
    if sha is None or gate.get('artifact_sha256') != sha:
        raise ValueError('Refusing to rewrite run_card.json: holdout is not bound to the receipt artifact SHA-256.')
    previous = read(root, 'run_card.json')
    old_sha = object_dict(object_dict(previous.get('raster')).get('zeros')).get('sha256') or previous.get('raster_sha256')
    if old_sha and old_sha != sha:
        if not replace:
            raise ValueError('Refusing to rewrite run_card.json: existing run card identifies a different artifact; use explicit replacement.')
        old_file = root / 'evidence/run_card.json'
        archive = old_file.with_name('run_card_archived_' + sha256_file(old_file) + '.json')
        if not archive.exists():
            archive.write_bytes(old_file.read_bytes())
    statistics = object_dict(gate.get('release_statistics'))
    certified = decision['download_enabled']
    fresh = read(root, 'registry-blocker.json')
    local = read(root, 'local-prior-audit.json')
    fresh_validator = read(root, 'validator-audit-2026-10-20.json')
    fresh_reports = fresh_validator.get('reports', [])
    latest_format = next((r for r in fresh_reports if isinstance(r, dict)
        and r.get('sha256') == decision['artifact_sha256']), {}) if isinstance(fresh_reports, list) else {}
    mean, half = gate.get('corridor_mean_dti'), gate.get('corridor_ci95_half')
    mean = mean if finite_number(mean) else None
    half = half if finite_number(half) else None
    claim_ci = [mean - half, mean + half] if finite_number(mean) and finite_number(half) else None
    card = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        lane='GEMSDOE69 relay-ramp and pull-apart corridors',
        hypothesis=receipt.get('hypothesis_id'),
        mechanism='Archived H69-J uses min of independent corridor-mean gravity and magnetic evidence maxima, magnetic lows, scarp magnitude, orientation and geometry priors. It does not test paired transverse tilt-zero crossings.',
        non_fault_mimic='Intrusive lithologic contacts and sedimentary basin margins can produce coincident gravity and magnetic edges; pluvial shorelines can mimic lidar scarps.',
        holdout=dict(evidence_class='HOLDOUT-DTI',
            dti=statistics.get('candidate_dti') if certified else None,
            ci95=statistics.get('candidate_ci95') if certified else None,
            evaluator_version=statistics.get('evaluator_version') if certified else gate.get('evaluator'),
            withheld_positive_pixel_evaluations=gate.get('withheld_positive_px_total'),
            unique_withheld_positive_pixels=None,
            status=('Gate-qualified pooled holdout; not an organizer score' if certified else
                    'NOT CERTIFIED: archived measurements were not rerun; current-best and provenance claims are not sufficient'),
            archived_claim=dict(mean_of_cells_dti=mean, ci95=claim_ci,
                control_mean_dti=gate.get('control_mean_dti'),
                uncertainty='Normal approximation across repeated cells, not independent spatial-block uncertainty; not a pooled statistic')),
        correlation_overlap_vs_registry=dict(evidence_class='REGISTRY-MEASUREMENT',
            scope=uniq.get('registry_scope'), worst_abs_spearman=uniq.get('worst_abs_spearman'),
            worst_literal_overlap=object_dict(uniq.get('worst_dot_overlap_all')).get('dot_overlap_3px'),
            literal_gate=uniq.get('literal_gate'),
            archived_scope_warning='The summary statistics above are archival and not certified; use the fresh partial measurements below.',
            fresh_counterexample=dict(report='registry-blocker.json',
                compared=fresh.get('compared_this_review'), registry_index_entries=fresh.get('registry_index_entries'),
                exhaustive_scan=fresh.get('exhaustive_scan'), spearman=fresh.get('full_footprint_spearman'),
                forward_overlap_3px=fresh.get('candidate_dots_within_3px')),
            local_prior_forward_overlap_max=local.get('max_dot_overlap_3px'),
            warning='Archived phase summaries contradict their own literal readings. No all-prior uniqueness clearance is claimed.'),
        raster=receipt.get('raster', {}), raster_sha256=decision['artifact_sha256'],
        validator_output=latest_format or decision['validator_report'],
        validator_output_source='evidence/validator-audit-2026-10-20.json' if latest_format else 'evidence/e3_receipt.json',
        submission_name=receipt.get('submission_name'),
        submission_note=str(receipt.get('submission_note', 'Archived audit candidate; DO NOT SUBMIT')),
        verdict=decision['verdict'], banner='ok' if decision['download_enabled'] else 'stop',
        submission_slots_used=0, scientific_experiments_this_review=0,
        note='Negative audit delivery. No new TIFF, no portal upload, no score projection. Literal duplicate-and-stop is binding.',
        release_policy=decision,
    )
    (root / 'evidence' / 'run_card.json').write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    return card


if __name__ == '__main__':
    # Audit CLI has no write side effects. Site/card writers are explicit.
    print(json.dumps(evaluate(ROOT), indent=2, allow_nan=False))
