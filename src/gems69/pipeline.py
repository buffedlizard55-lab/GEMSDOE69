"""Experiment pipeline: holdout arms, gate, leakage canary, hard-link masking test, live build.

Arms (all share the evidence layers, the out-of-fold calibration recipe, the
2-px flank exclusion and the 3-px tile-decimated greedy marginal-DTI allocator):

* ``A_corridor`` (the lane) -- candidates restricted to the corridor band
  (``dline <= 8 px`` of a generated relay-ramp, pull-apart, or displacement-
  transfer strand); 3-level hierarchical empirical-Bayes calibration on
  ``(dline, d_tip, d_vis, s_band, e_pix)``.
* ``AP_halo_corridor`` (sensitivity) -- full allowed domain with the same
  3-level hierarchical corridor calibration (corridor prior as a boost).
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
BAND_MAX_PX = 8.0
FIELD_BAND_PX = 12.0
TILE_PX = 3
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
    lines, counts = corridors.generate(tips, polys, include_cut=include_cut, max_partners=4, include_splays=True)
    corridors.rasterize_lines(lines, ctx.fp, visible)
    corridors.score_lines(lines, ctx.layers)
    s_band, dline, on = corridors.corridor_fields(lines, ctx.fp.shape, band_px=FIELD_BAND_PX)
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
    holdout edges reused for the live build).
    """
    if arm == "B0_evidence":
        e = edges if edges is not None else calibrate.quantile_edges(ctx.e_pix[train], 20)
        return calibrate.digitize(ctx.e_pix, e), len(e) - 1, e
    if arm == "C_distance":
        return calibrate.digitize(d_vis, calibrate.D_EDGES), len(calibrate.D_EDGES) - 1, None
    nd = len(calibrate.D_EDGES) - 1
    if arm == "B1_halo":
        e = edges if edges is not None else calibrate.quantile_edges(ctx.e_pix[train], 10)
        ne = len(e) - 1
        code = calibrate.digitize(ctx.e_pix, e) * nd + calibrate.digitize(d_vis, calibrate.D_EDGES)
        return code.astype(np.int32), ne * nd, e
    if arm in ("A_corridor", "AP_halo_corridor"):
        band = geo["dline"] <= BAND_MAX_PX
        if edges is not None:
            s_edges, e_edges = edges
        else:
            s_edges = calibrate.quantile_edges(geo["s_band"][train & band], 4)
            e_edges = calibrate.quantile_edges(ctx.e_pix[train & band], 4)
        vcode, gcode, fcode, dims = calibrate.hierarchical_codes(
            geo["dline"], geo["d_tip"], d_vis, geo["s_band"], ctx.e_pix, s_edges, e_edges
        )
        return (vcode, gcode, fcode, dims), dims[2], (s_edges, e_edges)
    raise KeyError(arm)


def fit_arm_rates(arm: str, code_info, truth: np.ndarray, cand_train: np.ndarray, n_codes: int):
    if arm in ("A_corridor", "AP_halo_corridor"):
        vcode, gcode, fcode, dims = code_info
        rate, calib = calibrate.fit_hierarchical_rates(vcode, gcode, fcode, dims, truth, cand_train)
        return fcode, rate, calib
    rate, calib = calibrate.fit_rates(code_info, truth, cand_train, n_codes, m=100.0)
    return code_info, rate, calib


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


def emit_decimated(p: np.ndarray, cand_mask: np.ndarray, k_truth: float, tile_px: int = TILE_PX):
    """Select the highest-rate candidate in each tile_px x tile_px cell before greedy allocation."""
    from gems57 import emit
    if tile_px <= 1:
        return emit.greedy_allocate(p, cand_mask, k_truth)
    ranked, _ = emit.emit_decimated(p, cand_mask, tile_px=tile_px)
    return emit.greedy_allocate(p, cand_mask & (ranked > 0), float(k_truth))
