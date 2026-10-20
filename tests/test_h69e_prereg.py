"""H69-E pre-registration pins. No data files required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems69.corridors import TipPair, select_stratified  # noqa: E402
from gems69.physics import local_depletion, straight_step  # noqa: E402
from gems69.scoring import (  # noqa: E402
    W_GEOM, W_GRAV, W_LIDAR, W_MAG, W_MAGLOW, W_ORIENT, W_RAD, W_STRAIGHT,
)


def _pair(w, dilat, sid):
    return TipPair(sid, sid + 1, (0, 0), (10, 10), w, 0.0, 5.0, 20.0, 14.0, dilat, 1, 2)


def test_weights_match_preregistration_and_sum_to_one():
    pin = json.loads((ROOT / "registry" / "preregistration_h69e.json").read_text())
    got = {
        "E_grav": W_GRAV, "E_mag": W_MAG, "E_maglow": W_MAGLOW, "E_lidar": W_LIDAR,
        "E_straight": W_STRAIGHT, "E_rad": W_RAD, "W_orient": W_ORIENT, "W_geom": W_GEOM,
    }
    assert abs(sum(got.values()) - 1.0) < 1e-9
    for k, v in pin["weights"].items():
        assert abs(got[k] - v) < 1e-9, k


def test_stratified_selection_spans_width_bins():
    pairs = []
    sid = 0
    for w in (5.0, 20.0, 45.0, 100.0):
        for i in range(40):
            pairs.append(_pair(w, True, sid))
            sid += 2
            pairs.append(_pair(w + 0.5, False, sid))
            sid += 2
    chosen = select_stratified(pairs, max_corridors=80)
    assert len(chosen) == 80
    widths = [p.w_px for p in chosen]
    assert any(w < 10 for w in widths)
    assert any(10 <= w < 30 for w in widths)
    assert any(30 <= w < 60 for w in widths)
    assert any(w >= 60 for w in widths)
    assert sum(p.dilatational for p in chosen) > sum(not p.dilatational for p in chosen)


def test_straight_step_and_depletion_are_finite_on_a_step():
    field = np.zeros((64, 64), np.float32)
    field[:, 32:] = 5.0
    field[0, 0] = np.nan
    s = straight_step(field, sigma=1.5, coh_sigma=2.0)
    d = local_depletion(field, sigma_local=1.0, sigma_bg=4.0)
    assert np.isfinite(s[32, 16])
    assert s[32, 31] > s[32, 8]  # the contact outscores the flat interior
    assert np.isnan(d[0, 0])
    assert np.isfinite(d[32, 32])
