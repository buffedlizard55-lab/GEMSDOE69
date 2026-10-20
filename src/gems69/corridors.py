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

from .tips import Strand, axial_diff, axial_mean
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
# PART 2: Raster skeleton tip-graph & corridor-polygon API (`test_tipgraph`)
# ===========================================================================

@dataclass
class TipPair:
    strand_a: int
    strand_b: int
    tip_a: tuple[int, int]
    tip_b: tuple[int, int]
    w_px: float
    along_px: float
    dtheta: float
    mean_az: float
    diag_px: float
    dilatational: bool
    comp_a: int
    comp_b: int
    overlap_px: float = 0.0
    separation_px: float = 0.0


@dataclass
class Corridor:
    cid: int
    pair: TipPair
    subtype: str
    bbox: tuple[int, int, int, int]
    local_mask: np.ndarray
    local_weight: np.ndarray
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


def _tip_window_interval(
    strand: Strand,
    end: int,
    origin_rc: tuple[float, float],
    u_e: float,
    u_n: float,
    window_px: float,
) -> tuple[float, float]:
    ys = strand.ys.astype(float)
    xs = strand.xs.astype(float)
    if end == 1:
        ys, xs = ys[::-1], xs[::-1]
    steps = np.hypot(np.diff(ys), np.diff(xs))
    s = np.concatenate([[0.0], np.cumsum(steps)])
    keep = s <= window_px
    if keep.sum() < 2:
        keep[:2] = True
    de = xs[keep] - origin_rc[1]
    dn = -(ys[keep] - origin_rc[0])
    axis = de * u_e + dn * u_n
    return float(axis.min()), float(axis.max())


def build_tip_pairs(
    strands: list[Strand],
    catalogue: np.ndarray,
    w_min: float = W_MIN_PX,
    w_max: float = W_MAX_PX,
) -> list[TipPair]:
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
    tree = cKDTree(pts)
    query_r = float(np.hypot(w_max, ALONG_MAX_RATIO * w_max)) + 2.0
    raw_pairs: dict[tuple[int, int], TipPair] = {}
    for i, (r0, c0, sid_a, end_a) in enumerate(tips):
        for j in tree.query_ball_point((r0, c0), r=query_r):
            if j <= i:
                continue
            r1, c1, sid_b, end_b = tips[j]
            if sid_a == sid_b:
                continue
            sa, sb = smap[sid_a], smap[sid_b]
            if comp[r0, c0] == comp[r1, c1] and comp[r0, c0] > 0:
                continue
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
            ia = _tip_window_interval(sa, end_a, (r0, c0), u_e, u_n, window)
            ib = _tip_window_interval(sb, end_b, (r0, c0), u_e, u_n, window)
            overlap = max(0.0, min(ia[1], ib[1]) - max(ia[0], ib[0]))
            separation = max(0.0, max(ia[0], ib[0]) - min(ia[1], ib[1]))
            if separation > ALONG_MAX_RATIO * cross:
                continue
            if overlap > -OVERLAP_RATIO * cross:
                continue
            along_signed = de * u_e + dn * u_n
            if abs(along_signed) > ALONG_MAX_RATIO * cross:
                continue
            cand_tp = TipPair(
                sid_a, sid_b, (int(r0), int(c0)), (int(r1), int(c1)),
                float(cross), float(along_signed), float(dth), float(m_az),
                diag, overlap <= DILATATION_MAX_ALONG * cross,
                int(comp[r0, c0]), int(comp[r1, c1]),
                overlap_px=float(overlap), separation_px=float(separation),
            )
            key = (i, j)
            raw_pairs[key] = cand_tp
    return sorted(raw_pairs.values(), key=lambda p: p.diag_px)


def _pair_key(p: TipPair) -> tuple:
    return (min(p.strand_a, p.strand_b), max(p.strand_a, p.strand_b),
            round(p.w_px, 1), round(p.along_px, 1))


