"""Radiometric K/Th evidence for H2 (alteration halo) - simple robust-z layers.

Uses ext_geodawn_rad_u8.tif (K, Th, TC) and ext_geodawn_extensions_u8.tif (ThK, UK, UTh)
All are uint8 quantized 1st-99th percentile; we convert to float32 and compute robust stats
via median/MAD on footprint subsample, then z-score.

New transforms (added to z_stack for corridor scoring):
  rad_K_neg      = -K (K depletion = alteration leached K)
  rad_ThK_pos    = Th/K (Th enrichment relative to K)
  rad_TC_neg     = -TC (optional, total count depletion)
  rad_Th_pos     = +Th (Th residual)
These are standardized like physics layers: median/MAD -> z, clip to 8.

Provenance: USGS GeoDAWN airborne magnetic & radiometric surveys (DOI 10.5066/P93LGLVQ)
Pinned mirror: registry/data_manifest_gemsdoe32.json ext_geodawn_rad_u8 sha256 c22420f7...
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "gems_data"
RAD_PATH = CACHE / "external" / "geodawn_rad_u8.tif"
EXT_PATH = CACHE / "external" / "geodawn_extensions_u8.tif"
STATS_CACHE = CACHE / "rad_stats.json"
MAD_SCALE = 1.4826
CLIP_Z = 8.0
SUBSAMPLE = 300_000

BAND_RAD = {"K": 1, "Th": 2, "U": 3, "TC": 4}
BAND_EXT = {"ThK": 1, "UK": 2, "UTh": 3, "TMI_up150": 4}

TRANSFORMS = {
    "rad_K_neg": ("rad", "K", -1.0),
    "rad_ThK_pos": ("ext", "ThK", +1.0),
    "rad_TC_neg": ("rad", "TC", -1.0),
    "rad_Th_pos": ("rad", "Th", +1.0),
}
NAMES = list(TRANSFORMS.keys())


def _read_band(path: Path, band: int, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(band).astype(np.float32)
    # uint8 quantized 0-255, nodata handling: outside footprint -> nan
    bad = ~footprint | ~np.isfinite(a)
    a[bad] = np.nan
    return a


def compute_transform(name: str, footprint: np.ndarray) -> np.ndarray:
    kind, band_key, sign = TRANSFORMS[name]
    if kind == "rad":
        a = _read_band(RAD_PATH, BAND_RAD[band_key], footprint)
    else:
        a = _read_band(EXT_PATH, BAND_EXT[band_key], footprint)
    return sign * a


def build_stats(footprint: np.ndarray, seed: int = 69) -> dict:
    if STATS_CACHE.exists():
        raw = json.loads(STATS_CACHE.read_text())
        return raw
    rng = np.random.default_rng(seed)
    fy, fx = np.nonzero(footprint)
    sel = rng.choice(len(fy), size=min(SUBSAMPLE, len(fy)), replace=False)
    sy, sx = fy[sel], fx[sel]
    stats = {}
    for name in NAMES:
        t = compute_transform(name, footprint)
        v = t[sy, sx]
        v = v[np.isfinite(v)]
        if v.size < 1000:
            stats[name] = {"median": 0.0, "mad": 1.0}
            continue
        med = float(np.median(v))
        mad = float(np.median(np.abs(v - med))) * MAD_SCALE
        stats[name] = {"median": med, "mad": mad if mad > 0 else 1.0}
        del t
    STATS_CACHE.write_text(json.dumps(stats, indent=1))
    return stats


def zscore(t: np.ndarray, median: float, mad: float) -> np.ndarray:
    return np.clip((t - median) / max(mad, 1e-9), -CLIP_Z, CLIP_Z)


def build_z_stack(footprint: np.ndarray, stats: dict | None = None, use_cache: bool = True) -> dict:
    if stats is None:
        stats = build_stats(footprint)
    cache = CACHE / "rad_z_stack.npz"
    if use_cache and cache.exists():
        with np.load(cache) as z:
            if all(n in z.files for n in NAMES):
                return {n: z[n] for n in NAMES}
    out = {}
    for n in NAMES:
        t = compute_transform(n, footprint)
        md = stats[n]["median"]
        mad = stats[n]["mad"]
        zz = zscore(t, md, mad)
        zz = np.where(np.isfinite(zz), zz, np.nan).astype(np.float16)
        out[n] = zz
        del t, zz
    if use_cache:
        np.savez_compressed(cache, **out)
    return out
