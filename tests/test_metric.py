"""Verify the DTI implementation against a brute-force transcription of the organizer definitions."""
import numpy as np
import pytest

from gems import metric


def brute_components(p, g, cell=100.0, R=300.0):
    """Literal O(N^2) transcription of the published definitions (pixel-centre Euclidean distance)."""
    p = np.nan_to_num(np.asarray(p, float), nan=0.0)
    G = np.argwhere(np.asarray(g) > 0)
    X = np.argwhere(np.ones_like(p, bool))
    def k(d):
        return max(1.0 - d / R, 0.0)
    def dist(a, b):
        return cell * np.hypot(a[0] - b[0], a[1] - b[1])
    TP = 0.0
    for gi in G:
        TP += max([p[tuple(x)] * k(dist(x, gi)) for x in X] + [0.0])
    FP = 0.0
    for x in X:
        if p[tuple(x)] > 0:
            FP += p[tuple(x)] * (1.0 - max([k(dist(x, gi)) for gi in G] + [0.0]))
    FN = 0.0
    for gi in G:
        FN += 1.0 - max([p[tuple(x)] * k(dist(x, gi)) for x in X] + [0.0])
    return TP, FP, FN


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_fast_matches_bruteforce(seed):
    rng = np.random.default_rng(seed)
    g = np.zeros((12, 13), bool)
    g[rng.integers(0, 12), :] = True            # a horizontal truth line
    g[:, rng.integers(0, 13)] |= rng.random(12) < 0.4
    p = rng.random((12, 13)) * (rng.random((12, 13)) < 0.3)
    TP, FP, FN, n = metric.components(p, g)
    bTP, bFP, bFN = brute_components(p, g)
    assert n == int(g.sum())
    assert TP == pytest.approx(bTP, abs=1e-9)
    assert FP == pytest.approx(bFP, abs=1e-9)
    assert FN == pytest.approx(bFN, abs=1e-9)


def test_identity_fn_equals_gt_minus_tp():
    rng = np.random.default_rng(7)
    g = rng.random((30, 30)) < 0.05
    p = rng.random((30, 30))
    TP, FP, FN, n = metric.components(p, g)
    assert FN == pytest.approx(n - TP, abs=1e-9)


def test_perfect_and_empty_predictions():
    g = np.zeros((20, 20), bool)
    g[10, 2:18] = True
    assert metric.dti(g.astype(float), g) == pytest.approx(1.0, abs=1e-6)
    assert metric.dti(np.zeros_like(g, float), g) == pytest.approx(0.0, abs=1e-6)


def test_organizer_worked_example_formula_level():
    # Organizer page 967: TPw=3.00, FPw=1.89, FNw=2.00 -> TI=0.60 (their rounding).
    assert metric.dti_from_components(3.00, 1.89, 2.00) == pytest.approx(0.60, abs=0.005)


def test_nan_is_no_prediction():
    g = np.zeros((10, 10), bool)
    g[5, 1:9] = True
    p = np.full((10, 10), np.nan)
    p[5, 1:9] = 1.0
    assert metric.dti(p, g) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("seed", range(5))
def test_admission_rule_matches_full_recomputation(seed):
    """dot_is_worth_adding must agree in sign with the exact change in DTI for one unit dot."""
    rng = np.random.default_rng(seed)
    g = rng.random((16, 16)) < 0.04
    p = (rng.random((16, 16)) < 0.1).astype(float)
    TP, FP, FN, n = metric.components(p, g)
    D = TP + 0.2 * FP + 0.8 * FN
    base = metric.dti(p, g, eps=0.0)
    checked = 0
    for i in range(16):
        for j in range(16):
            if p[i, j] > 0:
                continue
            q = p.copy()
            q[i, j] = 1.0
            T2, F2, N2, _ = metric.components(q, g)
            d_tp = T2 - TP
            # m = max_g k(d(x,g)) at candidate pixel x
            gi = np.argwhere(g)
            dists = [100.0 * np.hypot(i - a, j - b) for a, b in gi]
            m = float(max([metric.kernel(d) for d in dists] + [0.0]))
            pred = metric.dot_is_worth_adding(TP, D, d_tp, m)
            actual = metric.dti(q, g, eps=0.0) > base
            if abs(metric.dti(q, g, eps=0.0) - base) > 1e-12:
                assert pred == actual, (i, j)
                checked += 1
    assert checked > 0
