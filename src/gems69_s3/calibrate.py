"""Out-of-fold binned calibration: P(cell is withheld truth | bin) -> greedy allocator.

Every arm maps each pixel to an integer *bin code* built from its features.
Rates are fitted on the training regions only (leave-one-quadrant-out) with a
light shrinkage toward the training base rate (``m`` pseudo-pixels), then
looked up for the held-out region.  Quantile edges are also fitted on the
training regions, so nothing about the test region enters the calibration.
"""
from __future__ import annotations

import numpy as np

D_EDGES = np.array([0, 3, 4, 6, 9, 13, 20, 30, 50, 80, np.inf], np.float64)   # px to visible catalogue


def quantile_edges(values: np.ndarray, n: int) -> np.ndarray:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return np.array([-np.inf, np.inf])
    q = np.unique(np.quantile(v, np.linspace(0, 1, n + 1)[1:-1]))
    return np.concatenate([[-np.inf], q, [np.inf]])


def digitize(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.clip(np.searchsorted(edges, values, side="right") - 1, 0, len(edges) - 2).astype(np.int32)


def fit_rates(code: np.ndarray, truth: np.ndarray, train: np.ndarray, n_codes: int,
              m: float = 200.0) -> tuple[np.ndarray, dict]:
    c = code[train]
    y = truth[train].astype(np.float64)
    cnt = np.bincount(c, minlength=n_codes).astype(np.float64)
    pos = np.bincount(c, weights=y, minlength=n_codes)
    base = float(y.mean()) if y.size else 0.0
    rate = (pos + m * base) / (cnt + m)
    return rate.astype(np.float32), dict(base_rate=base, n_train=int(c.size), n_pos=int(y.sum()),
                                         max_rate=float(rate.max()) if rate.size else 0.0)
