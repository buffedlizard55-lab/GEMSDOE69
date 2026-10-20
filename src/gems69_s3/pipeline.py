"""Experiment pipeline: holdout arms, gate, leakage canary, hard-link masking test, live build.

Arms (all share the evidence layers, the out-of-fold calibration recipe, the
2-px flank exclusion and the template's greedy marginal-DTI allocator):

* ``A_corridor`` (the lane) -- candidates restricted to the corridor band
  (within 2 px of a generated trace); bin = corridor score decile x distance to
  the trace (0 / 1 / 2 px).
* ``AP_halo_corridor`` (sensitivity) -- ``B1`` bins x corridor class
  (none / low score / high score): the corridor prior as a *boost*.
* ``B1_halo`` (gate comparator: the same pipeline without corridor priors) --
  evidence decile x distance-to-visible-catalogue bin.
* ``B0_evidence`` -- evidence ventiles only (no geometry at all).
* ``C_distance`` -- distance-to-visible-catalogue bin only (no evidence).
* ``R_corridor_random`` -- as many dots as ``A_corridor`` placed at random
  (2 px Poisson-disk) inside the same corridor-band candidate set.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import ndimage as ndi

from . import calibrate, corridors, evidence, traces
from .data import dem, load_grid

FLANK_PX = 2.0
K_TRUTH_RATIO = 0.25          # withheld / visible ~= 0.20 / 0.80 (protocol hide fraction)
ARMS = ("A_corridor", "AP_halo_corridor", "B1_halo", "B0_evidence", "C_distance", "R_corridor_random")


class Context:
    def __init__(self):
        t0 = time.time()
        self.grid = load_grid()
        self.fp = self.grid.footprint
        self.cat = self.grid.catalogue
        self.parts = traces.load_parts()
        self.dip_receipt = traces.assign_dips(self.parts, dem(self.fp))
        self.layers = {n: evidence.load_layer(n) for n in evidence.LAYERS}
        acc = np.zeros(self.fp.shape, np.float32)
        for v in self.layers.values():
            acc += v
        self.e_pix = acc / np.float32(len(self.layers))
        self.e_pix[~self.fp] = 0
        self.setup_seconds = time.time() - t0


def geometry(ctx: Context, visible: np.ndarray, removed: np.ndarray | None, include_cut: bool = False) -> dict:
    polys = traces.visible_polys(ctx.parts, removed)
    tips, trec = traces.find_tips(polys, ctx.fp)
    lines, counts = corridors.generate(tips, polys, include_cut=include_cut)
    corridors.rasterize_lines(lines, ctx.fp, visible)
    corridors.score_lines(lines, ctx.layers)
    s_band, dline, on = corridors.corridor_fields(lines, ctx.fp.shape)
    tipmask = np.zeros(ctx.fp.shape, bool)
    for t in tips:
        if include_cut or not t.cut:
            r, c = int(np.floor(-t.pos[1])), int(np.floor(t.pos[0]))
            tipmask[r, c] = True
    d_tip = ndi.distance_transform_edt(~tipmask).astype(np.float32) if tipmask.any() else np.full(ctx.fp.shape, np.inf, np.float32)
    return dict(polys=polys, tips=tips, lines=lines, s_band=s_band, dline=dline, on=on,
                d_tip=d_tip, tip_receipt=trec, corridor_counts=counts)


def _codes(arm: str, ctx: Context, geo: dict, d_vis: np.ndarray, train: np.ndarray, edges=None):
    """Integer bin code per pixel for an arm.

    Edges are fitted on ``train`` pixels only, or taken from ``edges`` (frozen
    holdout edges reused for the live build).  Returns ``(code, n_codes, edges)``.
    """
    if arm == "B0_evidence":
        e = edges if edges is not None else calibrate.quantile_edges(ctx.e_pix[train], 20)
        return calibrate.digitize(ctx.e_pix, e), len(e) - 1, e
    if arm == "C_distance":
        return calibrate.digitize(d_vis, calibrate.D_EDGES), len(calibrate.D_EDGES) - 1, None
    nd = len(calibrate.D_EDGES) - 1
    if arm in ("B1_halo", "AP_halo_corridor"):
        if edges is not None:
            e, med = edges
        else:
            e = calibrate.quantile_edges(ctx.e_pix[train], 10)
            band0 = geo["s_band"] > 0
            med = float(np.median(geo["s_band"][train & band0])) if (train & band0).any() else 0.5
        ne = len(e) - 1
        code = calibrate.digitize(ctx.e_pix, e) * nd + calibrate.digitize(d_vis, calibrate.D_EDGES)
        n = ne * nd
        if arm == "AP_halo_corridor":
            band = geo["s_band"] > 0
            cls = np.where(band, np.where(geo["s_band"] > med, 2, 1), 0).astype(np.int32)
            code = code * 3 + cls
            n *= 3
        return code.astype(np.int32), n, (e, med)
    if arm == "A_corridor":
        band = geo["s_band"] > 0
        e = edges if edges is not None else calibrate.quantile_edges(geo["s_band"][train & band], 10)
        ne = len(e) - 1
        dp = np.clip(np.rint(geo["dline"]), 0, 2).astype(np.int32)
        code = calibrate.digitize(geo["s_band"], e) * 3 + dp
        return code.astype(np.int32), ne * 3, e
    raise KeyError(arm)


def poisson_random(allowed: np.ndarray, n: int, seed: int, radius: int = 2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    cand = np.flatnonzero(allowed)
    rng.shuffle(cand)
    H, W = allowed.shape
    occ = np.zeros(allowed.shape, bool)
    out = np.zeros(allowed.shape, bool)
    k = 0
    for f in cand:
        if k >= n:
            break
        y, x = divmod(int(f), W)
        if occ[y, x]:
            continue
        out[y, x] = True
        occ[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1] = True
        k += 1
    return out


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    from scipy.stats import rankdata
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))
