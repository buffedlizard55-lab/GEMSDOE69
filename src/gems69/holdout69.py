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
from .physics import (TRANSFORM_NAMES, build_layer_stats, build_z_stack,
                      compute_transform, corridor_evidence_from_z)
from .scoring import (GRAV_LAYERS, LIDAR_LAYERS, MAGLOW_LAYERS, MAG_LAYERS,
                      RAD_LAYERS, SCORE_FLOOR_QUANTILE, STRAIGHT_LAYERS,
                      W_GRAV, W_LIDAR, W_MAG, W_MAGLOW, W_RAD, W_STRAIGHT,
                      build_propensity, score_corridor)
from .tips import vectorize

ROOT = Path(__file__).resolve().parents[2]
FLANK_PX = 2            # catalogue flank exclusion (200 m), as in h33-2-b2


def load_template_grid():
    return tgrid.load_grid(data_dir=ROOT / "data" / "bridge")


def corridor_pipeline(catalogue: np.ndarray, shape: tuple[int, int], stats: dict,
                      max_corridors: int = 1200, zstack: dict | None = None):
    """Vectorize -> tip pairs -> corridors -> scored rationale -> propensity."""
    if zstack is None:
        zstack = build_z_stack(_footprint_from_shape(shape), stats)
    strands = vectorize(catalogue)
    corridors, pairs = build_corridors(catalogue, strands, shape,
                                       max_corridors=max_corridors,
                                       selection="stratified")
    t0 = time.time()
    for c in corridors:
        ev = corridor_evidence_from_z(zstack, c)
        score_corridor(c, ev)
    if corridors:
        scores = np.array([c.rationale.get("score_S", 0.0) for c in corridors])
        thr = float(np.quantile(scores, SCORE_FLOOR_QUANTILE))
        kept = [c for c in corridors if c.rationale.get("score_S", 0.0) >= thr]
    else:
        thr, kept = 0.0, corridors
    p = build_propensity(kept, shape)
    return dict(strands=len(strands), pairs=len(pairs), corridors=len(corridors),
                corridors_kept=len(kept), score_floor=thr,
                propensity=p, corridors_obj=kept,
                score_seconds=round(time.time() - t0, 1))


def _footprint_from_shape(shape):
    # only used when the caller did not pre-build the z stack; the stack is
    # footprint-agnostic outside robust stats, so any finite mask works here
    g = load_template_grid()
    return g.footprint


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
                     s0: float | None = None, zstack: dict | None = None):
    """Corridor vs control arm on every cell; returns per-cell results."""
    from .scoring import S0_DEFAULT
    s0 = S0_DEFAULT if s0 is None else s0
    shape = ctx.grid.footprint.shape
    catalogue = ctx.grid.catalogue
    if zstack is None:
        zstack = build_z_stack(ctx.grid.footprint, stats)
    d_cat = ndi.distance_transform_edt(~catalogue)
    offcat = d_cat > flank_px

    # ---- control propensity: same evidence groups, NO corridor prior --------
    # Orientation and geometry priors are corridor-only; they are omitted here
    # and the evidence weights are renormalized so the control is not weaker
    # just because it lacks a constant subtype bonus.
    def _posmax(names):
        m = None
        for name in names:
            if name not in zstack:
                continue
            z = np.nan_to_num(zstack[name].astype(np.float32), nan=0.0)
            z = np.maximum(z, 0.0)
            m = z if m is None else np.maximum(m, z)
        return m if m is not None else np.zeros(shape, np.float32)

    ev_w = W_GRAV + W_MAG + W_MAGLOW + W_LIDAR + W_STRAIGHT + W_RAD
    C = (W_GRAV * _posmax(GRAV_LAYERS) + W_MAG * _posmax(MAG_LAYERS)
         + W_MAGLOW * _posmax(MAGLOW_LAYERS) + W_LIDAR * _posmax(LIDAR_LAYERS)
         + W_STRAIGHT * _posmax(STRAIGHT_LAYERS) + W_RAD * _posmax(RAD_LAYERS))
    C = (C / ev_w).astype(np.float32)
    p_ctrl = (1.0 / (1.0 + np.exp(-1.5 * (C - s0)))).astype(np.float32)
    p_ctrl[~ctx.grid.footprint] = 0.0
    del C

    results = {}
    for cell in ctx.cells:
        if cell.mode not in modes:
            continue
        key = cell.key
        visible = ctx.visible(key)
        pipe = corridor_pipeline(visible, shape, stats, zstack=zstack)
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


