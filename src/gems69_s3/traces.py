"""Catalogue polylines, dip polarity and the fault-tip graph.

Source: the INGENIOUS Quaternary-fault export restored as
``external/trace_segments_utm11.csv`` (84,331 straight segments, UTM 11N
metres, grouped by ``record_id``) joined to ``external/qfault_attributes.csv``
(row index == ``record_id``; verified 1,126/1,126 on slip rate *and* slip
sense -- see ``evidence/e0_data_receipt.json``).

Coordinates
-----------
Everything geometric is done in *map pixel units*: ``E = col`` and
``N = -row`` with ``col = (x - 243350) / 100``, ``row = (4508550 - y) / 100``,
so azimuths are ordinary compass azimuths and "right of a direction" is the
usual map sense.  Rasterisation converts back to ``(row, col)``.

Dip polarity
------------
460 of the 1,126 in-footprint records carry a usable ``DIPDIRECT``.  For the
rest the hanging wall is inferred as the *topographically lower* side
(normal faults put the basin on the hanging wall): mean DEM elevation 600 m and
1.2 km either side of the trace, averaged along the part.  The inference is
validated against the recorded dips (agreement reported in the E1 receipt) and
is never derived from hidden faults.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from .data import DATA

X0, Y0, PX = 243350.0, 4508550.0, 100.0
DIP_AZ = {"N": 0.0, "NE": 45.0, "E": 90.0, "SE": 135.0, "S": 180.0, "SW": 225.0,
          "W": 270.0, "NW": 315.0}


@dataclass
class Part:
    pid: int
    record: int
    verts: np.ndarray                 # (n, 2) map pixel coords (E, N)
    sense: str                        # 'N', 'RL', 'LL' or 'unk'
    dip_az_recorded: float | None
    name: str
    slip: float | None
    dip_side: int = 0                 # +1 hanging wall right of vertex order, -1 left, 0 unknown
    dip_source: str = "none"          # 'recorded' | 'inferred' | 'none'
    inferred_side: int = 0
    inferred_strength: float = 0.0
    length: float = 0.0


@dataclass
class Poly:
    """A visible polyline (a part, or a piece of one after a holdout cut)."""
    part: Part
    verts: np.ndarray
    cut_start: bool = False           # start created by removing withheld/collar pixels
    cut_end: bool = False


@dataclass
class Tip:
    tid: int
    poly: int                          # index into the poly list
    pos: np.ndarray                    # (E, N)
    out: np.ndarray                    # unit outward direction at the tip
    sense: str
    dip_vec: np.ndarray | None         # horizontal unit vector toward the hanging wall
    dip_source: str
    part_len: float
    cut: bool
    record: int
    extra: dict = field(default_factory=dict)


def to_pix(x, y):
    return (np.asarray(x, float) - X0) / PX, -((Y0 - np.asarray(y, float)) / PX)


def rc_of(EN: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(E, N) map pixel coords -> integer (row, col)."""
    return np.floor(-EN[:, 1]).astype(np.int64), np.floor(EN[:, 0]).astype(np.int64)


def sample_polyline(verts: np.ndarray, step: float = 0.25) -> np.ndarray:
    if len(verts) == 1:
        return verts.copy()
    out = []
    for a, b in zip(verts[:-1], verts[1:]):
        L = float(np.hypot(*(b - a)))
        n = max(int(np.ceil(L / step)), 1)
        t = np.arange(n, dtype=float) / n
        out.append(a[None, :] + t[:, None] * (b - a)[None, :])
    out.append(verts[-1:])
    return np.vstack(out)


def poly_length(verts: np.ndarray) -> float:
    return float(np.hypot(*np.diff(verts, axis=0).T).sum()) if len(verts) > 1 else 0.0


