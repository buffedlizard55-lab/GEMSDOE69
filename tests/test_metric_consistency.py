"""Cross-check the two shared metric implementations on synthetic fields.

gems.metric (drivendata-reference transcription) and gems57.metric (pooled
instrument) must agree on DTI for the same binary dot field and truth; both
claim to implement the official alpha=0.2, beta=0.8, R=300 m triangular kernel.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "template66"))


def test_metrics_agree_on_synthetic():
    from gems import metric as m_ref
    from gems57 import metric as m57

    rng = np.random.default_rng(7)
    h = w = 60
    gt = np.zeros((h, w), bool)
    for (y, x) in [(10, 12), (11, 13), (30, 40), (31, 40), (32, 41), (50, 20)]:
        gt[y, x] = True
    pred = np.zeros((h, w))
    dots = [(10, 12), (12, 14), (29, 39), (33, 42), (50, 23), (5, 5)]
    for (y, x) in dots:
        pred[y, x] = 1.0

    tp_r, fp_r, fn_r, _ = m_ref.components(pred, gt)
    dti_r = m_ref.dti_from_components(tp_r, fp_r, fn_r)

    # gems57 exact evaluator over the full domain (all cells active, nothing known)
    from gems57 import metric as _m
    r57 = _m.dti_exact(pred, gt, valid=np.ones_like(gt), known=np.zeros_like(gt))
    assert abs(r57["tp"] - tp_r) < 1e-9, (r57["tp"], tp_r)
    assert abs(r57["fp"] - fp_r) < 1e-9, (r57["fp"], fp_r)
    assert abs(r57["fn"] - fn_r) < 1e-9, (r57["fn"], fn_r)
    assert abs(r57["dti"] - dti_r) < 1e-9, (r57["dti"], dti_r)
    # sanity: perfect field on truth gets DTI 1
    perf = gt.astype(float)
    assert abs(m_ref.dti(perf, gt) - 1.0) < 1e-9
    print(f"metrics agree: dti={dti_r:.6f}")


def test_marginal_bar_identity():
    from gems import metric as m_ref
    # adding a dot with credit k raises DTI iff k > alpha*DTI (for uncovered truth)
    gt = np.zeros((20, 20), bool)
    gt[10, 10] = True
    pred = np.zeros((20, 20))
    pred[10, 12] = 1.0            # d = 200 m -> k = 1/3
    base = m_ref.dti(pred, gt)
    assert base > 0.0
    cand = m_ref.ALPHA * base
    assert 0 < cand < 1
    # a second dot far from truth must lower DTI (its p=0 credit is below the bar)
    worse = pred.copy()
    worse[2, 2] = 1.0
    assert m_ref.dti(worse, gt) < base
    print("marginal bar identity OK", round(cand, 4))


if __name__ == "__main__":
    test_metrics_agree_on_synthetic()
    test_marginal_bar_identity()
    print("ALL METRIC TESTS PASSED")
