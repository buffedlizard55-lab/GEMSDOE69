"""Experiment pipeline: holdout arms, gate, leakage canary, hard-link masking test, live build.

Arms (all share the evidence layers, out-of-fold empirical-Bayes calibration,
the 2-px visible-catalogue flank exclusion, and the template's 3-px kernel
decimated greedy marginal-DTI allocator):

* ``A_corridor`` (the lane, H69-K) -- candidates inside the corridor band
  (within 6 px / 600 m of a generated trace); hierarchical empirical-Bayes posterior
  over (visible-catalogue distance x corridor-trace distance x fault-tip distance
  x H69-K corridor score quintile x pixel physics quartile).
* ``AP_halo_corridor`` (sensitivity) -- whole-footprint ``B1`` boosted by corridor
  membership & H69-K score class.
* ``B1_halo`` (gate comparator: the exact same pipeline WITHOUT corridor priors) --
  hierarchical empirical-Bayes posterior over (visible-catalogue distance x pixel
  physics decile).
* ``B0_evidence`` -- pixel physics ventiles only (no geometry at all).
* ``C_distance`` -- distance-to-visible-catalogue bin only (no physics).
* ``R_corridor_random`` -- exact same dot count as ``A_corridor`` placed at random
  (2-px Poisson disk) inside the exact same corridor band.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import ndimage as ndi

from gems57 import emit as temit

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
        self.evidence_receipt = evidence.build_cache(self.grid)
        self.layers = {n: evidence.load_layer(n) for n in evidence.ALL_CACHE_LAYERS}
        acc = np.zeros(self.fp.shape, np.float32)
        for n in evidence.LAYERS:
            acc += self.layers[n]
        self.e_pix = acc / np.float32(len(evidence.LAYERS))
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
    H, W = ctx.fp.shape
    for t in tips:
        if include_cut or not t.cut:
            r, c = int(np.floor(-t.pos[1])), int(np.floor(t.pos[0]))
            if 0 <= r < H and 0 <= c < W:
                tipmask[r, c] = True
    d_tip = (ndi.distance_transform_edt(~tipmask).astype(np.float32)
             if tipmask.any() else np.full(ctx.fp.shape, np.inf, np.float32))
    return dict(polys=polys, tips=tips, lines=lines, s_band=s_band, dline=dline, on=on,
                d_tip=d_tip, tip_receipt=trec, corridor_counts=counts)


def hierarchy_for_arm(arm: str, ctx: Context, geo: dict, d_vis: np.ndarray,
                      train: np.ndarray, edges=None):
    """Build nested empirical-Bayes code levels ``(levels, finest_code, fitted_edges)``."""
    b_vis = calibrate.digitize(d_vis, calibrate.D_EDGES)
    n_vis = len(calibrate.D_EDGES) - 1

    if arm == "B0_evidence":
        e = edges if edges is not None else calibrate.quantile_edges(ctx.e_pix[train], 20)
        c0 = calibrate.digitize(ctx.e_pix, e)
        n0 = len(e) - 1
        return [(c0, n0, 200.0)], c0, e

    if arm == "C_distance":
        return [(b_vis, n_vis, 100.0)], b_vis, None

    if arm == "B1_halo":
        e_epix = edges if edges is not None else calibrate.quantile_edges(ctx.e_pix[train], 10)
        b_ep = calibrate.digitize(ctx.e_pix, e_epix)
        n_ep = len(e_epix) - 1
        c2 = b_vis * n_ep + b_ep
        levels = [(b_vis, n_vis, 100.0), (c2, n_vis * n_ep, 300.0)]
        return levels, c2, e_epix

    if arm == "AP_halo_corridor":
        if edges is not None:
            e_epix, e_sb = edges
        else:
            e_epix = calibrate.quantile_edges(ctx.e_pix[train], 8)
            band_tr = train & (geo["s_band"] > 0)
            e_sb = (calibrate.quantile_edges(geo["s_band"][band_tr], 3)
                    if band_tr.any() else np.array([-np.inf, 0.5, np.inf]))
        b_ep = calibrate.digitize(ctx.e_pix, e_epix)
        n_ep = len(e_epix) - 1
        b_dl = calibrate.digitize(geo["dline"], calibrate.DLINE_EDGES)
        n_dl = len(calibrate.DLINE_EDGES) - 1
        b_sb = np.where(geo["s_band"] > 0, calibrate.digitize(geo["s_band"], e_sb) + 1, 0).astype(np.int32)
        n_sb = len(e_sb)
        c1 = b_vis
        c2 = c1 * n_dl + b_dl
        n2 = n_vis * n_dl
        c3 = (c2 * n_sb + b_sb) * n_ep + b_ep
        n3 = n2 * n_sb * n_ep
        levels = [(c1, n_vis, 100.0), (c2, n2, 250.0), (c3, n3, 350.0)]
        return levels, c3, (e_epix, e_sb)

    if arm == "A_corridor":
        e_sb = edges if edges is not None else calibrate.quantile_edges(
            geo["s_band"][train & (geo["s_band"] > 0)], 6
        )
        b_dl = calibrate.digitize(geo["dline"], calibrate.DLINE_EDGES)
        n_dl = len(calibrate.DLINE_EDGES) - 1
        b_dt = calibrate.digitize(geo["d_tip"], calibrate.DTIP_EDGES)
        n_dt = len(calibrate.DTIP_EDGES) - 1
        b_sb = calibrate.digitize(geo["s_band"], e_sb)
        n_sb = len(e_sb) - 1

        c1 = b_vis
        c2 = (c1 * n_dl + b_dl) * n_dt + b_dt
        n2 = n_vis * n_dl * n_dt
        c3 = c2 * n_sb + b_sb
        n3 = n2 * n_sb
        levels = [(c1, n_vis, 80.0), (c2, n2, 150.0), (c3, n3, 180.0)]
        return levels, c3, e_sb

    raise KeyError(arm)


def _codes(arm: str, ctx: Context, geo: dict, d_vis: np.ndarray, train: np.ndarray, edges=None):
    """Backward-compatible helper returning ``(finest_code, n_codes, edges)``."""
    levels, finest, fitted = hierarchy_for_arm(arm, ctx, geo, d_vis, train, edges=edges)
    return finest, levels[-1][1], fitted


def allocate_decimated_greedy(p: np.ndarray, allowed: np.ndarray, k_truth: float,
                              tile_px: int = 3) -> temit.Allocation:
    """3-px kernel-tile peak selection followed by exact template greedy_allocate."""
    ranked, _ = temit.emit_decimated(p, allowed, tile_px=tile_px, floor=1e-4)
    cand = allowed & (ranked > 0)
    return temit.greedy_allocate(p, cand, float(k_truth), floor=1e-4,
                                 max_dots=200_000, candidate_cap=400_000, per_round=40_000)


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
