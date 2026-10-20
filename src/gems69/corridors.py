"""Unified relay-ramp, synthetic-breach, pull-apart, splay & transfer corridor generator.

Combines:
  1. Vector polyline + dip-polarity + slip-sense corridor API (`Line`,
     `PolyIndex`, `dilation_tendency`, `_pair_ok`, `generate`,
     `generate_extended`, `rasterize_lines`, `score_lines`, `line_id_raster`,
     `corridor_fields`, `line_table`) driven by INGENIOUS Quaternary fault
     polylines, recorded dip directions, DEM hanging-wall dip polarity, and
     geodetic shear-rate context.
  2. Raster skeleton tip-graph & corridor-polygon API (`TipPair`, `Corridor`,
     `build_tip_pairs`, `corridor_from_pair`, `build_corridors`).

Physical geometry priors:
  * Giddens & Faulds (2025, SGP-TR-229): step-over widths W = 0.1-15 km
    (1-150 px at 100 m/px), along-strike separation |L| <= 3.5 W; oblique
    connectors + en echelon ramp strands; ~70% hard-linked above moderate T;
  * Walker Lane dextral / conjugate sinistral releasing step-overs -> pull-apart
    basins, cross-basin chords, N22.5E dilational strands, extensional horsetail
    splays, and strike-slip-to-normal displacement-transfer zones;
  * Asymmetric tip-to-flank synthetic breaches and normal fault-tip process zones
    (Peacock & Sanderson, 1994; Kim & Sanderson, 2005).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.draw import line as skline
from skimage.graph import route_through_array

from .tips import Strand, StrandKinematics, axial_deg, axial_diff, axial_mean
from .traces import Poly, Tip, rc_of, sample_polyline

# ---------------------------------------------------------------------------
# Constants shared across vector & raster corridor models
# ---------------------------------------------------------------------------
EXT_AZ = 292.5                         # WNW extension azimuth (deg)
W_MIN, W_MAX = 1.0, 150.0              # px (0.1-15 km)
ASPECT = 3.5
FACING_COS = float(np.cos(np.radians(35.0)))
STRAND_AZ = (EXT_AZ - 270.0) % 180.0   # 22.5 deg: perpendicular to WNW extension

W_MIN_PX = 1.0
W_MAX_PX = 150.0
ALONG_MAX_RATIO = 3.5
OVERLAP_RATIO = -1.0
MAX_DTHETA = 30.0
DILATATION_MAX_ALONG = 0.5
ECH_ANGLE = 25.0
CONNECTOR_HALF_W = lambda w: max(1, int(round(min(w / 6.0, 6.0))))
TIP_EXT_RATIO = 0.35
MIN_STRAND_PX = 4.0


# ===========================================================================
# PART 1: Vector polyline + dip-polarity + slip-sense corridor generator
# ===========================================================================

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
    return np.array([c * v[0] + s * v[1], -s * v[0] + c * v[1]])


class PolyIndex:
    def __init__(self, polys: list[Poly]):
        self.samples = [sample_polyline(q.verts, 0.5) for q in polys]
        self.polys = polys
        if self.samples:
            P = np.vstack(self.samples)
            self.owner = np.concatenate([np.full(len(s), i) for i, s in enumerate(self.samples)])
            self.pos_in_poly = np.concatenate([
                np.linspace(0.0, 1.0, len(s), dtype=np.float32) for s in self.samples
            ])
        else:
            P = np.zeros((0, 2), float)
            self.owner = np.zeros(0, int)
            self.pos_in_poly = np.zeros(0, np.float32)
        self.tree = cKDTree(P) if len(P) else None
        self.P = P

    def nearest_on(self, i: int, pt: np.ndarray) -> np.ndarray:
        s = self.samples[i]
        j = int(np.argmin(np.hypot(s[:, 0] - pt[0], s[:, 1] - pt[1])))
        return s[j]

    def nearest_on_with_frac(self, i: int, pt: np.ndarray) -> tuple[float, np.ndarray, float]:
        s = self.samples[i]
        dists = np.hypot(s[:, 0] - pt[0], s[:, 1] - pt[1])
        j = int(np.argmin(dists))
        frac = float(j) / max(len(s) - 1, 1)
        return float(dists[j]), s[j], frac


def dilation_tendency(az_deg: float) -> float:
    normal = (az_deg + 90.0) % 180.0
    beta = np.radians(((normal - EXT_AZ) + 90.0) % 180.0 - 90.0)
    return float(np.cos(beta) ** 2)


def _pair_ok(ti: Tip, tj: Tip) -> tuple[bool, str]:
    """Relay / pull-apart admissibility of a tip pair."""
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


def generate(
    tips: list[Tip],
    polys: list[Poly],
    *,
    include_cut: bool = False,
    k_partners: int = 1,
    include_flank_breaches: bool = False,
    include_normal_splays: bool = False,
    shearrate_grid: np.ndarray | None = None,
) -> tuple[list[Line], dict]:
    """Emit candidate fault corridors from the visible fault-tip graph.

    Default flags reproduce the strict single-partner vector contract tested by
    `tests/test_corridors.py`. Setting `k_partners > 1`, `include_flank_breaches=True`,
    and `include_normal_splays=True` enables multi-partner relays, asymmetric
    tip-to-flank synthetic breaches, normal/transtensional fault-tip propagation
    zones, and high-shear Walker Lane releasing pull-aparts.
    """
    idx = PolyIndex(polys)
    use = [t for t in tips if include_cut or not t.cut]
    lines: list[Line] = []
    counts = dict(
        relay_pairs=0,
        pullapart_pairs=0,
        flank_breaches=0,
        termination_tips=0,
        normal_tip_zones=0,
        transfer_links=0,
        rejected_dip=0,
        rejected_facing=0,
        rejected_geometry=0,
        rejected_step_sense=0,
        rejected_same_polyline=0,
        rejected_mixed_sense=0,
    )
    if not use:
        return lines, counts

    # Optional Walker Lane high-shear promotion for unlabelled ("unk") strands
    tip_shear = np.zeros(len(use), dtype=np.float32)
    shear_thr = np.inf
    if shearrate_grid is not None:
        H_sr, W_sr = shearrate_grid.shape
        rr, cc = rc_of(np.array([t.pos for t in use]))
        rr = np.clip(rr, 0, H_sr - 1)
        cc = np.clip(cc, 0, W_sr - 1)
        tip_shear = shearrate_grid[rr, cc].astype(np.float32)
        fin = tip_shear[np.isfinite(tip_shear)]
        if fin.size:
            shear_thr = float(np.quantile(fin, 0.78))

    pos = np.array([t.pos for t in use])
    tree = cKDTree(pos)
    query_r = max(W_MAX * 1.2, float(np.hypot(W_MAX, ASPECT * W_MAX)) if k_partners > 1 else W_MAX * 1.2)
    valid: list[tuple[float, int, int]] = []
    for i, j in sorted(tree.query_pairs(query_r)):
        ti, tj = use[i], use[j]
        ok, why = _pair_ok(ti, tj)
        if not ok:
            counts[why] += 1
            continue
        valid.append((float(np.hypot(*(tj.pos - ti.pos))), i, j))

    valid.sort(key=lambda t: t[0])
    counts["valid_pairs_before_partner_selection"] = len(valid)

    if k_partners <= 1:
        best_for: dict[int, tuple[float, int, int]] = {}
        for d, i, j in valid:
            for k in (i, j):
                if k not in best_for or d < best_for[k][0]:
                    best_for[k] = (d, i, j)
        chosen = sorted({(i, j) for _, i, j in best_for.values()})
    else:
        deg_count = [0] * len(use)
        chosen_list: list[tuple[int, int]] = []
        for d, i, j in valid:
            if deg_count[i] >= k_partners or deg_count[j] >= k_partners:
                continue
            deg_count[i] += 1
            deg_count[j] += 1
            chosen_list.append((i, j))
        chosen = sorted(set(chosen_list))

    for i, j in chosen:
        ti, tj = use[i], use[j]
        ss_i = ti.sense in ("RL", "LL")
        u = _unit(ti.out - tj.out)
        r = _right(u)
        v = tj.pos - ti.pos
        s, n = float(v @ u), float(v @ r)
        W = abs(n)
        inferred_rl = (
            not ss_i
            and ti.sense == "unk"
            and tj.sense == "unk"
            and n > 0
            and max(float(tip_shear[i]), float(tip_shear[j])) >= shear_thr
        )
        eff_sense = "RL" if inferred_rl else ti.sense
        meta = dict(
            overlap=s < 0,
            W_km=W / 10.0,
            L_km=s / 10.0,
            sense=eff_sense,
            dip_source="geod_shear_prior" if inferred_rl else f"{ti.dip_source}/{tj.dip_source}",
            records=(ti.record, tj.record),
        )
        if not (ss_i or inferred_rl):
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

    # Optional: asymmetric tip-to-flank synthetic breaches (W in 0.1..12 km)
    if include_flank_breaches and idx.tree is not None:
        w_flank_max = 120.0
        for t in use:
            near = idx.tree.query_ball_point(t.pos, w_flank_max)
            cand_polys = set(int(idx.owner[k]) for k in near)
            cand_polys.discard(t.poly)
            hits: list[tuple[float, int, np.ndarray]] = []
            for o in cand_polys:
                po = polys[o].part
                if po.record == t.record:
                    continue
                d_fl, foot, frac = idx.nearest_on_with_frac(o, t.pos)
                if not (0.08 <= frac <= 0.92):
                    continue
                if not (W_MIN <= d_fl <= w_flank_max):
                    continue
                v = foot - t.pos
                ahead = float(v @ t.out)
                if ahead < -0.5 * d_fl or ahead > 2.5 * d_fl:
                    continue
                # Local strike alignment with target strand
                s_arr = idx.samples[o]
                k0 = max(0, int(round(frac * (len(s_arr) - 1))) - 4)
                k1 = min(len(s_arr) - 1, k0 + 8)
                t_other = _unit(s_arr[k1] - s_arr[k0])
                if abs(float(t.out @ t_other)) < FACING_COS:
                    continue
                # Check dip compatibility for dip-slip strands
                if t.sense not in ("RL", "LL") and po.sense not in ("RL", "LL"):
                    if t.dip_vec is not None and po.dip_side != 0:
                        dv_o = po.dip_side * _right(t_other)
                        if float(t.dip_vec @ dv_o) <= 0:
                            continue
                hits.append((d_fl, o, foot))
            hits.sort(key=lambda item: item[0])
            for d_fl, o, foot in hits[:2]:
                counts["flank_breaches"] += 1
                meta_f = dict(
                    W_km=round(d_fl / 10.0, 3),
                    L_km=0.0,
                    sense=t.sense,
                    dip_source=f"{t.dip_source}/{polys[o].part.dip_source}",
                    records=(t.record, int(polys[o].part.record)),
                )
                lines.append(Line("flank_breach", "relay", t.pos, foot, (t.tid,),
                                  d_fl, 0.0, meta_f))
                # Synthetic diagonal ramp link shifted 0.6 W forward along target strand
                s_arr = idx.samples[o]
                mid_pt = s_arr[len(s_arr) // 2]
                diag_pt = 0.65 * foot + 0.35 * mid_pt
                if np.hypot(*(diag_pt - t.pos)) <= 1.8 * d_fl:
                    lines.append(Line("flank_synthetic", "relay", t.pos, diag_pt, (t.tid,),
                                      d_fl, 0.0, dict(meta_f)))

    # Strike-slip terminations -> horsetail splays + displacement-transfer links
    normal_polys = np.array([q.part.sense in ("N", "unk") for q in polys])
    for t in use:
        if t.sense in ("RL", "LL"):
            counts["termination_tips"] += 1
            side = 1.0 if t.sense == "RL" else -1.0
            length = float(np.clip(0.2 * t.part_len, 10.0, 40.0))
            for ang in (20.0, 40.0):
                d = _rot(t.out, side * ang)
                lines.append(Line("termination_splay", "transfer", t.pos, t.pos + length * d, (t.tid,),
                                  0.0, length, dict(sense=t.sense, angle=ang)))
            if idx.tree is not None:
                near = idx.tree.query_ball_point(t.pos, 80.0 if include_flank_breaches else 60.0)
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
        elif include_normal_splays:
            counts["normal_tip_zones"] += 1
            Lp = float(np.clip(0.35 * t.part_len, 6.0, 38.0))
            meta_tip = dict(sense=t.sense, dip_source=t.dip_source, records=(t.record,))
            lines.append(Line("tip_propagation", "relay", t.pos, t.pos + Lp * t.out, (t.tid,),
                              0.0, Lp, dict(meta_tip)))
            az_opt = np.radians(STRAND_AZ)
            u_opt = np.array([np.sin(az_opt), np.cos(az_opt)])
            if float(u_opt @ t.out) < 0:
                u_opt = -u_opt
            wing = _unit(0.55 * t.out + 0.45 * u_opt)
            lines.append(Line("tip_wing_splay", "relay", t.pos, t.pos + 0.72 * Lp * wing, (t.tid,),
                              0.0, 0.72 * Lp, dict(meta_tip)))

    return lines, counts


def rasterize_lines(
    lines: list[Line],
    footprint: np.ndarray,
    visible: np.ndarray,
    *,
    cost_surface_2x: np.ndarray | None = None,
    ridge_field: np.ndarray | None = None,
) -> None:
    """Rasterize candidate traces cleanly off the visible catalogue.

    When `cost_surface_2x` (downsampled 2x positive cost grid) and/or
    `ridge_field` (100 m multi-physics edge strength) are provided, links
    longer than 10 px follow the minimum-cost geodesic path across their cropped
    corridor box (`skimage.graph.route_through_array`) and snap within +-1 px to
    local multi-physics ridge maxima rather than blind straight chords.
    """
    H, W = footprint.shape
    H2, W2 = cost_surface_2x.shape if cost_surface_2x is not None else (0, 0)
    geodesic_kinds = {
        "relay_connector", "relay_breach", "flank_breach",
        "pullapart_chord", "pullapart_link", "transfer_link",
    }
    geodesic_budget = 2500
    geodesic_used = 0

    for ln in lines:
        chord_len = float(np.hypot(*(ln.b - ln.a)))
        use_geodesic = (
            cost_surface_2x is not None
            and geodesic_used < geodesic_budget
            and ln.kind in geodesic_kinds
            and 10.0 <= chord_len <= 140.0
        )
        if use_geodesic:
            geodesic_used += 1
            ends = np.vstack([ln.a, ln.b])
            r_end, c_end = rc_of(ends)
            r0_2, c0_2 = int(np.clip(r_end[0] // 2, 0, H2 - 1)), int(np.clip(c_end[0] // 2, 0, W2 - 1))
            r1_2, c1_2 = int(np.clip(r_end[1] // 2, 0, H2 - 1)), int(np.clip(c_end[1] // 2, 0, W2 - 1))
            pad = max(5, min(20, int(round(0.28 * chord_len / 2.0))))
            br0 = max(0, min(r0_2, r1_2) - pad)
            br1 = min(H2, max(r0_2, r1_2) + pad + 1)
            bc0 = max(0, min(c0_2, c1_2) - pad)
            bc1 = min(W2, max(c0_2, c1_2) + pad + 1)
            if (br1 - br0) >= 3 and (bc1 - bc0) >= 3 and (r0_2, c0_2) != (r1_2, c1_2):
                sub_cost = cost_surface_2x[br0:br1, bc0:bc1]
                path, _ = route_through_array(
                    sub_cost,
                    (r0_2 - br0, c0_2 - bc0),
                    (r1_2 - br0, c1_2 - bc0),
                    fully_connected=True,
                    geometric=True,
                )
                p_arr = np.asarray(path, dtype=np.float64)
                # Convert 2x grid cell centres back to 100 m (E, N) map-pixel coords
                pts_e = 2.0 * (p_arr[:, 1] + bc0) + 1.0
                pts_n = -(2.0 * (p_arr[:, 0] + br0) + 1.0)
                s = sample_polyline(np.column_stack([pts_e, pts_n]), 0.5)
            else:
                s = sample_polyline(np.vstack([ln.a, ln.b]), 0.5)
        else:
            s = sample_polyline(np.vstack([ln.a, ln.b]), 0.5)

        r, c = rc_of(s)
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        r, c = r[ok], c[ok]
        # Optional +-1 px local ridge snapping along normal direction
        if ridge_field is not None and r.size >= 4:
            best_v = ridge_field[r, c]
            best_r, best_c = r.copy(), c.copy()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr = np.clip(r + dr, 0, H - 1)
                nc = np.clip(c + dc, 0, W - 1)
                v = ridge_field[nr, nc]
                upd = (v > best_v) & footprint[nr, nc] & ~visible[nr, nc]
                best_v = np.where(upd, v, best_v)
                best_r = np.where(upd, nr, best_r)
                best_c = np.where(upd, nc, best_c)
            r, c = best_r, best_c

        keep = footprint[r, c] & ~visible[r, c]
        flat = np.unique(r[keep] * W + c[keep])
        ln.pix = flat


def score_lines(
    lines: list[Line],
    layers: dict[str, np.ndarray],
    weights: dict[str, float] | None = None,
) -> None:
    """Score every candidate trace on all pre-registered physical channels + dilation tendency."""
    for ln in lines:
        td = dilation_tendency(ln.azimuth)
        if ln.pix is None or ln.pix.size == 0:
            ln.terms = dict(td=td)
            ln.score = 0.0
            continue
        terms = {k: float(v.ravel()[ln.pix].mean()) for k, v in layers.items()}
        terms["td"] = td
        ln.terms = terms
        if weights is None:
            ln.score = float(np.mean(list(terms.values())))
        else:
            num = sum(weights.get(k, 0.0) * val for k, val in terms.items())
            den = max(sum(weights.get(k, 0.0) for k in terms), 1e-9)
            ln.score = float(num / den)


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
    """Per-pixel corridor score (max over traces within `band_px`), distance, and trace mask."""
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
        rows.append(dict(
            id=k,
            kind=ln.kind,
            setting=ln.setting,
            a_E=float(ln.a[0]),
            a_N=float(ln.a[1]),
            b_E=float(ln.b[0]),
            b_N=float(ln.b[1]),
            azimuth=ln.azimuth,
            W_km=round(ln.W / 10.0, 3),
            L_km=round(ln.L / 10.0, 3),
            n_pix=int(ln.pix.size if ln.pix is not None else 0),
            score=ln.score,
            **{f"t_{k2}": v for k2, v in ln.terms.items()},
            **{k2: (v if isinstance(v, (int, float, str, bool)) else str(v)) for k2, v in ln.meta.items()},
        ))
    return rows



# ===========================================================================
# PART 2: Raster skeleton tip-graph & kinematics-verified corridor generator
# ===========================================================================

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



def select_stratified(
    pairs: list[TipPair],
    max_corridors: int = 80,
    dilat_fraction: float = 0.7,
) -> list[TipPair]:
    """Stratified width-bin x regime selector across [1, 10, 30, 60, 150] px."""
    bins = [(1.0, 10.0), (10.0, 30.0), (30.0, 60.0), (60.0, 150.0001)]
    per_bin = max(1, max_corridors // len(bins))
    chosen: list[TipPair] = []
    seen: set[int] = set()
    for lo, hi in bins:
        in_bin = [i for i, p in enumerate(pairs) if lo <= p.w_px < hi]
        dil = [i for i in in_bin if pairs[i].dilatational]
        nondil = [i for i in in_bin if not pairs[i].dilatational]
        n_dil = min(len(dil), int(round(per_bin * dilat_fraction)))
        n_non = min(len(nondil), per_bin - n_dil)
        take = dil[:n_dil] + nondil[:n_non]
        if len(take) < per_bin:
            extra = [i for i in dil[n_dil:] + nondil[n_non:] if i not in take]
            take.extend(extra[: per_bin - len(take)])
        for idx in take:
            seen.add(idx)
            chosen.append(pairs[idx])
    if len(chosen) < max_corridors:
        for i, p in enumerate(pairs):
            if i not in seen:
                chosen.append(p)
                if len(chosen) >= max_corridors:
                    break
    return chosen[:max_corridors]