def leakage_canary(ctx, stats, max_neg: int = 200_000, seed: int = 69,
                   zstack: dict | None = None) -> dict:
    """Single-feature AUC vs pooled withheld truth (seed 20, mode 'all').

    AUC > 0.90 for any feature = leakage until proven otherwise (protocol 4).
    Physics layers are catalogue-independent by construction; the corridor
    propensity surface is the catalogue-derived feature under test.  AUC is the
    rank (Mann-Whitney) statistic computed on the precomputed z stack.
    """
    shape = ctx.grid.footprint.shape
    if zstack is None:
        zstack = build_z_stack(ctx.grid.footprint, stats)
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
    cor_pipe = corridor_pipeline(ctx.grid.catalogue, shape, stats, zstack=zstack)
    p_cor = cor_pipe["propensity"]

    def auc(vals_t: np.ndarray, vals_n: np.ndarray) -> float | None:
        a = np.asarray(vals_t, np.float64)
        b = np.asarray(vals_n, np.float64)
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if a.size < 10 or b.size < 10:
            return None
        allv = np.concatenate([a, b])
        order = np.argsort(allv, kind="mergesort")
        sorted_v = allv[order]
        # rank with tie averaging via unique boundaries
        change = np.flatnonzero(np.diff(sorted_v) != 0) + 1
        starts = np.concatenate([[0], change])
        ends = np.concatenate([change, [len(sorted_v)]])
        ranks = np.arange(1, len(sorted_v) + 1, dtype=np.float64)
        avg = np.empty_like(ranks)
        cum = np.cumsum(ranks)
        sums = cum[ends - 1] - np.where(starts > 0, cum[starts - 1], 0.0)
        for s0_, e0_, sm in zip(starts, ends, sums):
            avg[s0_:e0_] = sm / (e0_ - s0_)
        avg_rank = np.empty_like(avg)
        avg_rank[order] = avg
        rank_sum_t = avg_rank[: a.size].sum()
        return float((rank_sum_t - a.size * (a.size + 1) / 2.0) / (a.size * b.size))

    out = {}
    for name in list(zstack.keys()) + ["corridor_propensity"]:
        if name == "corridor_propensity":
            out[name] = dict(auc=auc(p_cor[ty, tx], p_cor[ny, nx]),
                             n_pos=int(len(ty)), n_neg=int(len(ny)))
        else:
            z = zstack[name]
            out[name] = dict(auc=auc(z[ty, tx].astype(np.float64),
                                     z[ny, nx].astype(np.float64)),
                             n_pos=int(len(ty)), n_neg=int(len(ny)))
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
    still_connected = 0
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
        comp2, _ = ndi.label(visible2, structure=np.ones((3, 3), int))
        ta, tb = vp.tip_a, vp.tip_b
        if not (visible2[ta] and visible2[tb]):
            continue
        if comp2[ta] == comp2[tb]:
            # the masked pixels were not the only link: flanks stay connected,
            # so the pair is (correctly) not re-emitted. Not a recovery target.
            still_connected += 1
            continue
        strands2 = vectorize(visible2)
        pairs2 = build_tip_pairs(strands2, visible2, w_max=w_max)
        # re-emission test: does the tip graph reform a pair at the same place?
        near = [p for p in pairs2
                if (abs(p.tip_a[0] - ta[0]) <= 2 and abs(p.tip_a[1] - ta[1]) <= 2
                    and abs(p.tip_b[0] - tb[0]) <= 2 and abs(p.tip_b[1] - tb[1]) <= 2)
                or (abs(p.tip_b[0] - ta[0]) <= 2 and abs(p.tip_b[1] - ta[1]) <= 2
                    and abs(p.tip_a[0] - tb[0]) <= 2 and abs(p.tip_a[1] - tb[1]) <= 2)]
        rebuilt = np.zeros(shape, bool)
        for k, np_ in enumerate(near[:4]):
            rebuilt |= corridor_from_pair(k, np_, strands2, shape).full_mask(shape)
        ly, lx = np.nonzero(linking)
        if len(ly) == 0:
            continue
        d = ndi.distance_transform_edt(~rebuilt)
        within3 = float((d[ly, lx] <= 3.0).mean())
        recs.append(dict(w_px=vp.w_px, linking_px=int(linking.sum()),
                         within_3px=within3, subtype=cor.subtype,
                         reemitted_pairs=len(near)))
    if not recs:
        return dict(n_hardlinked_found=len(virtual), n_disconnected_tested=0,
                    n_still_connected_after_mask=still_connected,
                    note="no same-component virtual pair whose mask actually disconnects the flanks")
    within = np.array([r["within_3px"] for r in recs])
    return dict(n_hardlinked_found=len(virtual), n_tested=len(recs),
                n_disconnected_tested=len(recs),
                n_still_connected_after_mask=still_connected,
                mean_recovery_within_300m=float(within.mean()),
                median_recovery_within_300m=float(np.median(within)),
                n_ramps_above_70pct=int((within >= 0.7).sum()),
                definition=("virtual pair = geometrically valid tip pair in ONE 8-connected component; "
                            "linking mass = corridor-masked catalogue pixels belonging to neither flank "
                            "strand; ramps are scored only when masking DISCONNECTS the flanks (the link "
                            "was the only connection = hard-linked ramp); recovery = fraction of masked "
                            "linking pixels within 3 px (300 m) of the corridor rebuilt from the remaining "
                            "visible catalogue"),
                ramps=recs)
