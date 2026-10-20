"""Unit tests for the tip-graph pairing arithmetic (synthetic step-overs)."""
import numpy as np
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "vendor" / "template66") not in sys.path:
    sys.path.append(str(ROOT / "vendor" / "template66"))

from gems69.tips import vectorize, axial_deg, axial_diff, axial_mean
from gems69.corridors import build_tip_pairs, build_corridors


def strand_vline(cat, r0, r1, c):
    cat[r0:r1 + 1, c] = True


def test_two_parallel_north_strands_stepover():
    cat = np.zeros((200, 200), bool)
    strand_vline(cat, 20, 90, 60)     # strand A: rows 20..90 at col 60
    strand_vline(cat, 110, 180, 80)   # strand B: rows 110..180 at col 80
    strands = vectorize(cat)
    assert len(strands) == 2, f"expected 2 strands, got {len(strands)}"
    pairs = build_tip_pairs(strands, cat)
    assert len(pairs) >= 1, "expected at least one step-over pair"
    p = pairs[0]
    assert abs(p.w_px - 20.0) <= 1.5, f"spacing W should be ~20 px, got {p.w_px}"
    assert abs(abs(p.along_px) - 20.0) <= 2.0, f"along sep should be ~20 px, got {p.along_px}"
    assert abs(p.dtheta) <= 5.0, f"strikes both N-S, dtheta={p.dtheta}"
    assert abs(p.along_px) <= 3.5 * p.w_px
    assert p.dilatational, "gap step-over (no overlap) must be dilatational"
    corridors, uniq = build_corridors(cat, strands, cat.shape)
    assert len(corridors) == len(uniq) >= 1
    c0 = corridors[0]
    assert c0.local_mask.sum() > 0
    assert c0.full_mask(cat.shape).sum() == c0.local_mask.sum()
    assert set(c0.rationale) >= {"layers", "signature", "source", "w_km", "along_km"}
    print("test_two_parallel_north_strands_stepover: p.w=", p.w_px, "along=", p.along_px,
          "dilat=", p.dilatational, "subtype=", c0.subtype)


def test_reject_too_far():
    cat = np.zeros((400, 400), bool)
    strand_vline(cat, 20, 60, 60)
    strand_vline(cat, 260, 300, 80)   # tip gap 200 px > 150 px limit
    strands = vectorize(cat)
    pairs = build_tip_pairs(strands, cat)
    assert len(pairs) == 0, f"expected no pairs for 200 px gap, got {len(pairs)}"
    print("test_reject_too_far: ok")


def test_reject_crossing_strikes():
    cat = np.zeros((200, 200), bool)
    strand_vline(cat, 20, 90, 100)                     # N-S strand
    cat[110, 60:140] = True                            # E-W strand, tip near? -> strike 90 deg
    strands = vectorize(cat)
    pairs = build_tip_pairs(strands, cat)
    for p in pairs:
        assert p.dtheta <= 30.0
    assert len(pairs) == 0, f"E-W vs N-S must be rejected, got {len(pairs)}"
    print("test_reject_crossing_strikes: ok")


def test_overlap_pair():
    cat = np.zeros((200, 200), bool)
    strand_vline(cat, 20, 120, 60)   # A extends DOWN past B's top tip
    strand_vline(cat, 100, 180, 80)  # B starts above A's bottom tip -> overlap
    strands = vectorize(cat)
    pairs = build_tip_pairs(strands, cat)
    # A bottom tip (120,60) vs B top tip (100,80): along = +? B tip is NORTH of A tip
    assert len(pairs) >= 1, "overlapping tips must still pair"
    p = pairs[0]
    assert p.w_px <= 150
    print("test_overlap_pair: along=", p.along_px, "w=", p.w_px)


def test_same_component_excluded():
    cat = np.zeros((200, 200), bool)
    strand_vline(cat, 20, 90, 60)
    strand_vline(cat, 90, 180, 80)
    cat[90, 60:81] = True   # linking strand sharing row 90 -> single component
    strands = vectorize(cat)
    pairs = build_tip_pairs(strands, cat)
    assert len(pairs) == 0, "tips within one connected component must not pair"
    print("test_same_component_excluded: ok")


def test_hard_linked_detection_present():
    """A linking strand between the flanks must be detectable for the recovery test."""
    cat = np.zeros((200, 200), bool)
    strand_vline(cat, 20, 90, 60)
    strand_vline(cat, 100, 180, 70)
    for r in range(90, 101):        # oblique linking fault (90,60) -> (100,70), slope 1
        cat[r, 60 + (r - 90)] = True
    from scipy import ndimage as ndi
    comp, n = ndi.label(cat, structure=np.ones((3, 3), int))
    assert n == 1, f"linking strand should merge the system, got {n} components"
    print("test_hard_linked_detection_present: ok (n=1)")


def test_axial_helpers():
    assert abs(axial_deg(1.0, 0.0) - 90.0) < 1e-9
    assert abs(axial_deg(0.0, 1.0) - 0.0) < 1e-9
    assert abs(axial_diff(10.0, 170.0) - 20.0) < 1e-9
    m = axial_mean([5.0, 175.0])
    assert abs(m - 180.0) < 1e-6 or abs(m - 0.0) < 1e-6, m
    print("test_axial_helpers: ok")


if __name__ == "__main__":
    test_axial_helpers()
    test_two_parallel_north_strands_stepover()
    test_reject_too_far()
    test_reject_crossing_strikes()
    test_overlap_pair()
    test_same_component_excluded()
    test_hard_linked_detection_present()
    print("ALL TIP-GRAPH TESTS PASSED")
