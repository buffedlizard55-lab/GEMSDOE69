"""Regression tests for the literal, hash-bound publication policy."""
import hashlib
import json
import sys

import pytest

from scripts import release_gate as policy


CANDIDATE_ID = "candidate-transfer"
NOTE = "transfer-corridor holdout candidate"


def put(root, name, obj, directory="evidence"):
    path = root / directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def cleared(tmp_path):
    raster = tmp_path / "candidate.tif"
    raster.write_bytes(b"test artifact: validator receipt fixture, not real geodata")
    digest = sha(raster)

    registry_path = put(tmp_path, "index.json", {
        "complete_accessible_scan": True,
        "n_unique_grid_rasters": 1,
        "errors": [],
    }, directory="registry")
    preregistration_path = put(tmp_path, "preregistration.json", {
        "repository": "buffedlizard55-lab/GEMSDOE69",
        "lane": "Relay-ramp and pull-apart corridor generator",
        "frozen_utc": "2026-10-20T20:00:00Z",
        "hypothesis": {"id": CANDIDATE_ID},
    }, directory="registry")

    checks = {key: True for key in policy.REQUIRED_VALIDATOR_CHECKS}
    surface_decoded = "surface-decoded-fixture"
    dots_decoded = "dots-decoded-fixture"
    phase_summary = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "phase": "surface",
        "rho_limit": 0.90,
        "overlap_limit": 0.70,
        "candidate_file_sha256": digest,
        "registry_rasters_expected": 1,
        "registry_rasters_checked": 1,
        "complete_accessible_scan": True,
        "missing_or_invalid": 0,
        "source_errors": [],
        "stop_required": False,
        "worst_spearman_full_footprint": 0.4,
        "worst_dot_overlap": 0.6,
    }
    incumbent_path = tmp_path / "incumbent.tif"
    incumbent_path.write_bytes(b"hash-bound current-best fixture")
    incumbent_digest = sha(incumbent_path)
    pooled = {"transfer": 0.31, "corridor_v1": 0.20, "control_noprior": 0.18, "current_best": 0.28}
    best = {
        "evidence_class": "HOLDOUT-DTI",
        "incumbent_role": "current_holdout_best",
        "incumbent_id": "registered-incumbent-1",
        "incumbent_artifact_path": "incumbent.tif",
        "incumbent_artifact_sha256": incumbent_digest,
        "incumbent_arm": "current_best",
        "evaluator": "gems57-test-v1",
        "artifact_sha256": digest,
        "candidate_pooled_dti": 0.31,
        "incumbent_pooled_dti": 0.28,
        "paired_delta_ci95": [0.02, 0.06],
        "n_cells": 8,
        "withheld_positive_px_total": 400,
    }

    candidate = {
        "candidate_id": CANDIDATE_ID,
        "artifact_path": "candidate.tif",
        "artifact_sha256": digest,
        "submission_name": "candidate-transfer-zeros",
        "submission_note": NOTE,
        "registry_index_path": "registry/index.json",
        "registry_index_sha256": sha(registry_path),
        "registry_expected_rasters": 1,
        "protocol_registration": {
            "path": "registry/preregistration.json",
            "sha256": sha(preregistration_path),
        },
        "evidence_files": {
            "artifact_receipt": "receipt.json",
            "holdout": "holdout.json",
            "uniqueness": "uniqueness.json",
            "surface_phase": "surface.json",
            "dots_phase": "dots.json",
            "method_manifest": "manifest.json",
            "canaries": "canaries.json",
            "validator": "validator.json",
        },
    }
    put(tmp_path, "current_candidate.json", candidate)
    put(tmp_path, "receipt.json", {
        "evidence_class": "SUBMISSION-RECEIPT",
        "hypothesis_id": CANDIDATE_ID,
        "submission_name": candidate["submission_name"],
        "submission_note": NOTE,
        "surface": {"decoded_sha256": surface_decoded},
        "raster": {"zeros": {"path": "candidate.tif", "sha256": digest, "decoded_sha256": dots_decoded}},
        "holdout": {"pooled_dti": pooled},
    })
    put(tmp_path, "holdout.json", {
        "evidence_class": "HOLDOUT-DTI",
        "hypothesis": CANDIDATE_ID,
        "evaluator": "gems57-test-v1",
        "n_cells": 8,
        "withheld_positive_px_total": 400,
        "preregistration": "registry/preregistration.json",
        "generated_utc": "2026-10-20T20:30:00Z",
        "prompt_gate_passed": True,
        "pooled_dti": pooled,
        "current_best_comparison": best,
    })
    put(tmp_path, "uniqueness.json", {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "rho_limit": 0.90,
        "overlap_limit": 0.70,
        "my_sha256": digest,
        "n_registry_blobs": 1,
        "n_compared": 1,
        "n_errors": 0,
        "errors": [],
        "literal_gate": {"rho_ok": True, "overlap_ok": True},
        "worst_abs_spearman": 0.4,
        "worst_dot_overlap_all": {"submission": "registry:prior.tif", "dot_overlap_3px": 0.6},
        "surface_phase": {
            "candidate_file_sha256": digest,
            "candidate_decoded_sha256": surface_decoded,
            "phase": "surface",
            "registry_rasters_expected": 1,
            "registry_rasters_checked": 1,
            "worst_spearman_full_footprint": 0.4,
            "worst_dot_overlap": 0.6,
        },
        "dots_phase": {
            "candidate_file_sha256": digest,
            "candidate_decoded_sha256": dots_decoded,
            "phase": "dots",
            "registry_rasters_expected": 1,
            "registry_rasters_checked": 1,
            "worst_spearman_full_footprint": 0.4,
            "worst_dot_overlap": 0.6,
        },
    })
    put(tmp_path, "surface.json", {
        "phase_order": "before_placement",
        "phases": {"surface": {"summary": {**phase_summary, "candidate_decoded_sha256": surface_decoded}}},
    })
    put(tmp_path, "dots.json", {
        "phase_order": "after_placement",
        "phases": {"dots": {"summary": {**phase_summary, "phase": "dots", "candidate_decoded_sha256": dots_decoded}}},
    })
    code = tmp_path / "model.py"
    code.write_text("# reproducible fixture", encoding="utf-8")
    put(tmp_path, "manifest.json", {
        "artifact_sha256": digest,
        "feature_names": ["hg"],
        "source_sha256": {"model.py": sha(code)},
    })
    put(tmp_path, "canaries.json", {"evidence_class": "LEAKAGE-CANARY", "artifact_sha256": digest, "hg": {"auc": 0.6}})
    put(tmp_path, "validator.json", {
        "all_files_passed": True,
        "reports": [{
            "sha256": digest,
            "all_checks_passed": True,
            "checks": checks,
            "n_nan_inside_footprint": 0,
            "min": 0.0,
            "max": 1.0,
            "meta": {
                "crs": "EPSG:32611",
                "shape": [3730, 3292],
                "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            },
        }],
    })
    candidate["evidence_sha256"] = {
        key: sha(tmp_path / "evidence" / name)
        for key, name in candidate["evidence_files"].items()
    }
    put(tmp_path, "current_candidate.json", candidate)
    return tmp_path


def test_complete_hash_bound_literal_receipts_pass(cleared):
    result = policy.evaluate(cleared)
    assert result["download_enabled"]
    assert result["verdict"] == "promote"


def test_missing_evidence_fails_closed(tmp_path):
    assert policy.evaluate(tmp_path)["verdict"] == "negative"


def test_stratified_or_dotlike_result_cannot_override_literal_failure(cleared):
    uniqueness = policy._evidence(cleared, policy._json_at(cleared / "evidence/current_candidate.json")["evidence_files"], "uniqueness")
    uniqueness["literal_gate"]["overlap_ok"] = False
    uniqueness["worst_dot_overlap_all"]["dot_overlap_3px"] = 0.61
    uniqueness["stratified_gate"] = {"dotlike_overlap_ok": True}
    put(cleared, "uniqueness.json", uniqueness)
    result = policy.evaluate(cleared)
    assert result["verdict"] == "negative"
    assert not result["download_enabled"]
    assert any("Literal registry dot-overlap" in reason or "Literal registry dot-overlap gate" in reason
               for reason in result["reasons"])


def test_literal_overlap_above_threshold_is_duplicate(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    uniqueness = policy._evidence(cleared, candidate["evidence_files"], "uniqueness")
    uniqueness["literal_gate"]["overlap_ok"] = False
    uniqueness["worst_dot_overlap_all"]["dot_overlap_3px"] = 0.71
    put(cleared, "uniqueness.json", uniqueness)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("duplicate-and-stop" in reason for reason in result["reasons"])


@pytest.mark.parametrize("phase", ["surface", "dots"])
def test_stale_phase_blocks(cleared, phase):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    key = "surface_phase" if phase == "surface" else "dots_phase"
    name = candidate["evidence_files"][key]
    document = policy._evidence(cleared, candidate["evidence_files"], key)
    document["phases"][phase]["summary"]["candidate_file_sha256"] = "stale"
    put(cleared, name, document)
    assert not policy.evaluate(cleared)["download_enabled"]


def test_tampered_evidence_json_is_hash_bound(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    validator = policy._evidence(cleared, candidate["evidence_files"], "validator")
    validator["changed_after_freeze"] = True
    put(cleared, candidate["evidence_files"]["validator"], validator)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("validator" in reason and "recorded SHA-256" in reason for reason in result["reasons"])


def test_surface_decoded_array_must_match_preplacement_receipt(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    document = policy._evidence(cleared, candidate["evidence_files"], "surface_phase")
    document["phases"]["surface"]["summary"]["candidate_decoded_sha256"] = "wrong decoded array"
    put(cleared, candidate["evidence_files"]["surface_phase"], document)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("decoded array" in reason for reason in result["reasons"])


def test_final_dots_decoded_array_must_match_aggregate(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    document = policy._evidence(cleared, candidate["evidence_files"], "dots_phase")
    document["phases"]["dots"]["summary"]["candidate_decoded_sha256"] = "wrong final array"
    put(cleared, candidate["evidence_files"]["dots_phase"], document)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("decoded array" in reason for reason in result["reasons"])


def test_surface_comparison_must_precede_placement(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    document = policy._evidence(cleared, candidate["evidence_files"], "surface_phase")
    document["phase_order"] = "after_placement"
    put(cleared, candidate["evidence_files"]["surface_phase"], document)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("before placement" in reason for reason in result["reasons"])


def test_phase_registry_count_must_match_aggregate(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    document = policy._evidence(cleared, candidate["evidence_files"], "dots_phase")
    document["phases"]["dots"]["summary"]["registry_rasters_checked"] = 2
    put(cleared, candidate["evidence_files"]["dots_phase"], document)
    assert not policy.evaluate(cleared)["download_enabled"]


def test_preregistration_after_holdout_generation_blocks(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    registration_path = cleared / candidate["protocol_registration"]["path"]
    registration = policy._json_at(registration_path)
    registration["frozen_utc"] = "2026-10-20T20:40:00Z"
    registration_path.write_text(json.dumps(registration), encoding="utf-8")
    candidate["protocol_registration"]["sha256"] = sha(registration_path)
    put(cleared, "current_candidate.json", candidate)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("not earlier than HOLDOUT-DTI generation" in reason for reason in result["reasons"])


def test_current_best_requires_hash_bound_positive_paired_ci(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    holdout = policy._evidence(cleared, candidate["evidence_files"], "holdout")
    holdout["current_best_comparison"]["paired_delta_ci95"] = [-0.01, 0.06]
    put(cleared, candidate["evidence_files"]["holdout"], holdout)
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("current holdout best" in reason for reason in result["reasons"])


def test_current_best_must_be_bound_to_incumbent_artifact(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    holdout = policy._evidence(cleared, candidate["evidence_files"], "holdout")
    incumbent = cleared / holdout["current_best_comparison"]["incumbent_artifact_path"]
    incumbent.write_bytes(b"mutated current-best artifact")
    result = policy.evaluate(cleared)
    assert not result["download_enabled"]
    assert any("current holdout best" in reason for reason in result["reasons"])


def test_boolean_current_best_claim_is_not_enough(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    holdout = policy._evidence(cleared, candidate["evidence_files"], "holdout")
    holdout["current_best_comparison"] = None
    holdout["beats_current_best"] = True
    put(cleared, candidate["evidence_files"]["holdout"], holdout)
    assert not policy.evaluate(cleared)["download_enabled"]


@pytest.mark.parametrize("change", ["missing", "modified", "validator", "registry_error", "receipt"])
def test_other_blockers(cleared, change):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    files = candidate["evidence_files"]
    if change == "missing":
        (cleared / "candidate.tif").unlink()
    elif change == "modified":
        (cleared / "candidate.tif").write_bytes(b"changed")
    elif change == "validator":
        report = policy._evidence(cleared, files, "validator")
        report["reports"][0]["checks"]["footprint_all_finite"] = False
        put(cleared, files["validator"], report)
    elif change == "registry_error":
        uniqueness = policy._evidence(cleared, files, "uniqueness")
        uniqueness["n_errors"] = 1
        put(cleared, files["uniqueness"], uniqueness)
    else:
        receipt = policy._evidence(cleared, files, "artifact_receipt")
        receipt["raster"]["zeros"]["sha256"] = "stale"
        put(cleared, files["artifact_receipt"], receipt)
    assert not policy.evaluate(cleared)["download_enabled"]


@pytest.mark.parametrize("auc", [0.91, float("nan"), None])
def test_invalid_or_flagged_canary_blocks(cleared, auc):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    canary = policy._evidence(cleared, candidate["evidence_files"], "canaries")
    canary["hg"]["auc"] = auc
    put(cleared, candidate["evidence_files"]["canaries"], canary)
    assert not policy.evaluate(cleared)["download_enabled"]


def test_source_mutation_blocks(cleared):
    (cleared / "model.py").write_text("# changed method", encoding="utf-8")
    assert not policy.evaluate(cleared)["download_enabled"]


def test_malformed_nested_json_fails_closed_without_crashing(cleared):
    candidate = policy._json_at(cleared / "evidence/current_candidate.json")
    uniqueness = policy._evidence(cleared, candidate["evidence_files"], "uniqueness")
    uniqueness["literal_gate"] = ["not", "a", "mapping"]
    put(cleared, candidate["evidence_files"]["uniqueness"], uniqueness)
    validator = policy._evidence(cleared, candidate["evidence_files"], "validator")
    validator["reports"][0]["meta"] = ["malformed"]
    validator["reports"][0]["min"] = "not numeric"
    put(cleared, candidate["evidence_files"]["validator"], validator)
    result = policy.evaluate(cleared)
    assert result["verdict"] == "negative"
    assert not result["download_enabled"]


def test_current_repo_fails_closed_on_literal_duplicate_and_stale_provenance():
    result = policy.evaluate()
    assert result["verdict"] == "negative"
    assert result["download_enabled"] is False
    assert any("duplicate-and-stop" in reason for reason in result["reasons"])
    assert any("current holdout best" in reason for reason in result["reasons"])
    assert any("method source manifest" in reason for reason in result["reasons"])


def test_builder_revokes_stale_downloads(tmp_path, monkeypatch):
    from scripts import build_site69 as site
    (tmp_path / "docs" / "downloads").mkdir(parents=True)
    stale = tmp_path / "docs" / "downloads" / "stale.tif"
    stale.write_bytes(b"stale")
    monkeypatch.setattr(site, "ROOT", tmp_path)
    monkeypatch.setattr(site, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(site, "EV", tmp_path / "evidence")
    monkeypatch.setitem(sys.modules, "release_gate", policy)
    banner, artifact = site.submission_banner()
    assert "DO NOT SUBMIT" in banner
    assert artifact is None
    assert not stale.exists()
    assert "download>" not in banner


def test_builder_copies_only_the_hash_cleared_current_candidate(cleared, monkeypatch):
    from scripts import build_site69 as site
    monkeypatch.setattr(site, "ROOT", cleared)
    monkeypatch.setattr(site, "DOCS", cleared / "docs")
    monkeypatch.setattr(site, "EV", cleared / "evidence")
    monkeypatch.setitem(sys.modules, "release_gate", policy)
    banner, artifact = site.submission_banner()
    assert "OK TO DOWNLOAD" in banner
    assert artifact == cleared / "candidate.tif"
    published = cleared / "docs" / "downloads" / "candidate.tif"
    assert published.read_bytes() == (cleared / "candidate.tif").read_bytes()
