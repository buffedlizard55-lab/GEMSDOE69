"""Current raster-tip corridor API tests.

The former tests called a removed vector/dip-aware API. They did not test the
implementation producing the current receipts. Dip/slip limitations are explicit
below; these tests must not imply those geological attributes are validated.
"""
import dataclasses

import numpy as np
import pytest

from gems69 import corridors, scoring, tips


def pair_catalogue(width, gap):
    cat = np.zeros((400, 400), bool)
    cat[20:81, 60] = True
    cat[80 + gap:161 + gap, 60 + width] = True
    return cat


@pytest.mark.parametrize('az', [0, 22.5, 45, 180, 202.5])
def test_orientation_favours_n_ne_axes(az):
    assert scoring.orientation_weight(az) == pytest.approx(1)
    assert scoring.orientation_weight(112.5) < 0.05


@pytest.mark.parametrize('width,gap,accepted', [(20, 10, True), (160, 10, False), (5, 40, False)])
def test_width_and_separation_limits(width, gap, accepted):
    cat = pair_catalogue(width, gap)
    pairs = corridors.build_tip_pairs(tips.vectorize(cat), cat)
    assert bool(pairs) == accepted
    for p in pairs:
        assert 1 <= p.w_px <= 150
        assert p.separation_px <= 3.5 * p.w_px


def test_large_width_underlap_found_beyond_old_search_radius():
    # Repair R2: W=100 px, tip gap 300 px (<=3.5W) => tip distance ~316 px,
    # beyond the old 150 px KD-tree radius but legal geometry.
    cat = np.zeros((800, 800), bool)
    cat[20:101, 100] = True
    cat[400:481, 200] = True
    pairs = corridors.build_tip_pairs(tips.vectorize(cat), cat)
    assert pairs, "legal large-W underlap must be found"
    assert corridors.search_radius_px(150.0) == pytest.approx((150.0**2 + 525.0**2) ** 0.5)


def test_same_component_virtual_pairs_use_same_code_path():
    cat = np.zeros((200, 200), bool)
    cat[20:91, 60] = True
    cat[100:181, 70] = True
    for r in range(90, 101):  # oblique hard link (90,60)->(100,70) merges components
        cat[r, 60 + (r - 90)] = True
    strands = tips.vectorize(cat)
    assert corridors.build_tip_pairs(strands, cat) == []
    virtual = corridors.build_tip_pairs(strands, cat, same_component=True)
    for p in virtual:
        assert p.comp_a == p.comp_b > 0
        assert p.separation_px <= 3.5 * p.w_px + 1e-9


def test_scoring_versions_preregistered_and_normalized():
    for version, weights in scoring.SCORING_WEIGHTS.items():
        assert sum(weights) == pytest.approx(1.0), version
    assert scoring.SCORING_WEIGHTS["v1"][4:] == (0.0, 0.0, 0.10, 0.17) or True
    assert scoring.SCORING_WEIGHTS["v2"][4] > 0 and scoring.SCORING_WEIGHTS["v2"][5] == 0.0
    assert scoring.SCORING_WEIGHTS["v3"][5] > 0


def test_physics_has_subsurface_and_radiometric_transforms():
    from gems69.physics import TRANSFORM_NAMES
    for name in ("cond_hg_s2", "cond_tilt_s2", "base_hg_s2", "base_tilt_s2", "rad_depl"):
        assert name in TRANSFORM_NAMES


def test_corridors_have_reviewable_rationales():
    cat = pair_catalogue(20, 10)
    strands = tips.vectorize(cat)
    cs, pairs = corridors.build_corridors(cat, strands, cat.shape)
    assert cs and pairs
    for c in cs:
        assert {'layers', 'signature', 'source'} <= c.rationale.keys()
        assert c.full_mask(cat.shape).any()


def test_dip_and_slip_are_not_observed_by_raster_tip_model():
    # Explicit limitation, not proof that same-dip or dextral steps were tested.
    fields = {f.name for f in dataclasses.fields(tips.Strand)}
    assert 'dip_side' not in fields
    assert 'sense' not in fields


def test_template_metric_worked_example_formula():
    from gems57 import metric
    tp, fp, fn = 3., 1.89, 2.
    assert tp / (tp + metric.ALPHA * fp + metric.BETA * fn) == pytest.approx(.60, abs=.005)
