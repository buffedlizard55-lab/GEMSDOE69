"""Data access for the lane: pinned inputs, band readers, small raster helpers.

Large inputs are restored outside the repository by ``scripts/restore_data.py``
(``$GEMS_DATA``, default ``/tmp/gems_data``) and verified by SHA-256 before use.
Derived feature caches go to ``$GEMS_CACHE`` (default ``/tmp/gems_cache``).
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

def _default_data_dir() -> Path:
    if "GEMS_DATA" in os.environ:
        return Path(os.environ["GEMS_DATA"])
    cand = ROOT / ".cache" / "gems_data"
    if (cand / "training_features.tif").is_file():
        return cand
    bridge = ROOT / "data" / "bridge"
    if (bridge / "sample_submission.tif").is_file() and (bridge / "labels.tif").is_file():
        return bridge
    return Path("/tmp/gems_data")


DATA = _default_data_dir()
CACHE = Path(os.environ.get("GEMS_CACHE", str(ROOT / ".cache" / "gems_data" / "derived69")))
FEATURES = DATA / "training_features.tif"
SENTINEL_LIMIT = -1e30          # the stack's nodata is -3.4028234663852886e+38

# SHA-256 pins (mirror consistency, not organizer authentication -- see README).
PINS = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "external/trace_segments_utm11.csv": "c5edf9df3e0e1413c52784884fc38e5b9ca54627b27c6f8baf7713e908f48513",
    "external/qfault_attributes.csv": "3b8745f0086a57b8255f6679afa1bf1168c10b5573491666c75cf53217029507",
    "external/geodawn_dem_a2_100m.tif": "d32762a38222764389e948da423ebc6cadd00ac617ad3938d3dd79c6cfe14431",
    "external/derived_sgmc_faults_100m_u8.tif": "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pins() -> dict:
    out = {}
    for rel, pin in PINS.items():
        p = DATA / rel
        got = sha256(p) if p.exists() else None
        out[rel] = dict(expected=pin, got=got, ok=got == pin)
    return out


def load_grid():
    """Footprint + catalogue via the shared template's grid loader (pinned files)."""
    from gems57.grid import load_grid as _load
    return _load(DATA)


def band_names() -> list[str]:
    with rasterio.open(FEATURES) as src:
        return [d.split(" - ")[0] for d in src.descriptions]


def band(name: str, footprint: np.ndarray) -> np.ndarray:
    """One feature band as float32; sentinels, non-finite and off-footprint -> NaN."""
    idx = band_names().index(name) + 1
    with rasterio.open(FEATURES) as src:
        a = src.read(idx).astype(np.float32)
    bad = ~np.isfinite(a) | (a <= SENTINEL_LIMIT) | ~footprint
    a[bad] = np.nan
    return a


def external_band(fname: str, name: str, footprint: np.ndarray) -> np.ndarray:
    """A named band of an external uint8/float raster on the grid; nodata -> NaN."""
    with rasterio.open(DATA / "external" / fname) as src:
        names = list(src.descriptions)
        idx = names.index(name) + 1
        a = src.read(idx).astype(np.float32)
        nod = src.nodata
    bad = ~footprint | ~np.isfinite(a)
    if nod is not None:
        bad |= a == nod
    a[bad] = np.nan
    return a


def dem(footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(DATA / "external" / "geodawn_dem_a2_100m.tif") as src:
        a = src.read(1).astype(np.float32)
        nod = src.nodata
    bad = ~np.isfinite(a) | ~footprint
    if nod is not None:
        bad |= a == nod
    a[bad] = np.nan
    return a


def fill_nearest(a: np.ndarray) -> np.ndarray:
    """Fill NaN cells with the nearest finite value (for spectral operators only)."""
    bad = ~np.isfinite(a)
    if not bad.any():
        return a.copy()
    _, (iy, ix) = ndi.distance_transform_edt(bad, return_indices=True)
    return a[iy, ix]


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile rank in [0, 1] of finite in-mask values; 0 elsewhere (float32)."""
    out = np.zeros(a.shape, np.float32)
    m = mask & np.isfinite(a)
    v = a[m]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="stable")
    r = np.empty(v.size, np.float64)
    r[order] = np.arange(v.size, dtype=np.float64)
    out[m] = (r / max(v.size - 1, 1)).astype(np.float32)
    return out
