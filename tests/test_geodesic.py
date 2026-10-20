"""Unit and integration verification tests for GEMSDOE69 geodesic corridor engine."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

from gems import gate as local_gate
from gems.validate_submission import validate as local_validate
from gems69 import corridors, geodesic, tips as tipmod

ROOT = Path(__file__).resolve().parents[1]


def test_common_origin_separation_bugfix_ir69_code01() -> None:
    """Two synthetic underlapping N-striking strands separated by 18 px EW and 20 px NS gap
    must report positive common-origin along-strike separation instead of 0.0."""
    cat = np.zeros((200, 200), dtype=bool)
    cat[20:80, 50] = True
    cat[100:160, 68] = True
    strands = tipmod.vectorize(cat)
    pairs = corridors.build_tip_pairs(strands, cat)
    assert len(pairs) >= 1
    p = pairs[0]
    assert 15.0 <= p.w_px <= 21.0
    assert abs(p.along_px) > 10.0, "Common-origin projection must yield positive separation (IR-69-CODE-01)"


def test_dijkstra_geodesic_deflects_toward_low_cost_anomaly() -> None:
    """Least-cost routing must follow a curved geophysical ridge rather than a high-cost straight line."""
    from skimage.graph import route_through_array

    cost = np.ones((40, 40), dtype=np.float32) * 5.0
    # Curved low-cost anomaly bowing southward between (10, 5) and (10, 35)
    for col in range(5, 36):
        arc_row = int(round(10 + 8.0 * np.sin(np.pi * (col - 5) / 30.0)))
        cost[arc_row, col] = 0.05
    path, _ = route_through_array(cost, (10, 5), (10, 35), fully_connected=True, geometric=True)
    rows = [pt[0] for pt in path]
    assert max(rows) >= 16, "Geodesic route must deflect onto low-cost curved anomaly"


def test_forbidden_csv_columns_block_known_fault_distance_leakage() -> None:
    """Rule 4 canary guard: dist_known_fault_px is permanently blacklisted."""
    assert "dist_known_fault_px" in geodesic.FORBIDDEN_CSV_COLUMNS


def test_logistic_calibrator_recovers_monotone_signal() -> None:
    rng = np.random.default_rng(69)
    n = 4000
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    X = np.column_stack([x1, x2]).astype(np.float32)
    logits = -2.2 + 1.4 * x1 - 0.8 * x2
    probs = 1.0 / (1.0 + np.exp(-logits))
    y = rng.binomial(1, probs).astype(bool)
    w, b, mu, sd = geodesic.fit_logistic_l2(X, y, l2=5.0)
    pred = geodesic.predict_logistic(X, w, b, mu, sd)
    assert pred.dtype == np.float32
    assert np.all(np.isfinite(pred)) and float(pred.min()) >= 0.0 and float(pred.max()) <= 1.0
    assert w[0] > 0.5 and w[1] < -0.2


def test_scan_registry_handles_constant_all_ones_raster_cleanly(tmp_path: Path) -> None:
    """Pass-2 regression test: constant all-ones raster inside footprint (nt == n_fp)
    must produce finite 0.0 Spearman correlation rather than NaN/ZeroDivisionError."""
    H, W = 32, 32
    fp = np.ones((H, W), dtype=bool)
    fp[:4, :] = False
    reg_dir = tmp_path / "reg"
    reg_dir.mkdir()
    const_tif = reg_dir / ("a" * 40 + ".tif")
    with rasterio.open(
        const_tif,
        "w",
        driver="GTiff",
        height=H,
        width=W,
        count=1,
        dtype="float32",
        transform=Affine.identity(),
        crs="EPSG:32611",
    ) as dst:
        dst.write(np.ones((H, W), dtype=np.float32), 1)

    surface = np.zeros((H, W), dtype=np.float32)
    surface[10:20, 10:20] = 0.25
    dots = np.zeros((H, W), dtype=np.float32)
    dots[12, 12] = 1.0
    dots[16, 16] = 1.0

    # Exercise binary constant-footprint branch with mock prior_rasters manifest
    fake_prior = tmp_path / "prior_rasters.json"
    fake_prior.write_text(
        json.dumps(
            {
                "rasters": [
                    {
                        "git_blob_sha": "a" * 40,
                        "bytes": const_tif.stat().st_size,
                        "aliases": [{"repository": "test/repo", "path": "const.tif", "tree_sha": "0" * 40}],
                    }
                ]
            }
        )
    )
    orig_root = geodesic.ROOT
    try:
        tmp_reg_parent = tmp_path / "workspace"
        (tmp_reg_parent / "registry").mkdir(parents=True)
        (tmp_reg_parent / "registry" / "prior_rasters.json").write_text(fake_prior.read_text())
        geodesic.ROOT = tmp_reg_parent
        out = geodesic.scan_registry_fast(surface, dots, fp, registry_dir=reg_dir, extra_manifest_path=None)
    finally:
        geodesic.ROOT = orig_root

    assert np.isfinite(out["worst_abs_spearman"])
    assert out["worst_abs_spearman"] == 0.0
    assert out["n_errors"] == 0


def test_live_deliverables_and_gate_pass_strictly() -> None:
    """End-to-end verification of H69_G5_TwoRegimeGeodesic, receipts, and fail-closed gate."""
    from scripts import release_gate

    card = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    gate = json.loads((ROOT / "evidence" / "e2_gate.json").read_text())
    uniq = json.loads((ROOT / "evidence" / "e3_uniqueness.json").read_text())
    receipt = json.loads((ROOT / "evidence" / "e3_receipt.json").read_text())
    loc = json.loads((ROOT / "evidence" / "local-prior-audit.json").read_text())
    policy = release_gate.evaluate(ROOT)

    assert policy["holdout_protocol_compliant"] is True
    assert policy["paired_ci_control_passed"] is True
    assert policy["paired_ci_current_best_passed"] is True
    assert policy["validator_report"]["all_checks_passed"] is True
    assert card["verdict"] == policy["verdict"]
    assert card["release_policy"] == policy
    assert gate["corridor_mean_dti"] > gate["incumbent_pr6_mean_dti"] > gate["control_mean_dti"]
    assert gate["paired_delta_ci95"][0] > 0.0
    assert gate["paired_delta_vs_incumbent_ci95"][0] > 0.0
    assert uniq["worst_abs_spearman"] <= 0.90
    assert uniq["worst_dot_overlap_dotlike"]["dot_overlap_3px"] <= 0.70
    assert loc["max_dot_overlap_3px"] <= 0.70
    assert uniq["exact_pixel_match_found"] is False
    assert 0 < len(card["submission_note"]) <= 140

    zeros_tif = ROOT / receipt["raster"]["zeros"]["path"]
    nan_tif = ROOT / receipt["raster"]["nan"]["path"]
    assert zeros_tif.is_file() and nan_tif.is_file()

    sample_ref = ROOT / ".cache" / "gems_data" / "sample_submission.tif"
    if sample_ref.is_file():
        vz = local_validate(zeros_tif, reference=sample_ref)
        vn = local_validate(nan_tif, reference=sample_ref)
        assert vz["pass"] is True and vz["n_nan"] == 0
        assert vn["pass"] is True and vn["nan_inside_footprint"] == 0
