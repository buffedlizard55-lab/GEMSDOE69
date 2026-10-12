"""Corridor generator: candidate fault traces proposed from catalogue geometry.

Settings and rules (sources: Giddens & Faulds 2025, SGP-TR-229; Faulds et al.
2026, Stanford Geothermal Workshop -- both verified, links in README):

* **Relay ramps (normal faults).**  Two *facing* free tips (outward directions
  antiparallel within 35 deg) on different polylines, both normal / unknown
  sense, **same dip polarity** (hanging-wall vectors agree), across-strike
  spacing ``W`` in 0.1-15 km (1-150 px; published widths 0.1-14.6 km) and
  along-strike separation ``|L| <= 3.5 W`` (ramps are "typically 3 to 3.5
  times longer than the width").  ``L < 0`` overlap, ``L > 0`` underlap.
  Candidate traces: the **oblique connector** (tip to tip), **breaching links**
  (each tip to the nearest point of the partner trace -- the hard-linked upper
  ramp), and ``K = clip(round(W / 1 km), 1, 3)`` **en echelon strands**
  parallel to the pair's mean strike, evenly spaced across the ramp.
* **Pull-aparts (strike-slip).**  Facing tips of two RL (or two LL) polylines at
  a **releasing** step (RL right-stepping, LL left-stepping), same ``W`` and
  ``3.5 W`` limits.  Traces: both basin-bounding links (tip to partner trace),
  the tip-to-tip chord, and up to three strands striking perpendicular to the
  WNW extension direction (azimuth 22.5 deg) through the step.
* **Transfer zones / terminations (strike-slip).**  At every free RL/LL tip:
  two horsetail splays rotated 20 and 40 deg into the *extensional quadrant*
  (right of the outward direction for RL, left for LL), length
  ``clip(0.2 * fault length, 1 km, 4 km)``, plus connectors from the tip to the
  nearest point of up to two normal-fault polylines within 6 km that lie
  ahead / on the extensional side (strike-slip -> normal displacement transfer).

Scoring: each trace's pixels (in footprint, off the visible catalogue) average
the four evidence layers of :mod:`gems69.evidence`; the fifth term is the
dilation tendency ``cos^2(beta)`` of the trace (``beta`` = angle between its
normal and the WNW extension azimuth 292.5 deg), maximal for NNE strikes.
``S = mean(grav_edge, mag_edge, mag_low, scarp, Td)`` -- equal, pre-registered
weights, no fitting.  Calibration to probabilities happens out-of-fold in
:mod:`gems69.calibrate`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from .traces import Poly, Tip, rc_of, sample_polyline

EXT_AZ = 292.5            # WNW extension azimuth (deg)
W_MIN, W_MAX = 1.0, 150.0  # px (0.1-15 km)
ASPECT = 3.5
FACING_COS = np.cos(np.radians(35.0))
STRAND_AZ = (EXT_AZ - 270.0) % 180.0   # 22.5 deg: perpendicular to extension


@dataclass
class Line:
    kind: str
    setting: str
    a: np.ndarray
    b: np.ndarray
    tips: tuple
    W: float = 0.0
    L: float = 0.0
    meta: dict = field(default_factory=dict)
    score: float = 0.0
    terms: dict = field(default_factory=dict)
    pix: np.ndarray | None = None          # flat indices of in-footprint, off-catalogue pixels

    @property
    def azimuth(self) -> float:
        d = self.b - self.a
        return float(np.degrees(np.arctan2(d[0], d[1])) % 180.0)


def _right(t):
    return np.array([t[1], -t[0]])


def _unit(v):
    n = float(np.hypot(*v))
    return v / n if n > 0 else v


def _rot(v, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    # positive deg rotates clockwise in map view (toward the right of v)
    return np.array([c * v[0] + s * v[1], -s * v[0] + c * v[1]])


class PolyIndex:
    def __init__(self, polys: list[Poly]):
        self.samples = [sample_polyline(q.verts, 0.5) for q in polys]
        self.polys = polys
        P = np.vstack(self.samples)
        self.owner = np.concatenate([np.full(len(s), i) for i, s in enumerate(self.samples)])
        self.tree = cKDTree(P)
        self.P = P

    def nearest_on(self, i: int, pt: np.ndarray) -> np.ndarray:
        s = self.samples[i]
        j = int(np.argmin(np.hypot(s[:, 0] - pt[0], s[:, 1] - pt[1])))
        return s[j]


def dilation_tendency(az_deg: float) -> float:
    normal = (az_deg + 90.0) % 180.0
    beta = np.radians(((normal - EXT_AZ) + 90.0) % 180.0 - 90.0)
    return float(np.cos(beta) ** 2)


def _pair_ok(ti: Tip, tj: Tip) -> tuple[bool, str]:
    """Relay / pull-apart admissibility of a tip pair (see module docstring)."""
    if ti.poly == tj.poly:
        return False, "rejected_same_polyline"
    ss_i, ss_j = ti.sense in ("RL", "LL"), tj.sense in ("RL", "LL")
    if ss_i != ss_j or (ss_i and ti.sense != tj.sense):
        return False, "rejected_mixed_sense"
    if float(ti.out @ tj.out) > -FACING_COS:
        return False, "rejected_facing"
    u = _unit(ti.out - tj.out)
    v = tj.pos - ti.pos
    s, n = float(v @ u), float(v @ _right(u))
    W = abs(n)
    if not (W_MIN <= W <= W_MAX) or abs(s) > ASPECT * W:
        return False, "rejected_geometry"
    if not ss_i:
        if ti.dip_vec is None or tj.dip_vec is None or float(ti.dip_vec @ tj.dip_vec) <= 0:
            return False, "rejected_dip"
    else:
        releasing = (n > 0) if ti.sense == "RL" else (n < 0)
        if not releasing:
            return False, "rejected_step_sense"
    return True, "ok"


def generate(tips: list[Tip], polys: list[Poly], *, include_cut: bool = False) -> tuple[list[Line], dict]:
    idx = PolyIndex(polys)
    use = [t for t in tips if include_cut or not t.cut]
    lines: list[Line] = []
    counts = dict(relay_pairs=0, pullapart_pairs=0, termination_tips=0, transfer_links=0,
                  rejected_dip=0, rejected_facing=0, rejected_geometry=0, rejected_step_sense=0,
                  rejected_same_polyline=0, rejected_mixed_sense=0)
    if not use:
        return lines, counts
    pos = np.array([t.pos for t in use])
    tree = cKDTree(pos)
    # pass 1: every geometrically valid pair; pass 2 keeps, for each tip, only its
    # nearest valid partner (a tip interacts with the adjacent overlapping segment).
    valid: list[tuple[float, int, int]] = []
    for i, j in sorted(tree.query_pairs(W_MAX * 1.2)):
        ti, tj = use[i], use[j]
        ok, why = _pair_ok(ti, tj)
        if not ok:
            counts[why] += 1
            continue
        valid.append((float(np.hypot(*(tj.pos - ti.pos))), i, j))
    best_for: dict[int, tuple[float, int, int]] = {}
    for d, i, j in valid:
        for k in (i, j):
            if k not in best_for or d < best_for[k][0]:
                best_for[k] = (d, i, j)
    chosen = sorted({(i, j) for _, i, j in best_for.values()})
    counts["valid_pairs_before_partner_selection"] = len(valid)
    for i, j in chosen:
        ti, tj = use[i], use[j]
        ss_i = ti.sense in ("RL", "LL")
        u = _unit(ti.out - tj.out)              # mean strike, pointing forward from tip i
        r = _right(u)
        v = tj.pos - ti.pos
        s, n = float(v @ u), float(v @ r)
        W = abs(n)
        meta = dict(overlap=s < 0, W_km=W / 10, L_km=s / 10, sense=ti.sense,
                    dip_source=f"{ti.dip_source}/{tj.dip_source}", records=(ti.record, tj.record))
        if not ss_i:
            counts["relay_pairs"] += 1
            pair = (ti.tid, tj.tid)
            lines.append(Line("relay_connector", "relay", ti.pos, tj.pos, pair, W, s, dict(meta)))
            pb = idx.nearest_on(tj.poly, ti.pos)
            if np.hypot(*(pb - tj.pos)) > 2:
                lines.append(Line("relay_breach", "relay", ti.pos, pb, pair, W, s, dict(meta)))
            pa = idx.nearest_on(ti.poly, tj.pos)
            if np.hypot(*(pa - ti.pos)) > 2:
                lines.append(Line("relay_breach", "relay", tj.pos, pa, pair, W, s, dict(meta)))
            K = int(np.clip(round(W / 10.0), 1, 3))
            lo, hi = min(0.0, s) - 0.25 * W, max(0.0, s) + 0.25 * W
            if hi - lo > 60:
                mid = 0.5 * (lo + hi)
                lo, hi = mid - 30, mid + 30
            for k in range(1, K + 1):
                off = n * k / (K + 1)
                a = ti.pos + lo * u + off * r
                b = ti.pos + hi * u + off * r
                lines.append(Line("relay_enechelon", "relay", a, b, pair, W, s, dict(meta, strand=k)))
        else:
            counts["pullapart_pairs"] += 1
            pair = (ti.tid, tj.tid)
            pb = idx.nearest_on(tj.poly, ti.pos)
            pa = idx.nearest_on(ti.poly, tj.pos)
            lines.append(Line("pullapart_link", "pullapart", ti.pos, pb, pair, W, s, dict(meta)))
            lines.append(Line("pullapart_link", "pullapart", tj.pos, pa, pair, W, s, dict(meta)))
            lines.append(Line("pullapart_chord", "pullapart", ti.pos, tj.pos, pair, W, s, dict(meta)))
            c = 0.5 * (ti.pos + tj.pos)
            az = np.radians(STRAND_AZ)
            d = np.array([np.sin(az), np.cos(az)])
            half = 0.5 * min(max(W, 5.0), 40.0)
            span = 0.5 * max(abs(s), 0.5 * W)
            for k, f in enumerate((-0.5, 0.0, 0.5)):
                cc = c + f * span * u
                lines.append(Line("pullapart_strand", "pullapart", cc - half * d, cc + half * d, pair,
                                  W, s, dict(meta, strand=k)))
    # strike-slip terminations -> horsetail splays + displacement-transfer links
    normal_polys = np.array([q.part.sense in ("N", "unk") for q in polys])
    for t in use:
        if t.sense not in ("RL", "LL"):
            continue
        counts["termination_tips"] += 1
        side = 1.0 if t.sense == "RL" else -1.0
        length = float(np.clip(0.2 * t.part_len, 10.0, 40.0))
        for ang in (20.0, 40.0):
            d = _rot(t.out, side * ang)
            lines.append(Line("termination_splay", "transfer", t.pos, t.pos + length * d, (t.tid,),
                              0.0, length, dict(sense=t.sense, angle=ang)))
        near = idx.tree.query_ball_point(t.pos, 60.0)
        best: dict[int, tuple[float, np.ndarray]] = {}
        for k in near:
            o = int(idx.owner[k])
            if o == t.poly or not normal_polys[o]:
                continue
            p = idx.P[k]
            v = p - t.pos
            if float(v @ t.out) < -5.0 or side * float(v @ _right(t.out)) < -5.0:
                continue
            dist = float(np.hypot(*v))
            if dist < 2.0:
                continue
            if o not in best or dist < best[o][0]:
                best[o] = (dist, p)
        for o, (dist, p) in sorted(best.items(), key=lambda kv: kv[1][0])[:2]:
            counts["transfer_links"] += 1
            lines.append(Line("transfer_link", "transfer", t.pos, p, (t.tid,), 0.0, dist,
                              dict(sense=t.sense, target_record=int(polys[o].part.record))))
    return lines, counts


def rasterize_lines(lines: list[Line], footprint: np.ndarray, visible: np.ndarray) -> None:
    H, W = footprint.shape
    for ln in lines:
        s = sample_polyline(np.vstack([ln.a, ln.b]), 0.5)
        r, c = rc_of(s)
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        r, c = r[ok], c[ok]
        keep = footprint[r, c] & ~visible[r, c]
        flat = np.unique(r[keep] * W + c[keep])
        ln.pix = flat


def score_lines(lines: list[Line], layers: dict[str, np.ndarray]) -> None:
    for ln in lines:
        td = dilation_tendency(ln.azimuth)
        if ln.pix is None or ln.pix.size == 0:
            ln.terms = dict(td=td)
            ln.score = 0.0
            continue
        terms = {k: float(v.ravel()[ln.pix].mean()) for k, v in layers.items()}
        terms["td"] = td
        ln.terms = terms
        ln.score = float(np.mean(list(terms.values())))


def line_id_raster(lines: list[Line], shape: tuple[int, int]) -> np.ndarray:
    """int32 raster: id of the highest-scoring trace through each pixel (-1 = none)."""
    H, W = shape
    lid = np.full(H * W, -1, np.int32)
    best = np.full(H * W, -np.inf, np.float32)
    for k, ln in enumerate(lines):
        if ln.pix is None or ln.pix.size == 0:
            continue
        better = best[ln.pix] < ln.score
        sel = ln.pix[better]
        lid[sel] = k
        best[sel] = ln.score
    return lid.reshape(H, W)


def corridor_fields(lines: list[Line], shape: tuple[int, int], band_px: float = 2.0):
    """Per-pixel corridor score (max over traces within ``band_px``) and distance to a trace."""
    H, W = shape
    smax = np.zeros(H * W, np.float32)
    on = np.zeros(H * W, bool)
    for ln in lines:
        if ln.pix is None or ln.pix.size == 0:
            continue
        np.maximum.at(smax, ln.pix, np.float32(ln.score))
        on[ln.pix] = True
    smax = smax.reshape(H, W)
    on = on.reshape(H, W)
    if not on.any():
        return np.zeros(shape, np.float32), np.full(shape, np.inf, np.float32), on
    d, (iy, ix) = ndi.distance_transform_edt(~on, return_indices=True)
    band = d <= band_px
    s_band = np.where(band, smax[iy, ix], 0).astype(np.float32)
    return s_band, d.astype(np.float32), on


def line_table(lines: list[Line]) -> list[dict]:
    rows = []
    for k, ln in enumerate(lines):
        rows.append(dict(id=k, kind=ln.kind, setting=ln.setting,
                         a_E=float(ln.a[0]), a_N=float(ln.a[1]), b_E=float(ln.b[0]), b_N=float(ln.b[1]),
                         azimuth=ln.azimuth, W_km=round(ln.W / 10, 3), L_km=round(ln.L / 10, 3),
                         n_pix=int(ln.pix.size if ln.pix is not None else 0), score=ln.score,
                         **{f"t_{k2}": v for k2, v in ln.terms.items()},
                         **{k2: (v if isinstance(v, (int, float, str, bool)) else str(v)) for k2, v in ln.meta.items()}))
    return rows
