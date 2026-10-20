"""Out-of-fold binned calibration: P(cell is withheld truth | bin) -> greedy allocator.

Every arm maps each pixel to an integer *bin code* built from its features.
Rates are fitted on the training regions only (leave-one-quadrant-out) with
empirical-Bayes shrinkage toward the training base rate (``m`` pseudo-pixels)
or hierarchical shrinkage (`d_vis` -> `(dline, d_tip, d_vis)` -> `(s_band, e_pix)`),
then looked up for the held-out region.  Quantile edges are also fitted on the
training regions, so nothing about the test region enters the calibration.
"""
from __future__ import annotations

import numpy as np

# Distance-to-catalogue bins (px = 100 m):
# (0,2] = forbidden 200 m flank; (2,4] = 200-400 m near-trace collar;
# (4,20] = 0.4-2.0 km relay-ramp / pull-apart interior (Giddens & Faulds 2025 mean width 2.8 km);
# (20,40] = 2.0-4.0 km outer step-over; (40,65], (65,inf).
D_EDGES = np.array([0, 2, 4, 20, 40, 65, np.inf], np.float64)
DLINE_EDGES = np.array([0, 1, 2, 4, 8, np.inf], np.float64)
DTIP_EDGES = np.array([0, 8, 22, 50, np.inf], np.float64)


def quantile_edges(values: np.ndarray, n: int) -> np.ndarray:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return np.array([-np.inf, np.inf])
    q = np.unique(np.quantile(v, np.linspace(0, 1, n + 1)[1:-1]))
    return np.concatenate([[-np.inf], q, [np.inf]])


def digitize(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.clip(np.searchsorted(edges, values, side="right") - 1, 0, len(edges) - 2).astype(np.int32)


def fit_rates(code: np.ndarray, truth: np.ndarray, train: np.ndarray, n_codes: int,
              m: float = 100.0) -> tuple[np.ndarray, dict]:
    c = code[train]
    y = truth[train].astype(np.float64)
    cnt = np.bincount(c, minlength=n_codes).astype(np.float64)
    pos = np.bincount(c, weights=y, minlength=n_codes)
    base = float(y.mean()) if y.size else 0.0
    rate = (pos + m * base) / np.maximum(cnt + m, 1.0)
    return rate.astype(np.float32), dict(base_rate=base, n_train=int(c.size), n_pos=int(y.sum()),
                                         max_rate=float(rate.max()) if rate.size else 0.0)


def hierarchical_codes(dline: np.ndarray, d_tip: np.ndarray, d_vis: np.ndarray,
                       s_band: np.ndarray, e_pix: np.ndarray,
                       s_edges: np.ndarray, e_edges: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, int, int]]:
    ndl = len(DLINE_EDGES) - 1
    ndt = len(DTIP_EDGES) - 1
    ndv = len(D_EDGES) - 1
    ns = len(s_edges) - 1
    ne = len(e_edges) - 1
    nse = ns * ne
    ng = ndl * ndt * ndv
    vcode = digitize(d_vis, D_EDGES)
    gcode = (digitize(dline, DLINE_EDGES) * ndt + digitize(d_tip, DTIP_EDGES)) * ndv + vcode
    se_code = digitize(s_band, s_edges) * ne + digitize(e_pix, e_edges)
    fcode = gcode * nse + se_code
    return vcode, gcode, fcode, (ndv, ng, ng * nse)


def fit_hierarchical_rates(vcode: np.ndarray, gcode: np.ndarray, fcode: np.ndarray,
                           dims: tuple[int, int, int], truth: np.ndarray, train: np.ndarray,
                           m_v: float = 100.0, m_g: float = 250.0, m_f: float = 350.0) -> tuple[np.ndarray, dict]:
    ndv, ng, nf = dims
    nse = nf // ng
    ndl_ndt = ng // ndv
    y = truth[train].astype(np.float64)
    base = float(y.mean()) if y.size else 0.0
    tv = np.bincount(vcode[train], minlength=ndv).astype(np.float64)
    pv = np.bincount(vcode[train], weights=y, minlength=ndv).astype(np.float64)
    vrate = (pv + m_v * base) / np.maximum(tv + m_v, 1.0)

    tg = np.bincount(gcode[train], minlength=ng).astype(np.float64)
    pg = np.bincount(gcode[train], weights=y, minlength=ng).astype(np.float64)
    grate = (pg + m_g * np.tile(vrate, ndl_ndt)) / np.maximum(tg + m_g, 1.0)

    tf = np.bincount(fcode[train], minlength=nf).astype(np.float64)
    pf = np.bincount(fcode[train], weights=y, minlength=nf).astype(np.float64)
    rate = ((pf + m_f * np.repeat(grate, nse)) / np.maximum(tf + m_f, 1.0)).astype(np.float32)
    return rate, dict(base_rate=base, n_train=int(y.size), n_pos=int(y.sum()),
                      max_rate=float(rate.max()) if rate.size else 0.0,
                      m_v=m_v, m_g=m_g, m_f=m_f)
