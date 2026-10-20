"""Tip-graph step-over pairing and relay-ramp / pull-apart corridor emission.

Geometry model (standing prompt, Giddens & Faulds 2025 SGP-TR-229 as cited
there): relay ramps are typically 3-3.5x longer than wide, widths 0.1-14.6 km
(mean 2.8 km); ~70% of higher-temperature step-overs are hard-linked; breaching
faults range from oblique connectors to en echelon strands; Walker Lane hot
systems favour pull-aparts and displacement-transfer zones; N-NE faults are
best oriented for dilation under WNW extension.

Pair acceptance (all lengths in 100 m pixels):
  * tips belong to different 8-connected catalogue components;
  * terminal strikes sub-parallel: axial angle difference <= MAX_DTHETA (30 deg)
    -- the raster catalogue carries no dip polarity, so "same dip" is proxied by
    sub-parallel strike and disclosed as a limitation (IR-69-DIP-01);
  * cross-strike spacing W in [W_MIN_PX, W_MAX_PX] = [1, 150] px (0.1-15 km);
  * signed along-strike separation a in [-W, 3.5 W]  (a < 0 = overlapping tips,
    a > 0 = underlapping tips);
  * pair is the closest matching tip of each strand (mutual nearest among
    accepted pairs is NOT required; all geometrically valid pairs are emitted,
    duplicates pruned by corridor union later).

Sense model: slip sense is not observable from the raster catalogue.  The
Walker Lane dextral-shear prior is applied through the *dilation diagnostic*:
underlapping-to-neutral steps (a <= 0.5 W) are dilatational candidates and
receive the pull-apart rhomb + en echelon strands; strongly overlapping steps
(a > 0.5 W) are contractional candidates and receive only the oblique connector
(transfer/pressure corridor).  Recorded per corridor in the rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.draw import line as skline

from .tips import Strand, axial_diff, axial_deg, axial_mean
from .traces import Poly, Tip, rc_of, sample_polyline

EXT_AZ = 292.5            # WNW extension azimuth (deg)
W_MIN, W_MAX = 1.0, 150.0  # px (0.1-15 km)
ASPECT = 3.5
FACING_COS = np.cos(np.radians(35.0))
STRAND_AZ = (EXT_AZ - 270.0) % 180.0   # 22.5 deg: perpendicular to extension

W_MIN_PX = 1.0        # 0.1 km
W_MAX_PX = 150.0      # 15 km
ALONG_MAX_RATIO = 3.5
OVERLAP_RATIO = -1.0  # accept overlap down to one spacing width
MAX_DTHETA = 30.0     # deg, sub-parallel terminal strikes ("same dip" proxy)
DILATATION_MAX_ALONG = 0.5  # a/W <= this -> dilatational candidate
ECH_ANGLE = 25.0      # deg, en echelon strand angle to the connector
CONNECTOR_HALF_W = lambda w: max(1, int(round(min(w / 6.0, 6.0))))
TIP_EXT_RATIO = 0.35  # extend connector 0.35 W beyond each tip along strike
MIN_STRAND_PX = 4.0   # strands shorter than this carry no tips into the graph


@dataclass
class TipPair:
    strand_a: int
    strand_b: int
    tip_a: tuple[int, int]     # (row, col)
    tip_b: tuple[int, int]
    w_px: float                # cross-strike spacing (100 m px)
    along_px: float            # signed tip-to-tip projection on strike axis (record only)
    dtheta: float              # axial strike difference (deg)
    mean_az: float             # mean axial azimuth of the two terminal strikes
    diag_px: float             # tip-to-tip distance
    dilatational: bool
    comp_a: int
    comp_b: int
    overlap_px: float = 0.0    # along-strike overlap of tip-adjacent windows
    separation_px: float = 0.0  # along-strike gap of tip-adjacent windows


@dataclass
class Corridor:
    cid: int
    pair: TipPair
    subtype: str               # 'relay-ramp' | 'pull-apart' | 'transfer-overlap'
    bbox: tuple[int, int, int, int]   # (r0, r1, c0, c1) full-grid window
    local_mask: np.ndarray     # bool, corridor pixels inside bbox
    local_weight: np.ndarray   # float32, membership weight (0.85-1.0) inside bbox
    geometry: dict
    rationale: dict = field(default_factory=dict)

    @property
    def npix(self) -> int:
        return int(self.local_mask.sum())

    def full_mask(self, shape: tuple[int, int]) -> np.ndarray:
        m = np.zeros(shape, bool)
        r0, r1, c0, c1 = self.bbox
        m[r0:r1, c0:c1] = self.local_mask
        return m

    def render_into(self, propensity: np.ndarray, value: float) -> None:
        r0, r1, c0, c1 = self.bbox
        contrib = value * self.local_weight
        sl = propensity[r0:r1, c0:c1]
        m = self.local_mask
        sl[m] = np.maximum(sl[m], contrib[m])


def _component_ids(catalogue: np.ndarray) -> np.ndarray:
    comp, _ = ndi.label(catalogue, structure=np.ones((3, 3), int))
    return comp


def _tip_window_interval(strand: Strand, end: int, u_e: float, u_n: float,
                         window_px: float) -> tuple[float, float]:
    """Project the tip-adjacent part of a strand onto the strike axis.

    Returns the (min, max) axis coordinate of the last ``window_px`` of the
    strand at the given end (0 = tip0, 1 = tip1).  Strike-axis intervals make
    overlap/underlap well defined even though axial directions have no sign.
    """
    ys = strand.ys.astype(float)
    xs = strand.xs.astype(float)
    if end == 1:
        ys, xs = ys[::-1], xs[::-1]
    # cumulative polyline distance from the tip
    steps = np.hypot(np.diff(ys), np.diff(xs))
    s = np.concatenate([[0.0], np.cumsum(steps)])
    keep = s <= window_px
    if keep.sum() < 2:
        keep[:2] = True
    de = xs[keep] - xs[0]
    dn = -(ys[keep] - ys[0])
    axis = de * u_e + dn * u_n
    return float(axis.min()), float(axis.max())


def build_tip_pairs(strands: list[Strand], catalogue: np.ndarray,
                    w_min: float = W_MIN_PX, w_max: float = W_MAX_PX) -> list[TipPair]:
    """Emit every geometrically valid step-over tip pair from the tip graph.

    Along-strike separation and overlap are computed as interval arithmetic on
    the strike-axis projection of the tip-adjacent strand windows (length
    ``max(4W, 40 px)``), which is invariant to the sign ambiguity of axial
    directions.  Acceptance: W in [w_min, w_max]; separation <= 3.5 W;
    overlap <= 1.0 W.
    """
    strands = [s for s in strands if s.length_px >= MIN_STRAND_PX]
    if len(strands) < 2:
        return []
    comp = _component_ids(catalogue)
    smap = {s.sid: s for s in strands}
    tips = []           # (row, col, strand_idx, which_end)
    for s in strands:
        tips.append((s.tip0[0], s.tip0[1], s.sid, 0))
        tips.append((s.tip1[0], s.tip1[1], s.sid, 1))
    pts = np.array([(t[0], t[1]) for t in tips], float)
    tree = cKDTree(pts)
    pairs: list[TipPair] = []
    for i, (r0, c0, sid_a, end_a) in enumerate(tips):
        for j in tree.query_ball_point((r0, c0), r=w_max):
            if j <= i:
                continue
            r1, c1, sid_b, end_b = tips[j]
            if sid_a == sid_b:
                continue
            sa, sb = smap[sid_a], smap[sid_b]
            if comp[r0, c0] == comp[r1, c1] and comp[r0, c0] > 0:
                continue  # already linked within one connected component
            # terminal strikes at these tips
            az_a = sa.az0 if end_a == 0 else sa.az1
            az_b = sb.az0 if end_b == 0 else sb.az1
            dth = axial_diff(az_a, az_b)
            if dth > MAX_DTHETA:
                continue
            m_az = axial_mean([az_a, az_b])
            u_e, u_n = np.sin(np.radians(m_az)), np.cos(np.radians(m_az))
            de = float(c1 - c0)
            dn = float(-(r1 - r0))
            diag = float(np.hypot(de, dn))
            cross = abs(de * u_n - dn * u_e)
            if not (w_min <= cross <= w_max):
                continue
            window = max(4.0 * cross, 40.0)
            ia = _tip_window_interval(sa, end_a, u_e, u_n, window)
            ib = _tip_window_interval(sb, end_b, u_e, u_n, window)
            overlap = max(0.0, min(ia[1], ib[1]) - max(ia[0], ib[0]))
            separation = max(0.0, max(ia[0], ib[0]) - min(ia[1], ib[1]))
            if separation > ALONG_MAX_RATIO * cross:
                continue
            if overlap > -OVERLAP_RATIO * cross:   # OVERLAP_RATIO = -1.0
                continue
            # signed along kept for the record (projection of B tip - A tip)
            along_signed = de * u_e + dn * u_n
            pairs.append(TipPair(sid_a, sid_b, (int(r0), int(c0)), (int(r1), int(c1)),
                                 float(cross), float(along_signed), float(dth), float(m_az),
                                 diag, overlap <= DILATATION_MAX_ALONG * cross,
                                 int(comp[r0, c0]), int(comp[r1, c1]),
                                 overlap_px=float(overlap), separation_px=float(separation)))
    return pairs


def _pair_key(p: TipPair) -> tuple:
    return (min(p.strand_a, p.strand_b), max(p.strand_a, p.strand_b),
            round(p.w_px, 1), round(p.along_px, 1))


def corridor_from_pair(cid: int, pair: TipPair, strands: list[Strand],
                       shape: tuple[int, int]) -> Corridor:
    """Rasterize the corridor geometry for one tip pair.

    Components: oblique connector (tip-to-tip, extended 0.35W beyond each tip
    along the local strikes), en echelon strands inside the step-over for
    dilatational pairs, and a pull-apart rhomb (rotated ellipse) at the
    step-over centre for dilatational pairs.
    """
    smap = {s.sid: s for s in strands}
    sa, sb = smap[pair.strand_a], smap[pair.strand_b]
    r0, c0 = pair.tip_a
    r1, c1 = pair.tip_b
    half = CONNECTOR_HALF_W(pair.w_px)
    # local bbox around the whole step-over structure
    span = int(np.ceil(max(pair.diag_px, pair.w_px) + 4.0 * half + 12))
    br0 = max(0, min(r0, r1) - span)
    br1 = min(shape[0], max(r0, r1) + span + 1)
    bc0 = max(0, min(c0, c1) - span)
    bc1 = min(shape[1], max(c0, c1) + span + 1)
    bbox = (br0, br1, bc0, bc1)
    lh, lw = br1 - br0, bc1 - bc0
    mask = np.zeros((lh, lw), bool)
    weight = np.zeros((lh, lw), np.float32)
    # local coordinates of the tips
    lr0, lc0 = r0 - br0, c0 - bc0
    lr1, lc1 = r1 - br0, c1 - bc0

    # --- oblique connector with tip extensions -------------------------------
    az_a = sa.az0 if pair.tip_a == sa.tip0 else sa.az1
    az_b = sb.az0 if pair.tip_b == sb.tip0 else sb.az1
    ext = TIP_EXT_RATIO * pair.w_px
    def ext_pt(r, c, az, sgn):
        e, n = np.sin(np.radians(az)), np.cos(np.radians(az))
        # choose the direction pointing away from the other tip
        de, dn = float(c1 - c0), float(-(r1 - r0))
        if sgn < 0:
            de, dn = -de, -dn
        if e * de + n * dn < 0:
            e, n = -e, -n
        return r - int(round(sgn * ext * n)), c + int(round(sgn * ext * e))
    p0 = ext_pt(lr0, lc0, az_a, +1)
    p1 = ext_pt(lr1, lc1, az_b, -1)
    p0 = (int(np.clip(p0[0], 0, lh - 1)), int(np.clip(p0[1], 0, lw - 1)))
    p1 = (int(np.clip(p1[0], 0, lh - 1)), int(np.clip(p1[1], 0, lw - 1)))
    rr, cc = skline(p0[0], p0[1], p1[0], p1[1])
    base = np.zeros((lh, lw), bool)
    base[rr, cc] = True
    if half > 1:
        base = ndi.binary_dilation(base, iterations=half - 1)
    mask |= base
    weight[base] = np.maximum(weight[base], 1.0)

    diag = pair.diag_px
    mid_r = int(round((lr0 + lr1) / 2))
    mid_c = int(round((lc0 + lc1) / 2))
    geom = dict(connector_half_w_px=half, connector_len_px=float(np.hypot(p1[0] - p0[0], p1[1] - p0[1])),
                n_echelon=0, rhomb_a_px=0.0, rhomb_b_px=0.0)

    if pair.dilatational:
        # --- en echelon strands ----------------------------------------------
        le = float(np.clip(1.5 * pair.w_px, 4.0, 30.0))
        n_e = max(2, int(diag / max(0.6 * le, 1.0))) if diag > 0 else 2
        n_e = min(n_e, 8)
        # connector direction (tip a -> tip b) in (east, north)
        ce, cn = float(c1 - c0), float(-(r1 - r0))
        nrm = max(np.hypot(ce, cn), 1e-9)
        ce, cn = ce / nrm, cn / nrm
        for k in range(n_e):
            f = (k + 0.5) / n_e
            cr = lr0 + f * (lr1 - lr0)
            cc_ = lc0 + f * (lc1 - lc0)
            ang = pair.mean_az + (ECH_ANGLE if k % 2 == 0 else -ECH_ANGLE)
            e_, n_ = np.sin(np.radians(ang)), np.cos(np.radians(ang))
            r_a = int(np.clip(round(cr - 0.5 * le * n_), 0, lh - 1))
            c_a = int(np.clip(round(cc_ + 0.5 * le * e_), 0, lw - 1))
            r_b = int(np.clip(round(cr + 0.5 * le * n_), 0, lh - 1))
            c_b = int(np.clip(round(cc_ - 0.5 * le * e_), 0, lw - 1))
            rr, cc = skline(r_a, c_a, r_b, c_b)
            mask[rr, cc] = True
            weight[rr, cc] = np.maximum(weight[rr, cc], 0.85)
        geom["n_echelon"] = n_e

        # --- pull-apart rhomb (rotated ellipse at the step-over centre) ------
        a_ax = 0.8 * max(diag, pair.w_px)
        b_ax = 0.45 * max(diag, pair.w_px)
        rr0 = max(0, mid_r - int(np.ceil(a_ax)) - 2)
        rr1 = min(lh, mid_r + int(np.ceil(a_ax)) + 3)
        cc0 = max(0, mid_c - int(np.ceil(a_ax)) - 2)
        cc1 = min(lw, mid_c + int(np.ceil(a_ax)) + 3)
        yy, xx = np.mgrid[rr0:rr1, cc0:cc1]
        de, dn = (xx - mid_c).astype(float), (-(yy - mid_r)).astype(float)
        az = pair.mean_az
        u_e, u_n = np.sin(np.radians(az)), np.cos(np.radians(az))
        du = de * u_e + dn * u_n
        dv = de * u_n - dn * u_e
        ell = (du / max(a_ax, 1e-6)) ** 2 + (dv / max(b_ax, 1e-6)) ** 2 <= 1.0
        mask[rr0:rr1, cc0:cc1] |= ell
        weight[rr0:rr1, cc0:cc1] = np.maximum(weight[rr0:rr1, cc0:cc1],
                                                np.where(ell, 0.9, 0.0).astype(np.float32))
        geom["rhomb_a_px"], geom["rhomb_b_px"] = float(a_ax), float(b_ax)
        subtype = "pull-apart"
    else:
        subtype = "transfer-overlap"

    geom_km = {k: (round(v / 10.0, 3) if k.endswith("_px") and v else v) for k, v in geom.items()}
    rationale = dict(
        layers=[],            # filled by scoring
        signature="tip-graph step-over: oblique connector"
                  + (" + en echelon strands + pull-apart rhomb" if pair.dilatational
                     else " (contractile overlap, transfer corridor)"),
        source=("GEMSDOE69 tip-graph v1; step-over geometry priors per standing prompt "
                "(Giddens & Faulds 2025 SGP-TR-229, as cited in the prompt)"),
        w_km=round(pair.w_px / 10.0, 3), along_km=round(pair.along_px / 10.0, 3),
        overlap_km=round(pair.overlap_px / 10.0, 3), separation_km=round(pair.separation_px / 10.0, 3),
        dtheta_deg=round(pair.dtheta, 2), mean_az_deg=round(pair.mean_az, 2),
        dilatational=bool(pair.dilatational),
        sense_note=("slip sense unobservable from raster catalogue; Walker Lane dextral prior "
                    "applied via the dilation diagnostic (a/W <= 0.5 -> dilatational)"),
        geometry=geom_km,
        strands=(pair.strand_a, pair.strand_b),
        tips=(pair.tip_a, pair.tip_b),
    )
    if not mask.any():
        mask[0, 0] = True   # degenerate guard; never expected at accepted geometry
    return Corridor(cid, pair, subtype, bbox, mask, weight, geom, rationale)


def _priority(p: TipPair) -> tuple:
    """Corridor priority before scoring: dilatational (pull-apart) first —
    Walker Lane hot systems favour pull-aparts/transfer zones (standing
    prompt) — then spacing close to the 2.8 km mean ramp width, then smaller
    gaps."""
    return (0 if p.dilatational else 1, abs(p.w_px - 28.0), p.w_px)


def build_corridors(catalogue: np.ndarray, strands: list[Strand],
                    shape: tuple[int, int], max_corridors: int = 1200,
                    w_min: float = W_MIN_PX, w_max: float = W_MAX_PX):
    """Pairs + corridors, de-duplicated by (strand pair, W, along)."""
    pairs = build_tip_pairs(strands, catalogue, w_min=w_min, w_max=w_max)
    seen, uniq = set(), []
    for p in sorted(pairs, key=_priority):
        k = _pair_key(p)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
        if len(uniq) >= max_corridors:
            break
    corridors = [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(uniq)]
    return corridors, uniq


# ---------------------------------------------------------------------------
# Vector-polyline corridor generator (INGENIOUS Qfaults polylines + dip polarity)
# ---------------------------------------------------------------------------

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


def generate(tips: list[Tip], polys: list[Poly], *, include_cut: bool = False,
             max_partners: int = 1, include_splays: bool = False) -> tuple[list[Line], dict]:
    idx = PolyIndex(polys)
    use = [t for t in tips if include_cut or not t.cut]
    lines: list[Line] = []
    counts = dict(relay_pairs=0, pullapart_pairs=0, termination_tips=0, transfer_links=0,
                  tip_continuations=0, wing_splays=0, flank_relay_breaches=0,
                  rejected_dip=0, rejected_facing=0, rejected_geometry=0, rejected_step_sense=0,
                  rejected_same_polyline=0, rejected_mixed_sense=0)
    if not use:
        return lines, counts
    pos = np.array([t.pos for t in use])
    tree = cKDTree(pos)
    valid: list[tuple[float, int, int]] = []
    for i, j in sorted(tree.query_pairs(W_MAX * 1.2)):
        ti, tj = use[i], use[j]
        ok, why = _pair_ok(ti, tj)
        if not ok:
            counts[why] += 1
            continue
        valid.append((float(np.hypot(*(tj.pos - ti.pos))), i, j))
    if max_partners <= 1:
        best_for: dict[int, tuple[float, int, int]] = {}
        for d, i, j in valid:
            for k in (i, j):
                if k not in best_for or d < best_for[k][0]:
                    best_for[k] = (d, i, j)
        chosen = sorted({(i, j) for _, i, j in best_for.values()})
    else:
        by_tip: dict[int, list[tuple[float, int, int]]] = {}
        for d, i, j in valid:
            by_tip.setdefault(i, []).append((d, i, j))
            by_tip.setdefault(j, []).append((d, i, j))
        chosen_set = set()
        for k, lst in by_tip.items():
            lst.sort(key=lambda t: t[0])
            for _, i, j in lst[:max_partners]:
                chosen_set.add((i, j))
        chosen = sorted(chosen_set)
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
    if include_splays:
        az_nne = np.radians(STRAND_AZ)
        d_nne = np.array([np.sin(az_nne), np.cos(az_nne)])
        for t in use:
            length = float(np.clip(0.30 * t.part_len, 10.0, 45.0))
            counts["tip_continuations"] += 1
            lines.append(Line("tip_continuation", "relay", t.pos, t.pos + length * t.out, (t.tid,),
                              0.0, length, dict(sense=t.sense, records=(t.record,))))
            wdir = d_nne if float(d_nne @ t.out) >= 0 else -d_nne
            sdir = _unit(0.6 * t.out + 0.4 * wdir)
            counts["wing_splays"] += 1
            lines.append(Line("wing_splay", "relay", t.pos, t.pos + 0.85 * length * sdir, (t.tid,),
                              0.0, 0.85 * length, dict(sense=t.sense, records=(t.record,))))
            near = idx.tree.query_ball_point(t.pos, 90.0)
            best_b: dict[int, tuple[float, np.ndarray]] = {}
            for k in near:
                o = int(idx.owner[k])
                if o == t.poly:
                    continue
                p = idx.P[k]
                v = p - t.pos
                if float(v @ t.out) < -10.0:
                    continue
                dist = float(np.hypot(*v))
                if dist < 2.0:
                    continue
                if o not in best_b or dist < best_b[o][0]:
                    best_b[o] = (dist, p)
            for o, (dist, p) in sorted(best_b.items(), key=lambda kv: kv[1][0])[:3]:
                counts["flank_relay_breaches"] += 1
                lines.append(Line("flank_relay_breach", "relay", t.pos, p, (t.tid,), dist, dist,
                                  dict(sense=t.sense, records=(t.record, int(polys[o].part.record)),
                                       target_record=int(polys[o].part.record))))
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
