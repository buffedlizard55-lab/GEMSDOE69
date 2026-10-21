"""Out-of-fold empirical-Bayes binned calibration -> template greedy allocator.

Every arm maps each pixel to hierarchical integer bin codes built strictly from
visible features.  Rates are fitted on training regions only (leave-one-quadrant
out) via 3-stage empirical-Bayes shrinkage so fine bins with sparse counts shrink
smoothly toward coarser structural/distance bins rather than noisy zero/one spikes.
"""
from __future__ import annotations

import numpy as np

D_EDGES = np.array([0, 3, 4, 6, 9, 13, 20, 30, 50, 80, np.inf], np.float64)            # px to visible catalogue
DLINE_EDGES = np.array([0, 1.05, 2.25, 4.05, 6.05, 8.05, 10.05, np.inf], np.float64)    # px to corridor trace
DTIP_EDGES = np.array([0, 6.0, 15.0, 35.0, np.inf], np.float64)                         # px to free fault tip


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


def fit_hierarchical_rates(codes_hierarchy: list[tuple[np.ndarray, int, float]],
                           truth: np.ndarray, train: np.ndarray) -> tuple[np.ndarray, dict]:
    """Multi-level empirical-Bayes shrinkage across nested bin refinements.

    ``codes_hierarchy`` is ``[(code_l, n_codes_l, m_l), ...]`` from coarsest to
    finest, where each ``code_{l}`` deterministically refines ``code_{l-1}``
    (i.e. ``code_l // stride_l == code_{l-1}``).  Returns the finest rate table
    aligned to ``codes_hierarchy[-1][0]``.
    """
    y = truth[train].astype(np.float64)
    base = float(y.mean()) if y.size else 0.0
    prev_rate_at_obs = np.full(y.size, base, dtype=np.float64)
    prev_table = None
    prev_code = None

    for code, n_codes, m in codes_hierarchy:
        c = code[train]
        cnt = np.bincount(c, minlength=n_codes).astype(np.float64)
        pos = np.bincount(c, weights=y, minlength=n_codes)
        # Prior per fine bin from its parent bin
        if prev_table is None:
            prior = np.full(n_codes, base, dtype=np.float64)
        else:
            # Map each fine bin to parent bin via stride factor
            stride = max(1, n_codes // len(prev_table))
            parent_idx = np.clip(np.arange(n_codes) // stride, 0, len(prev_table) - 1)
            prior = prev_table[parent_idx]
        table = (pos + m * prior) / (cnt + m)
        prev_table = table
        prev_code = c

    assert prev_table is not None
    return prev_table.astype(np.float32), dict(
        base_rate=base,
        n_train=int(y.size),
        n_pos=int(y.sum()),
        n_bins=int(len(prev_table)),
        max_rate=float(prev_table.max()) if prev_table.size else 0.0,
        min_rate=float(prev_table.min()) if prev_table.size else 0.0,
    )
