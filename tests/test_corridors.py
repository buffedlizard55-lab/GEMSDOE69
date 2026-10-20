"""Unit tests for the corridor geometry rules (synthetic faults, no data needed)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems69 import corridors, traces  # noqa: E402


def _poly(verts, sense="N", dip_side=1, pid=0):
    part = traces.Part(pid=pid, record=pid, verts=np.array(verts, float), sense=sense,
                       dip_az_recorded=None, name=f"f{pid}", slip=None, dip_side=dip_side,
                       dip_source="recorded", length=traces.poly_length(np.array(verts, float)))
    return traces.Poly(part, part.verts.copy())


def _tip(poly_idx, poly, at_end, tid):
    v = poly.verts
    pos = v[-1] if at_end else v[0]
    out = traces._outward(v, at_end)
    d = out if at_end else -out
    dip_vec = poly.part.dip_side * np.array([d[1], -d[0]])
    return traces.Tip(tid, poly_idx, pos.copy(), out, poly.part.sense, dip_vec, "recorded",
                      poly.part.length, False, poly.part.record)


def _pair(a_verts, b_verts, sense="N", dip_a=1, dip_b=1):
    """Fault A runs south->north and ends at its tip; fault B starts at its tip and runs north."""
    A = _poly(a_verts, sense, dip_a, 0)
    B = _poly(b_verts, sense, dip_b, 1)
    ta = _tip(0, A, True, 0)      # northern end of A, pointing north
    tb = _tip(1, B, False, 1)     # southern end of B, pointing south
    return ta, tb, [A, B]


def test_dilation_tendency_peaks_for_nne_strike():
    td = {az: corridors.dilation_tendency(az) for az in range(0, 180, 5)}
    best = max(td, key=td.get)
    assert abs(best - 22.5) <= 5
    assert td[110] < 0.05          # strike parallel to the WNW extension axis: no dilation


def test_overlapping_same_dip_relay_is_admissible():
    # A: x=0, y 0..40 (tip at y=40);  B: x=20 (2 km east), y 30..80 (tip at y=30): overlap 1 km
    ta, tb, polys = _pair([[0, 0], [0, 40]], [[20, 30], [20, 80]])
    ok, why = corridors._pair_ok(ta, tb)
    assert ok, why
    lines, counts = corridors.generate([ta, tb], polys)
    kinds = {ln.kind for ln in lines}
    assert {"relay_connector", "relay_breach", "relay_enechelon"} <= kinds
    assert counts["relay_pairs"] == 1
    conn = next(ln for ln in lines if ln.kind == "relay_connector")
    assert abs(conn.W - 20) < 1e-6 and conn.meta["overlap"]


def test_opposite_dip_is_rejected():
    ta, tb, _ = _pair([[0, 0], [0, 40]], [[20, 30], [20, 80]], dip_a=1, dip_b=-1)
    ok, why = corridors._pair_ok(ta, tb)
    assert not ok and why == "rejected_dip"


def test_width_and_aspect_limits():
    ta, tb, _ = _pair([[0, 0], [0, 40]], [[160, 30], [160, 80]])      # W = 16 km > 15 km
    assert corridors._pair_ok(ta, tb) == (False, "rejected_geometry")
    ta, tb, _ = _pair([[0, 0], [0, 40]], [[5, 60], [5, 100]])          # W 0.5 km, gap 2 km > 3.5 W
    assert corridors._pair_ok(ta, tb) == (False, "rejected_geometry")


def test_releasing_step_logic_for_strike_slip():
    # right step (B east of A, looking north) is releasing for RL, restraining for LL
    ta, tb, _ = _pair([[0, 0], [0, 40]], [[20, 30], [20, 80]], sense="RL")
    assert corridors._pair_ok(ta, tb)[0]
    ta, tb, _ = _pair([[0, 0], [0, 40]], [[20, 30], [20, 80]], sense="LL")
    assert corridors._pair_ok(ta, tb) == (False, "rejected_step_sense")
    ta, tb, _ = _pair([[0, 0], [0, 40]], [[-20, 30], [-20, 80]], sense="LL")
    assert corridors._pair_ok(ta, tb)[0]


def test_dextral_termination_splays_rotate_into_extensional_quadrant():
    # NW-striking dextral fault ending at its NW tip: extensional quadrant is NE (right of NW)
    A = _poly([[0, 0], [-30, 30]], "RL", 0, 0)
    t = _tip(0, A, True, 0)
    lines, _ = corridors.generate([t], [A])
    splays = [ln for ln in lines if ln.kind == "termination_splay"]
    assert len(splays) == 2
    for ln in splays:
        d = ln.b - ln.a
        right = np.array([t.out[1], -t.out[0]])
        assert float(d @ right) > 0


def test_template_metric_reproduces_official_worked_example():
    from gems57 import metric
    tp, fp, fn = 3.0, 1.89, 2.0
    dti = tp / (tp + metric.ALPHA * fp + metric.BETA * fn)
    assert abs(dti - 0.60) < 0.005


def test_include_splays_emits_continuations_and_flank_breaches():
    ta, tb, polys = _pair([[0, 0], [0, 40]], [[20, 30], [20, 80]])
    lines, counts = corridors.generate([ta, tb], polys, max_partners=4, include_splays=True)
    kinds = {ln.kind for ln in lines}
    assert {"tip_continuation", "wing_splay", "flank_relay_breach"} <= kinds
    assert counts["tip_continuations"] >= 2
    assert counts["wing_splays"] >= 2
    assert counts["flank_relay_breaches"] >= 2


def test_hierarchical_calibration_and_decimated_emission():
    from gems69 import calibrate, pipeline
    rng = np.random.default_rng(42)
    shape = (30, 30)
    cand = np.ones(shape, dtype=bool)
    cand[:3, :] = False
    d_vis = rng.uniform(2.5, 50.0, size=shape).astype(np.float32)
    d_line = rng.uniform(0.0, 10.0, size=shape).astype(np.float32)
    d_tip = rng.uniform(0.0, 40.0, size=shape).astype(np.float32)
    s_band = np.where(d_line <= 8.0, rng.uniform(0.2, 0.9, size=shape), 0.0).astype(np.float32)
    e_pix = rng.uniform(0.1, 0.9, size=shape).astype(np.float32)
    withheld = (d_vis < 12.0) & (d_line < 4.0) & cand

    s_edges = calibrate.quantile_edges(s_band[cand & (s_band > 0)], 4)
    e_edges = calibrate.quantile_edges(e_pix[cand & (s_band > 0)], 4)
    vcode, gcode, fcode, dims = calibrate.hierarchical_codes(d_line, d_tip, d_vis, s_band, e_pix, s_edges, e_edges)
    rate, _ = calibrate.fit_hierarchical_rates(vcode, gcode, fcode, dims, withheld, cand & (s_band > 0))
    p = np.where(cand & (s_band > 0), rate[fcode], 0.0).astype(np.float32)
    assert p.shape == shape and p.dtype == np.float32
    assert np.isfinite(p).all() and (p >= 0.0).all() and (p <= 1.0).all()
    assert (p[~cand | (s_band <= 0)] == 0.0).all()
    assert p[withheld].mean() > p[cand & ~withheld & (s_band > 0)].mean()

    alloc = pipeline.emit_decimated(p, cand & (s_band > 0), k_truth=25, tile_px=3)
    dots = alloc.emitted
    assert dots.shape == shape and dots.dtype == bool
    assert not (dots & ~cand).any()
    # At most one dot per 3x3 tile
    H3, W3 = shape[0] // 3, shape[1] // 3
    tiles = dots[:H3 * 3, :W3 * 3].reshape(H3, 3, W3, 3).sum(axis=(1, 3))
    assert (tiles <= 1).all()
    assert alloc.n_dots == int(dots.sum())