def corridor_from_pair(
    cid: int, pair: TipPair, strands: list[Strand], shape: tuple[int, int],
) -> Corridor:
    smap = {s.sid: s for s in strands}
    sa, sb = smap[pair.strand_a], smap[pair.strand_b]
    r0, c0 = pair.tip_a
    r1, c1 = pair.tip_b
    half = CONNECTOR_HALF_W(pair.w_px)
    span = int(np.ceil(max(pair.diag_px, pair.w_px) + 4.0 * half + 12))
    br0 = max(0, min(r0, r1) - span)
    br1 = min(shape[0], max(r0, r1) + span + 1)
    bc0 = max(0, min(c0, c1) - span)
    bc1 = min(shape[1], max(c0, c1) + span + 1)
    bbox = (br0, br1, bc0, bc1)
    lh, lw = br1 - br0, bc1 - bc0
    mask = np.zeros((lh, lw), bool)
    weight = np.zeros((lh, lw), np.float32)
    lr0, lc0 = r0 - br0, c0 - bc0
    lr1, lc1 = r1 - br0, c1 - bc0

    az_a = sa.az0 if pair.tip_a == sa.tip0 else sa.az1
    az_b = sb.az0 if pair.tip_b == sb.tip0 else sb.az1
    ext = TIP_EXT_RATIO * pair.w_px

    def ext_pt(r, c, az, sgn):
        e, n = np.sin(np.radians(az)), np.cos(np.radians(az))
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
    geom = dict(
        connector_half_w_px=half,
        connector_len_px=float(np.hypot(p1[0] - p0[0], p1[1] - p0[1])),
        n_echelon=0,
        rhomb_a_px=0.0,
        rhomb_b_px=0.0,
    )

    if pair.dilatational:
        le = float(np.clip(1.5 * pair.w_px, 4.0, 30.0))
        n_e = min(max(2, int(diag / max(0.6 * le, 1.0))) if diag > 0 else 2, 8)
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
        weight[rr0:rr1, cc0:cc1] = np.maximum(
            weight[rr0:rr1, cc0:cc1], np.where(ell, 0.9, 0.0).astype(np.float32)
        )
        geom["rhomb_a_px"], geom["rhomb_b_px"] = float(a_ax), float(b_ax)
        subtype = "pull-apart"
    else:
        subtype = "transfer-overlap"

    geom_km = {k: (round(v / 10.0, 3) if k.endswith("_px") and v else v) for k, v in geom.items()}
    rationale = dict(
        layers=[],
        signature="tip-graph step-over: oblique connector"
                  + (" + en echelon strands + pull-apart rhomb" if pair.dilatational
                     else " (contractile overlap, transfer corridor)"),
        source=("GEMSDOE69 tip-graph; step-over geometry priors per standing prompt "
                "(Giddens & Faulds 2025 SGP-TR-229, as cited in the prompt)"),
        w_km=round(pair.w_px / 10.0, 3),
        along_km=round(pair.along_px / 10.0, 3),
        overlap_km=round(pair.overlap_px / 10.0, 3),
        separation_km=round(pair.separation_px / 10.0, 3),
        dtheta_deg=round(pair.dtheta, 2),
        mean_az_deg=round(pair.mean_az, 2),
        dilatational=bool(pair.dilatational),
        sense_note=("Walker Lane dextral prior + INGENIOUS vector slip/dip polarity where available"),
        geometry=geom_km,
        strands=(pair.strand_a, pair.strand_b),
        tips=(pair.tip_a, pair.tip_b),
    )
    if not mask.any():
        mask[0, 0] = True
    return Corridor(cid, pair, subtype, bbox, mask, weight, geom, rationale)


def _priority(p: TipPair) -> tuple:
    return (0 if p.dilatational else 1, abs(p.w_px - 28.0), p.w_px)


def build_corridors(
    catalogue: np.ndarray,
    strands: list[Strand],
    shape: tuple[int, int],
    max_corridors: int = 1200,
    w_min: float = W_MIN_PX,
    w_max: float = W_MAX_PX,
):
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
