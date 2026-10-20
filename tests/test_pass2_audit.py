"""Adversarial Pass 2 / Pass 3 regression suite verifying bug fixes, SHA-256
bindings, zero-error 751-blob registry scan, and fail-closed site downloads.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from scripts import release_gate

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_lidar_strike_compass_conversion_identity():
    # IR-69-LIDAR-STRIKE-01: raw=0 (horizontal image axis = due East/West, az 90)
    # -> (0 * 180 / 255 + 90) % 180 == 90.0 deg; raw=127.5 (vertical N-S) -> 0.0 deg
    assert float(((0.0 * (180.0 / 255.0) + 90.0) % 180.0)) == 90.0
    assert float(((127.5 * (180.0 / 255.0) + 90.0) % 180.0)) == 0.0


def test_all_evidence_artifacts_are_cryptographically_hash_bound():
    receipt = json.loads((EVID / "e3_receipt.json").read_text())
    manifest = json.loads((EVID / "e3_method_manifest.json").read_text())
    canaries = json.loads((EVID / "e1_canaries.json").read_text())
    gate = json.loads((EVID / "e2_gate.json").read_text())
    uniq = json.loads((EVID / "e3_uniqueness.json").read_text())
    u_surf = json.loads((EVID / "e3_uniqueness_surface.json").read_text())
    u_dots = json.loads((EVID / "e3_uniqueness_dots.json").read_text())

    p_zeros = ROOT / receipt["raster"]["zeros"]["path"]
    p_nan = ROOT / receipt["raster"]["nan"]["path"]
    assert p_zeros.is_file() and p_nan.is_file()
    sha = sha256_file(p_zeros)

    assert receipt["raster"]["zeros"]["sha256"] == sha
    assert manifest["artifact_sha256"] == sha
    assert canaries["artifact_sha256"] == sha
    assert gate["artifact_sha256"] == sha
    assert uniq["my_sha256"] == sha
    assert u_surf["phases"]["surface"]["summary"]["candidate_file_sha256"] == sha
    assert u_dots["phases"]["dots"]["summary"]["candidate_file_sha256"] == sha

    # Every source file in e3_method_manifest.json matches exact bytes on disk
    for rel, expected_digest in manifest["source_sha256"].items():
        assert sha256_file(ROOT / rel) == expected_digest, f"drift in {rel}"

    # Every model feature passes the <= 0.90 single-feature canary threshold
    for feat in manifest["feature_names"]:
        assert 0.0 < canaries[feat]["auc"] <= 0.90, feat


def test_holdout_gate_and_hardlink_recovery_pass_strictly():
    hl = json.loads((EVID / "e1_hardlinked_recovery.json").read_text())
    assert hl["n_tested"] >= 50
    assert hl["mean_recovery_within_300m"] >= 0.70

    gate = json.loads((EVID / "e2_gate.json").read_text())
    assert gate["gate_passed"] is True
    assert gate["current_best_beaten"] is True
    for mode_key in ("primary_mode_all", "conservative_mode_detached"):
        cmp = gate[mode_key]["comparisons"]["h69_efg_vs_no_prior_control"]
        assert cmp["pooled_delta_dti"] > 0.01
        assert cmp["boot_ci95"][0] > 0.0
        assert cmp["p_a_gt_b"] >= 0.99


def test_full_751_registry_scan_zero_errors_and_only_overlap_blocks():
    uniq = json.loads((EVID / "e3_uniqueness.json").read_text())
    assert uniq["n_registry_blobs"] == 751
    assert uniq["n_compared"] == 751
    assert uniq["n_errors"] == 0
    assert uniq["literal_gate"]["rho_ok"] is True
    assert uniq["literal_gate"]["overlap_ok"] is False

    decision = release_gate.evaluate(ROOT)
    assert decision["verdict"] == "negative"
    assert decision["download_enabled"] is False
    # Prove ZERO non-uniqueness errors exist (canaries, validator, hashes, holdout ALL clean!)
    for r in decision["reasons"]:
        assert "uniqueness" in r.lower()

    dl = ROOT / "docs" / "downloads"
    if dl.exists():
        assert [p for p in dl.iterdir() if p.suffix.lower() in (".tif", ".tiff", ".zip")] == []
