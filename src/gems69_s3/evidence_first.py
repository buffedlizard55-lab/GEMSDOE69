"""H69-M evidence-first corridor selection (registry/preregistration-2026-10-20-h69m-evidence-first.json).

Every earlier selector in this lane capped the tip-pair list at 1,200 by a
*geometry* priority before any evidence was looked at.  Here every step-over is
scored first and only the top corridors are rasterized:

1. de-duplicate the repaired tip graph to one pair per unordered strand pair
   (the pair with the closest tips) -- removes outer-tip duplicates (IR-69-SEL-01);
2. sample the robust-z evidence stack along the oblique tip-to-tip connector
   (<= 64 samples per connector) and score it with the same convergent joint
   grav+mag weights as ``scoring_joint.py``;
3. keep the top ``max_corridors`` by that line score.

No weight or constant here is fit on the holdout.
"""
from __future__ import annotations

import numpy as np

from .corridors import TipPair, corridor_from_pair
from .scoring import GEOM_PRIOR, GRAV_LAYERS, LIDAR_LAYERS, MAG_LAYERS, MAGLOW_LAYERS, orientation_weight

LINE_SAMPLES_MAX = 64
JOINT_LAYERS = GRAV_LAYERS + MAG_LAYERS + MAGLOW_LAYERS + LIDAR_LAYERS


def dedupe_per_strand_pair(pairs: list[TipPair]) -> list[TipPair]:
    """One step-over per unordered strand pair: keep the closest-tip pair."""
    best: dict[tuple[int, int], TipPair] = {}
    for p in pairs:
        k = (min(p.strand_a, p.strand_b), max(p.strand_a, p.strand_b))
        q = best.get(k)
        if q is None or (p.diag_px, p.w_px) < (q.diag_px, q.w_px):
            best[k] = p
    return sorted(best.values(), key=lambda p: (min(p.strand_a, p.strand_b), max(p.strand_a, p.strand_b)))


def line_evidence(zstack: dict, pairs: list[TipPair], n_max: int = LINE_SAMPLES_MAX) -> dict[str, np.ndarray]:
    """Mean robust z of each joint layer along each tip-to-tip connector (NaN-aware)."""
    n = len(pairs)
    if n == 0:
        return {name: np.zeros(0) for name in JOINT_LAYERS}
    r0 = np.array([p.tip_a[0] for p in pairs], float)
    c0 = np.array([p.tip_a[1] for p in pairs], float)
    r1 = np.array([p.tip_b[0] for p in pairs], float)
    c1 = np.array([p.tip_b[1] for p in pairs], float)
    ns = np.clip(np.ceil(np.hypot(r1 - r0, c1 - c0)).astype(int) + 1, 2, n_max)
    t = np.linspace(0.0, 1.0, n_max)[None, :]                    # (1, n_max)
    # per-pair sample fractions: use the first ns[i] points of an ns[i]-grid
    frac = np.minimum(np.arange(n_max)[None, :] / np.maximum(ns[:, None] - 1, 1), 1.0)
    valid = np.arange(n_max)[None, :] < ns[:, None]
    del t
    rr = np.rint(r0[:, None] + frac * (r1 - r0)[:, None]).astype(np.int64)
    cc = np.rint(c0[:, None] + frac * (c1 - c0)[:, None]).astype(np.int64)
    out = {}
    for name in JOINT_LAYERS:
        z = zstack[name]
        v = z[rr, cc].astype(np.float32)
        ok = valid & np.isfinite(v)
        s = np.where(ok, v, 0.0).sum(axis=1)
        k = ok.sum(axis=1)
        out[name] = np.where(k > 0, s / np.maximum(k, 1), 0.0)
    return out


def line_scores(pairs: list[TipPair], ev: dict[str, np.ndarray]) -> np.ndarray:
    """Convergent joint score, identical weights to scoring_joint.score_corridor_joint."""
    if not pairs:
        return np.zeros(0)
    e_grav = np.max(np.stack([ev[n] for n in GRAV_LAYERS]), axis=0)
    e_mag = np.max(np.stack([ev[n] for n in MAG_LAYERS]), axis=0)
    e_low = np.max(np.stack([ev[n] for n in MAGLOW_LAYERS]), axis=0)
    e_lid = np.max(np.stack([ev[n] for n in LIDAR_LAYERS]), axis=0)
    g, m = np.maximum(e_grav, 0.0), np.maximum(e_mag, 0.0)
    joint, single = np.minimum(g, m), np.maximum(g, m)
    low_w = np.maximum(e_low, 0.0) * np.where(joint > 0.5, 1.0, 0.6)
    w_o = np.array([orientation_weight(p.mean_az) for p in pairs])
    w_g = np.array([GEOM_PRIOR["pull-apart"] if p.dilatational else GEOM_PRIOR["transfer-overlap"] for p in pairs])
    return 0.35 * joint + 0.15 * single + 0.15 * low_w + 0.15 * np.maximum(e_lid, 0.0) + 0.10 * w_o + 0.10 * w_g


def select_evidence_first(pairs: list[TipPair], zstack: dict, max_corridors: int = 1200):
    """Return (chosen pairs ranked by line score, line scores of chosen, n_deduped)."""
    uniq = dedupe_per_strand_pair(pairs)
    ev = line_evidence(zstack, uniq)
    s = line_scores(uniq, ev)
    order = np.argsort(-s, kind="stable")[:max_corridors]
    return [uniq[i] for i in order], s[order], len(uniq)


def build_evidence_first_corridors(pairs: list[TipPair], strands, shape, zstack: dict,
                                   max_corridors: int = 1200):
    chosen, s_line, n_uniq = select_evidence_first(pairs, zstack, max_corridors)
    corridors = [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(chosen)]
    for c, s in zip(corridors, s_line):
        c.rationale["selection"] = "evidence_first_top_by_connector_joint_score"
        c.rationale["line_score_S"] = round(float(s), 4)
        c.rationale["source"] = ("GEMSDOE69 H69-M: repaired tip graph (R1/R2), one step-over per strand pair, "
                                 "ranked by convergent grav+mag connector evidence; geometry priors per standing "
                                 "prompt (Giddens & Faulds 2025 SGP-TR-229 as cited there)")
    return corridors, dict(n_raw_pairs=len(pairs), n_dedup_step_overs=n_uniq, n_chosen=len(chosen),
                           n_pull_apart=int(sum(p.dilatational for p in chosen)),
                           n_transfer=int(sum(not p.dilatational for p in chosen)),
                           w_km_chosen=dict(
                               min=float(min((p.w_px for p in chosen), default=0) / 10),
                               median=float(np.median([p.w_px for p in chosen]) / 10) if chosen else 0.0,
                               max=float(max((p.w_px for p in chosen), default=0) / 10)))
