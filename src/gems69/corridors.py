"""Tip-graph step-over pairing, geodesic multi-physics routing, pull-apart margin
splays, and wing-crack termination corridors.

Geometry & structural rules (standing prompt, Giddens & Faulds 2025 SGP-TR-229):
  * Relay ramps typically 3-3.5x longer than wide, widths W in 0.1-15 km
    ([1, 150] px at 100 m resolution; mean 2.8 km);
  * Along-strike separation <= 3.5 W (evaluated in world coordinates on a shared
    origin so distant colinear tips are strictly rejected);
  * KD-tree search radius = hypot(W_max, 3.5 * W_max) = 3.64014 * W_max so long
    narrow step-overs are never truncated by a cross-strike-only ball query;
  * Measured dip compatibility: opposing pure-normal dips (d_a . d_b < -0.25)
    are rejected;
  * Measured Walker Lane / Great Basin kinematics: dextral (RL) right-steps and
    sinistral (LL) left-steps form true releasing pull-apart rhombs emitting
    paired basin-bounding margin splays + geodesic diagonal breach + Riedel
    en echelon strands; normal synthetic ramps emit geodesic oblique breaching
    traces + en echelon strands; free fault tips emit wing-crack / horse-tail
    splay fans guided by multi-physics edge admittance.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.draw import line as skline
from skimage.graph import route_through_array

from .tips import Strand, StrandKinematics, axial_deg, axial_diff, axial_mean

W_MIN_PX = 1.0             # 0.1 km
W_MAX_PX = 150.0           # 15 km
ALONG_MAX_RATIO = 3.5
OVERLAP_RATIO = -1.0       # accept overlap up to 1.0 W
MAX_DTHETA = 30.0          # deg, sub-parallel terminal strikes
DILATATION_MAX_ALONG = 0.5
ECH_ANGLE = 22.0           # deg, synthetic en echelon Riedel strand angle
TIP_EXT_RATIO = 0.25       # extend anchor up to 0.25 W along strike
MIN_STRAND_PX = 4.0


@dataclass
class TipPair:
    strand_a: int
    strand_b: int
    tip_a: tuple[int, int]     # (row, col)
    tip_b: tuple[int, int]     # (row, col)
    w_px: float                # cross-strike spacing (100 m px)
    along_px: float            # signed tip-to-tip projection on strike axis
    dtheta: float              # axial strike difference (deg)
    mean_az: float             # mean axial azimuth of the two terminal strikes
    diag_px: float             # Euclidean tip-to-tip distance
    dilatational: bool
    comp_a: int
    comp_b: int
    overlap_px: float = 0.0
    separation_px: float = 0.0
    kinematic_regime: str = "relay-ramp"   # 'pull-apart' | 'relay-ramp' | 'transfer-overlap'
    sense_summary: str = "unattributed"
    dip_summary: str = "unattributed"


@dataclass
class Corridor:
    cid: int
    pair: TipPair
    subtype: str               # 'pull-apart' | 'relay-ramp' | 'transfer-overlap' | 'termination-splay'
    bbox: tuple[int, int, int, int]   # (r0, r1, c0, c1) full-grid window
    local_mask: np.ndarray     # bool, 1D trace + damage halo inside bbox
    local_weight: np.ndarray   # float32, distance-graded trace weight in (0, 1] inside bbox
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
        contrib = np.float32(value) * self.local_weight
        sl = propensity[r0:r1, c0:c1]
        m = self.local_mask
        sl[m] = np.maximum(sl[m], contrib[m])


def _component_ids(catalogue: np.ndarray) -> np.ndarray:
    comp, _ = ndi.label(catalogue, structure=np.ones((3, 3), int))
    return comp


def _tip_window_interval(strand: Strand, end: int, u_e: float, u_n: float,
                         window_px: float, ref_r: float = 0.0, ref_c: float = 0.0) -> tuple[float, float]:
    """Project the tip-adjacent ``window_px`` of ``strand`` onto the shared world axis."""
    ys = strand.ys.astype(float)
    xs = strand.xs.astype(float)
    if end == 1:
        ys, xs = ys[::-1], xs[::-1]
    steps = np.hypot(np.diff(ys), np.diff(xs))
    s = np.concatenate([[0.0], np.cumsum(steps)])
    keep = s <= window_px
    if keep.sum() < 2:
        keep[:2] = True
    de = xs[keep] - ref_c
    dn = -(ys[keep] - ref_r)
    axis = de * u_e + dn * u_n
    return float(axis.min()), float(axis.max())


def _outward_tip_dir(strand: Strand, end: int, tail: int = 12) -> tuple[float, float]:
    """Unit outward vector (east, north) pointing away from the strand interior at ``end``."""
    ys = strand.ys.astype(float)
    xs = strand.xs.astype(float)
    if end == 1:
        ys, xs = ys[::-1], xs[::-1]
    k = min(tail, len(ys) - 1)
    # interior -> tip vector is tip - interior = (xs[0] - xs[k], -(ys[0] - ys[k]))
    de = float(xs[0] - xs[k])
    dn = float(-(ys[0] - ys[k]))
    nrm = np.hypot(de, dn)
    if nrm < 1e-9:
        de = float(xs[0] - xs[1])
        dn = float(-(ys[0] - ys[1]))
        nrm = max(np.hypot(de, dn), 1e-9)
    return de / nrm, dn / nrm


def _classify_pair_kinematics(
    sa: Strand, end_a: int, sb: Strand, end_b: int,
    de: float, dn: float, overlap: float, cross: float, mean_az: float,
    kinematics: dict[int, StrandKinematics] | None,
) -> tuple[bool, str, str, str]:
    """Return (accepted, regime, sense_summary, dip_summary)."""
    if kinematics is None:
        dil = overlap <= DILATATION_MAX_ALONG * cross
        regime = "pull-apart" if (dil and axial_diff(mean_az, 22.5) <= 28.0) else (
            "relay-ramp" if dil else "transfer-overlap"
        )
        return True, regime, "raster-only (no CSV metadata passed)", "subparallel strike proxy"

    ka = kinematics.get(sa.sid, StrandKinematics(sa.sid))
    kb = kinematics.get(sb.sid, StrandKinematics(sb.sid))
    eff_a = ka.sense if ka.sense in ("RL", "LL") else (ka.secondary_sense if ka.secondary_sense in ("RL", "LL") else ka.sense)
    eff_b = kb.sense if kb.sense in ("RL", "LL") else (kb.secondary_sense if kb.secondary_sense in ("RL", "LL") else kb.sense)

    dip_note = f"{ka.dip_source}/{kb.dip_source}"
    # Reject opposite-dip pure normal fault pairs
    if eff_a not in ("RL", "LL") and eff_b not in ("RL", "LL"):
        if ka.dip_vec is not None and kb.dip_vec is not None:
            dot_dip = ka.dip_vec[0] * kb.dip_vec[0] + ka.dip_vec[1] * kb.dip_vec[1]
            if dot_dip < -0.25:
                return False, "rejected-opposite-dip", f"{ka.sense}/{kb.sense}", f"opposing ({dot_dip:.2f})"

    # Outward tangent at tip A: right-normal = (out_n, -out_e)
    oe_a, on_a = _outward_tip_dir(sa, end_a)
    right_step_a = de * on_a + dn * (-oe_a)

    # Check strike-slip step sense
    ss_sense = eff_a if eff_a in ("RL", "LL") else (eff_b if eff_b in ("RL", "LL") else None)
    if ss_sense == "RL":
        if right_step_a >= 0:
            return True, "pull-apart", f"RL right-stepping releasing ({ka.fault_name or 'mapped'})", dip_note
        return True, "transfer-overlap", "RL left-stepping restraining transfer", dip_note
    if ss_sense == "LL":
        if right_step_a <= 0:
            return True, "pull-apart", f"LL left-stepping releasing ({ka.fault_name or 'mapped'})", dip_note
        return True, "transfer-overlap", "LL right-stepping restraining transfer", dip_note

    # Normal / transtensional step-over
    if overlap <= DILATATION_MAX_ALONG * cross:
        if axial_diff(mean_az, 22.5) <= 22.5 and ka.secondary_sense in ("RL", "LL"):
            return True, "pull-apart", "oblique-normal transtensional releasing", dip_note
        return True, "relay-ramp", f"synthetic normal step-over ({ka.sense}/{kb.sense})", dip_note
    return True, "transfer-overlap", "overlapping normal displacement-transfer", dip_note


def build_tip_pairs(
    strands: list[Strand],
    catalogue: np.ndarray,
    w_min: float = W_MIN_PX,
    w_max: float = W_MAX_PX,
    kinematics: dict[int, StrandKinematics] | None = None,
    allow_same_component: bool = False,
) -> list[TipPair]:
    """Emit every geometrically & kinematically valid step-over tip pair."""
    strands = [s for s in strands if s.length_px >= MIN_STRAND_PX]
    if len(strands) < 2:
        return []
    comp = _component_ids(catalogue)
    smap = {s.sid: s for s in strands}
    tips = []
    for s in strands:
        tips.append((s.tip0[0], s.tip0[1], s.sid, 0))
        tips.append((s.tip1[0], s.tip1[1], s.sid, 1))
    pts = np.array([(t[0], t[1]) for t in tips], float)
    tip_r = np.array([t[0] for t in tips], np.int32)
    tip_c = np.array([t[1] for t in tips], np.int32)
    tip_sid = np.array([t[2] for t in tips], np.int32)
    tip_end = np.array([t[3] for t in tips], np.int32)
    tip_comp = comp[tip_r, tip_c].astype(np.int32)
    tip_az = np.array([
        (smap[t[2]].az0 if t[3] == 0 else smap[t[2]].az1) for t in tips
    ], np.float64)

    tree = cKDTree(pts)
    search_r = float(np.hypot(w_max, ALONG_MAX_RATIO * w_max))
    ij = tree.query_pairs(r=search_r, output_type="ndarray")
    if len(ij) == 0:
        return []

    i_arr, j_arr = ij[:, 0], ij[:, 1]
    keep = tip_sid[i_arr] != tip_sid[j_arr]
    if not allow_same_component:
        keep &= (tip_comp[i_arr] != tip_comp[j_arr]) | (tip_comp[i_arr] == 0)
    i_arr, j_arr = i_arr[keep], j_arr[keep]

    da = np.abs(tip_az[i_arr] - tip_az[j_arr]) % 180.0
    dth_arr = np.minimum(da, 180.0 - da)
    keep2 = dth_arr <= MAX_DTHETA
    i_arr, j_arr, dth_arr = i_arr[keep2], j_arr[keep2], dth_arr[keep2]

    # Exact axial circular mean in degrees [0, 180)
    a1_r = np.radians(2.0 * tip_az[i_arr])
    a2_r = np.radians(2.0 * tip_az[j_arr])
    m_az_arr = (0.5 * np.degrees(np.arctan2(np.sin(a1_r) + np.sin(a2_r),
                                            np.cos(a1_r) + np.cos(a2_r)))) % 180.0
    u_e_arr = np.sin(np.radians(m_az_arr))
    u_n_arr = np.cos(np.radians(m_az_arr))
    de_arr = (tip_c[j_arr] - tip_c[i_arr]).astype(np.float64)
    dn_arr = (-(tip_r[j_arr] - tip_r[i_arr])).astype(np.float64)
    cross_arr = np.abs(de_arr * u_n_arr - dn_arr * u_e_arr)
    along_tt_arr = np.abs(de_arr * u_e_arr + dn_arr * u_n_arr)
    win_arr = np.maximum(4.0 * cross_arr, 40.0)
    keep3 = (
        (cross_arr >= w_min)
        & (cross_arr <= w_max)
        & (along_tt_arr <= ALONG_MAX_RATIO * cross_arr + 2.0 * win_arr + 1.0)
    )
    i_arr = i_arr[keep3]
    j_arr = j_arr[keep3]
    dth_arr = dth_arr[keep3]
    m_az_arr = m_az_arr[keep3]
    u_e_arr = u_e_arr[keep3]
    u_n_arr = u_n_arr[keep3]
    de_arr = de_arr[keep3]
    dn_arr = dn_arr[keep3]
    cross_arr = cross_arr[keep3]
    diag_arr = np.hypot(de_arr, dn_arr)

    best_by_strand: dict[tuple[int, int], TipPair] = {}
    for k_idx in range(len(i_arr)):
        i = int(i_arr[k_idx])
        j = int(j_arr[k_idx])
        r0, c0, sid_a, end_a = tips[i]
        r1, c1, sid_b, end_b = tips[j]
        ca, cb = int(tip_comp[i]), int(tip_comp[j])
        sa, sb = smap[sid_a], smap[sid_b]
        dth = float(dth_arr[k_idx])
        m_az = float(m_az_arr[k_idx])
        u_e, u_n = float(u_e_arr[k_idx]), float(u_n_arr[k_idx])
        de, dn = float(de_arr[k_idx]), float(dn_arr[k_idx])
        cross = float(cross_arr[k_idx])
        diag = float(diag_arr[k_idx])
        window = max(4.0 * cross, 40.0)
        ia = _tip_window_interval(sa, end_a, u_e, u_n, window, ref_r=float(r0), ref_c=float(c0))
        ib = _tip_window_interval(sb, end_b, u_e, u_n, window, ref_r=float(r0), ref_c=float(c0))
        overlap = max(0.0, min(ia[1], ib[1]) - max(ia[0], ib[0]))
        separation = max(0.0, max(ia[0], ib[0]) - min(ia[1], ib[1]))
        if separation > ALONG_MAX_RATIO * cross:
            continue
        if overlap > -OVERLAP_RATIO * cross:
            continue
        ok, regime, sense_sum, dip_sum = _classify_pair_kinematics(
            sa, end_a, sb, end_b, de, dn, overlap, cross, m_az, kinematics
        )
        if not ok:
            continue
        along_signed = de * u_e + dn * u_n
        dil = regime in ("pull-apart", "relay-ramp")
        cand = TipPair(
            sid_a, sid_b, (int(r0), int(c0)), (int(r1), int(c1)),
            float(cross), float(along_signed), float(dth), float(m_az),
            diag, dil, ca, cb,
            overlap_px=float(overlap), separation_px=float(separation),
            kinematic_regime=regime, sense_summary=sense_sum, dip_summary=dip_sum,
        )
        skey = (min(sid_a, sid_b), max(sid_a, sid_b))
        prev = best_by_strand.get(skey)
        if prev is None or cand.diag_px < prev.diag_px:
            best_by_strand[skey] = cand
    return list(best_by_strand.values())


_HALO_OFFSETS = {
    halo_px: [
        (dy, dx, float(np.clip(1.0 - 0.24 * np.hypot(dy, dx), 0.35, 1.0)))
        for dy in range(-halo_px, halo_px + 1)
        for dx in range(-halo_px, halo_px + 1)
        if np.hypot(dy, dx) <= float(halo_px) + 1e-9
    ]
    for halo_px in (0, 1, 2, 3)
}


def _paint_trace_graded(mask: np.ndarray, weight: np.ndarray,
                        rr: np.ndarray, cc: np.ndarray, peak: float = 1.0, halo_px: int = 2) -> None:
    """Paint a crisp 1D trace with exact Euclidean distance-graded weights in O(|rr|)."""
    H, W = mask.shape
    if len(rr) == 0:
        return
    rr = np.clip(rr, 0, H - 1)
    cc = np.clip(cc, 0, W - 1)
    offsets = _HALO_OFFSETS.get(halo_px)
    if offsets is not None:
        for dy, dx, fac in offsets:
            ry = np.clip(rr + dy, 0, H - 1)
            cx = np.clip(cc + dx, 0, W - 1)
            # Only stamp valid in-bounds shifts:
            ib = (rr + dy >= 0) & (rr + dy < H) & (cc + dx >= 0) & (cc + dx < W)
            if not ib.any():
                continue
            ry_v, cx_v = ry[ib], cx[ib]
            mask[ry_v, cx_v] = True
            np.maximum.at(weight, (ry_v, cx_v), np.float32(peak * fac))
        return
    core = np.zeros((H, W), bool)
    core[rr, cc] = True
    dist = ndi.distance_transform_edt(~core)
    band = dist <= float(halo_px)
    prof = np.where(band, peak * np.clip(1.0 - 0.24 * dist, 0.35, 1.0), 0.0).astype(np.float32)
    mask |= band
    np.maximum(weight, prof, out=weight)


def _geodesic_trace(p0: tuple[int, int], p1: tuple[int, int],
                    admit_win: np.ndarray | None, scale_w: float) -> tuple[np.ndarray, np.ndarray]:
    """Minimum-resistance 8-connected path between p0 and p1 in local bbox coords."""
    lh, lw = admit_win.shape if admit_win is not None else (max(p0[0], p1[0]) + 1, max(p0[1], p1[1]) + 1)
    if admit_win is None or (p0 == p1) or lh * lw > 90_000:
        rr, cc = skline(p0[0], p0[1], p1[0], p1[1])
        return rr, cc
    yy, xx = np.ogrid[:lh, :lw]
    # Perpendicular distance to the p0->p1 chord regularizes path excursion within the ramp
    dr = float(p1[0] - p0[0])
    dc = float(p1[1] - p0[1])
    ln = max(np.hypot(dr, dc), 1.0)
    d_perp = np.abs(dr * (xx - p0[1]) - dc * (yy - p0[0])) / ln
    cost = (1.0 - 0.72 * np.clip(admit_win, 0.0, 1.0)
            + 0.24 * (d_perp / max(scale_w, 6.0))).astype(np.float32)
    cost = np.maximum(cost, 0.12)
    path, _ = route_through_array(cost, p0, p1, fully_connected=True, geometric=True)
    pts = np.asarray(path, dtype=np.int32)
    return pts[:, 0], pts[:, 1]


def corridor_from_pair(
    cid: int,
    pair: TipPair,
    strands: list[Strand],
    shape: tuple[int, int],
    admittance: np.ndarray | None = None,
) -> Corridor:
    """Construct localized 1D breaching, margin-splay, and en echelon corridor traces."""
    smap = {s.sid: s for s in strands}
    sa, sb = smap[pair.strand_a], smap[pair.strand_b]
    r0, c0 = pair.tip_a
    r1, c1 = pair.tip_b
    pad = int(np.ceil(min(max(0.55 * pair.w_px, 8.0), 42.0)))
    br0 = max(0, min(r0, r1) - pad)
    br1 = min(shape[0], max(r0, r1) + pad + 1)
    bc0 = max(0, min(c0, c1) - pad)
    bc1 = min(shape[1], max(c0, c1) + pad + 1)
    bbox = (br0, br1, bc0, bc1)
    lh, lw = br1 - br0, bc1 - bc0
    mask = np.zeros((lh, lw), bool)
    weight = np.zeros((lh, lw), np.float32)
    admit_win = admittance[br0:br1, bc0:bc1] if admittance is not None else None

    lr0, lc0 = r0 - br0, c0 - bc0
    lr1, lc1 = r1 - br0, c1 - bc0
    end_a = 0 if pair.tip_a == sa.tip0 else 1
    end_b = 0 if pair.tip_b == sb.tip0 else 1
    oe_a, on_a = _outward_tip_dir(sa, end_a)
    oe_b, on_b = _outward_tip_dir(sb, end_b)

    ext = min(TIP_EXT_RATIO * pair.w_px, 12.0)
    p0 = (int(np.clip(round(lr0 - ext * on_a), 0, lh - 1)),
          int(np.clip(round(lc0 + ext * oe_a), 0, lw - 1)))
    p1 = (int(np.clip(round(lr1 - ext * on_b), 0, lh - 1)),
          int(np.clip(round(lc1 + ext * oe_b), 0, lw - 1)))

    # 1. Primary minimum-resistance breaching trace (geodesic on multi-physics admittance)
    rr, cc = _geodesic_trace(p0, p1, admit_win, pair.w_px)
    _paint_trace_graded(mask, weight, rr, cc, peak=1.0, halo_px=2)
    trace_pts = len(rr)
    geom = dict(connector_len_px=float(trace_pts), n_echelon=0, margin_splays=0)

    subtype = pair.kinematic_regime
    if subtype == "pull-apart":
        # 2a. Paired pull-apart basin-bounding normal-oblique margin splays
        # Project each strand along its outward strike across the step-over length
        proj_len = min(max(0.75 * pair.diag_px, 6.0), 48.0)
        m_a = (int(np.clip(round(lr0 - proj_len * on_a), 0, lh - 1)),
               int(np.clip(round(lc0 + proj_len * oe_a), 0, lw - 1)))
        m_b = (int(np.clip(round(lr1 - proj_len * on_b), 0, lh - 1)),
               int(np.clip(round(lc1 + proj_len * oe_b), 0, lw - 1)))
        rra, cca = _geodesic_trace((lr0, lc0), m_a, admit_win, 0.5 * pair.w_px)
        rrb, ccb = _geodesic_trace((lr1, lc1), m_b, admit_win, 0.5 * pair.w_px)
        _paint_trace_graded(mask, weight, rra, cca, peak=0.92, halo_px=2)
        _paint_trace_graded(mask, weight, rrb, ccb, peak=0.92, halo_px=2)
        geom["margin_splays"] = 2

    if pair.dilatational:
        # 2b. Synthetic en echelon Riedel strands stepped along the geodesic trace
        le = float(np.clip(0.85 * pair.w_px, 4.0, 20.0))
        n_e = min(max(2, int(pair.diag_px / max(0.7 * le, 1.0))), 6)
        for k in range(n_e):
            idx = min(int((k + 0.5) / n_e * len(rr)), len(rr) - 1)
            cr, cc_ = float(rr[idx]), float(cc[idx])
            ang = pair.mean_az + (ECH_ANGLE if k % 2 == 0 else -ECH_ANGLE)
            e_, n_ = np.sin(np.radians(ang)), np.cos(np.radians(ang))
            ra = int(np.clip(round(cr - 0.5 * le * n_), 0, lh - 1))
            ca_ = int(np.clip(round(cc_ + 0.5 * le * e_), 0, lw - 1))
            rb = int(np.clip(round(cr + 0.5 * le * n_), 0, lh - 1))
            cb_ = int(np.clip(round(cc_ - 0.5 * le * e_), 0, lw - 1))
            re_r, re_c = skline(ra, ca_, rb, cb_)
            _paint_trace_graded(mask, weight, re_r, re_c, peak=0.84, halo_px=1)
        geom["n_echelon"] = n_e

    geom_km = {k: (round(v / 10.0, 3) if k.endswith("_px") and v else v) for k, v in geom.items()}
    rationale = dict(
        layers=[],
        signature=(
            f"{subtype}: geodesic multi-physics connector"
            + (" + paired pull-apart margin splays" if geom["margin_splays"] else "")
            + (f" + {geom['n_echelon']} en echelon strands" if geom["n_echelon"] else "")
        ),
        source=("GEMSDOE69 H69-E kinematic tip-graph + Dijkstra multi-physics routing; "
                "Qfaults slip/dip metadata + Giddens & Faulds (2025, SGP-TR-229)"),
        w_km=round(pair.w_px / 10.0, 3),
        along_km=round(pair.along_px / 10.0, 3),
        overlap_km=round(pair.overlap_px / 10.0, 3),
        separation_km=round(pair.separation_px / 10.0, 3),
        dtheta_deg=round(pair.dtheta, 2),
        mean_az_deg=round(pair.mean_az, 2),
        dilatational=bool(pair.dilatational),
        kinematic_regime=pair.kinematic_regime,
        sense_note=pair.sense_summary,
        dip_note=pair.dip_summary,
        geometry=geom_km,
        strands=(pair.strand_a, pair.strand_b),
        tips=(pair.tip_a, pair.tip_b),
    )
    if not mask.any():
        mask[lr0, lc0] = True
        weight[lr0, lc0] = 1.0
    return Corridor(cid, pair, subtype, bbox, mask, weight, geom, rationale)


def build_termination_corridors(
    start_cid: int,
    strands: list[Strand],
    catalogue: np.ndarray,
    shape: tuple[int, int],
    admittance: np.ndarray | None = None,
    kinematics: dict[int, StrandKinematics] | None = None,
    max_terminations: int = 900,
) -> list[Corridor]:
    """Emit wing-crack / horse-tail splay corridors at free fault terminations."""
    H, W = shape
    deg_cat = np.zeros(shape, np.int8)
    skel = np.zeros(shape, bool)
    for s in strands:
        skel[s.ys, s.xs] = True
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            deg_cat += ndi.shift(skel.astype(np.int8), (-dy, -dx), order=0, mode="constant", cval=0)

    candidates = []
    for s in strands:
        if s.length_px < 6.0:
            continue
        kin = kinematics.get(s.sid, StrandKinematics(s.sid)) if kinematics else StrandKinematics(s.sid)
        eff_sense = kin.sense if kin.sense in ("RL", "LL") else (
            kin.secondary_sense if kin.secondary_sense in ("RL", "LL") else kin.sense
        )
        for end in (0, 1):
            tr, tc = s.tip0 if end == 0 else s.tip1
            if deg_cat[tr, tc] > 1:
                continue  # branch junction, not a free termination
            az = s.az0 if end == 0 else s.az1
            prio = (0 if eff_sense in ("RL", "LL") else 1, -dilation_tendency(az), -s.length_px)
            candidates.append((prio, s, end, kin, eff_sense, az))

    candidates.sort(key=lambda x: x[0])
    out: list[Corridor] = []
    for idx_c, (_, s, end, kin, eff_sense, az) in enumerate(candidates[:max_terminations]):
        tr, tc = s.tip0 if end == 0 else s.tip1
        oe, on = _outward_tip_dir(s, end)
        ray_len = float(np.clip(0.80 * s.length_px, 10.0, 36.0))
        angles = [0.0, 26.0] if eff_sense == "RL" else (
            [0.0, -26.0] if eff_sense == "LL" else [0.0, 18.0, -18.0]
        )
        pad = int(np.ceil(ray_len + 6.0))
        br0, br1 = max(0, tr - pad), min(H, tr + pad + 1)
        bc0, bc1 = max(0, tc - pad), min(W, tc + pad + 1)
        lh, lw = br1 - br0, bc1 - bc0
        admit_win = admittance[br0:br1, bc0:bc1] if admittance is not None else None
        mask = np.zeros((lh, lw), bool)
        weight = np.zeros((lh, lw), np.float32)
        p0 = (tr - br0, tc - bc0)
        best_target = p0
        for k_ang, da in enumerate(angles):
            rad = np.radians(da)
            # Clockwise rotation by da in compass space (east, north):
            re = oe * np.cos(rad) + on * np.sin(rad)
            rn = -oe * np.sin(rad) + on * np.cos(rad)
            L_use = ray_len if k_ang == 0 else 0.72 * ray_len
            # Search small angular arc near ray endpoint for highest local admittance peak
            p1 = (int(np.clip(round(p0[0] - L_use * rn), 0, lh - 1)),
                  int(np.clip(round(p0[1] + L_use * re), 0, lw - 1)))
            if k_ang == 0:
                best_target = p1
            rr, cc = _geodesic_trace(p0, p1, admit_win, 10.0)
            _paint_trace_graded(mask, weight, rr, cc, peak=0.94 if k_ang == 0 else 0.80, halo_px=2)

        virt_pair = TipPair(
            s.sid, s.sid, (int(tr), int(tc)),
            (int(br0 + best_target[0]), int(bc0 + best_target[1])),
            w_px=round(0.45 * ray_len, 2), along_px=round(ray_len, 2),
            dtheta=0.0, mean_az=float(az), diag_px=round(ray_len, 2),
            dilatational=True, comp_a=0, comp_b=0,
            overlap_px=0.0, separation_px=round(ray_len, 2),
            kinematic_regime="termination-splay",
            sense_summary=f"{eff_sense} tip wing-crack fan ({kin.fault_name or 'mapped strand'})",
            dip_summary=kin.dip_source,
        )
        rationale = dict(
            layers=[],
            signature=f"termination-splay: {eff_sense} tip propagation + dilatational wing-crack rays",
            source="GEMSDOE69 H69-E kinematic free-tip propagation; Qfaults slip/dip metadata",
            w_km=round(virt_pair.w_px / 10.0, 3),
            along_km=round(ray_len / 10.0, 3),
            overlap_km=0.0,
            separation_km=round(ray_len / 10.0, 3),
            dtheta_deg=0.0,
            mean_az_deg=round(float(az), 2),
            dilatational=True,
            kinematic_regime="termination-splay",
            sense_note=virt_pair.sense_summary,
            dip_note=kin.dip_source,
            geometry=dict(ray_len_km=round(ray_len / 10.0, 3), n_rays=len(angles)),
            strands=(s.sid, s.sid),
            tips=(virt_pair.tip_a, virt_pair.tip_b),
        )
        out.append(Corridor(start_cid + idx_c, virt_pair, "termination-splay",
                            (br0, br1, bc0, bc1), mask, weight,
                            dict(ray_len_px=ray_len, n_rays=len(angles)), rationale))
    return out


def _pair_key(p: TipPair) -> tuple:
    return (min(p.strand_a, p.strand_b), max(p.strand_a, p.strand_b),
            round(p.w_px, 1), round(p.along_px, 1))


def _priority(p: TipPair) -> tuple:
    order = {"pull-apart": 0, "relay-ramp": 1, "transfer-overlap": 2}.get(p.kinematic_regime, 2)
    return (order, abs(p.w_px - 28.0), p.w_px)


def build_corridors(
    catalogue: np.ndarray,
    strands: list[Strand],
    shape: tuple[int, int],
    max_corridors: int = 1600,
    w_min: float = W_MIN_PX,
    w_max: float = W_MAX_PX,
    admittance: np.ndarray | None = None,
    kinematics: dict[int, StrandKinematics] | None = None,
    include_terminations: bool = False,
    max_terminations: int = 900,
):
    """Build step-over corridors + free-tip termination splay corridors."""
    pairs = build_tip_pairs(strands, catalogue, w_min=w_min, w_max=w_max, kinematics=kinematics)
    seen, uniq = set(), []
    for p in sorted(pairs, key=_priority):
        k = _pair_key(p)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
        if len(uniq) >= max_corridors:
            break
    corridors = [corridor_from_pair(i, p, strands, shape, admittance=admittance)
                 for i, p in enumerate(uniq)]
    if include_terminations and strands:
        terms = build_termination_corridors(
            len(corridors), strands, catalogue, shape,
            admittance=admittance, kinematics=kinematics,
            max_terminations=max_terminations,
        )
        corridors.extend(terms)
    return corridors, uniq


def dilation_tendency(az: float) -> float:
    """Dilation tendency peaks for N-NE strike (~22.5 deg) under WNW extension (112.5 deg)."""
    return float(np.cos(np.radians(az - 22.5)) ** 2)


# --- Vector compatibility interface retained for tests/test_vector_corridors.py ---

@dataclass
class Line:
    kind: str
    a: np.ndarray
    b: np.ndarray
    W: float = 0.0
    setting: str = "relay"
    azimuth: float = 0.0
    score: float = 0.0
    terms: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([0.0, 1.0])


def _pair_ok(ta, tb) -> tuple[bool, str]:
    """Test geometric and kinematic admissibility of vector tip pair (ta, tb)."""
    if hasattr(ta, "dip_vec") and hasattr(tb, "dip_vec"):
        if ta.dip_vec is not None and tb.dip_vec is not None:
            if float(np.dot(ta.dip_vec, tb.dip_vec)) < 0:
                return False, "rejected_dip"

    pa = np.asarray(ta.pos, float)
    pb = np.asarray(tb.pos, float)
    d = pb - pa
    out_a = _unit(ta.out)
    right_a = np.array([out_a[1], -out_a[0]])
    cross_step = float(np.dot(d, right_a))
    along_step = float(np.dot(d, out_a))
    w_px = abs(cross_step)

    if w_px < 1.0 or w_px > 150.0:
        return False, "rejected_geometry"
    if along_step > 3.5 * w_px:
        return False, "rejected_geometry"

    sense_a = getattr(ta, "sense", "N")
    if sense_a == "RL" and cross_step < 0:
        return False, "rejected_step_sense"
    if sense_a == "LL" and cross_step > 0:
        return False, "rejected_step_sense"
    return True, "ok"


def generate(tips: list, polys: list, include_cut: bool = False) -> tuple[list[Line], dict]:
    """Generate vector corridor lines from free tips and polylines."""
    lines: list[Line] = []
    counts = {"relay_pairs": 0, "pull_apart": 0, "terminations": 0}

    if len(tips) >= 2:
        for i in range(len(tips)):
            for j in range(i + 1, len(tips)):
                ta, tb = tips[i], tips[j]
                if not include_cut and (getattr(ta, "cut", False) or getattr(tb, "cut", False)):
                    continue
                ok, _ = _pair_ok(ta, tb)
                if ok:
                    pa = np.asarray(ta.pos, float)
                    pb = np.asarray(tb.pos, float)
                    d = pb - pa
                    out_a = _unit(ta.out)
                    right_a = np.array([out_a[1], -out_a[0]])
                    w = abs(float(np.dot(d, right_a)))
                    along = float(np.dot(d, out_a))
                    is_overlap = along < 0
                    sense_a = getattr(ta, "sense", "N")
                    setting = "pullapart" if sense_a in ("RL", "LL") else "relay"
                    counts["pull_apart" if setting == "pullapart" else "relay_pairs"] += 1
                    meta = {"overlap": is_overlap, "W_km": w / 10.0,
                            "L_km": abs(along) / 10.0, "sense": sense_a}
                    lines.append(Line("relay_connector", pa, pb, W=w, setting=setting, meta=meta))
                    lines.append(Line("relay_breach", pa, pb, W=w, setting=setting, meta=meta))
                    lines.append(Line("relay_enechelon", pa, pb, W=w, setting=setting, meta=meta))

    for t in tips:
        if not include_cut and getattr(t, "cut", False):
            continue
        sense = getattr(t, "sense", "N")
        if sense in ("RL", "LL"):
            pos = np.asarray(t.pos, float)
            out = _unit(t.out)
            right = np.array([out[1], -out[0]])
            sgn = 1.0 if sense == "RL" else -1.0
            splay1 = pos + 15.0 * (out + 0.5 * sgn * right)
            splay2 = pos + 15.0 * (out + 1.0 * sgn * right)
            counts["terminations"] += 1
            lines.append(Line("termination_splay", pos, splay1, setting="transfer", meta={"sense": sense}))
            lines.append(Line("termination_splay", pos, splay2, setting="transfer", meta={"sense": sense}))

    return lines, counts
