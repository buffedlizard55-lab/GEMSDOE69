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


def search_radius_px(w_max: float) -> float:
    """Largest legal tip-to-tip distance: hypot(W, 3.5W) at W = w_max.

    Repair R2 (2026-10-20 review): the candidate search previously used
    ``r = w_max`` (150 px), which cannot reach legal large-W underlaps whose
    tip-to-tip distance reaches ``hypot(150, 525) ~= 546`` px.
    """
    return float(np.hypot(w_max, ALONG_MAX_RATIO * w_max))


def build_tip_pairs(strands: list[Strand], catalogue: np.ndarray,
                    w_min: float = W_MIN_PX, w_max: float = W_MAX_PX,
                    same_component: bool = False) -> list[TipPair]:
    """Emit every geometrically valid step-over tip pair from the tip graph.

    Along-strike separation and overlap are computed as interval arithmetic on
    the strike-axis projection of the tip-adjacent strand windows (length
    ``max(4W, 40 px)``), which is invariant to the sign ambiguity of axial
    directions.  Acceptance: W in [w_min, w_max]; separation <= 3.5 W;
    overlap <= 1.0 W.

    Repair R1 (2026-10-20 review): ``_tip_window_interval`` returns
    coordinates relative to *its own tip*, so strand B's interval must be
    offset by the tip-to-tip along-strike projection before the two intervals
    are compared.  Without the offset both intervals contain 0, separation is
    ~0 by construction, and the 3.5W rule never rejects anything (a 40 px gap
    at W = 5 px was admitted; see tests/test_corridors.py).

    ``same_component=False`` (production) keeps only pairs in different
    8-connected components; ``True`` keeps only same-component "virtual"
    pairs (hard-linked-ramp recovery test), through this same code path.
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
    radius = search_radius_px(w_max)
    pairs: list[TipPair] = []
    for i, (r0, c0, sid_a, end_a) in enumerate(tips):
        for j in tree.query_ball_point((r0, c0), r=radius):
            if j <= i:
                continue
            r1, c1, sid_b, end_b = tips[j]
            if sid_a == sid_b:
                continue
            sa, sb = smap[sid_a], smap[sid_b]
            same_comp = comp[r0, c0] == comp[r1, c1] and comp[r0, c0] > 0
            if same_comp != same_component:
                continue  # production: skip already-linked; virtual: keep only linked
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
            # signed along-strike projection of (B tip - A tip); also the
            # offset that puts B's tip-local interval into A's coordinates.
            along_signed = de * u_e + dn * u_n
            window = max(4.0 * cross, 40.0)
            # Cheap guaranteed-reject prefilter (keeps the 546 px search
            # tractable): each interval is at most ``window`` long, so the
            # global separation is >= |along| - 2*window.
            if abs(along_signed) - 2.0 * window > ALONG_MAX_RATIO * cross:
                continue
            ia = _tip_window_interval(sa, end_a, u_e, u_n, window)
            ib_local = _tip_window_interval(sb, end_b, u_e, u_n, window)
            ib = (ib_local[0] + along_signed, ib_local[1] + along_signed)
            overlap = max(0.0, min(ia[1], ib[1]) - max(ia[0], ib[0]))
            separation = max(0.0, max(ia[0], ib[0]) - min(ia[1], ib[1]))
            if separation > ALONG_MAX_RATIO * cross:
                continue
            if overlap > -OVERLAP_RATIO * cross:   # OVERLAP_RATIO = -1.0
                continue
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

    # Basin-interior disk (pre-registered, not fit). Ties the connector at
    # weight 1.0 so greedy placement can sit in the step-over interior, which
    # is where Walker Lane hot systems concentrate, without erasing the
    # oblique connector the prompt requires.
    rad = max(2, int(round(min(pair.w_px / 8.0, 6.0))))
    rr0 = max(0, mid_r - rad)
    rr1 = min(lh, mid_r + rad + 1)
    cc0 = max(0, mid_c - rad)
    cc1 = min(lw, mid_c + rad + 1)
    yy, xx = np.mgrid[rr0:rr1, cc0:cc1]
    disk = (yy - mid_r) ** 2 + (xx - mid_c) ** 2 <= rad * rad
    mask[rr0:rr1, cc0:cc1] |= disk
    weight[rr0:rr1, cc0:cc1] = np.maximum(
        weight[rr0:rr1, cc0:cc1], np.where(disk, 1.0, 0.0).astype(np.float32))
    geom["basin_disk_radius_px"] = float(rad)

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


# H69-E pre-registered width bins (100 m pixels). The 2026-10-12 cap sorted by
# |W - 2.8 km| and filled all 1,200 slots at exactly 2.8 km, so the published
# 0.1-14.6 km range never entered the emission. Bins span that range.
# Within each bin the quota is 70% dilatational / 30% overlapping (transfer).
WIDTH_BINS_PX = ((1.0, 10.0), (10.0, 30.0), (30.0, 60.0), (60.0, 150.0))
DILATATIONAL_FRACTION = 0.70


def select_stratified(pairs: list[TipPair], max_corridors: int = 1200) -> list[TipPair]:
    """Width-stratified, de-duplicated pair sample. Fixed quotas, not fit."""
    if max_corridors <= 0 or not pairs:
        return []
    per = max(1, max_corridors // len(WIDTH_BINS_PX))
    chosen: list[TipPair] = []
    used: set[tuple] = set()

    def take(group: list[TipPair], n: int) -> None:
        if n <= 0:
            return
        got = 0
        for p in group:
            k = _pair_key(p)
            if k in used:
                continue
            used.add(k)
            chosen.append(p)
            got += 1
            if got >= n:
                return

    for lo, hi in WIDTH_BINS_PX:
        bin_pairs = [p for p in pairs if lo <= p.w_px < hi or (hi == WIDTH_BINS_PX[-1][1] and p.w_px == hi)]
        dil = sorted((p for p in bin_pairs if p.dilatational), key=_priority)
        ov = sorted((p for p in bin_pairs if not p.dilatational), key=_priority)
        n_dil = int(round(DILATATIONAL_FRACTION * per))
        take(dil, n_dil)
        take(ov, per - n_dil)
        # if a class is short, fill the bin from the other class
        if sum(1 for p in chosen if lo <= p.w_px <= hi) < per:
            take(dil + ov, per - sum(1 for p in chosen if lo <= p.w_px <= hi))
    if len(chosen) < max_corridors:
        take(sorted(pairs, key=_priority), max_corridors - len(chosen))
    return chosen[:max_corridors]


def build_corridors(catalogue: np.ndarray, strands: list[Strand],
                    shape: tuple[int, int], max_corridors: int = 1200,
                    w_min: float = W_MIN_PX, w_max: float = W_MAX_PX,
                    selection: str = "stratified"):
    """Pairs + corridors, de-duplicated by (strand pair, W, along).

    ``selection='stratified'`` (H69-E default) spans the published width range.
    ``selection='mean_width'`` is the 2026-10-12 cap (nearest to 2.8 km) kept
    so the prior experiment remains reproducible.
    """
    pairs = build_tip_pairs(strands, catalogue, w_min=w_min, w_max=w_max)
    if selection == "mean_width":
        seen, uniq = set(), []
        for p in sorted(pairs, key=_priority):
            k = _pair_key(p)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(p)
            if len(uniq) >= max_corridors:
                break
    else:
        uniq = select_stratified(pairs, max_corridors=max_corridors)
    corridors = [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(uniq)]
    for c in corridors:
        c.rationale["selection"] = selection
        c.rationale["source"] = (
            "GEMSDOE69 tip-graph H69-E; step-over geometry priors per standing prompt "
            "(Giddens & Faulds 2025 SGP-TR-229, as cited in the prompt); "
            "width-stratified quotas, not the 2.8 km-only cap"
            if selection == "stratified" else c.rationale.get("source", "")
        )
    return corridors, uniq


def dilation_tendency(az: float) -> float:
    """Dilation tendency peaks for N-NE strike (~22.5 deg) under WNW extension (112.5 deg)."""
    return float(np.cos(np.radians(az - 22.5)) ** 2)


CORRIDOR_BAND_PX = 10.0
KINEMATIC_PRIOR = {"pullapart": 1.0, "relay": 0.9, "transfer": 0.8}


def _unit(v: np.ndarray) -> np.ndarray:
    a = np.asarray(v, float)
    n = float(np.hypot(a[0], a[1]))
    return a / n if n > 1e-9 else np.array([0.0, 1.0], dtype=float)


class PolyIndex:
    """Spatial KD-tree index over sampled visible polylines (map pixel units)."""

    def __init__(self, polys: list, step: float = 0.5):
        from . import traces
        pts, own, tang, dips = [], [], [], []
        for i, q in enumerate(polys):
            s = traces.sample_polyline(q.verts, step)
            d = traces._local_dirs(s)
            pts.append(s)
            own.append(np.full(len(s), i, dtype=np.int32))
            tang.append(d.astype(np.float32))
            if q.part.dip_side != 0:
                rn = np.stack([d[:, 1], -d[:, 0]], axis=1) * float(q.part.dip_side)
                dips.append(rn.astype(np.float32))
            else:
                dips.append(np.zeros_like(d, dtype=np.float32))
        if pts:
            self.pts = np.vstack(pts)
            self.owner = np.concatenate(own)
            self.tang = np.vstack(tang)
            self.dip_vec = np.vstack(dips)
        else:
            self.pts = np.zeros((0, 2), dtype=float)
            self.owner = np.zeros(0, dtype=np.int32)
            self.tang = np.zeros((0, 2), dtype=np.float32)
            self.dip_vec = np.zeros((0, 2), dtype=np.float32)
        self.tree = cKDTree(self.pts) if len(self.pts) else None


@dataclass
class Line:
    kind: str
    a: np.ndarray
    b: np.ndarray
    W: float = 0.0
    meta: dict = field(default_factory=dict)
    setting: str = "relay"
    score: float = 0.0
    terms: dict = field(default_factory=dict)
    rr: np.ndarray | None = field(default=None, repr=False)
    cc: np.ndarray | None = field(default=None, repr=False)

    @property
    def azimuth(self) -> float:
        d = np.asarray(self.b, float) - np.asarray(self.a, float)
        return axial_deg(float(d[0]), float(d[1]))

    @property
    def normal(self) -> np.ndarray:
        t = _unit(np.asarray(self.b, float) - np.asarray(self.a, float))
        return np.array([t[1], -t[0]], dtype=float)


def _pair_ok(ta, tb) -> tuple[bool, str]:
    """Test geometric and measured kinematic admissibility of tip pair (ta, tb)."""
    if getattr(ta, "poly", -1) == getattr(tb, "poly", -2):
        return False, "rejected_same_poly"

    out_a = _unit(np.asarray(ta.out, float))
    out_b = _unit(np.asarray(tb.out, float))
    # Sub-parallel terminal strikes (<= 35 deg axial divergence)
    if abs(float(np.dot(out_a, out_b))) < np.cos(np.radians(35.0)):
        return False, "rejected_strike"

    # Dip polarity check (recorded INGENIOUS DIPDIRECT + DEM hanging-wall polarity)
    if hasattr(ta, "dip_vec") and hasattr(tb, "dip_vec"):
        if ta.dip_vec is not None and tb.dip_vec is not None:
            if float(np.dot(ta.dip_vec, tb.dip_vec)) < 0:
                return False, "rejected_dip"

    pa = np.asarray(ta.pos, float)
    pb = np.asarray(tb.pos, float)
    d = pb - pa

    right_a = np.array([out_a[1], -out_a[0]])
    cross_step = float(np.dot(d, right_a))
    along_step = float(np.dot(d, out_a))
    w_px = abs(cross_step)

    # Spacing W in [1, 150] px (0.1 to 15 km)
    if w_px < 1.0 or w_px > 150.0:
        return False, "rejected_geometry"

    # Along-strike separation / overlap within [-3.5 W, +3.5 W]
    if abs(along_step) > 3.5 * w_px:
        return False, "rejected_geometry"

    # Strike-slip releasing step sense check (measured RL / LL where recorded)
    sense_a = getattr(ta, "sense", "N")
    sense_b = getattr(tb, "sense", "N")
    if sense_a == "RL":
        if cross_step < 0:
            return False, "rejected_step_sense"
    elif sense_a == "LL":
        if cross_step > 0:
            return False, "rejected_step_sense"
    elif sense_b in ("RL", "LL"):
        right_b = np.array([out_b[1], -out_b[0]])
        cross_b = float(np.dot(-d, right_b))
        if sense_b == "RL" and cross_b < 0:
            return False, "rejected_step_sense"
        if sense_b == "LL" and cross_b > 0:
            return False, "rejected_step_sense"

    return True, "ok"


def generate(tips: list, polys: list, include_cut: bool = False,
             max_partners: int = 4, include_splays: bool = True) -> tuple[list[Line], dict]:
    """Generate kinematics-resolved relay, pull-apart, and termination/transfer corridors."""
    active_tips = [t for t in tips if include_cut or not getattr(t, "cut", False)]
    lines: list[Line] = []
    counts = {"relay_pairs": 0, "pull_apart": 0, "terminations": 0, "transfer_links": 0}
    if not active_tips:
        return lines, counts

    pts = np.array([np.asarray(t.pos, float) for t in active_tips], dtype=float)
    tip_tree = cKDTree(pts)
    pidx = PolyIndex(polys) if (polys and include_splays) else None

    if len(active_tips) >= 2:
        rad = search_radius_px(W_MAX_PX)
        candidates_by_tip: dict[int, list[tuple[float, int]]] = {}
        for i, ta in enumerate(active_tips):
            for j in tip_tree.query_ball_point(pts[i], r=rad):
                if j == i:
                    continue
                ok, _ = _pair_ok(ta, active_tips[j])
                if ok:
                    dist = float(np.hypot(*(pts[j] - pts[i])))
                    candidates_by_tip.setdefault(i, []).append((dist, j))
        emitted_pairs: set[tuple[int, int]] = set()
        for i, cands in candidates_by_tip.items():
            cands.sort(key=lambda x: x[0])
            for _, j in cands[:max_partners]:
                pkey = (min(i, j), max(i, j))
                if pkey in emitted_pairs:
                    continue
                ta, tb = active_tips[i], active_tips[j]
                ok, _ = _pair_ok(ta, tb)
                if not ok:
                    continue
                emitted_pairs.add(pkey)
                pa = np.asarray(ta.pos, float)
                pb = np.asarray(tb.pos, float)
                d = pb - pa
                out_a = _unit(np.asarray(ta.out, float))
                out_b = _unit(np.asarray(tb.out, float))
                right_a = np.array([out_a[1], -out_a[0]])
                cross = float(np.dot(d, right_a))
                w = abs(cross)
                along = float(np.dot(d, out_a))
                is_overlap = along < 0
                sa = getattr(ta, "sense", "N")
                sb = getattr(tb, "sense", "N")
                mean_az = axial_deg(out_a[0], out_a[1])
                is_pullapart = (
                    sa in ("RL", "LL")
                    or sb in ("RL", "LL")
                    or (135.0 <= mean_az <= 175.0 and cross > 0)
                )
                setting = "pullapart" if is_pullapart else "relay"
                if is_pullapart:
                    counts["pull_apart"] += 1
                else:
                    counts["relay_pairs"] += 1
                meta = {
                    "overlap": is_overlap,
                    "W_km": round(w / 10.0, 3),
                    "L_km": round(abs(along) / 10.0, 3),
                    "sense": sa if sa in ("RL", "LL", "N") else sb,
                    "dip_source": f"{getattr(ta, 'dip_source', 'unk')}/{getattr(tb, 'dip_source', 'unk')}",
                    "records": (getattr(ta, "record", None), getattr(tb, "record", None)),
                }
                lines.append(Line("relay_connector", pa.copy(), pb.copy(), W=w, meta=meta, setting=setting))
                # Pull-apart / relay-ramp bounding sidewall continuations (soft-linked propagation)
                L_side_a = float(np.clip(abs(along) if along > 0 else 0.75 * w, 4.0, 45.0))
                along_b = float(np.dot(-d, out_b))
                L_side_b = float(np.clip(abs(along_b) if along_b > 0 else 0.75 * w, 4.0, 45.0))
                lines.append(Line("relay_sidewall", pa.copy(), pa + L_side_a * out_a, W=w, meta=meta, setting=setting))
                lines.append(Line("relay_sidewall", pb.copy(), pb + L_side_b * out_b, W=w, meta=meta, setting=setting))
                # Diagonal ramp breach / cross-basin fault between inner flank shoulders
                back = min(0.45 * w, 0.35 * getattr(ta, "part_len", w), 10.0)
                ba = pa - back * out_a
                bb = pb - min(0.45 * w, 0.35 * getattr(tb, "part_len", w), 10.0) * out_b
                lines.append(Line("relay_breach", ba, bb, W=w, meta=meta, setting=setting))
                # Staggered en echelon strands across the step-over interior
                n_ech = min(4, max(1, int(round(np.hypot(w, along) / 8.0))))
                span = np.clip(0.55 * w, 2.5, 16.0)
                ech_az = np.radians(mean_az + (22.0 if cross >= 0 else -22.0))
                ech_dir = np.array([np.sin(ech_az), np.cos(ech_az)], dtype=float)
                for k in range(n_ech):
                    frac = (k + 0.5) / n_ech
                    mid = pa + frac * d
                    lines.append(Line("relay_enechelon", mid - 0.5 * span * ech_dir,
                                      mid + 0.5 * span * ech_dir, W=w, meta=meta, setting=setting))

    if include_splays:
        counts["flank_relays"] = 0
        nne_u = np.array([np.sin(np.radians(22.5)), np.cos(np.radians(22.5))], dtype=float)
        cos35 = float(np.cos(np.radians(35.0)))
        for t in active_tips:
            pos = np.asarray(t.pos, float)
            out = _unit(np.asarray(t.out, float))
            right = np.array([out[1], -out[0]], dtype=float)
            sense = getattr(t, "sense", "N")
            L_tip = float(np.clip(0.50 * getattr(t, "part_len", 30.0), 10.0, 30.0))
            tmeta = {
                "sense": sense,
                "dip_source": getattr(t, "dip_source", "unk"),
                "records": (getattr(t, "record", None),),
                "W_km": round(L_tip / 10.0, 3),
                "L_km": round(L_tip / 10.0, 3),
            }
            if sense in ("RL", "LL"):
                sgn = 1.0 if sense == "RL" else -1.0
                splay1 = pos + 15.0 * (out + 0.5 * sgn * right)
                splay2 = pos + 15.0 * (out + 1.0 * sgn * right)
                lines.append(Line("termination_splay", pos.copy(), splay1, W=L_tip, meta=tmeta, setting="transfer"))
                lines.append(Line("termination_splay", pos.copy(), splay2, W=L_tip, meta=tmeta, setting="transfer"))
                counts["terminations"] += 2
            else:
                lines.append(Line("tip_continuation", pos.copy(), pos + L_tip * out,
                                  W=L_tip, meta=tmeta, setting="transfer"))
                # Conjugate tensile wing splays (hanging-wall / WNW-extension quadrants)
                for sgn_w in (-1.0, 1.0):
                    wdir = _unit(out + 0.36 * sgn_w * right)
                    lines.append(Line("wing_splay", pos.copy(), pos + 0.70 * L_tip * wdir,
                                      W=L_tip, meta=tmeta, setting="transfer"))
                counts["terminations"] += 3

            # Overlapping tip-to-flank synthetic relays + oblique transfer links
            if pidx is not None and pidx.tree is not None:
                near_idx = pidx.tree.query_ball_point(pos, r=85.0)
                if near_idx:
                    idx_arr = np.asarray(near_idx, dtype=np.int64)
                    owners = pidx.owner[idx_arr]
                    mask_other = owners != getattr(t, "poly", -1)
                    if mask_other.any():
                        idx_arr = idx_arr[mask_other]
                        owners = owners[mask_other]
                        deltas = pidx.pts[idx_arr] - pos[None, :]
                        dists = np.hypot(deltas[:, 0], deltas[:, 1])
                        # Group by owner polyline (up to 3 closest flank strands)
                        seen_poly = set()
                        order_d = np.argsort(dists)
                        for oi in order_d:
                            p_own = int(owners[oi])
                            if p_own in seen_poly:
                                continue
                            seen_poly.add(p_own)
                            kpt = int(idx_arr[oi])
                            fpt = pidx.pts[kpt]
                            ftang = pidx.tang[kpt]
                            fdip = pidx.dip_vec[kpt]
                            dvec = deltas[oi]
                            cross_f = float(np.dot(dvec, right))
                            w_f = abs(cross_f)
                            along_f = float(np.dot(dvec, out))
                            target_poly = polys[p_own]
                            rmeta = dict(tmeta, W_km=round(w_f / 10.0, 3),
                                         L_km=round(float(dists[oi]) / 10.0, 3),
                                         target_record=getattr(target_poly.part, "record", None),
                                         records=(getattr(t, "record", None), getattr(target_poly.part, "record", None)))
                            sub_parallel = abs(float(np.dot(out, ftang))) >= cos35
                            same_dip = True
                            if getattr(t, "dip_vec", None) is not None and np.hypot(fdip[0], fdip[1]) > 0.5:
                                same_dip = float(np.dot(t.dip_vec, fdip)) >= 0.0
                            step_ok = True
                            if sense == "RL" and cross_f < 0:
                                step_ok = False
                            elif sense == "LL" and cross_f > 0:
                                step_ok = False

                            if sub_parallel and same_dip and step_ok and 2.5 <= w_f <= 80.0 and abs(along_f) <= 2.5 * w_f + 15.0:
                                f_set = "pullapart" if sense in ("RL", "LL") else "relay"
                                # Oblique synthetic ramp connector from tip across ramp forward along flank
                                target_oblique = fpt + min(1.2 * w_f, 20.0) * out
                                lines.append(Line("flank_relay", pos.copy(), target_oblique,
                                                  W=w_f, meta=rmeta, setting=f_set))
                                # Mid-ramp synthetic breach strand parallel to strike
                                mid_f = 0.5 * (pos + fpt)
                                span_f = min(1.0 * w_f, 18.0)
                                lines.append(Line("flank_breach", mid_f - 0.5 * span_f * out,
                                                  mid_f + 1.1 * span_f * out,
                                                  W=w_f, meta=rmeta, setting=f_set))
                                counts["flank_relays"] += 1
                            elif along_f > 2.0 and float(dists[oi]) <= 45.0:
                                lines.append(Line("transfer_link", pos.copy(), fpt.copy(),
                                                  W=float(dists[oi]), meta=rmeta, setting="transfer"))
                                counts["transfer_links"] += 1
                            if len(seen_poly) >= 3:
                                break

    return lines, counts


def rasterize_lines(lines: list[Line], footprint: np.ndarray, visible: np.ndarray | None = None) -> None:
    """Sample every candidate corridor trace to grid pixels, stopping at known visible traces."""
    from . import traces
    H, W = footprint.shape
    is_splay = {"termination_splay", "tip_continuation", "wing_splay"}
    for ln in lines:
        seg = traces.sample_polyline(np.vstack([ln.a, ln.b]), step=0.5)
        r, c = traces.rc_of(seg)
        inside = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        if ln.kind in is_splay and visible is not None and len(r) > 4:
            # Truncate free-tip splays if they run into another visible fault after leaving tip
            hit_vis = np.zeros(len(r), bool)
            hit_vis[inside] = visible[r[inside], c[inside]]
            hit_vis[:4] = False
            stops = np.flatnonzero(hit_vis)
            if stops.size:
                cut = int(stops[0])
                r, c, inside = r[:cut], c[:cut], inside[:cut]
        r, c = r[inside], c[inside]
        if r.size == 0:
            ln.rr = np.zeros(0, dtype=np.int32)
            ln.cc = np.zeros(0, dtype=np.int32)
            continue
        ok = footprint[r, c]
        if visible is not None:
            ok = ok & ~visible[r, c]
        r, c = r[ok], c[ok]
        if r.size > 1:
            packed = r * np.int64(W) + c
            _, uniq_idx = np.unique(packed, return_index=True)
            uniq_idx.sort()
            r, c = r[uniq_idx], c[uniq_idx]
        ln.rr = r.astype(np.int32)
        ln.cc = c.astype(np.int32)


def score_lines(lines: list[Line], layers: dict[str, np.ndarray]) -> None:
    """Score candidate corridors with H69-K cross-corridor directional gradient + physics."""
    g_edge = layers["grav_edge"]
    m_edge = layers["mag_edge"]
    m_low = layers["mag_low"]
    scarp = layers["scarp"]
    g_ge = layers.get("grav_ge")
    g_gn = layers.get("grav_gn")
    m_ge = layers.get("mag_ge")
    m_gn = layers.get("mag_gn")
    has_dir = all(x is not None for x in (g_ge, g_gn, m_ge, m_gn))

    for ln in lines:
        td = dilation_tendency(ln.azimuth)
        w_kin = KINEMATIC_PRIOR.get(ln.setting, 0.8)
        if ln.rr is None or ln.rr.size == 0:
            ln.score = float(0.08 * td + 0.06 * w_kin)
            ln.terms = {"grav_edge": 0.0, "mag_edge": 0.0, "grav_perp": 0.0,
                        "mag_perp": 0.0, "joint_conv": 0.0, "mag_low": 0.0,
                        "scarp": 0.0, "td": td, "kinematic": w_kin}
            continue
        rr, cc = ln.rr, ln.cc
        ge_val = float(g_edge[rr, cc].mean())
        me_val = float(m_edge[rr, cc].mean())
        ml_val = float(m_low[rr, cc].mean())
        sc_val = float(scarp[rr, cc].mean())
        if has_dir:
            n_e, n_n = float(ln.normal[0]), float(ln.normal[1])
            gp_dir = float(np.abs(g_ge[rr, cc] * n_e + g_gn[rr, cc] * n_n).mean())
            mp_dir = float(np.abs(m_ge[rr, cc] * n_e + m_gn[rr, cc] * n_n).mean())
            grav_perp = 0.55 * gp_dir + 0.45 * ge_val
            mag_perp = 0.55 * mp_dir + 0.45 * me_val
        else:
            grav_perp = ge_val
            mag_perp = me_val
        joint_conv = min(grav_perp, mag_perp)
        # Pre-registered H69-K score (weights sum to 1.00)
        s = (
            0.22 * grav_perp
            + 0.20 * mag_perp
            + 0.16 * joint_conv
            + 0.14 * ml_val
            + 0.14 * sc_val
            + 0.08 * td
            + 0.06 * w_kin
        )
        ln.score = float(s)
        ln.terms = {
            "grav_edge": ge_val,
            "mag_edge": me_val,
            "grav_perp": grav_perp,
            "mag_perp": mag_perp,
            "joint_conv": joint_conv,
            "mag_low": ml_val,
            "scarp": sc_val,
            "td": td,
            "kinematic": w_kin,
        }


def line_id_raster(lines: list[Line], shape: tuple[int, int]) -> np.ndarray:
    """Paint corridor trace indices onto ``shape`` (-1 off trace; highest score wins)."""
    lid = np.full(shape, -1, dtype=np.int32)
    order = sorted(range(len(lines)), key=lambda k: lines[k].score)
    for k in order:
        ln = lines[k]
        if ln.rr is not None and ln.rr.size:
            lid[ln.rr, ln.cc] = k
    return lid


def corridor_fields(lines: list[Line], shape: tuple[int, int],
                    max_dist_px: float = CORRIDOR_BAND_PX) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute corridor score field ``s_band``, trace distance ``dline``, and trace mask ``on``."""
    lid = line_id_raster(lines, shape)
    on = lid >= 0
    if not on.any():
        return (np.zeros(shape, np.float32),
                np.full(shape, np.inf, np.float32),
                on)
    dline, (iy, ix) = ndi.distance_transform_edt(~on, return_indices=True)
    dline = dline.astype(np.float32)
    scores = np.array([ln.score for ln in lines], dtype=np.float32)
    nearest_id = lid[iy, ix]
    s_band = np.where((dline <= max_dist_px) & (nearest_id >= 0),
                      scores[np.maximum(nearest_id, 0)],
                      np.float32(0.0)).astype(np.float32)
    return s_band, dline, on
