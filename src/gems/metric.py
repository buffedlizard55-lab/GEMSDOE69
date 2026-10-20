"""Distance-weighted Tversky index (DTI) exactly as published by the organizer.

Source (checked 2026-10-12): DrivenData GEMS competition homepage; navigate to Problem Description for the metric definition.
  TPw = sum_{g in G} max_x p(x) k(d(x,g))
  FPw = sum_{x: p(x)>0} p(x) [1 - max_{g in G} k(d(x,g))]
  FNw = sum_{g in G} [1 - max_{x: d(x,g)<=R} p(x) k(d(x,g))]
  DTI = TPw / (TPw + alpha*FPw + beta*FNw + eps),  alpha=0.2, beta=0.8, R=300 m
  k(d) = max(1 - d/R, 0)   (triangular kernel)

Consequence used below (derived from the definitions above, checked in tests):
  FNw = |G| - TPw  exactly, so  DTI = T / ((1-beta) T + alpha FP + beta |G|).

Labels: every number produced here is a LOCAL computation. It is HOLDOUT-DTI only when
it is computed on withheld labels; it is never an organizer score.
"""
from __future__ import annotations

import numpy as np

ALPHA = 0.2
BETA = 0.8
R_METRES = 300.0
EPS = 1e-9


def kernel(d, radius: float = R_METRES):
    """Triangular kernel k(d) = max(1 - d/R, 0)."""
    return np.maximum(1.0 - np.asarray(d, dtype=float) / radius, 0.0)


def _offsets(cell_m: float, radius: float):
    """All pixel offsets (a, b) whose centre distance is < radius, with kernel weight."""
    n = int(np.ceil(radius / cell_m))
    out = []
    for a in range(-n, n + 1):
        for b in range(-n, n + 1):
            d = cell_m * np.hypot(a, b)
            k = float(kernel(d, radius))
            if k > 0.0:
                out.append((a, b, k))
    return n, out


def components(p, g, cell_m: float = 100.0, radius: float = R_METRES):
    """Return (TPw, FPw, FNw, n_gt) for prediction p in [0,1] and binary truth g.

    NaN in p is treated as 'no prediction' (0). Vectorised over the raster; the
    maximum over neighbours uses every offset with a positive kernel weight.
    """
    p = np.asarray(p, dtype=float)
    G = np.asarray(g) > 0
    if p.shape != G.shape:
        raise ValueError(f"shape mismatch: p {p.shape} vs g {G.shape}")
    if np.isinf(p).any():
        raise ValueError("prediction contains infinite values")
    finite_p = p[np.isfinite(p)]
    if finite_p.size and (finite_p.min() < 0.0 or finite_p.max() > 1.0):
        raise ValueError("finite predictions must be in [0, 1]")
    if not np.isfinite(cell_m) or cell_m <= 0 or not np.isfinite(radius) or radius <= 0:
        raise ValueError("cell_m and radius must be finite and positive")
    p = np.nan_to_num(p, nan=0.0, posinf=0.0, neginf=0.0)
    H, W = p.shape
    n, offs = _offsets(cell_m, radius)
    Pp = np.pad(p, n, mode="constant", constant_values=0.0)
    Gp = np.pad(G.astype(float), n, mode="constant", constant_values=0.0)

    tp_best = np.zeros((H, W))   # per truth pixel: max_x p(x) k(d)
    maxk_x = np.zeros((H, W))    # per predicted pixel: max_g k(d(x,g))
    for a, b, k in offs:
        ps = Pp[n + a: n + a + H, n + b: n + b + W]   # p at g + (a,b)
        np.maximum(tp_best, ps * k, out=tp_best)
        gs = Gp[n + a: n + a + H, n + b: n + b + W]   # G at x + (a,b)
        np.maximum(maxk_x, gs * k, out=maxk_x)

    tp_best = np.where(G, tp_best, 0.0)
    TP = float(tp_best[G].sum())
    FN = float((1.0 - tp_best[G]).sum())
    FP = float((p * (1.0 - maxk_x)).sum())
    return TP, FP, FN, int(G.sum())


def dti(p, g, cell_m: float = 100.0, radius: float = R_METRES,
        alpha: float = ALPHA, beta: float = BETA, eps: float = EPS) -> float:
    """Distance-weighted Tversky index of prediction p against truth g."""
    TP, FP, FN, _ = components(p, g, cell_m=cell_m, radius=radius)
    return TP / (TP + alpha * FP + beta * FN + eps)


def dti_from_components(tp: float, fp: float, fn: float,
                        alpha: float = ALPHA, beta: float = BETA, eps: float = EPS) -> float:
    """Formula-level check: TP / (TP + alpha FP + beta FN + eps)."""
    return tp / (tp + alpha * fp + beta * fn + eps)


def tversky_terms(pred, gt, cell_m: float = 100.0, range_m: float = R_METRES):
    """Return (tp, fp, fn) for compatibility with template consistency tests."""
    tp, fp, fn, _ = components(pred, gt, cell_m=cell_m, radius=range_m)
    return tp, fp, fn


def dti_from_terms(tp: float, fp: float, fn: float, alpha: float = ALPHA, beta: float = BETA, eps: float = EPS) -> float:
    return dti_from_components(tp, fp, fn, alpha=alpha, beta=beta, eps=eps)


def marginal_credit_bar(dti_value: float, alpha: float = ALPHA) -> float:
    """Break-even kernel credit for one extra dot."""
    return alpha * dti_value


def dot_is_worth_adding(T: float, D: float, d_tp: float, m: float,
                        alpha: float = ALPHA, beta: float = BETA) -> bool:
    """Exact admission test for adding ONE unit-mass dot to a prediction.

    T  : current TPw
    D  : current denominator TPw + alpha*FPw + beta*FNw (no eps)
    d_tp: increase of TPw the dot would cause (sum over truth pixels of the gain in
          their best-covering weight)
    m  : max_g k(d(x,g)) at the candidate pixel x (how much of the dot's mass is
          already 'explained' by truth; the FP cost of the dot is (1 - m))

    Derivation: adding the dot gives T' = T + d_tp and D' = D + d_tp(1-beta) + alpha(1-m).
    DTI' > DTI  <=>  d_tp (D - (1-beta) T) > alpha T (1 - m).
    Verified against full recomputation in tests/test_metric.py.
    """
    return d_tp * (D - (1.0 - beta) * T) > alpha * T * (1.0 - m)


def tversky_terms(pred, gt, pixel_m: float = 100.0, range_m: float = R_METRES):
    """Return (TP_w, FP_w, FN_w) matching vendor/template66/gems/metric.py."""
    tp, fp, fn, _ = components(pred, gt, cell_m=pixel_m, radius=range_m)
    return tp, fp, fn


def dti_from_terms(tp: float, fp: float, fn: float, alpha: float = ALPHA,
                   beta: float = BETA, eps: float = EPS) -> float:
    return dti_from_components(tp, fp, fn, alpha=alpha, beta=beta, eps=eps)


def marginal_credit_bar(dti_value: float, alpha: float = ALPHA) -> float:
    """Break-even kernel credit for one isolated dot on uncovered truth: k > alpha * DTI."""
    return alpha * dti_value

