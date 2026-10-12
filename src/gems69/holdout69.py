"""Holdout pipeline for the corridor lane (reuses the shared template fold
instrument byte-pinned in vendor/template66; nothing here re-implements DTI).

Arms compared on identical folds:
  * corridor arm  : propensity from the visible-catalogue tip graph (this lane)
  * control arm   : same physics evidence layers, identical weight budget, but
                    NO corridor prior (per-pixel composite over the footprint)
Gate: the corridor arm must beat the control arm on pooled DTI (paired over
folds, CI reported).  Every number produced here is HOLDOUT-DTI class.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from gems57 import grid as tgrid
from gems57 import holdout as thold
from gems57.emit import greedy_allocate

from .corridors import build_corridors
from .physics import (TRANSFORM_NAMES, build_layer_stats, compute_transform,
                      corridor_evidence)
from .scoring import (GRAV_LAYERS, LIDAR_LAYERS, MAGLOW_LAYERS, MAG_LAYERS,
                      W_GRAV, W_GEOM, W_LIDAR, W_MAG, W_MAGLOW, W_ORIENT,
                      build_propensity, propensity_from_score, score_corridor)
from .tips import vectorize

ROOT = Path(__file__).resolve().parents[2]
FLANK_PX = 2            # catalogue flank exclusion (200 m), as in h33-2-b2


def load_template_grid():
    return tgrid.load_grid(data_dir=ROOT / "data" / "bridge")


def corridor_pipeline(catalogue: np.ndarray, shape: tuple[int, int], stats: dict,
                      max_corridors: int = 4000):
    """Vectorize -> tip pairs -> corridors -> scored rationale -> propensity."""
    strands = vectorize(catalogue)
    corridors, pairs = build_corridors(catalogue, strands, shape,
                                       max_corridors=max_corridors)
    t0 = time.time()
    for c in corridors:
        ev = corridor_evidence(c, stats, shape=shape)
        score_corridor(c, ev)
    p = build_propensity(corridors, shape)
    return dict(strands=len(strands), pairs=len(pairs), corridors=len(corridors),
                propensity=p, corridors_obj=corridors,
                score_seconds=round(time.time() - t0, 1))


def emit_dots(p: np.ndarray, allowed: np.ndarray, k_truth: int) -> np.ndarray:
    """Calibrated greedy marginal-DTI dot placement (shared template allocator)."""
    alloc = greedy_allocate(np.asarray(p, np.float32), allowed, k_truth,
                            floor=0.05, max_dots=250_000, candidate_cap=300_000)
    return alloc.emitted


def cell_allowed(cell, shape) -> np.ndarray:
    full = np.zeros(shape, bool)
    full[cell.bbox] = cell.active
    return full


def run_holdout_arms(ctx, stats, modes=("all",), flank_px: int = FLANK_PX,
                     s0: float | None = None):
    """Corridor vs control arm on every cell; returns per-cell results."""
    from .scoring import S0_DEFAULT
    s0 = S0_DEFAULT if s0 is None else s0
    shape = ctx.grid.footprint.shape
    catalogue = ctx.grid.catalogue
    d_cat = ndi.distance_transform_edt(~catalogue)
    offcat = d_cat > flank_px

    # ---- control propensity: same layers, no corridor prior (full grid) -----
    ctrl_layers = ["grav_hg_s2", "grav_tilt_s2", "mag_hg_s2", "mag_tilt_s2",
                   "mag_low_tmi", "mag_low_rtp", "lidar_scarp"]
    C = np.zeros(shape, np.float32)
    for name in ctrl_layers:
        t = compute_transform(name)
        z = np.clip(stats[name].z(t), -8, 8)
        z = np.where(np.isfinite(z), z, 0.0).astype(np.float32)
        C += z
        del t, z
    C /= len(ctrl_layers)
    p_ctrl = (1.0 / (1.0 + np.exp(-1.5 * (C - s0)))).astype(np.float32)
    p_ctrl[~ctx.grid.footprint] = 0.0

    results = {}
    for cell in ctx.cells:
        if cell.mode not in modes:
            continue
        key = cell.key
        visible = ctx.visible(key)
        vis_safe = visible & (ndi.distance_transform_edt(~ctx.hidden_by_cell[key]) > 0)
        pipe = corridor_pipeline(vis_safe, shape, stats)
        p_cor = pipe["propensity"]
        allowed = cell_allowed(cell, shape) & offcat
        allowed_ctrl = allowed.copy()

        em_cor = emit_dots(p_cor, allowed & (p_cor > 0), cell.n_truth)
        em_ctrl = emit_dots(p_ctrl, allowed_ctrl & (p_ctrl > 0), cell.n_truth)
        r_cor = thold.score_cell(cell, em_cor)
        r_ctrl = thold.score_cell(cell, em_ctrl)
        results[key] = dict(
            corridor=dict(dti=r_cor["dti"], coverage=r_cor["coverage"],
                          n_dots=int((em_cor & allowed).sum()),
                          n_corridors=pipe["corridors"], n_pairs=pipe["pairs"],
                          n_truth=cell.n_truth),
            control=dict(dti=r_ctrl["dti"], coverage=r_ctrl["coverage"],
                         n_dots=int((em_ctrl & allowed_ctrl).sum()),
                         n_truth=cell.n_truth),
        )
    return results


def pooled_from_results(results: dict, arm: str) -> dict:
    dtis = np.array([results[k][arm]["dti"] for k in sorted(results)])
    return dict(mean_dti=float(dtis.mean()), std_dti=float(dtis.std(ddof=1)),
                ci95_half=1.96 * float(dtis.std(ddof=1)) / np.sqrt(len(dtis)),
                n_cells=len(dtis), per_cell={k: results[k][arm]["dti"] for k in sorted(results)},
                dots=[results[k][arm]["n_dots"] for k in sorted(results)],
                n_truth=[results[k][arm]["n_truth"] for k in sorted(results)])


def leakage_canary(ctx, stats, max_neg: int = 200_000, seed: int = 69) -> dict:
    """Single-feature AUC vs pooled withheld truth (seed 20, mode 'all').

    AUC > 0.90 for any feature = leakage until proven otherwise (protocol 4).
    Physics layers are catalogue-independent by construction; the corridor
    membership surface is the catalogue-derived feature under test.
    """
    from .scoring import build_propensity
    shape = ctx.grid.footprint.shape
    cells = [c for c in ctx.cells if "draw20" in c.key and c.mode == "all"]
    truth = np.zeros(shape, bool)
    active = np.zeros(shape, bool)
    for cell in cells:
        h = ctx.hidden_by_cell[cell.key]
        full_active = cell_allowed(cell, shape)
        truth |= h & full_active
        active |= full_active
    neg_pool = np.nonzero(active & ~truth)
    rng = np.random.default_rng(seed)
    n_neg = min(max_neg, len(neg_pool[0]))
    sel = rng.choice(len(neg_pool[0]), size=n_neg, replace=False)
    ny, nx = neg_pool[0][sel], neg_pool[1][sel]
    ty, tx = np.nonzero(truth)
    out = {}
    names = list(TRANSFORM_NAMES) + ["corridor_propensity"]
    cor_pipe = corridor_pipeline(ctx.grid.catalogue, shape, stats)  # FULL catalogue:
    # canary runs on the unsplit catalogue to measure the surface itself, not a fold view
    p_cor = cor_pipe["propensity"]
    for name in names:
        if name == "corridor_propensity":
            vals_t = p_cor[ty, tx].astype(np.float64)
            vals_n = p_cor[ny, nx].astype(np.float64)
        else:
            t = compute_transform(name)
            vals_t = t[ty, tx].astype(np.float64)
            vals_n = t[ny, nx].astype(np.float64)
        fin = np.isfinite(vals_t) & np.isfinite(vals_n)
        a, b = vals_t[fin], vals_n[fin]
        if a.size < 10 or b.size < 10:
            out[name] = dict(auc=None, note="degenerate")
            continue
        allv = np.concatenate([a, b])
        ranks = np.argsort(np.argsort(allv, kind="mergesort"), kind="mergesort") + 1.0
        # average ranks for ties
        order = np.argsort(allv, kind="mergesort")
        sorted_v = allv[order]
        _, idx, counts = np.unique(sorted_v, return_index=True, return_counts=True)
        avg_rank = np.empty_like(ranks)
        cum = np.cumsum(ranks[order])
        for i0, cnt in zip(idx, counts):
            avg_rank[order[i0:i0 + cnt]] = (cum[i0 + cnt - 1] - (cum[i0 - 1] if i0 else 0.0)) / cnt
        rank_sum_t = avg_rank[: a.size].sum()
        auc = (rank_sum_t - a.size * (a.size + 1) / 2.0) / (a.size * b.size)
        out[name] = dict(auc=float(auc), n_pos=int(a.size), n_neg=int(b.size))
    out["_truth_px"] = int(truth.sum())
    out["_corridors"] = cor_pipe["corridors"]
    return out


def hardlinked_recovery(catalogue: np.ndarray, shape: tuple[int, int], stats: dict,
                        max_ramps: int = 40, w_max: float = 60.0) -> dict:
    """Mask known linking faults in hard-linked ramps; test corridor recovery
    within 3 px (300 m) of the masked trace.

    Operational definition: a 'virtual pair' is a geometrically valid tip pair
    whose two tips belong to the SAME 8-connected component (i.e. the tips are
    linked elsewhere by mapped faulting - a hard-linked ramp).  The catalogue
    pixels inside the pair's corridor that belong to neither flank strand are
    masked, the corridor is rebuilt from the remaining visible catalogue, and
    recovery = fraction of masked linking pixels within 3 px of the rebuilt
    corridor.
    """
    from .corridors import build_tip_pairs, corridor_from_pair
    strands = vectorize(catalogue)
    pairs = build_tip_pairs(strands, catalogue, w_max=w_max)
    same = [p for p in pairs if p.comp_a == p.comp_b and p.comp_a > 0]
    # build_tip_pairs currently skips same-component pairs; regenerate without the filter
    # by calling the geometry directly on the tip list:
    from .corridors import (_component_ids, _tip_window_interval, TipPair,
                            ALONG_MAX_RATIO, DILATATION_MAX_ALONG, MAX_DTHETA,
                            OVERLAP_RATIO)
    from .tips import axial_diff, axial_mean
    from scipy.spatial import cKDTree
    smap = {s.sid: s for s in strands if s.length_px >= 4.0}
    tips = []
    for s in smap.values():
        tips.append((s.tip0[0], s.tip0[1], s.sid, 0))
        tips.append((s.tip1[0], s.tip1[1], s.sid, 1))
    comp = _component_ids(catalogue)
    pts = np.array([(t[0], t[1]) for t in tips], float)
    tree = cKDTree(pts)
    virtual = []
    for i, (r0, c0, sid_a, end_a) in enumerate(tips):
        for j in tree.query_ball_point((r0, c0), r=w_max):
            if j <= i:
                continue
            r1, c1, sid_b, end_b = tips[j]
            if sid_a == sid_b or comp[r0, c0] != comp[r1, c1] or comp[r0, c0] == 0:
                continue
            sa, sb = smap[sid_a], smap[sid_b]
            az_a = sa.az0 if end_a == 0 else sa.az1
            az_b = sb.az0 if end_b == 0 else sb.az1
            dth = axial_diff(az_a, az_b)
            if dth > MAX_DTHETA:
                continue
            m_az = axial_mean([az_a, az_b])
            u_e, u_n = np.sin(np.radians(m_az)), np.cos(np.radians(m_az))
            de, dn = float(c1 - c0), float(-(r1 - r0))
            cross = abs(de * u_n - dn * u_e)
            if not (1.0 <= cross <= w_max):
                continue
            window = max(4.0 * cross, 40.0)
            ia = _tip_window_interval(sa, end_a, u_e, u_n, window)
            ib = _tip_window_interval(sb, end_b, u_e, u_n, window)
            overlap = max(0.0, min(ia[1], ib[1]) - max(ia[0], ib[0]))
            separation = max(0.0, max(ia[0], ib[0]) - min(ia[1], ib[1]))
            if separation > ALONG_MAX_RATIO * cross or overlap > -OVERLAP_RATIO * cross:
                continue
            virtual.append(TipPair(sid_a, sid_b, (int(r0), int(c0)), (int(r1), int(c1)),
                                   float(cross), de * u_e + dn * u_n, float(dth), float(m_az),
                                   float(np.hypot(de, dn)), overlap <= DILATATION_MAX_ALONG * cross,
                                   int(comp[r0, c0]), int(comp[r1, c1]),
                                   overlap_px=float(overlap), separation_px=float(separation)))
    recs = []
    for cid, vp in enumerate(virtual[:max_ramps]):
        cor = corridor_from_pair(cid, vp, list(smap.values()), shape)
        sa, sb = smap[vp.strand_a], smap[vp.strand_b]
        flank = np.zeros(shape, bool)
        flank[sa.ys, sa.xs] = True
        flank[sb.ys, sb.xs] = True
        linking = cor.full_mask(shape) & catalogue & ~flank
        if linking.sum() < 5:
            continue
        visible2 = catalogue & ~linking
        strands2 = vectorize(visible2)
        cors2, _ = build_corridors(visible2, strands2, shape, max_corridors=600, w_max=w_max)
        rebuilt = np.zeros(shape, bool)
        for c2 in cors2:
            rebuilt |= c2.full_mask(shape)
        ly, lx = np.nonzero(linking)
        if len(ly) == 0:
            continue
        d = ndi.distance_transform_edt(~rebuilt)
        within3 = float((d[ly, lx] <= 3.0).mean())
        recs.append(dict(w_px=vp.w_px, linking_px=int(linking.sum()),
                         within_3px=within3, subtype=cor.subtype))
    if not recs:
        return dict(n_hardlinked_found=0, note="no same-component virtual pairs with linking mass")
    within = np.array([r["within_3px"] for r in recs])
    return dict(n_hardlinked_found=len(virtual), n_tested=len(recs),
                mean_recovery_within_300m=float(within.mean()),
                median_recovery_within_300m=float(np.median(within)),
                n_ramps_above_70pct=int((within >= 0.7).sum()),
                ramps=recs)
