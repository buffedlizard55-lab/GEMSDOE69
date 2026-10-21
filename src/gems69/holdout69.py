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
                      W_GRAV, W_GEOM, W_LIDAR, W_MAG, W_MAGLOW, W_ORIENT,
                      build_propensity, propensity_from_score, score_corridor)
from .tips import vectorize

ROOT = Path(__file__).resolve().parents[2]
FLANK_PX = 2            # catalogue flank exclusion (200 m), as in h33-2-b2


def load_template_grid():
    return tgrid.load_grid(data_dir=ROOT / "data" / "bridge")


def corridor_pipeline(catalogue: np.ndarray, shape: tuple[int, int], stats: dict,
                      max_corridors: int = 1200, zstack: dict | None = None,
                      version: str = "v1",
                      scoring_mode: str = "base",
                      zstack_rad: dict | None = None,
                      rad_stats: dict | None = None):
    """Vectorize -> tip pairs -> corridors -> scored rationale -> propensity.

    ``version`` selects relayfix evidence arms (v1/v2/v3, scoring.py).
    ``scoring_mode`` supports the merged H69-J generators ("joint", "rad",
    "joint_rad") via scoring_joint/scoring_rad; default "base" preserves
    the relayfix behaviour executed 2026-10-20.
    """
    if zstack is None:
        zstack = build_z_stack(_footprint_from_shape(shape), stats)
    if scoring_mode in ("rad", "joint_rad") and zstack_rad is None:
        from .radiometric import build_stats as build_rad_stats, build_z_stack as build_rad_z
        g = load_template_grid()
        zstack_rad = build_rad_z(g.footprint, build_rad_stats(g.footprint))
    strands = vectorize(catalogue)
    corridors, pairs = build_corridors(catalogue, strands, shape,
                                       max_corridors=max_corridors)
    t0 = time.time()
    for c in corridors:
        ev = corridor_evidence_from_z(zstack, c)
        if zstack_rad is not None:
            ev.update(corridor_evidence_from_z(zstack_rad, c))
        if scoring_mode == "joint":
            from .scoring_joint import score_corridor_joint
            score_corridor_joint(c, ev)
        elif scoring_mode in ("rad", "joint_rad"):
            from .scoring_rad import score_corridor_rad
            score_corridor_rad(c, ev)
        else:
            score_corridor(c, ev, version=version)
    if scoring_mode == "joint":
        from .scoring_joint import build_propensity_joint
        p = build_propensity_joint(corridors, shape)
    elif scoring_mode in ("rad", "joint_rad"):
        from .scoring_rad import build_propensity_rad
        p = build_propensity_rad(corridors, shape)
    else:
        p = build_propensity(corridors, shape)
    return dict(strands=len(strands), pairs=len(pairs), corridors=len(corridors),
                propensity=p, corridors_obj=corridors, version=version,
                scoring_mode=scoring_mode,
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
    # ---- control propensity: same layers, no corridor prior (full grid) -----
    ctrl_layers = ["grav_hg_s2", "grav_tilt_s2", "mag_hg_s2", "mag_tilt_s2",
                   "mag_low_tmi", "mag_low_rtp", "lidar_scarp"]
    C = np.zeros(shape, np.float32)
    for name in ctrl_layers:
        z = zstack[name].astype(np.float32)
        z = np.where(np.isfinite(z), z, 0.0)
        C += z
        del z
    C /= len(ctrl_layers)
    p_ctrl = (1.0 / (1.0 + np.exp(-1.5 * (C - s0)))).astype(np.float32)
    p_ctrl[~ctx.grid.footprint] = 0.0

    results = {}
    for cell in ctx.cells:
        if cell.mode not in modes:
            continue
        key = cell.key
        visible = ctx.visible(key)
        # Bug fix IR-69-17: flank exclusion must be computed strictly from
        # fold-visible faults, NEVER ctx.grid.catalogue (which contains hidden truth).
        offvis = ndi.distance_transform_edt(~visible) > flank_px
        pipe = corridor_pipeline(visible, shape, stats, zstack=zstack)
        p_cor = pipe["propensity"]
        allowed = cell_allowed(cell, shape) & offvis
        allowed_ctrl = allowed.copy()

        em_cor = emit_dots(p_cor, allowed & (p_cor > 0), cell.n_truth)
        em_ctrl = emit_dots(p_ctrl, allowed_ctrl & (p_ctrl > 0), cell.n_truth)
        r_cor = thold.score_cell(cell, em_cor)
        r_ctrl = thold.score_cell(cell, em_ctrl)
        results[key] = dict(
            corridor=dict(dti=r_cor["dti"], coverage=r_cor["coverage"],
                          tp=r_cor["tp"], fp=r_cor["fp"], fn=r_cor["fn"],
                          n_dots=int((em_cor & allowed).sum()),
                          n_corridors=pipe["corridors"], n_pairs=pipe["pairs"],
                          n_truth=cell.n_truth),
            control=dict(dti=r_ctrl["dti"], coverage=r_ctrl["coverage"],
                         tp=r_ctrl["tp"], fp=r_ctrl["fp"], fn=r_ctrl["fn"],
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
    if not cells:
        cells = [c for c in ctx.cells if c.mode == "all"][:4]
    truth = np.zeros(shape, bool)
    active = np.zeros(shape, bool)
    p_cor = np.zeros(shape, np.float32)
    total_corridors = 0
    for cell in cells:
        h = ctx.hidden_by_cell[cell.key]
        full_active = cell_allowed(cell, shape)
        truth |= h & full_active
        active |= full_active
        # Bug fix IR-69-17: build corridor propensity strictly from fold-visible
        # catalogue per cell so withheld faults never leak into the canary surface.
        vis = ctx.visible(cell.key)
        cpipe = corridor_pipeline(vis, shape, stats, zstack=zstack)
        p_cor[full_active] = cpipe["propensity"][full_active]
        total_corridors += cpipe["corridors"]
    neg_pool = np.nonzero(active & ~truth)
    rng = np.random.default_rng(seed)
    n_neg = min(max_neg, len(neg_pool[0]))
    sel = rng.choice(len(neg_pool[0]), size=n_neg, replace=False)
    ny, nx = neg_pool[0][sel], neg_pool[1][sel]
    ty, tx = np.nonzero(truth)

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
    out["_corridors"] = int(total_corridors)
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
    # Same repaired code path as production pairing (repairs R1/R2); the former
    # private copy of the geometry here duplicated both bugs. Never fork it.
    virtual = build_tip_pairs(strands, catalogue, w_max=w_max, same_component=True)
    smap = {s.sid: s for s in strands if s.length_px >= 4.0}
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
