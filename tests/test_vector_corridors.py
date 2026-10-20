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
