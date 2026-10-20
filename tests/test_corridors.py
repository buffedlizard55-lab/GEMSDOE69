"""Lane-69 tip-graph, world-origin separation, search-radius, and kinematics tests."""
import dataclasses

import numpy as np
import pytest

from gems69 import corridors, scoring, tips


def pair_catalogue(width, gap):
    cat = np.zeros((450, 450), bool)
    cat[20:81, 60] = True
    cat[80 + gap:161 + gap, 60 + width] = True
    return cat


@pytest.mark.parametrize("az", [0, 22.5, 45, 180, 202.5])
def test_orientation_favours_n_ne_axes(az):
    assert scoring.orientation_weight(az) == pytest.approx(1)
    assert scoring.orientation_weight(112.5) < 0.05


@pytest.mark.parametrize(
    "width,gap,accepted",
    [
        (20, 10, True),
        (160, 10, False),
        (5, 40, False),     # Fixed IR-69-TIP-01: gap=40 > 3.5 * 5 = 17.5 -> rejected!
        (50, 160, True),    # Fixed IR-69-CORR-01: hypot(50, 160)=167.6 > 150, sep <= 175 -> accepted!
    ],
)
def test_width_and_separation_limits(width, gap, accepted):
    cat = pair_catalogue(width, gap)
    pairs = corridors.build_tip_pairs(tips.vectorize(cat), cat)
    assert bool(pairs) == accepted
    for p in pairs:
        assert 1 <= p.w_px <= 150
        assert p.separation_px <= 3.5 * p.w_px + 1e-6


def test_corridors_have_reviewable_rationales():
    cat = pair_catalogue(20, 10)
    strands = tips.vectorize(cat)
    cs, pairs = corridors.build_corridors(cat, strands, cat.shape)
    assert cs and pairs
    for c in cs:
        assert {"layers", "signature", "source", "kinematic_regime"} <= c.rationale.keys()
        assert c.full_mask(cat.shape).any()


def right_step_catalogue(width=20, gap=10):
    cat = np.zeros((450, 450), bool)
    cat[90 + gap:171 + gap, 60] = True   # southern strand (west)
    cat[20:81, 60 + width] = True        # northern strand (east -> right step!)
    return cat


def test_raster_strand_schema_and_kinematics_attachment():
    fields = {f.name for f in dataclasses.fields(tips.Strand)}
    assert "dip_side" not in fields
    assert "sense" not in fields
    # True Walker Lane right-step: RL is releasing pull-apart, LL is restraining transfer
    cat = right_step_catalogue(20, 10)
    strands = tips.vectorize(cat)
    s0, s1 = strands[0], strands[1]
    kin_rl = {
        s0.sid: tips.StrandKinematics(sid=s0.sid, sense="RL", dip_vec=(1.0, 0.0)),
        s1.sid: tips.StrandKinematics(sid=s1.sid, sense="RL", dip_vec=(1.0, 0.0)),
    }
    pairs_rl = corridors.build_tip_pairs(strands, cat, kinematics=kin_rl)
    assert len(pairs_rl) == 1
    assert pairs_rl[0].kinematic_regime == "pull-apart"

    kin_ll = {
        s0.sid: tips.StrandKinematics(sid=s0.sid, sense="LL", dip_vec=(1.0, 0.0)),
        s1.sid: tips.StrandKinematics(sid=s1.sid, sense="LL", dip_vec=(1.0, 0.0)),
    }
    pairs_ll = corridors.build_tip_pairs(strands, cat, kinematics=kin_ll)
    assert len(pairs_ll) == 1
    assert pairs_ll[0].kinematic_regime == "transfer-overlap"


def test_antithetic_dips_are_rejected():
    cat = pair_catalogue(20, 10)
    strands = tips.vectorize(cat)
    s0, s1 = sorted(strands, key=lambda s: s.tip0[1])
    kin_anti = {
        s0.sid: tips.StrandKinematics(sid=s0.sid, sense="N", dip_vec=(1.0, 0.0)),
        s1.sid: tips.StrandKinematics(sid=s1.sid, sense="N", dip_vec=(-1.0, 0.0)),
    }
    assert corridors.build_tip_pairs(strands, cat, kinematics=kin_anti) == []


def test_template_metric_worked_example_formula():
    from gems57 import metric
    tp, fp, fn = 3.0, 1.89, 2.0
    assert tp / (tp + metric.ALPHA * fp + metric.BETA * fn) == pytest.approx(0.60, abs=0.005)
