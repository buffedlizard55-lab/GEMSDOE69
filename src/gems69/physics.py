"""Physics evidence layers for corridor scoring (windowed, memory-lean).

All band names below were read from the ``training_features.tif`` band
descriptions (see ``evidence/band_metadata.json``); no names are assumed.

Transforms (per standing prompt: multi-scale horizontal-gradient and tilt
evidence in gravity and magnetics, including magnetic lows, plus the lidar
scarp channel):

* HG_sigma(L)   = |grad gaussian_sigma(L)|, sigma in {1, 2, 4} px
* TILT_sigma(L) = arctan2(VD, HG),  VD = G_sigma - G_2sigma (upward-continuation
                  difference as a vertical-derivative proxy); the edge evidence
                  used is |sin(TILT)| (1 on a crisp step, 0 on flat)
* provided edges: iso_grav_anom_hg (18), iso_grav_anom_vg (11), tmi_hg (3),
                  tmi_vg (9), tc (6), geod_2ndinv (4)
* magnetic lows: -tmi, -rtp (reduction-to-pole), standardized
* lidar scarp channel: max(ex_max, step_max, downface_max) of the
                  ``lidar_scarp_features_u8.tif`` composite

Robust standardization uses footprint median/MAD (subsampled), computed once
per transform by full-grid passes that never hold more than one band and its
Gaussian ladder in memory at a time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / ".cache" / "gems_data" / "training_features.tif"
LIDAR_PATH = ROOT / ".cache" / "gems_data" / "external" / "lidar_scarp_features_u8.tif"
RAD_PATH = ROOT / ".cache" / "gems_data" / "external" / "geodawn_rad_u8.tif"
STATS_CACHE = ROOT / ".cache" / "gems_data" / "layer_stats.json"

# band index (1-based) read from file descriptions on 2026-10-12
BAND = {
    "mag_anom": 1, "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4, "iso_grav_slope": 5,
    "tc": 6, "geod_shear": 7, "geod_dilat": 8, "tmi_vg": 9, "deq": 10,
    "iso_grav_vg": 11, "det_elev": 12, "iso_grav": 13, "tmi": 14,
    "basement_depth": 15, "ieq": 16, "cond_surf": 17, "iso_grav_hg": 18,
    "det_elev_slope": 19,
}
LIDAR_BANDS = {"ex_max": 1, "step_max": 3, "downface_max": 6, "valid": 12}

SIGMAS = (1.0, 2.0, 4.0)
MAD_SCALE = 1.4826
STATS_SUBSAMPLE = 300_000
CLIP_Z = 8.0


@dataclass
class LayerStats:
    median: float
    mad: float

    def z(self, x):
        return np.clip((x - self.median) / max(self.mad, 1e-9), -CLIP_Z, CLIP_Z)


def _band_window(path: Path, band: int, bbox: tuple[int, int, int, int] | None):
    """Read one band, optionally cropped; sentinel -> NaN. bbox=(r0,r1,c0,c1)."""
    with rasterio.open(path) as src:
        if bbox is None:
            a = src.read(band).astype(np.float32)
        else:
            r0, r1, c0, c1 = bbox
            w = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
            a = src.read(band, window=w, boundless=False).astype(np.float32)
    a[a < -1e38] = np.nan
    return a


def _rad_depletion_window(bbox: tuple[int, int, int, int] | None):
    """Radiometric depletion raw field: -(K + Th)/2 from geodawn_rad_u8.tif.

    Bands read by name-verified index (1=K, 2=Th, 3=U, 4=TC; uint8,
    nodata 0 — verified 2026-10-20: outside-footprint cells are all 0,
    inside-footprint zeros are a 0.025% survey-hole mask shared by all
    bands, so 0 is nodata, not a depletion extreme).  Source pin:
    registry/data_manifest_gemsdoe32.json ``ext_geodawn_rad_u8``
    (sha256 c22420f7…; USGS GeoDAWN DOI 10.5066/P93LGLVQ per manifest).
    Robust-z standardization is applied by the caller like every layer.
    """
    with rasterio.open(RAD_PATH) as src:
        if bbox is None:
            k = src.read(1).astype(np.float32)
            th = src.read(2).astype(np.float32)
        else:
            r0, r1, c0, c1 = bbox
            w = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
            k = src.read(1, window=w).astype(np.float32)
            th = src.read(2, window=w).astype(np.float32)
    out = -(k + th) / 2.0
    out[(k == 0) | (th == 0)] = np.nan
    return out


def _lidar_scarp_window(bbox: tuple[int, int, int, int] | None):
    with rasterio.open(LIDAR_PATH) as src:
        if bbox is None:
            ex = src.read(LIDAR_BANDS["ex_max"]).astype(np.float32)
            st = src.read(LIDAR_BANDS["step_max"]).astype(np.float32)
            df = src.read(LIDAR_BANDS["downface_max"]).astype(np.float32)
            valid = src.read(LIDAR_BANDS["valid"]) > 0
        else:
            r0, r1, c0, c1 = bbox
            w = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
            ex = src.read(LIDAR_BANDS["ex_max"], window=w).astype(np.float32)
            st = src.read(LIDAR_BANDS["step_max"], window=w).astype(np.float32)
            df = src.read(LIDAR_BANDS["downface_max"], window=w).astype(np.float32)
            valid = src.read(LIDAR_BANDS["valid"], window=w) > 0
    s = np.maximum(np.maximum(ex, st), df)
    s[~valid] = np.nan
    return s


def hg(field: np.ndarray, sigma: float) -> np.ndarray:
    g = ndi.gaussian_filter(field, sigma)
    gy, gx = np.gradient(g)
    return np.hypot(gy, gx)


def tilt_edge(field: np.ndarray, sigma: float) -> np.ndarray:
    """|sin(tilt)| edge evidence: 1 on a crisp contact step, 0 on flat."""
    g1 = ndi.gaussian_filter(field, sigma)
    g2 = ndi.gaussian_filter(field, 2.0 * sigma)
    vd = g1 - g2
    gy, gx = np.gradient(g1)
    h = np.hypot(gy, gx)
    tilt = np.arctan2(vd, h + 1e-12)
    return np.abs(np.sin(tilt))


TRANSFORM_SPECS = []   # (name, kind, source_band_or_key, sigma)
for s in SIGMAS:
    TRANSFORM_SPECS.append((f"grav_hg_s{s:g}", "hg", "iso_grav", s))
    TRANSFORM_SPECS.append((f"mag_hg_s{s:g}", "hg", "tmi", s))
TRANSFORM_SPECS += [
    ("grav_tilt_s2", "tilt", "iso_grav", 2.0),
    ("mag_tilt_s2", "tilt", "tmi", 2.0),
    ("grav_hg_prov", "raw", "iso_grav_hg", 0.0),
    ("grav_vg_prov", "raw", "iso_grav_vg", 0.0),
    ("geod_2ndinv", "raw", "geod_2ndinv", 0.0),
    ("mag_hg_prov", "raw", "tmi_hg", 0.0),
    ("mag_vg_prov", "raw", "tmi_vg", 0.0),
    ("tc_prov", "raw", "tc", 0.0),
    ("mag_low_tmi", "negraw", "tmi", 0.0),
    ("mag_low_rtp", "negraw", "rtp", 0.0),
    ("lidar_scarp", "lidar", None, 0.0),
    # H69-F (preregistered 2026-10-20): subsurface straight-step evidence.
    # Same HG/tilt operators as gravity/magnetics, applied to the
    # conductivity surface (band 17) and basement depth (band 15).
    ("cond_hg_s2", "hg", "cond_surf", 2.0),
    ("cond_tilt_s2", "tilt", "cond_surf", 2.0),
    ("base_hg_s2", "hg", "basement_depth", 2.0),
    ("base_tilt_s2", "tilt", "basement_depth", 2.0),
    # H69-G sensitivity (preregistered 2026-10-20): radiometric depletion.
    ("rad_depl", "rad", None, 0.0),
]
TRANSFORM_NAMES = [t[0] for t in TRANSFORM_SPECS]


def compute_transform(name: str, bbox=None) -> np.ndarray:
    kind = dict((t[0], t[1]) for t in TRANSFORM_SPECS)[name]
    src = dict((t[0], t[2]) for t in TRANSFORM_SPECS)[name]
    sigma = dict((t[0], t[3]) for t in TRANSFORM_SPECS)[name]
    if kind == "lidar":
        return _lidar_scarp_window(bbox)
    if kind == "rad":
        return _rad_depletion_window(bbox)
    f = _band_window(FEATURES_PATH, BAND[src], bbox)
    if kind == "hg":
        return hg(f, sigma)
    if kind == "tilt":
        return tilt_edge(f, sigma)
    if kind == "raw":
        return f
    if kind == "negraw":
        return -f
    raise KeyError(name)


def build_layer_stats(footprint: np.ndarray, seed: int = 69) -> dict[str, LayerStats]:
    """One full-grid pass per transform; subsampled robust stats. Cached."""
    if STATS_CACHE.exists():
        raw = json.loads(STATS_CACHE.read_text())
        return {k: LayerStats(v["median"], v["mad"]) for k, v in raw.items()}
    rng = np.random.default_rng(seed)
    fy, fx = np.nonzero(footprint)
    sel = rng.choice(len(fy), size=min(STATS_SUBSAMPLE, len(fy)), replace=False)
    sy, sx = fy[sel], fx[sel]
    stats: dict[str, LayerStats] = {}
    for name in TRANSFORM_NAMES:
        t = compute_transform(name)
        v = t[sy, sx]
        v = v[np.isfinite(v)]
        if v.size < 1000:
            stats[name] = LayerStats(0.0, 1.0)
            continue
        med = float(np.median(v))
        mad = float(np.median(np.abs(v - med))) * MAD_SCALE
        stats[name] = LayerStats(med, mad if mad > 0 else 1.0)
        del t
    STATS_CACHE.write_text(json.dumps({k: {"median": v.median, "mad": v.mad}
                                       for k, v in stats.items()}, indent=1))
    return stats


def build_z_stack(footprint: np.ndarray, stats: dict[str, LayerStats],
                  names: list[str] | None = None, use_cache: bool = True) -> dict:
    """Precompute robust-z layers for the full grid once (float16, NaN where nodata).

    Corridor scoring then becomes a pure lookup, which is what keeps the lane
    inside the 2-core / 3 GB budget.  Cached under .cache/gems_data/z_stack.npz.
    """
    names = names or TRANSFORM_NAMES
    cache = STATS_CACHE.parent / "z_stack.npz"
    if use_cache and cache.exists():
        with np.load(cache) as z:
            if all(n in z.files for n in names):
                return {n: z[n] for n in names}
    out = {}
    for n in names:
        t = compute_transform(n)
        zz = stats[n].z(t)
        zz = np.where(np.isfinite(zz), zz, np.nan).astype(np.float16)
        out[n] = zz
        del t, zz
    if use_cache:
        np.savez_compressed(cache, **out)
    return out


def corridor_evidence_from_z(zstack: dict, corridor) -> dict[str, float]:
    """Robust-z mean of every precomputed layer inside the corridor (lookup)."""
    if corridor.npix == 0:
        return {n: 0.0 for n in zstack}
    br0, br1, bc0, bc1 = corridor.bbox
    m = corridor.local_mask
    out = {}
    for n, z in zstack.items():
        v = z[br0:br1, bc0:bc1][m]
        v = v[np.isfinite(v)]
        out[n] = float(v.mean()) if v.size else 0.0
    return out


def corridor_evidence(corridor, stats: dict[str, LayerStats], pad: int = 4,
                      shape: tuple[int, int] | None = None) -> dict[str, float]:
    """Robust-z mean of every transform inside a Corridor (windowed reads)."""
    if corridor.npix == 0:
        return {n: 0.0 for n in TRANSFORM_NAMES}
    br0, br1, bc0, bc1 = corridor.bbox
    H, W = shape if shape is not None else (br1, bc1)
    r0, r1 = max(0, br0 - pad), min(H, br1 + pad)
    c0, c1 = max(0, bc0 - pad), min(W, bc1 + pad)
    m = np.zeros((r1 - r0, c1 - c0), bool)
    m[br0 - r0:br1 - r0, bc0 - c0:bc1 - c0] = corridor.local_mask
    out: dict[str, float] = {}
    for name in TRANSFORM_NAMES:
        t = compute_transform(name, bbox=(r0, r1, c0, c1))
        z = stats[name].z(t)[m]
        z = z[np.isfinite(z)]
        out[name] = float(z.mean()) if z.size else 0.0
    return out
