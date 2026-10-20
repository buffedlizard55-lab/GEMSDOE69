#!/usr/bin/env python3
"""Fail-closed publication policy for the exact current candidate.

This file is orchestration only: it never computes a score, changes a TIFF, or
alters the shared scientific template.  It binds publication decisions to the
current-candidate manifest, hash-bound evidence, the literal two-phase registry
rule, and the exact validator report.  In particular, a stratified/dotlike
comparison is diagnostic only and can never override a literal overlap failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = "evidence"
REQUIRED_VALIDATOR_CHECKS = (
    "single_band",
    "dtype_float32",
    "crs_epsg_32611",
    "shape_3730x3292",
    "transform_and_bounds_match_sample_submission",
    "footprint_all_finite",
    "footprint_values_in_0_1",
    "nan_only_outside_footprint",
    "no_infinite_values",
    "all_finite_values_in_0_1",
    "template_validator_passed",
)


def _json_at(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _sha256(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _safe_repo_path(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _evidence_path(root: Path, files: dict[str, Any], key: str) -> Path | None:
    name = files.get(key)
    if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
        return None
    base = (root / EVIDENCE_DIR).resolve()
    path = (base / name).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return None
    return path


def _evidence(root: Path, files: dict[str, Any], key: str) -> dict[str, Any]:
    path = _evidence_path(root, files, key)
    return _json_at(path) if path is not None else {}


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if len(value) == 16 and value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _phase_summary(document: dict[str, Any], phase: str) -> dict[str, Any]:
    item = document.get("phases", {}).get(phase, {}) if isinstance(document.get("phases"), dict) else {}
    if not isinstance(item, dict):
        return {}
    summary = item.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _reported_artifact_matches(reported: Any, expected_relative: str) -> bool:
    if not isinstance(reported, str) or not reported:
        return False
    actual = Path(reported)
    expected = Path(expected_relative)
    if actual.is_absolute():
        # Historical receipts were made in a different checkout root. Match the
        # complete path suffix, not just an arbitrary basename.
        return len(actual.parts) >= len(expected.parts) and actual.parts[-len(expected.parts):] == expected.parts
    return actual == expected


def _registry_expectation(root: Path, candidate: dict[str, Any], reasons: list[str]) -> int | None:
    expected = candidate.get("registry_expected_rasters")
    index_path = _safe_repo_path(root, candidate.get("registry_index_path"))
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1 or index_path is None:
        reasons.append("Pinned registry index path/count is missing or unsafe.")
        return None
    got_sha = _sha256(index_path)
    if got_sha is None or got_sha != candidate.get("registry_index_sha256"):
        reasons.append("Registry index is missing or does not match its recorded SHA-256.")
        return None
    index = _json_at(index_path)
    if (index.get("complete_accessible_scan") is not True
            or index.get("n_unique_grid_rasters") != expected
            or index.get("errors") != []):
        reasons.append("Registry index does not certify a complete, error-free accessible scan.")
    return expected


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    """Return the publication verdict for the exact artifact in current_candidate.json."""
    root = Path(root)
    reasons: list[str] = []
    candidate = _json_at(root / EVIDENCE_DIR / "current_candidate.json")
    if not candidate:
        return dict(verdict="negative", download_enabled=False,
                    reasons=["Current-candidate manifest is missing or invalid."],
                    artifact_sha256=None, validator_report={})

    artifact_relative = candidate.get("artifact_path")
    artifact_path = _safe_repo_path(root, artifact_relative)
    expected_sha = candidate.get("artifact_sha256")
    artifact_sha = _sha256(artifact_path) if artifact_path is not None and artifact_path.is_file() else None
    if artifact_sha is None or artifact_sha != expected_sha:
        reasons.append("Candidate TIFF is missing or does not match the current-candidate SHA-256.")

    files = candidate.get("evidence_files", {})
    if not isinstance(files, dict):
        files = {}
    evidence_hashes = _mapping(candidate.get("evidence_sha256"))
    required_evidence = ("artifact_receipt", "holdout", "uniqueness", "surface_phase",
                         "dots_phase", "method_manifest", "canaries", "validator")
    for key in required_evidence:
        path = _evidence_path(root, files, key)
        expected_evidence_sha = evidence_hashes.get(key)
        actual_evidence_sha = _sha256(path) if path is not None and path.is_file() else None
        if actual_evidence_sha is None or actual_evidence_sha != expected_evidence_sha:
            reasons.append(f"Evidence file {key!r} is missing or does not match its recorded SHA-256.")
    receipt = _evidence(root, files, "artifact_receipt")
    holdout = _evidence(root, files, "holdout")
    uniqueness = _evidence(root, files, "uniqueness")
    manifest = _evidence(root, files, "method_manifest")
    canaries = _evidence(root, files, "canaries")
    validator = _evidence(root, files, "validator")

    # Exact-artifact identity: file bytes, the submission receipt, the method
    # manifest, and all evidence references must describe the same candidate.
    receipt_raster = _mapping(receipt.get("raster"))
    raster = _mapping(receipt_raster.get("zeros"))
    if (receipt.get("evidence_class") != "SUBMISSION-RECEIPT"
            or raster.get("sha256") != artifact_sha
            or not _reported_artifact_matches(raster.get("path"), str(artifact_relative))):
        reasons.append("Submission receipt is missing or not bound to the exact candidate TIFF.")
    if (candidate.get("candidate_id") != receipt.get("hypothesis_id")
            or candidate.get("submission_name") != receipt.get("submission_name")
            or candidate.get("submission_note") != receipt.get("submission_note")):
        reasons.append("Candidate name/note does not match its hash-bound submission receipt.")
    note = candidate.get("submission_note")
    if not isinstance(note, str) or not note.strip() or len(note) > 140:
        reasons.append("Submission note is empty or longer than 140 characters.")

    # Holdout score is a screen. Require the exact pooled hide-and-recover result
    # to be repeated in the artifact receipt, and require a separately declared,
    # same-evaluator paired CI against the actual current holdout best.
    if holdout.get("evidence_class") != "HOLDOUT-DTI":
        reasons.append("HOLDOUT-DTI comparison is missing or incorrectly labelled.")
    if holdout.get("hypothesis") != candidate.get("candidate_id"):
        reasons.append("HOLDOUT-DTI comparison is not for the current candidate hypothesis.")
    if holdout.get("prompt_gate_passed") is not True:
        reasons.append("Corridor-versus-no-prior HOLDOUT-DTI gate failed or is missing.")
    if not isinstance(holdout.get("evaluator"), str) or not holdout.get("evaluator", "").strip():
        reasons.append("HOLDOUT-DTI evaluator is missing or unlabelled.")
    for count_key in ("n_cells", "withheld_positive_px_total"):
        count = holdout.get(count_key)
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            reasons.append(f"HOLDOUT-DTI {count_key} is missing or invalid.")
    registration = _mapping(candidate.get("protocol_registration"))
    registration_relative = registration.get("path")
    registration_path = _safe_repo_path(root, registration_relative)
    registration_sha = _sha256(registration_path) if registration_path is not None and registration_path.is_file() else None
    if (registration_sha is None or registration_sha != registration.get("sha256")):
        reasons.append("Holdout protocol preregistration is missing or does not match its pinned SHA-256.")
    else:
        preregistration = _json_at(registration_path)
        prereg_hypothesis = _mapping(preregistration.get("hypothesis"))
        if (holdout.get("preregistration") != registration_relative
                or prereg_hypothesis.get("id") != candidate.get("candidate_id")
                or not isinstance(preregistration.get("lane"), str)
                or "relay-ramp" not in preregistration.get("lane", "").lower()):
            reasons.append("Holdout protocol preregistration is not bound to the candidate and active method lane.")
        frozen_at = _parse_utc(preregistration.get("frozen_utc"))
        generated_at = _parse_utc(holdout.get("generated_utc"))
        if frozen_at is None or generated_at is None:
            reasons.append("Preregistration/holdout UTC timestamps are missing or invalid; protocol order is unverified.")
        elif frozen_at >= generated_at:
            reasons.append("Recorded preregistration is not earlier than HOLDOUT-DTI generation; protocol order is unverified.")
    pooled = _mapping(holdout.get("pooled_dti"))
    receipt_holdout = _mapping(receipt.get("holdout"))
    receipt_pooled = _mapping(receipt_holdout.get("pooled_dti"))
    if not pooled or not receipt_pooled:
        reasons.append("Pooled HOLDOUT-DTI values are missing.")
    else:
        for arm in ("transfer", "corridor_v1", "control_noprior"):
            if (not _finite_number(pooled.get(arm))
                    or not _finite_number(receipt_pooled.get(arm))
                    or pooled.get(arm) != receipt_pooled.get(arm)):
                reasons.append("Holdout values do not match the artifact receipt; candidate binding failed.")
                break
    if artifact_sha is None or raster.get("sha256") != artifact_sha:
        reasons.append("HOLDOUT-DTI receipt is not linked to the exact artifact hash.")

    best = holdout.get("current_best_comparison")
    valid_best = isinstance(best, dict)
    if valid_best:
        ci = best.get("paired_delta_ci95")
        incumbent_arm = best.get("incumbent_arm")
        incumbent_path = _safe_repo_path(root, best.get("incumbent_artifact_path"))
        incumbent_sha = _sha256(incumbent_path) if incumbent_path is not None and incumbent_path.is_file() else None
        valid_best = (
            best.get("evidence_class") == "HOLDOUT-DTI"
            and best.get("incumbent_role") == "current_holdout_best"
            and isinstance(best.get("incumbent_id"), str) and bool(best.get("incumbent_id"))
            and incumbent_sha is not None
            and incumbent_sha == best.get("incumbent_artifact_sha256")
            and best.get("evaluator") == holdout.get("evaluator")
            and best.get("artifact_sha256") == artifact_sha
            and best.get("n_cells") == holdout.get("n_cells")
            and best.get("withheld_positive_px_total") == holdout.get("withheld_positive_px_total")
            and _finite_number(best.get("candidate_pooled_dti"))
            and best.get("candidate_pooled_dti") == pooled.get("transfer")
            and isinstance(incumbent_arm, str)
            and _finite_number(best.get("incumbent_pooled_dti"))
            and best.get("incumbent_pooled_dti") == pooled.get(incumbent_arm)
            and isinstance(ci, list) and len(ci) == 2
            and all(_finite_number(x) for x in ci)
            and float(best["candidate_pooled_dti"]) > float(best["incumbent_pooled_dti"])
            and float(ci[0]) > 0
        )
    if not valid_best:
        reasons.append("No hash-bound paired HOLDOUT-DTI 95% CI proves improvement over the declared current holdout best.")

    # The protocol's overlap definition is literal: a single firing registry
    # raster is a duplicate. Density/stratification diagnostics never waive it.
    if uniqueness.get("evidence_class") != "REGISTRY-MEASUREMENT":
        reasons.append("Aggregate uniqueness evidence has the wrong evidence class or is missing.")
    if (uniqueness.get("rho_limit") != 0.90
            or uniqueness.get("overlap_limit") != 0.70):
        reasons.append("Aggregate uniqueness evidence does not record the required literal thresholds.")
    literal = _mapping(uniqueness.get("literal_gate"))
    worst_rho = uniqueness.get("worst_abs_spearman")
    worst_overlap = uniqueness.get("worst_dot_overlap_all", {})
    if not isinstance(worst_overlap, dict):
        worst_overlap = {}
    overlap_value = worst_overlap.get("dot_overlap_3px")
    rho_ok = literal.get("rho_ok") is True and _finite_number(worst_rho) and float(worst_rho) <= 0.90
    overlap_ok = literal.get("overlap_ok") is True and _finite_number(overlap_value) and float(overlap_value) <= 0.70
    if not rho_ok:
        reasons.append("Literal registry Spearman gate failed or is missing (limit |rho| <= 0.90).")
    if not overlap_ok:
        if _finite_number(overlap_value) and float(overlap_value) > 0.70:
            prior = worst_overlap.get("submission", "unidentified registry raster")
            reasons.append(f"Literal registry dot-overlap is {float(overlap_value):.3f} against {prior}; above 0.700, so duplicate-and-stop applies.")
        else:
            reasons.append("Literal registry dot-overlap gate failed or is missing; duplicate-and-stop applies.")

    expected_registry = _registry_expectation(root, candidate, reasons)
    if (not isinstance(uniqueness.get("n_registry_blobs"), int)
            or not isinstance(uniqueness.get("n_compared"), int)
            or uniqueness.get("n_registry_blobs") != expected_registry
            or uniqueness.get("n_compared") != expected_registry
            or uniqueness.get("n_errors") != 0
            or uniqueness.get("my_sha256") != artifact_sha
            or uniqueness.get("errors") != []):
        reasons.append("Aggregate uniqueness scan is incomplete, has errors, or is not hash/scope-bound to the current candidate.")

    phase_files = {
        "surface": ("surface_phase", "before_placement"),
        "dots": ("dots_phase", "after_placement"),
    }
    for phase, (evidence_key, required_order) in phase_files.items():
        phase_doc = _evidence(root, files, evidence_key)
        summary = _phase_summary(phase_doc, phase)
        if summary.get("candidate_file_sha256") != artifact_sha or artifact_sha is None:
            reasons.append(f"{phase} uniqueness phase is missing or not bound to the current artifact.")
        aggregate_phase = _mapping(uniqueness.get(f"{phase}_phase"))
        if phase == "surface":
            expected_decoded = _mapping(receipt.get("surface")).get("decoded_sha256")
            if aggregate_phase.get("candidate_decoded_sha256") != expected_decoded:
                reasons.append("Aggregate surface digest does not match the frozen pre-placement surface receipt.")
        else:
            expected_decoded = aggregate_phase.get("candidate_decoded_sha256")
        if (not expected_decoded
                or summary.get("candidate_decoded_sha256") != expected_decoded
                or aggregate_phase.get("candidate_file_sha256") != artifact_sha
                or aggregate_phase.get("phase") != phase):
            reasons.append(f"{phase} uniqueness phase is not bound to the receipt's exact decoded array.")
        if (aggregate_phase.get("registry_rasters_expected") != summary.get("registry_rasters_expected")
                or aggregate_phase.get("registry_rasters_checked") != summary.get("registry_rasters_checked")
                or aggregate_phase.get("worst_spearman_full_footprint") != summary.get("worst_spearman_full_footprint")
                or aggregate_phase.get("worst_dot_overlap") != summary.get("worst_dot_overlap")):
            reasons.append(f"{phase} aggregate and phase-specific uniqueness summaries disagree.")
        counts_ok = (
            expected_registry is not None
            and summary.get("evidence_class") == "REGISTRY-MEASUREMENT"
            and summary.get("phase") == phase
            and summary.get("rho_limit") == 0.90
            and summary.get("overlap_limit") == 0.70
            and summary.get("registry_rasters_expected") == expected_registry
            and summary.get("registry_rasters_checked") == expected_registry
            and summary.get("complete_accessible_scan") is True
            and summary.get("missing_or_invalid") == 0
            and summary.get("source_errors") == []
        )
        if not counts_ok:
            reasons.append(f"{phase} uniqueness phase is incomplete, has errors, or compares a different registry scope.")
        if summary.get("stop_required") is not False:
            reasons.append(f"{phase} uniqueness phase failed its literal duplicate gate or is missing.")
        phase_rho = summary.get("worst_spearman_full_footprint")
        phase_overlap = summary.get("worst_dot_overlap")
        if not _finite_number(phase_rho) or abs(float(phase_rho)) > 0.90:
            reasons.append(f"{phase} uniqueness phase exceeds or lacks the literal Spearman limit.")
        if not _finite_number(phase_overlap) or float(phase_overlap) > 0.70:
            reasons.append(f"{phase} uniqueness phase exceeds or lacks the literal 3-px dot-overlap limit.")
        if phase_doc.get("phase_order") != required_order:
            reasons.append(f"{phase} uniqueness scan is not certified at the required {required_order.replace('_', ' ')} stage.")

    # Reproducibility check: every named source must exist in this checkout and
    # match the hash recorded when the candidate was generated.
    source_hashes_raw = manifest.get("source_sha256")
    source_hashes = source_hashes_raw if isinstance(source_hashes_raw, dict) else {}
    source_ok = bool(source_hashes) and manifest.get("artifact_sha256") == artifact_sha
    source_mismatches: list[str] = []
    if source_ok:
        for rel, digest in source_hashes.items():
            source = _safe_repo_path(root, rel)
            if source is None or not source.is_file() or _sha256(source) != digest:
                source_mismatches.append(str(rel))
        source_ok = not source_mismatches
    if not source_ok:
        detail = f"; source hash mismatch: {', '.join(source_mismatches)}" if source_mismatches else ""
        reasons.append("Reproducible method source manifest is missing, stale, or not artifact-bound" + detail + ".")

    # Feature-alone canaries are tied to the same artifact/method; any missing,
    # non-finite, or >0.90 AUC blocks publication as possible leakage.
    features_raw = manifest.get("feature_names", [])
    features = features_raw if isinstance(features_raw, list) else []
    canary_ok = (bool(features)
                 and canaries.get("evidence_class") == "LEAKAGE-CANARY"
                 and canaries.get("artifact_sha256") == artifact_sha)
    if canary_ok:
        for feature in features:
            if not isinstance(feature, str):
                canary_ok = False
                break
            record = canaries.get(feature, {})
            auc = record.get("auc") if isinstance(record, dict) else None
            if not _finite_number(auc) or not 0.0 <= float(auc) <= 0.90:
                canary_ok = False
                break
    if not canary_ok:
        reasons.append("Artifact-bound feature-alone leakage canaries are missing or flagged.")

    # Exact-byte validator receipt. A locally passing format check does not imply
    # scientific validity or organizer acceptance.
    reports = validator.get("reports", [])
    report = next((item for item in reports if isinstance(item, dict)
                   and item.get("sha256") == artifact_sha), {}) if isinstance(reports, list) else {}
    checks = _mapping(report.get("checks"))
    meta = _mapping(report.get("meta"))
    minimum = report.get("min")
    maximum = report.get("max")
    validator_ok = (
        report.get("all_checks_passed") is True
        and validator.get("all_files_passed") is True
        and all(checks.get(key) is True for key in REQUIRED_VALIDATOR_CHECKS)
        and report.get("n_nan_inside_footprint") == 0
        and _finite_number(minimum) and float(minimum) >= 0
        and _finite_number(maximum) and float(maximum) <= 1
        and meta.get("crs") == "EPSG:32611"
        and meta.get("shape") == [3730, 3292]
        and meta.get("transform") == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
    )
    if not validator_ok:
        reasons.append("Hash-bound validator receipt is missing or failed the submission grid/range checks.")

    # Preserve first occurrence only so a failed gate is readable in the UI.
    reasons = list(dict.fromkeys(reasons))
    return dict(verdict="negative" if reasons else "promote",
                download_enabled=not reasons,
                reasons=reasons,
                artifact_sha256=artifact_sha,
                validator_report=report,
                scope_note=candidate.get("scope_note", ""))


def _mean_ci95(values: list[float]) -> list[float] | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return [mean - half, mean + half]


def write_card(root: Path = ROOT) -> dict[str, Any]:
    """Write the one current JSON run card from frozen receipts (no model rerun)."""
    root = Path(root)
    candidate = _json_at(root / EVIDENCE_DIR / "current_candidate.json")
    files = candidate.get("evidence_files", {})
    receipt = _evidence(root, files, "artifact_receipt")
    holdout = _evidence(root, files, "holdout")
    uniqueness = _evidence(root, files, "uniqueness")
    validator = _evidence(root, files, "validator")
    method = _evidence(root, files, "method_manifest")
    canaries = _evidence(root, files, "canaries")
    gate = evaluate(root)
    pooled = _mapping(holdout.get("pooled_dti"))
    pairs = _mapping(holdout.get("paired_cell_bootstrap"))
    transfer_delta = _mapping(pairs.get("transfer_minus_control"))
    v1_delta = _mapping(pairs.get("transfer_minus_v1"))
    per_cell_raw = holdout.get("per_cell", {})
    per_cell = per_cell_raw if isinstance(per_cell_raw, dict) else {}
    cell_values = [record.get("dti") for record in per_cell.values()
                   if isinstance(record, dict) and _finite_number(record.get("dti"))]
    mean_dti = holdout.get("mean_of_cells_dti")
    mean_ci = _mean_ci95([float(x) for x in cell_values])
    surface = _phase_summary(_evidence(root, files, "surface_phase"), "surface")
    dots = _phase_summary(_evidence(root, files, "dots_phase"), "dots")
    raster = _mapping(receipt.get("raster"))
    zeros_raster = _mapping(raster.get("zeros"))
    validator_reports = validator.get("reports", []) if isinstance(validator.get("reports"), list) else []
    report = next((item for item in validator_reports if isinstance(item, dict)
                   and item.get("sha256") == gate.get("artifact_sha256")), {}) if isinstance(validator_reports, list) else {}
    features_raw = method.get("feature_names", [])
    features = features_raw if isinstance(features_raw, list) else []
    aucs = [float(canaries[name]["auc"]) for name in features
            if isinstance(name, str) and isinstance(canaries.get(name), dict)
            and _finite_number(canaries[name].get("auc"))]
    card = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "GEMSDOE69 relay-ramp and pull-apart corridor generator",
        "candidate_id": candidate.get("candidate_id"),
        "hypothesis": "H69-H2 transfer-only: oblique-connector corridors at overlapping transfer steps, selected from the repaired catalogue tip graph.",
        "mechanism": "Tip-pair geometry proposes transfer-overlap corridors; existing gravity/magnetic HG and tilt, magnetic lows, lidar scarp, and N-NE orientation score them; the shared greedy allocator places dots. Dip polarity and dextral slip sense are not observed in the raster catalogue.",
        "non_fault_mimic": "Lithologic contacts, restraining-overlap pressure ridges, pluvial shorelines, and road-cut scarps can mimic the geophysical or lidar lineaments.",
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": holdout.get("evaluator"),
            "withheld_positive_pixels": holdout.get("withheld_positive_px_total"),
            "n_cells": holdout.get("n_cells"),
            "primary_statistic": "pooled DTI from summed TP/FP/FN",
            "pooled_dti": pooled.get("transfer"),
            "pooled_dti_ci95": None,
            "mean_of_cell_dti": mean_dti,
            "mean_of_cell_dti_ci95_normal_approximation": mean_ci,
            "paired_delta_vs_control": {
                "mean": transfer_delta.get("mean"),
                "ci95": transfer_delta.get("ci95"),
                "evidence_class": "HOLDOUT-DTI",
            },
            "paired_delta_vs_corridor_v1": {
                "mean": v1_delta.get("mean"),
                "ci95": v1_delta.get("ci95"),
                "evidence_class": "HOLDOUT-DTI",
            },
            "current_best_comparison": "NOT ESTABLISHED: no hash-bound paired CI against an explicitly declared current-best artifact is present.",
            "uncertainty_note": "The archived normal-approximation CI is across repeated holdout cells, not an independent spatial-block bootstrap. The paired CIs are bootstrap differences versus the named comparators, not absolute pooled-DTI CIs. Holdout is a screen, never a leaderboard projection.",
        },
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY",
            "feature_count": len(features),
            "worst_auc": max(aucs) if aucs else None,
            "rule": "AUC > 0.90 is leakage until proven otherwise",
        },
        "correlation_overlap_vs_registry": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "registry_scope": candidate.get("scope_note"),
            "registry_rasters_expected": uniqueness.get("n_registry_blobs"),
            "registry_rasters_compared": uniqueness.get("n_compared"),
            "registry_errors": uniqueness.get("n_errors"),
            "literal_gate": uniqueness.get("literal_gate"),
            "worst_abs_spearman": uniqueness.get("worst_abs_spearman"),
            "worst_dot_overlap_all": uniqueness.get("worst_dot_overlap_all"),
            "surface_phase": {
                "worst_abs_spearman": surface.get("worst_spearman_full_footprint"),
                "worst_dot_overlap": surface.get("worst_dot_overlap"),
                "stop_required": surface.get("stop_required"),
                "phase_order": _evidence(root, files, "surface_phase").get("phase_order"),
            },
            "dots_phase": {
                "worst_abs_spearman": dots.get("worst_spearman_full_footprint"),
                "worst_dot_overlap": dots.get("worst_dot_overlap"),
                "stop_required": dots.get("stop_required"),
                "phase_order": _evidence(root, files, "dots_phase").get("phase_order"),
            },
            "literal_rule": "Any registry raster with >70% of candidate dots within 3 px is duplicate-and-stop; stratification is diagnostic only.",
        },
        "raster": {
            "path": candidate.get("artifact_path"),
            "sha256": gate.get("artifact_sha256"),
            "bytes": Path(root / candidate.get("artifact_path", "")).stat().st_size if _safe_repo_path(root, candidate.get("artifact_path")) and _safe_repo_path(root, candidate.get("artifact_path")).is_file() else None,
            "positive_pixels": receipt.get("n_dots"),
        },
        "validator_output": report,
        "submission_name": candidate.get("submission_name"),
        "submission_note": (candidate.get("submission_note") or "")[:140],
        "verdict": gate["verdict"],
        "banner": "ok" if gate["download_enabled"] else "stop",
        "release_policy": gate,
        "note": "No submission slot used. A locally format-valid TIFF remains non-submittable while any literal or provenance gate is negative.",
    }
    (root / EVIDENCE_DIR / "run_card.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    return card


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-card", action="store_true", help="refresh evidence/run_card.json from existing receipts; does not rerun science")
    args = parser.parse_args()
    result = write_card() if args.write_card else evaluate()
    print(json.dumps(result.get("release_policy", result), indent=2))
    return 0 if result.get("download_enabled", result.get("verdict") == "promote") else 1


if __name__ == "__main__":
    raise SystemExit(main())