def load_parts() -> list[Part]:
    attrs = list(csv.DictReader(open(DATA / "external" / "qfault_attributes.csv", newline="",
                                     encoding="utf-8", errors="replace")))
    rows = list(csv.DictReader(open(DATA / "external" / "trace_segments_utm11.csv")))
    by_rec: dict[int, list[dict]] = {}
    for r in rows:
        by_rec.setdefault(int(r["record_id"]), []).append(r)
    parts: list[Part] = []
    for rec, segs in by_rec.items():
        a = attrs[rec]
        sense = segs[0]["sense"] or "unk"
        if sense not in ("N", "RL", "LL"):
            sense = "unk"
        dd = (a.get("DIPDIRECT") or "").strip()
        dip_az = DIP_AZ.get(dd)
        try:
            slip = float(a["SLIPRTNUM"]) if a.get("SLIPRTNUM") else None
        except ValueError:
            slip = None
        cur: list[np.ndarray] = []
        last = None
        chains: list[list[np.ndarray]] = []
        for s in segs:
            e0, n0 = to_pix(float(s["x0"]), float(s["y0"]))
            e1, n1 = to_pix(float(s["x1"]), float(s["y1"]))
            p0, p1 = np.array([e0, n0]), np.array([e1, n1])
            if last is None or np.hypot(*(p0 - last)) > 0.01:     # > 1 m gap -> new part
                if cur:
                    chains.append(cur)
                cur = [p0]
            cur.append(p1)
            last = p1
        if cur:
            chains.append(cur)
        for ch in chains:
            v = np.array(ch)
            if len(v) < 2 or poly_length(v) < 0.5:
                continue
            parts.append(Part(pid=len(parts), record=rec, verts=v, sense=sense,
                              dip_az_recorded=dip_az, name=a.get("NAME", ""), slip=slip,
                              length=poly_length(v)))
    return parts


def rasterize_parts(parts, shape, step: float = 0.25) -> np.ndarray:
    out = np.zeros(shape, bool)
    for p in parts:
        r, c = rc_of(sample_polyline(p.verts if isinstance(p, Part) else p, step))
        ok = (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])
        out[r[ok], c[ok]] = True
    return out


def _right(t: np.ndarray) -> np.ndarray:
    return np.array([t[1], -t[0]])


def _local_dirs(v: np.ndarray) -> np.ndarray:
    d = np.zeros_like(v)
    d[1:-1] = v[2:] - v[:-2]
    d[0] = v[1] - v[0]
    d[-1] = v[-1] - v[-2]
    n = np.hypot(d[:, 0], d[:, 1])[:, None]
    return d / np.maximum(n, 1e-9)


def assign_dips(parts: list[Part], elev: np.ndarray, offsets=(6.0, 12.0)) -> dict:
    """Recorded dip side where available, topographic inference everywhere; validate."""
    H, W = elev.shape
    agree = n_cmp = 0
    for p in parts:
        v = sample_polyline(p.verts, 2.0)
        d = _local_dirs(v)
        rn = np.stack([d[:, 1], -d[:, 0]], axis=1)          # right normals
        diffs = []
        for o in offsets:
            L = v - o * rn
            R = v + o * rn
            rl, cl = rc_of(L)
            rr, cr = rc_of(R)
            ok = (rl >= 0) & (rl < H) & (cl >= 0) & (cl < W) & (rr >= 0) & (rr < H) & (cr >= 0) & (cr < W)
            if not ok.any():
                continue
            el = elev[rl[ok], cl[ok]]
            er = elev[rr[ok], cr[ok]]
            good = np.isfinite(el) & np.isfinite(er)
            if good.any():
                diffs.append(float(np.mean(el[good] - er[good])))
        if diffs:
            m = float(np.mean(diffs))
            p.inferred_side = 1 if m > 0 else -1           # left higher -> hanging wall right
            p.inferred_strength = abs(m)
        if p.dip_az_recorded is not None:
            az = np.radians(p.dip_az_recorded)
            dv = np.array([np.sin(az), np.cos(az)])
            proj = float(np.mean(rn @ dv))
            if abs(proj) >= 0.3:
                p.dip_side = 1 if proj > 0 else -1
                p.dip_source = "recorded"
                if p.inferred_side != 0:
                    n_cmp += 1
                    agree += int(p.inferred_side == p.dip_side)
        if p.dip_source == "none" and p.inferred_side != 0:
            p.dip_side = p.inferred_side
            p.dip_source = "inferred"
    n_rec = sum(p.dip_source == "recorded" for p in parts)
    n_inf = sum(p.dip_source == "inferred" for p in parts)
    return dict(parts=len(parts), recorded=n_rec, inferred=n_inf,
                none=len(parts) - n_rec - n_inf,
                inference_vs_recorded_agreement=(agree / n_cmp) if n_cmp else None,
                inference_compared=n_cmp,
                rule="hanging wall = lower mean DEM at 600 m and 1.2 km offsets (normal-fault polarity)")


