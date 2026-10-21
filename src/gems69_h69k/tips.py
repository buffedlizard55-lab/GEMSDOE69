"""Vectorize a rasterized fault catalogue into strands (polylines) with tips.

A strand is a chain of skeleton pixels between two *nodes*, where a node is an
endpoint (8-neighbour degree 1) or a branch point (degree >= 3).  Each strand
carries its two tips and the local (terminal) strike at each tip, which is what
the tip-graph step-over pairing in :mod:`gems69.corridors` consumes.

Coordinate convention: pixels are ``(row, col)``; map deltas are
``(east, north) = (dcol, -drow)`` because row index grows south.  Azimuths are
in degrees, 0 = north, 90 = east, axial (mod 180).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

NEIGH8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
STEP_LEN = {(dy, dx): np.hypot(dy, dx) for dy, dx in NEIGH8}


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
        # fall back to the first actual step
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
    """Skeletonize a binary catalogue and trace strands between nodes.

    ``min_len_px`` drops stubby strands (map noise / rasterization spurs).
    Deterministic: no randomness anywhere in this function.
    """
    catalogue = np.asarray(catalogue, bool)
    if not catalogue.any():
        return []
    skel = skeletonize(catalogue)
    deg = degree_map(skel)
    ys, xs = np.nonzero(skel)
    n = len(ys)
    if n == 0:
        return []
    pid = np.full(skel.shape, -1, np.int64)          # pixel -> index
    pid[ys, xs] = np.arange(n)
    d = deg[ys, xs]

    # neighbour index lists (CSR-ish, built once)
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
        """Walk from node ``s`` along the specific edge ``s -> first``."""
        path = [s, first]
        p, cur = s, first
        while d[cur] == 2:
            nxt = [int(j) for j in neigh[cur] if j != p]
            if not nxt:
                break
            cur, p = nxt[0], cur
            path.append(cur)
        return path

    # start walks from every node (deg != 2); each undirected edge taken once
    node_idx = np.nonzero(d != 2)[0]
    for s in node_idx:
        for j in neigh[s]:
            key = (min(int(s), int(j)), max(int(s), int(j)))
            if key in seen_edges:
                continue
            path = walk_from(int(s), int(j))
            # mark every edge of this strand seen so the far node re-emits nothing
            for a, b in zip(path[:-1], path[1:]):
                seen_edges.add((min(int(a), int(b)), max(int(a), int(b))))
            _emit(path, ys, xs, d, strands, min_len_px)

    # closed loops have no nodes; trace any remaining unvisited skeleton pixels
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
