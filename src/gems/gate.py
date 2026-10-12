"""Fail-closed candidate-download gate.

A candidate is offered only after a complete HOLDOUT-DTI receipt, a positive paired
advantage over both baselines, clean leakage canaries, a non-duplicate registry result,
and a passing exact-grid format validation. This gate does not select or spend a weekly
submission slot; promotion remains a separate decision.
"""
from __future__ import annotations

import math
import re
from typing import Any

NOTE_MAX = 140
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = (
    "evidence_class",
    "candidate_dti",
    "baseline_dti",
    "incumbent_dti",
    "ci95_low",
    "ci95_high",
    "delta_vs_baseline_ci95_low",
    "delta_vs_baseline_ci95_high",
    "delta_vs_incumbent_ci95_low",
    "delta_vs_incumbent_ci95_high",
    "n_withheld_positives",
    "evaluator_version",
    "leakage_canaries_clean",
    "registry_raster_count",
    "max_registry_rank_correlation",
    "max_dots_within_3px_fraction",
    "exact_pixel_match_found",
    "raster_sha256",
    "format_validation_passed",
    "format_validation_reference_type",
    "format_validation_reference",
    "format_validation_reference_sha256",
    "submission_name",
    "submission_name_unique",
    "note",
)
SCORE_FIELDS = ("candidate_dti", "baseline_dti", "incumbent_dti", "ci95_low", "ci95_high")
DELTA_CI_FIELDS = (
    "delta_vs_baseline_ci95_low",
    "delta_vs_baseline_ci95_high",
    "delta_vs_incumbent_ci95_low",
    "delta_vs_incumbent_ci95_high",
)


def _blocked(reason: str) -> dict[str, Any]:
    return {"status": "BLOCKED", "download_enabled": False, "reason": reason}


def _negative(reason: str) -> dict[str, Any]:
    return {"status": "NEGATIVE", "download_enabled": False, "reason": reason}


def _number(receipt: dict[str, Any], key: str) -> float | None:
    value = receipt.get(key)
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def decide(receipt: dict[str, Any] | None) -> dict[str, Any]:
    """Return BLOCKED, NEGATIVE, or OFFER_DOWNLOAD; missing/invalid evidence fails closed."""
    if not isinstance(receipt, dict) or not receipt:
        return _blocked("no holdout receipt: gate not evaluated")

    missing = [key for key in REQUIRED if key not in receipt or receipt[key] is None or receipt[key] == ""]
    if missing:
        return _blocked(f"receipt incomplete: {missing}")

    if receipt["evidence_class"] != "HOLDOUT-DTI":
        return _blocked("candidate result is not labelled HOLDOUT-DTI")
    if not isinstance(receipt["evaluator_version"], str) or not receipt["evaluator_version"].strip():
        return _blocked("evaluator version is missing")
    if isinstance(receipt["n_withheld_positives"], bool) or not isinstance(receipt["n_withheld_positives"], int) or receipt["n_withheld_positives"] <= 0:
        return _blocked("withheld-positive count must be a positive integer")

    score = {key: _number(receipt, key) for key in SCORE_FIELDS}
    if any(value is None or not 0.0 <= value <= 1.0 for value in score.values()):
        return _blocked("candidate, baseline, incumbent, and candidate CI must be finite values in [0, 1]")
    if score["ci95_low"] > score["ci95_high"]:
        return _blocked("candidate 95% CI is malformed: lower bound exceeds upper bound")

    delta = {key: _number(receipt, key) for key in DELTA_CI_FIELDS}
    if any(value is None or not -1.0 <= value <= 1.0 for value in delta.values()):
        return _blocked("paired-difference CI bounds must be finite values in [-1, 1]")
    if delta["delta_vs_baseline_ci95_low"] > delta["delta_vs_baseline_ci95_high"]:
        return _blocked("paired CI vs baseline is malformed")
    if delta["delta_vs_incumbent_ci95_low"] > delta["delta_vs_incumbent_ci95_high"]:
        return _blocked("paired CI vs incumbent is malformed")

    if receipt["leakage_canaries_clean"] is not True:
        return _negative("leakage canaries did not pass")
    if isinstance(receipt["registry_raster_count"], bool) or not isinstance(receipt["registry_raster_count"], int) or receipt["registry_raster_count"] <= 0:
        return _blocked("registry comparison must cover at least one prior raster")

    max_corr = _number(receipt, "max_registry_rank_correlation")
    max_near = _number(receipt, "max_dots_within_3px_fraction")
    if max_corr is None or not -1.0 <= max_corr <= 1.0:
        return _blocked("maximum registry rank-correlation must be finite and in [-1, 1]")
    if max_near is None or not 0.0 <= max_near <= 1.0:
        return _blocked("maximum three-pixel dot overlap must be finite and in [0, 1]")
    if max_corr > 0.90 or max_near > 0.70 or receipt["exact_pixel_match_found"] is not False:
        return _negative("candidate is a registry duplicate or exceeds a uniqueness threshold")

    if receipt["format_validation_passed"] is not True:
        return _negative("exact-grid format validation did not pass")
    if receipt["format_validation_reference_type"] != "official_sample_submission":
        return _blocked("validation must use the official sample-submission grid")
    if not isinstance(receipt["format_validation_reference"], str) or not receipt["format_validation_reference"].strip():
        return _blocked("format validation reference is missing")
    if not HASH_RE.fullmatch(str(receipt["format_validation_reference_sha256"])):
        return _blocked("official sample-submission reference SHA-256 is missing or malformed")
    if not HASH_RE.fullmatch(str(receipt["raster_sha256"])):
        return _blocked("candidate raster SHA-256 is missing or malformed")
    if not isinstance(receipt["submission_name"], str) or not receipt["submission_name"].strip():
        return _blocked("unique submission name is missing")
    if receipt["submission_name_unique"] is not True:
        return _blocked("submission name has not been compared with previous submissions")
    if not note_ok(receipt["note"]):
        return _blocked(f"submission note must contain 1–{NOTE_MAX} characters")

    candidate = score["candidate_dti"]
    baseline = score["baseline_dti"]
    incumbent = score["incumbent_dti"]
    if candidate <= baseline or candidate <= incumbent:
        return _negative("candidate does not beat both the no-corridor baseline and current holdout best")
    if delta["delta_vs_baseline_ci95_low"] <= 0 or delta["delta_vs_incumbent_ci95_low"] <= 0:
        return _negative("paired 95% CI does not establish improvement over both baselines")

    return {
        "status": "OFFER_DOWNLOAD",
        "download_enabled": True,
        "reason": "all holdout, leakage, registry, and exact-grid format gates pass; slot selection is separate",
    }


def note_ok(note: Any) -> bool:
    return isinstance(note, str) and 0 < len(note) <= NOTE_MAX