def visible_polys(parts: list[Part], removed: np.ndarray | None) -> list[Poly]:
    """Split parts where their sampled pixels hit ``removed`` (withheld + collar)."""
    polys: list[Poly] = []
    H, W = (removed.shape if removed is not None else (None, None))
    for p in parts:
        if removed is None:
            polys.append(Poly(p, p.verts.copy()))
            continue
        s = sample_polyline(p.verts, 0.25)
        r, c = rc_of(s)
        inside = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        hit = np.zeros(len(s), bool)
        hit[inside] = removed[r[inside], c[inside]]
        if not hit.any():
            polys.append(Poly(p, p.verts.copy()))
            continue
        keep = ~hit
        # runs of kept samples become visible polylines (sampled vertices, 0.25 px)
        idx = np.flatnonzero(np.diff(np.concatenate([[0], keep.astype(np.int8), [0]])))
        for a, b in zip(idx[::2], idx[1::2]):
            seg = s[a:b]
            if len(seg) < 3 or poly_length(seg) < 1.0:
                continue
            polys.append(Poly(p, seg[::4] if len(seg) > 8 else seg,
                              cut_start=a > 0, cut_end=b < len(s)))
    return polys


def _outward(verts: np.ndarray, at_end: bool, back: float = 10.0) -> np.ndarray:
    v = verts if at_end else verts[::-1]
    tip = v[-1]
    acc = 0.0
    j = len(v) - 1
    while j > 0 and acc < back:
        acc += float(np.hypot(*(v[j] - v[j - 1])))
        j -= 1
    d = tip - v[j]
    n = float(np.hypot(*d))
    return d / n if n > 0 else np.array([1.0, 0.0])


def find_tips(polys: list[Poly], footprint: np.ndarray, junction_px: float = 2.5,
              edge_px: float = 3.0, min_len_px: float = 3.0) -> tuple[list[Tip], dict]:
    """Free fault tips: polyline ends with no other polyline within ``junction_px``.

    250 m is the junction tolerance: catalogue linework is compiled at
    1:24k-1:250k, so ends closer than ~2.5 px to another trace are treated as
    connected rather than as a resolvable step-over.  Polylines shorter than
    300 m give no reliable outward direction and contribute no tips.
    """
    pts, owner = [], []
    for i, q in enumerate(polys):
        s = sample_polyline(q.verts, 0.5)
        pts.append(s)
        owner.append(np.full(len(s), i))
    P = np.vstack(pts)
    O = np.concatenate(owner)
    tree = cKDTree(P)
    edge = ndi.distance_transform_edt(footprint)
    H, W = footprint.shape
    tips: list[Tip] = []
    n_junction = n_edge = n_cut = n_short = 0
    for i, q in enumerate(polys):
        if poly_length(q.verts) < min_len_px:
            n_short += 2
            continue
        for at_end in (False, True):
            pos = q.verts[-1] if at_end else q.verts[0]
            cut = q.cut_end if at_end else q.cut_start
            near = tree.query_ball_point(pos, junction_px)
            if any(O[j] != i for j in near):
                n_junction += 1
                continue
            r, c = int(np.floor(-pos[1])), int(np.floor(pos[0]))
            if not (0 <= r < H and 0 <= c < W) or edge[r, c] <= edge_px:
                n_edge += 1
                continue
            out = _outward(q.verts, at_end)
            dip_vec = None
            if q.part.dip_side != 0:
                # local vertex-order direction at this end, then right normal * side
                d = out if at_end else -out
                dip_vec = q.part.dip_side * _right(d)
            n_cut += int(cut)
            tips.append(Tip(tid=len(tips), poly=i, pos=pos.copy(), out=out, sense=q.part.sense,
                            dip_vec=dip_vec, dip_source=q.part.dip_source,
                            part_len=q.part.length, cut=cut, record=q.part.record))
    return tips, dict(free_tips=len(tips), junction_ends=n_junction, edge_ends=n_edge,
                      short_polyline_ends=n_short, cut_tips=n_cut, polylines=len(polys),
                      junction_px=junction_px, min_len_px=min_len_px)
