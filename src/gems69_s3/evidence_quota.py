"""H69-N: evidence-first selection with a spatial quota.

registry/preregistration-2026-10-20-h69n-evidence-quota.json.  Only the selection
step differs from H69-M (``evidence_first.py``, left byte-identical): the 1,200
corridor slots are apportioned to 200 x 200 px tiles in proportion to each tile's
de-duplicated step-over count (largest remainder), and the connector line score
ranks step-overs *within* each tile.  Geometry density decides how many corridors a
region gets; evidence decides which ones.  No constant is fit on the holdout.
"""
from __future__ import annotations

import numpy as np

from .corridors import TipPair, corridor_from_pair
from .evidence_first import dedupe_per_strand_pair, line_evidence, line_scores

TILE_PX = 200


def tile_ids(pairs: list[TipPair], shape, tile_px: int = TILE_PX) -> np.ndarray:
    """Tile index of each pair's tip-to-tip midpoint."""
    ncols = -(-shape[1] // tile_px)
    r = np.array([(p.tip_a[0] + p.tip_b[0]) / 2.0 for p in pairs])
    c = np.array([(p.tip_a[1] + p.tip_b[1]) / 2.0 for p in pairs])
    rr = np.clip((r // tile_px).astype(int), 0, -(-shape[0] // tile_px) - 1)
    cc = np.clip((c // tile_px).astype(int), 0, ncols - 1)
    return rr * ncols + cc


def apportion(counts: np.ndarray, total: int) -> np.ndarray:
    """Largest-remainder (Hamilton) apportionment of ``total`` slots, capped by counts."""
    counts = np.asarray(counts, np.int64)
    n = int(counts.sum())
    if n == 0 or total <= 0:
        return np.zeros_like(counts)
    if total >= n:
        return counts.copy()
    exact = counts * (total / n)
    q = np.floor(exact).astype(np.int64)
    rem = total - int(q.sum())
    order = np.lexsort((np.arange(len(counts)), -(exact - q)))   # largest remainder, ties by index
    q[order[:rem]] += 1
    return np.minimum(q, counts)


def select_evidence_quota(pairs: list[TipPair], zstack: dict, shape, max_corridors: int = 1200,
                          tile_px: int = TILE_PX):
    """Return (chosen pairs, their line scores, n_deduped, n_tiles_used)."""
    uniq = dedupe_per_strand_pair(pairs)
    if not uniq:
        return [], np.zeros(0), 0, 0
    s = line_scores(uniq, line_evidence(zstack, uniq))
    t = tile_ids(uniq, shape, tile_px)
    tiles, inv, counts = np.unique(t, return_inverse=True, return_counts=True)
    quota = apportion(counts, max_corridors)
    chosen_idx = []
    for k in range(len(tiles)):
        if quota[k] == 0:
            continue
        members = np.flatnonzero(inv == k)
        top = members[np.argsort(-s[members], kind="stable")[: quota[k]]]
        chosen_idx.extend(top.tolist())
    chosen_idx = np.array(sorted(chosen_idx, key=lambda i: (-s[i], i)), dtype=np.int64)
    return [uniq[i] for i in chosen_idx], s[chosen_idx], len(uniq), int((quota > 0).sum())


def build_evidence_quota_corridors(pairs: list[TipPair], strands, shape, zstack: dict,
                                   max_corridors: int = 1200, tile_px: int = TILE_PX):
    chosen, s_line, n_uniq, n_tiles = select_evidence_quota(pairs, zstack, shape, max_corridors, tile_px)
    corridors = [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(chosen)]
    for c, s in zip(corridors, s_line):
        c.rationale["selection"] = f"evidence_quota_top_in_{tile_px}px_tile_by_connector_joint_score"
        c.rationale["line_score_S"] = round(float(s), 4)
        c.rationale["source"] = ("GEMSDOE69 H69-N: repaired tip graph (R1/R2), one step-over per strand pair, "
                                 "tile quota by step-over density, ranked within tile by convergent grav+mag "
                                 "connector evidence (Giddens & Faulds 2025 SGP-TR-229 geometry priors)")
    w = [p.w_px / 10 for p in chosen]
    return corridors, dict(n_raw_pairs=len(pairs), n_dedup_step_overs=n_uniq, n_chosen=len(chosen),
                           n_tiles_used=n_tiles,
                           n_pull_apart=int(sum(p.dilatational for p in chosen)),
                           n_transfer=int(sum(not p.dilatational for p in chosen)),
                           w_km_chosen=dict(min=float(min(w, default=0)), median=float(np.median(w)) if w else 0.0,
                                            max=float(max(w, default=0))))
