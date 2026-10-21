"""Unit and integration regression tests for H69-K kinematics, directional physics,
IR-69-17 visible-only holdout fix, empirical-Bayes calibration, and hash-bound receipts.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from gems69 import calibrate, corridors, evidence, holdout69, traces

ROOT = Path(__file__).resolve().parents[1]


def _make_poly(verts, sense="N", dip_side=1, pid=0):
    arr = np.array(verts, float)
    part = traces.Part(
        pid=pid, record=pid, verts=arr, sense=sense, dip_az_recorded=None,
        name=f"fault_{pid}", slip=0.5, dip_side=dip_side, dip_source="recorded",
        length=traces.poly_length(arr),
    )
    return traces.Poly(part, arr.copy())


def _make_tip(poly_idx, poly, at_end, tid):
    v = poly.verts
    pos = v[-1] if at_end else v[0]
    out = traces._outward(v, at_end)
    d = out if at_end else -out
    dip_vec = poly.part.dip_side * np.array([d[1], -d[0]])
    return traces.Tip(
        tid, poly_idx, pos.copy(), out, poly.part.sense, dip_vec,
        "recorded", poly.part.length, False, poly.part.record,
    )


def test_directional_gradient_suppresses_orthogonal_contacts():
    fp = np.ones((80, 80), bool)
    # Field steps strictly eastward (col grows east -> dF/dE > 0, dF/dN == 0)
    col = np.broadcast_to(np.arange(80, dtype=np.float32), (80, 80)).copy()
    ge, gn = evidence.directional_scaled_gradient(col, fp, sigma_px=2.0)
    # Interior region free of boundary reflection
    assert float(np.abs(gn[20:60, 20:60]).max()) < 1e-5
    assert float(ge[20:60, 20:60].mean()) > 0.35

    # N-S striking corridor has normal n = (1, 0) -> strong cross-corridor step
    ns_line = corridors.Line("relay_connector", np.array([40.0, -55.0]), np.array([40.0, -25.0]))
    # E-W striking corridor crosses the N-S step perpendicularly -> normal n = (0, -1) -> zero projection
    ew_line = corridors.Line("relay_connector", np.array([25.0, -40.0]), np.array([55.0, -40.0]))
    corridors.rasterize_lines([ns_line, ew_line], fp, None)
    layers = {
        "grav_edge": np.full((80, 80), 0.5, np.float32),
        "mag_edge": np.full((80, 80), 0.5, np.float32),
        "mag_low": np.full((80, 80), 0.5, np.float32),
        "scarp": np.full((80, 80), 0.5, np.float32),
        "grav_ge": ge, "grav_gn": gn, "mag_ge": ge, "mag_gn": gn,
    }
    corridors.score_lines([ns_line, ew_line], layers)
    assert ns_line.terms["grav_perp"] > ew_line.terms["grav_perp"] + 0.20
    assert ns_line.score > ew_line.score


def test_stepover_emits_sidewalls_breach_flank_relay_and_horsetails():
    # Overlapping synthetic step-over where strand B continues far past strand A's tip
    A = _make_poly([[10, -100], [10, -50]], sense="N", dip_side=1, pid=0)
    B = _make_poly([[30, -120], [30, -10]], sense="N", dip_side=1, pid=1)
    ta = _make_tip(0, A, True, 0)
    tb = _make_tip(1, B, False, 1)
    lines, counts = corridors.generate([ta, tb], [A, B])
    kinds = {ln.kind for ln in lines}
    assert "flank_relay" in kinds and "flank_breach" in kinds
    assert "tip_continuation" in kinds and "wing_splay" in kinds
    assert counts["flank_relays"] >= 1


def test_hierarchical_calibration_bounds_and_zero_count_shrinkage():
    n = 500
    c1 = np.zeros(n, dtype=np.int32)
    c1[250:] = 1
    c2 = c1 * 2 + (np.arange(n) % 2).astype(np.int32)
    # Leave bin 3 empty in training to test shrinkage to parent bin 1
    train = np.ones(n, bool)
    train[c2 == 3] = False
    truth = np.zeros(n, bool)
    truth[(c1 == 1) & train] = True
    rate, stats = calibrate.fit_hierarchical_rates([(c1, 2, 10.0), (c2, 4, 20.0)], truth, train)
    assert rate.shape == (4,)
    assert np.all((rate >= 0.0) & (rate <= 1.0))
    # Empty child bin 3 inherits non-zero parent rate from bin 1 rather than collapsing to 0
    assert rate[3] > 0.5
    assert rate[2] > rate[0]
    assert stats["n_bins"] == 4


def test_holdout69_never_builds_flank_or_canary_from_full_catalogue():
    src_arms = inspect.getsource(holdout69.run_holdout_arms)
    src_canary = inspect.getsource(holdout69.leakage_canary)
    assert "edt(~visible)" in src_arms
    assert "edt(~catalogue)" not in src_arms
    assert "corridor_pipeline(ctx.grid.catalogue" not in src_canary


def test_h69k_artifact_and_evidence_chain_hash_bound():
    receipt = json.loads((ROOT / "evidence" / "e3_receipt.json").read_text())
    card = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    gate = json.loads((ROOT / "evidence" / "e2_gate.json").read_text())
    uniq = json.loads((ROOT / "evidence" / "e3_uniqueness.json").read_text())
    manifest = json.loads((ROOT / "evidence" / "e3_method_manifest.json").read_text())

    zeros_rel = receipt["raster"]["zeros"]["path"]
    zeros_file = ROOT / zeros_rel
    assert zeros_file.is_file()
    actual_sha = hashlib.sha256(zeros_file.read_bytes()).hexdigest()

    assert receipt["raster"]["zeros"]["sha256"] == actual_sha
    assert gate["artifact_sha256"] == actual_sha
    assert uniq["my_sha256"] == actual_sha
    assert manifest["artifact_sha256"] == actual_sha
    assert card["raster"]["zeros"]["sha256"] == actual_sha
    assert len(card["submission_note"]) <= 140
    assert card["verdict"] == "negative"
    assert uniq["n_errors"] == 0
    assert uniq["worst_dot_overlap_dotlike"]["dot_overlap_3px"] <= 0.70
    assert uniq["local_prior_overlap"]["ok"] is True
