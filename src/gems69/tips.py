"""Vectorize a rasterized fault catalogue into strands (polylines) with tips,
plus leak-free spatial join to measured fault kinematics (slip sense & dip).

Coordinate convention: pixels are ``(row, col)``; map deltas are
``(east, north) = (dcol, -drow)`` because row index grows south. Azimuths are
in degrees, 0 = north, 90 = east, axial (mod 180).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

NEIGH8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
STEP_LEN = {(dy, dx): np.hypot(dy, dx) for dy, dx in NEIGH8}

X0, Y0, PX = 243350.0, 4508550.0, 100.0
DIP_AZ = {
    "N": 0.0, "NE": 45.0, "E": 90.0, "SE": 135.0,
    "S": 180.0, "SW": 225.0, "W": 270.0, "NW": 315.0,
}


@dataclass
class Strand:
    sid: int
    ys: np.ndarray          # int32 rows, tip0 -> tip1
    xs: np.ndarray          # int32 cols
    length_px: float        # polyline length (diagonal steps = sqrt(2))
    az0: float              # axial azimuth (deg) at tip0
    az1: float              # axial azimuth (deg) at tip1

    @property
    def tip0(self) -> tuple[int, int]:
        return int(self.ys[0]), int(self.xs[0])

    @property
    def tip1(self) -> tuple[int, int]:
        return int(self.ys[-1]), int(self.xs[-1])


@dataclass
class StrandKinematics:
    sid: int
    sense: str = "unk"                       # 'N' | 'RL' | 'LL' | 'unk'
    secondary_sense: str = ""                # 'RL' | 'LL' | 'N' | ''
    dip_vec: tuple[float, float] | None = None   # unit (east, north) toward hanging wall
    dip_source: str = "none"                 # 'recorded' | 'dem_inferred' | 'none'
    slip_mm_yr: float | None = None
    record_id: int | None = None
    fault_name: str = ""


def axial_deg(v_east: float, v_north: float) -> float:
    """Axial azimuth (0..180) of a vector given in (east, north)."""
    az = np.degrees(np.arctan2(v_east, v_north)) % 180.0
    return float(az)


def axial_diff(a: float, b: float) -> float:
    """Smallest angle (0..90) between two axial azimuths."""
    d = abs(float(a) - float(b)) % 180.0
    return min(d, 180.0 - d)


def axial_mean(azs, weights=None) -> float:
    """Mean of axial azimuths via direction doubling."""
    t = np.radians(2.0 * np.asarray(azs, float))
    w = np.ones_like(t) if weights is None else np.asarray(weights, float)
    m = np.average(np.exp(1j * t), weights=w)
    return float((np.degrees(np.angle(m)) / 2.0) % 180.0)


def _terminal_azimuth(ys: np.ndarray, xs: np.ndarray, tail: int = 12) -> float:
    """Axial azimuth of the first ``tail`` points of a (tip-first) polyline."""
    n = len(ys)
    if n < 2:
        return 0.0
    k = min(tail, n - 1)
    de = float(xs[k] - xs[0])
    dn = float(-(ys[k] - ys[0]))
    if de == 0.0 and dn == 0.0:
        de = float(xs[1] - xs[0])
        dn = float(-(ys[1] - ys[0]))
    return axial_deg(de, dn)


def degree_map(skel: np.ndarray) -> np.ndarray:
    """Number of 8-connected skeleton neighbours per skeleton pixel."""
    deg = np.zeros(skel.shape, np.int8)
    for dy, dx in NEIGH8:
        shifted = ndi.shift(skel.astype(np.int8), (-dy, -dx), order=0, mode="constant", cval=0)
        deg += shifted
    deg[~skel] = 0
    return deg


def vectorize(catalogue: np.ndarray, min_len_px: int = 3) -> list[Strand]:
    """Skeletonize a binary catalogue and trace strands between nodes."""
    catalogue = np.asarray(catalogue, bool)
    if not catalogue.any():
        return []
    skel = skeletonize(catalogue)
    deg = degree_map(skel)
    ys, xs = np.nonzero(skel)
    n = len(ys)
    if n == 0:
        return []
    pid = np.full(skel.shape, -1, np.int64)
    pid[ys, xs] = np.arange(n)
    d = deg[ys, xs]

    neigh: list[np.ndarray] = [[] for _ in range(n)]  # type: ignore[list-item]
    for dy, dx in NEIGH8:
        ny, nx = ys + dy, xs + dx
        ok = (ny >= 0) & (ny < skel.shape[0]) & (nx >= 0) & (nx < skel.shape[1])
        q = np.where(ok, pid[np.clip(ny, 0, skel.shape[0] - 1),
                             np.clip(nx, 0, skel.shape[1] - 1)], -1)
        for i, j in enumerate(q):
            if j >= 0:
                neigh[i].append(int(j))
    neigh = [np.asarray(v, np.int64) for v in neigh]

    strands: list[Strand] = []
    seen_edges: set[tuple[int, int]] = set()

    def walk_from(s: int, first: int) -> list[int]:
        path = [s, first]
        p, cur = s, first
        while d[cur] == 2:
            nxt = [int(j) for j in neigh[cur] if j != p]
            if not nxt:
                break
            cur, p = nxt[0], cur
            path.append(cur)
        return path

    node_idx = np.nonzero(d != 2)[0]
    for s in node_idx:
        for j in neigh[s]:
            key = (min(int(s), int(j)), max(int(s), int(j)))
            if key in seen_edges:
                continue
            path = walk_from(int(s), int(j))
            for a, b in zip(path[:-1], path[1:]):
                seen_edges.add((min(int(a), int(b)), max(int(a), int(b))))
            _emit(path, ys, xs, d, strands, min_len_px)

    visited = np.zeros(n, bool)
    for a, b in seen_edges:
        visited[a] = visited[b] = True
    for s in range(n):
        if visited[s]:
            continue
        path = [s]
        visited[s] = True
        p, cur = -1, s
        while True:
            nxt = [int(j) for j in neigh[cur] if j != p and not visited[j]]
            if not nxt:
                break
            cur, p = nxt[0], cur
            path.append(cur)
            visited[cur] = True
        if len(path) >= 2:
            _emit(path, ys, xs, d, strands, min_len_px)
    return strands


def _emit(path, ys, xs, d, strands: list[Strand], min_len_px: int) -> None:
    if len(path) < 2:
        return
    py = ys[np.asarray(path)]
    px = xs[np.asarray(path)]
    steps = np.hypot(np.diff(py), np.diff(px))
    length = float(steps.sum())
    if length < min_len_px:
        return
    sid = len(strands)
    strands.append(Strand(sid, py.astype(np.int32), px.astype(np.int32), length,
                          _terminal_azimuth(py, px),
                          _terminal_azimuth(py[::-1], px[::-1])))


def strand_mask(strand: Strand, shape: tuple[int, int]) -> np.ndarray:
    m = np.zeros(shape, bool)
    m[strand.ys, strand.xs] = True
    return m


_KIN_CACHE: dict | None = None


def _load_kinematic_catalog(data_dir: Path | None = None) -> dict | None:
    """Load segment midpoints & Qfaults metadata once; filter per call by visible mask."""
    global _KIN_CACHE
    if _KIN_CACHE is not None:
        return _KIN_CACHE
    root = Path(__file__).resolve().parents[2]
    d = Path(data_dir) if data_dir is not None else (root / ".cache" / "gems_data" / "external")
    seg_path = d / "trace_segments_utm11.csv"
    attr_path = d / "qfault_attributes.csv"
    dem_path = d / "geodawn_dem_a2_100m.tif"
    if not (seg_path.exists() and attr_path.exists()):
        return None
    attrs = list(csv.DictReader(open(attr_path, encoding="utf-8", errors="replace")))
    rows, cols, recs = [], [], []
    with open(seg_path, encoding="utf-8", errors="replace") as f:
        for s in csv.DictReader(f):
            mx = 0.5 * (float(s["x0"]) + float(s["x1"]))
            my = 0.5 * (float(s["y0"]) + float(s["y1"]))
            r = int(np.floor((Y0 - my) / PX))
            c = int(np.floor((mx - X0) / PX))
            rows.append(r)
            cols.append(c)
            recs.append(int(s["record_id"]))
    dem_arr = None
    if dem_path.exists():
        with rasterio.open(dem_path) as src:
            dem_arr = src.read(1).astype(np.float32)
            nod = src.nodata
        bad = ~np.isfinite(dem_arr)
        if nod is not None:
            bad |= dem_arr == nod
        dem_arr[bad] = np.nan
    _KIN_CACHE = {
        "rows": np.asarray(rows, np.int32),
        "cols": np.asarray(cols, np.int32),
        "recs": np.asarray(recs, np.int32),
        "attrs": attrs,
        "dem": dem_arr,
    }
    return _KIN_CACHE


def attach_catalogue_kinematics(
    strands: list[Strand],
    visible_catalogue: np.ndarray,
    data_dir: Path | None = None,
) -> dict[int, StrandKinematics]:
    """Attach measured Qfaults slip sense + dip polarity to visible strands ONLY.

    Leak-safety guarantee: ONLY segment midpoints falling strictly on pixels where
    ``visible_catalogue`` is True (dilated by 1 px within visible components only)
    are eligible to join, and DEM hanging-wall polarity is evaluated strictly at
    the visible strand's own coordinates. Withheld segments cannot enter.
    """
    cat_meta = _load_kinematic_catalog(data_dir)
    out: dict[int, StrandKinematics] = {}
    if cat_meta is None or not strands:
        return {s.sid: StrandKinematics(sid=s.sid) for s in strands}

    H, W = visible_catalogue.shape
    vis_band = ndi.binary_dilation(visible_catalogue, iterations=1)
    r_seg, c_seg, rec_seg = cat_meta["rows"], cat_meta["cols"], cat_meta["recs"]
    in_bounds = (r_seg >= 0) & (r_seg < H) & (c_seg >= 0) & (c_seg < W)
    keep = np.zeros(len(r_seg), bool)
    keep[in_bounds] = vis_band[r_seg[in_bounds], c_seg[in_bounds]]

    tree = None
    if keep.any():
        pts = np.column_stack([r_seg[keep], c_seg[keep]]).astype(np.float64)
        kept_recs = rec_seg[keep]
        tree = cKDTree(pts)

    attrs = cat_meta["attrs"]
    dem = cat_meta["dem"]

    for s in strands:
        kin = StrandKinematics(sid=s.sid)
        # 1. Join visible strand sample points to visible Qfaults segments
        if tree is not None:
            step = max(1, len(s.ys) // 16)
            qpts = np.column_stack([s.ys[::step], s.xs[::step]]).astype(np.float64)
            dists, idxs = tree.query(qpts, distance_upper_bound=2.5)
            good = np.isfinite(dists) & (idxs < len(kept_recs))
            if good.any():
                vals, counts = np.unique(kept_recs[idxs[good]], return_counts=True)
                rec_id = int(vals[int(np.argmax(counts))])
                kin.record_id = rec_id
                if 0 <= rec_id < len(attrs):
                    a = attrs[rec_id]
                    kin.fault_name = (a.get("NAME") or "").strip()
                    ss = (a.get("SLIPSENSE") or "").strip()
                    kin.sense = ss if ss in ("N", "RL", "LL") else ("N" if ss.lower() == "normal" else "unk")
                    sec = (a.get("SECONDARY") or "").strip()
                    kin.secondary_sense = sec if sec in ("N", "RL", "LL") else ""
                    try:
                        kin.slip_mm_yr = float(a["SLIPRTNUM"]) if a.get("SLIPRTNUM") else None
                    except ValueError:
                        kin.slip_mm_yr = None
                    dd = (a.get("DIPDIRECT") or "").strip()
                    if dd in DIP_AZ:
                        az_rad = np.radians(DIP_AZ[dd])
                        kin.dip_vec = (float(np.sin(az_rad)), float(np.cos(az_rad)))
                        kin.dip_source = "recorded"

        # 2. If normal/unknown dip vector not recorded, infer hanging-wall side from DEM
        if kin.dip_vec is None and dem is not None and len(s.ys) >= 4:
            step = max(1, len(s.ys) // 12)
            idx = np.arange(0, len(s.ys), step)
            if len(idx) >= 2:
                de = float(s.xs[-1] - s.xs[0])
                dn = float(-(s.ys[-1] - s.ys[0]))
                nrm = np.hypot(de, dn)
                if nrm > 1e-6:
                    # right normal to tip0->tip1 in (east, north)
                    re, rn = dn / nrm, -de / nrm
                    diffs = []
                    for off in (6.0, 12.0):
                        rl = np.clip(np.rint(s.ys[idx] + off * rn).astype(int), 0, H - 1)
                        cl = np.clip(np.rint(s.xs[idx] - off * re).astype(int), 0, W - 1)
                        rr = np.clip(np.rint(s.ys[idx] - off * rn).astype(int), 0, H - 1)
                        cr = np.clip(np.rint(s.xs[idx] + off * re).astype(int), 0, W - 1)
                        el, er = dem[rl, cl], dem[rr, cr]
                        ok = np.isfinite(el) & np.isfinite(er)
                        if ok.any():
                            diffs.append(float(np.mean(el[ok] - er[ok])))
                    if diffs and abs(float(np.mean(diffs))) >= 1.5:
                        sgn = 1.0 if float(np.mean(diffs)) > 0.0 else -1.0
                        kin.dip_vec = (sgn * re, sgn * rn)
                        kin.dip_source = "dem_inferred"
        out[s.sid] = kin
    return out
