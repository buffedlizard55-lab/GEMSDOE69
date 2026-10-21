"""Physics evidence layers for corridor routing, scoring, and leak-free calibration.

Every layer computed here is strictly independent of the fault catalogue (zero
inventory features, zero hidden-fault distance columns). All band names match
verified GeoTIFF band descriptions on disk (see ``evidence/band_metadata.json``).

Key physical transforms:
  * Wavenumber upward-continued potential-field edge operators (Miller & Singh
    1994): ``iso_grav_anom`` (Band 13) and ``rtp`` (Band 2) continued upward to
    h in {150 m, 500 m, 1500 m}; total horizontal derivative THDR gated by tilt
    zero-crossing ``1 - |tilt| / (pi/2)``.
  * Multi-scale magnetic lows: negated residual of ``rtp`` at 1 km and 3 km
    scales (magnetite destruction along hydrothermally altered fault conduits).
  * Cultural-vetoed 1 m LiDAR scarp strength, 100 m orientation coherence
    (``coh100``, Band 10), and verified compass scarp strike azimuth
    (``(strike_u8 * 180 / 255 + 90) % 180``, fixing the 90-deg image-axis
    offset documented as IR-69-LIDAR-STRIKE-01).
  * 100%-coverage topographic breakline curvature ridge from ``det_elev``
    (Band 12 maximum Hessian principal curvature at sigma = 1.5, 3.0 px plus
    ``det_elev_slope`` Band 19), seamlessly bridging the 24.6% 3DEP LiDAR gap.
  * Subsurface basin-margin architecture: horizontal gradient of smoothed
    ``depth_to_base_surf`` (Band 15) and ``cond_surf`` (Band 17).
  * Active Walker Lane crustal strain invariants used raw without noisy
    re-differentiation: ``geod_2ndinv`` (Band 4), ``geod_shearrate`` (Band 7),
    ``geod_dilaterate`` (Band 8).
  * Local corridor-scale radiometric alteration contrast: high-pass magnitude on
    GeoDAWN ``K`` and ``ThK`` (capturing potassic enrichment AND argillic K
    leaching while removing broad plutonic/volcanic lithologic background).
  * Leak-free thermal conduit field from ``gdr_wellspring_in_footprint.csv``
    using ONLY measured temperature/geothermometer columns (``temp_c``,
    ``geothermquartz_c``, ``geothermchalc_c``, ``geothermcat_c``; explicitly
    forbidding ``dist_known_fault_px``).
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
import scipy.fft as sfft
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / ".cache" / "gems_data" / "training_features.tif"
LIDAR_PATH = ROOT / ".cache" / "gems_data" / "external" / "lidar_scarp_features_u8.tif"
RAD_PATH = ROOT / ".cache" / "gems_data" / "external" / "geodawn_rad_u8.tif"
EXT_PATH = ROOT / ".cache" / "gems_data" / "external" / "geodawn_extensions_u8.tif"
WELLSPRING_CSV = ROOT / ".cache" / "gems_data" / "external" / "gdr_wellspring_in_footprint.csv"
STATS_CACHE = ROOT / ".cache" / "gems_data" / "layer_stats_v2.json"
ZSTACK_CACHE = ROOT / ".cache" / "gems_data" / "z_stack_v2.npz"

BAND = {
    "mag_anom": 1, "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4, "iso_grav_slope": 5,
    "tc": 6, "geod_shear": 7, "geod_dilat": 8, "tmi_vg": 9, "deq": 10,
    "iso_grav_vg": 11, "det_elev": 12, "iso_grav": 13, "tmi": 14,
    "basement_depth": 15, "ieq": 16, "cond_surf": 17, "iso_grav_hg": 18,
    "det_elev_slope": 19,
}
LIDAR_BANDS = {
    "ex_max": 1, "ex_mean": 2, "step_max": 3, "lapneg_max": 4, "lappos_max": 5,
    "downface_max": 6, "upface_max": 7, "cross_max": 8, "relief": 9,
    "coh100": 10, "strike": 11, "valid": 12,
}

SIGMAS = (1.0, 2.0, 4.0)
UPWARD_HEIGHTS_PX = (1.5, 5.0, 15.0)   # 150 m, 500 m, 1.5 km upward continuation
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
    a[~np.isfinite(a) | (a < -1e30)] = np.nan
    return a


def _fill_nearest(a: np.ndarray) -> np.ndarray:
    bad = ~np.isfinite(a)
    if not bad.any():
        return a.copy()
    if bad.all():
        return np.zeros_like(a, dtype=np.float32)
    _, (iy, ix) = ndi.distance_transform_edt(bad, return_indices=True)
    return a[iy, ix].astype(np.float32, copy=False)


def _rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape, np.float32)
    m = mask & np.isfinite(a)
    v = a[m]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="mergesort")
    r = np.empty(v.size, np.float64)
    r[order] = np.arange(v.size, dtype=np.float64)
    out[m] = (r / max(v.size - 1, 1)).astype(np.float32)
    return out


def upward_tilt_edge(field: np.ndarray, footprint: np.ndarray,
                     heights_px=UPWARD_HEIGHTS_PX, pad: int = 96) -> np.ndarray:
    """Multi-scale wavenumber upward-continued THDR * (1 - |tilt|/(pi/2))."""
    f = _fill_nearest(field)
    f -= np.float32(np.nanmean(field[footprint]))
    H, W = f.shape
    ph = sfft.next_fast_len(H + 2 * pad, real=True)
    pw = sfft.next_fast_len(W + 2 * pad, real=True)
    fp_pad = np.pad(f, ((pad, ph - H - pad), (pad, pw - W - pad)), mode="reflect")
    del f
    F = sfft.rfft2(fp_pad, workers=2)
    del fp_pad
    ky = (np.fft.fftfreq(ph) * 2.0 * np.pi).astype(np.float32)[:, None]
    kx = (np.fft.rfftfreq(pw) * 2.0 * np.pi).astype(np.float32)[None, :]
    k = np.sqrt(kx * kx + ky * ky)
    best = np.zeros((H, W), np.float32)
    for h in heights_px:
        up = F * np.exp(-k * np.float32(h))
        g = sfft.irfft2(up, s=(ph, pw), workers=2)[pad:pad + H, pad:pad + W].astype(np.float32)
        vdr = sfft.irfft2(up * k, s=(ph, pw), workers=2)[pad:pad + H, pad:pad + W].astype(np.float32)
        del up
        gy, gx = np.gradient(g)
        del g
        thdr = np.hypot(gx, gy).astype(np.float32)
        del gx, gy
        tilt = np.arctan2(vdr, thdr + 1e-12)
        del vdr
        edge = _rank01(thdr, footprint) * (1.0 - np.abs(tilt) / np.float32(np.pi / 2.0))
        del thdr, tilt
        np.maximum(best, _rank01(edge, footprint), out=best)
        del edge
    del F, k
    best[~footprint] = np.nan
    return best


def hessian_breakline_ridge(field: np.ndarray, sigmas=(1.5, 3.5)) -> np.ndarray:
    """Maximum principal curvature breakline ridge across scales (100% coverage)."""
    f = _fill_nearest(field)
    acc = np.zeros(f.shape, np.float32)
    for s in sigmas:
        g = ndi.gaussian_filter(f, s)
        gy, gx = np.gradient(g)
        gyy, gyx = np.gradient(gy)
        gxy, gxx = np.gradient(gx)
        tr = gxx + gyy
        disc = np.sqrt(np.maximum((gxx - gyy) ** 2 + 4.0 * gxy * gyx, 0.0))
        eig_max = 0.5 * np.maximum(np.abs(tr + disc), np.abs(tr - disc)) * (s ** 1.5)
        acc = np.maximum(acc, eig_max.astype(np.float32))
    acc[~np.isfinite(field)] = np.nan
    return acc


def _lidar_scarp_window(bbox: tuple[int, int, int, int] | None):
    with rasterio.open(LIDAR_PATH) as src:
        w = (None if bbox is None
             else rasterio.windows.Window(bbox[2], bbox[0], bbox[3] - bbox[2], bbox[1] - bbox[0]))
        ex = src.read(LIDAR_BANDS["ex_max"], window=w).astype(np.float32)
        st = src.read(LIDAR_BANDS["step_max"], window=w).astype(np.float32)
        df = src.read(LIDAR_BANDS["downface_max"], window=w).astype(np.float32)
        cr = src.read(LIDAR_BANDS["cross_max"], window=w).astype(np.float32)
        coh = src.read(LIDAR_BANDS["coh100"], window=w).astype(np.float32)
        valid = src.read(LIDAR_BANDS["valid"], window=w) > 0
    raw = (0.45 * ex + 0.35 * st + 0.20 * df) * (1.0 - 0.30 * (cr / 255.0)) * (0.55 + 0.45 * (coh / 255.0))
    raw[~valid] = np.nan
    return raw


def load_lidar_strike_deg(footprint: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (compass_strike_deg [0..180), coherence_01) with NaN where invalid.

    Verified empirically on high-coherence mapped scarps (IR-69-LIDAR-STRIKE-01):
    raw uint8 encodes image-axis angle, so ``(raw * 180 / 255 + 90) % 180`` gives
    geographic compass azimuth (median error 10.96 deg vs 79.04 deg uncorrected).
    """
    cache = STATS_CACHE.parent / "lidar_orient_v2.npz"
    if cache.exists():
        with np.load(cache) as z:
            return z["strike_deg"].astype(np.float32), z["coh01"].astype(np.float32)
    with rasterio.open(LIDAR_PATH) as src:
        raw_st = src.read(LIDAR_BANDS["strike"]).astype(np.float32)
        raw_coh = src.read(LIDAR_BANDS["coh100"]).astype(np.float32) / 255.0
        valid = (src.read(LIDAR_BANDS["valid"]) > 0) & footprint
    strike_deg = np.where(valid, (raw_st * (180.0 / 255.0) + 90.0) % 180.0, np.nan).astype(np.float32)
    coh01 = np.where(valid, raw_coh, 0.0).astype(np.float32)
    np.savez_compressed(cache, strike_deg=strike_deg.astype(np.float16), coh01=coh01.astype(np.float16))
    return strike_deg, coh01


def _radiometric_contrast(footprint: np.ndarray) -> np.ndarray:
    """Local corridor-scale contrast of GeoDAWN K and Th/K (removes regional pluton drift)."""
    if not RAD_PATH.exists():
        return np.full(footprint.shape, np.nan, np.float32)
    with rasterio.open(RAD_PATH) as src:
        k = src.read(1).astype(np.float32)
        th = src.read(2).astype(np.float32)
    valid = footprint & (k > 0) & (th > 0)
    k_f = _fill_nearest(np.where(valid, k, np.nan))
    k_hp = np.abs(k_f - ndi.gaussian_filter(k_f, 20.0))
    if EXT_PATH.exists():
        with rasterio.open(EXT_PATH) as src:
            thk = src.read(1).astype(np.float32)
        thk_f = _fill_nearest(np.where(valid, thk, np.nan))
        thk_hp = np.abs(thk_f - ndi.gaussian_filter(thk_f, 20.0))
        out = 0.5 * _rank01(k_hp, valid) + 0.5 * _rank01(thk_hp, valid)
    else:
        out = _rank01(k_hp, valid)
    out[~valid] = np.nan
    return out


def _thermal_conduit_field(footprint: np.ndarray) -> np.ndarray:
    """Thermal well/spring anomaly kernel strictly from physical temperatures/geothermometers.

    Explicitly forbids reading ``dist_known_fault_px`` (verified leak-free by canary).
    """
    out = np.zeros(footprint.shape, np.float32)
    if not WELLSPRING_CSV.exists():
        out[~footprint] = np.nan
        return out
    ALLOWED_COLS = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
    H, W = footprint.shape
    imp = np.zeros((H, W), np.float32)
    with open(WELLSPRING_CSV, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sub = {k: row[k] for k in ALLOWED_COLS if k in row}
            try:
                r = int(float(sub["row"]))
                c = int(float(sub["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= r < H and 0 <= c < W) or not footprint[r, c]:
                continue
            vals = []
            for key, thresh in (("temp_c", 25.0), ("geothermquartz_c", 70.0),
                                ("geothermchalc_c", 60.0), ("geothermcat_c", 80.0)):
                try:
                    v = float(sub.get(key, ""))
                    if np.isfinite(v) and v >= thresh:
                        vals.append(min((v - thresh) / thresh + 0.5, 3.0))
                except ValueError:
                    pass
            if vals:
                imp[r, c] = max(imp[r, c], max(vals))
    if imp.max() > 0:
        out = 0.65 * ndi.gaussian_filter(imp, 12.0) + 0.35 * ndi.gaussian_filter(imp, 26.0)
    out[~footprint] = np.nan
    return out


def hg(field: np.ndarray, sigma: float) -> np.ndarray:
    f = _fill_nearest(field)
    g = ndi.gaussian_filter(f, sigma)
    gy, gx = np.gradient(g)
    res = np.hypot(gy, gx).astype(np.float32)
    res[~np.isfinite(field)] = np.nan
    return res


def tilt_edge(field: np.ndarray, sigma: float) -> np.ndarray:
    """|sin(tilt)| edge evidence on smoothed potential/surface field."""
    f = _fill_nearest(field)
    g1 = ndi.gaussian_filter(f, sigma)
    g2 = ndi.gaussian_filter(f, 2.0 * sigma)
    vd = g1 - g2
    gy, gx = np.gradient(g1)
    h = np.hypot(gy, gx)
    res = np.abs(np.sin(np.arctan2(vd, h + 1e-12))).astype(np.float32)
    res[~np.isfinite(field)] = np.nan
    return res


TRANSFORM_SPECS = []
for _s in SIGMAS:
    TRANSFORM_SPECS.append((f"grav_hg_s{_s:g}", "hg", "iso_grav", _s))
    TRANSFORM_SPECS.append((f"mag_hg_s{_s:g}", "hg", "tmi", _s))
TRANSFORM_SPECS += [
    ("grav_upward_edge", "upward", "iso_grav", 0.0),
    ("mag_upward_edge", "upward", "rtp", 0.0),
    ("grav_tilt_s2", "tilt", "iso_grav", 2.0),
    ("mag_tilt_s2", "tilt", "tmi", 2.0),
    ("grav_hg_prov", "raw", "iso_grav_hg", 0.0),
    ("grav_vg_prov", "raw", "iso_grav_vg", 0.0),
    ("geod_2ndinv", "raw", "geod_2ndinv", 0.0),
    ("geod_shear", "raw", "geod_shear", 0.0),
    ("geod_dilat", "raw", "geod_dilat", 0.0),
    ("mag_hg_prov", "raw", "tmi_hg", 0.0),
    ("mag_vg_prov", "raw", "tmi_vg", 0.0),
    ("tc_prov", "raw", "tc", 0.0),
    ("mag_low_rtp_res", "maglow", "rtp", 0.0),
    ("mag_low_tmi", "negraw", "tmi", 0.0),
    ("mag_low_rtp", "negraw", "rtp", 0.0),
    ("lidar_scarp", "lidar", None, 0.0),
    ("elev_curv_ridge", "curv", "det_elev", 0.0),
    ("det_elev_slope", "raw", "det_elev_slope", 0.0),
    ("basement_step", "hg", "basement_depth", 2.0),
    ("cond_step", "hg", "cond_surf", 2.0),
    ("rad_kth_contrast", "rad", None, 0.0),
    ("thermal_conduit", "thermal", None, 0.0),
]
TRANSFORM_NAMES = [t[0] for t in TRANSFORM_SPECS]
_SPEC_MAP = {t[0]: t for t in TRANSFORM_SPECS}


def compute_transform(name: str, bbox=None, footprint: np.ndarray | None = None) -> np.ndarray:
    _, kind, src, sigma = _SPEC_MAP[name]
    if kind == "lidar":
        return _lidar_scarp_window(bbox)
    if kind in ("upward", "rad", "thermal"):
        if footprint is None:
            with rasterio.open(FEATURES_PATH) as r:
                b1 = r.read(1)
            footprint = np.isfinite(b1) & (b1 > -1e30)
        if kind == "rad":
            arr = _radiometric_contrast(footprint)
        elif kind == "thermal":
            arr = _thermal_conduit_field(footprint)
        else:
            f_full = _band_window(FEATURES_PATH, BAND[src], None)
            arr = upward_tilt_edge(f_full, footprint)
        if bbox is not None:
            r0, r1, c0, c1 = bbox
            return arr[r0:r1, c0:c1]
        return arr
    f = _band_window(FEATURES_PATH, BAND[src], bbox)
    if kind == "hg":
        return hg(f, sigma)
    if kind == "tilt":
        return tilt_edge(f, sigma)
    if kind == "curv":
        return hessian_breakline_ridge(f)
    if kind == "maglow":
        fn = _fill_nearest(f)
        res = np.maximum(-(fn - ndi.gaussian_filter(fn, 10.0)),
                         -(fn - ndi.gaussian_filter(fn, 30.0))).astype(np.float32)
        res[~np.isfinite(f)] = np.nan
        return res
    if kind == "raw":
        return f
    if kind == "negraw":
        return -f
    raise KeyError(name)


def build_layer_stats(footprint: np.ndarray, seed: int = 69) -> dict[str, LayerStats]:
    """One full-grid pass per transform; subsampled robust stats. Cached."""
    if STATS_CACHE.exists():
        raw = json.loads(STATS_CACHE.read_text())
        if all(n in raw for n in TRANSFORM_NAMES):
            return {k: LayerStats(v["median"], v["mad"]) for k, v in raw.items()}
    rng = np.random.default_rng(seed)
    fy, fx = np.nonzero(footprint)
    sel = rng.choice(len(fy), size=min(STATS_SUBSAMPLE, len(fy)), replace=False)
    sy, sx = fy[sel], fx[sel]
    stats: dict[str, LayerStats] = {}
    for name in TRANSFORM_NAMES:
        t = compute_transform(name, footprint=footprint)
        v = t[sy, sx]
        v = v[np.isfinite(v)]
        if v.size < 100:
            stats[name] = LayerStats(0.0, 1.0)
            continue
        med = float(np.median(v))
        mad = float(np.median(np.abs(v - med))) * MAD_SCALE
        stats[name] = LayerStats(med, mad if mad > 1e-6 else float(np.std(v) or 1.0))
        del t
    STATS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    STATS_CACHE.write_text(json.dumps({k: {"median": v.median, "mad": v.mad}
                                       for k, v in stats.items()}, indent=1))
    return stats


def build_z_stack(footprint: np.ndarray, stats: dict[str, LayerStats],
                  names: list[str] | None = None, use_cache: bool = True) -> dict:
    """Precompute robust-z layers for the full grid once (float16, NaN where nodata)."""
    names = names or TRANSFORM_NAMES
    if use_cache and ZSTACK_CACHE.exists():
        with np.load(ZSTACK_CACHE) as z:
            if all(n in z.files for n in names):
                return {n: z[n] for n in names}
    out = {}
    for n in names:
        t = compute_transform(n, footprint=footprint)
        zz = stats[n].z(t)
        zz = np.where(np.isfinite(zz), zz, np.nan).astype(np.float16)
        out[n] = zz
        del t, zz
    if use_cache:
        ZSTACK_CACHE.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(ZSTACK_CACHE, **out)
    return out


def build_admittance_surface(zstack: dict, footprint: np.ndarray) -> np.ndarray:
    """Composite 1D fault-admittance surface A(y, x) in [0, 1] for geodesic routing.

    Combines geomorphic scarp/breakline ridges (LiDAR scarp where valid, seamlessly
    backed by 100%-coverage ``elev_curv_ridge`` + ``det_elev_slope``) with multi-scale
    gravity & magnetic edges, magnetite-destruction troughs, and buried basement steps.
    Zero catalogue features enter this surface.
    """
    def _pos(name: str) -> np.ndarray:
        z = zstack[name].astype(np.float32)
        return np.where(np.isfinite(z), np.clip(z, -2.0, 5.0), 0.0)

    lid_raw = zstack["lidar_scarp"].astype(np.float32)
    has_lid = np.isfinite(lid_raw)
    geomorph = np.where(
        has_lid,
        0.60 * _pos("lidar_scarp") + 0.40 * np.maximum(_pos("elev_curv_ridge"), _pos("det_elev_slope")),
        np.maximum(_pos("elev_curv_ridge"), _pos("det_elev_slope")),
    )
    grav = np.maximum(_pos("grav_upward_edge"), _pos("grav_hg_s2"))
    mag = np.maximum(np.maximum(_pos("mag_upward_edge"), _pos("mag_hg_s2")), 0.85 * _pos("mag_low_rtp_res"))
    sub = 0.65 * _pos("basement_step") + 0.35 * _pos("cond_step")
    comp = 0.42 * geomorph + 0.24 * grav + 0.22 * mag + 0.12 * sub
    admit = _rank01(comp, footprint)
    admit[~footprint] = 0.0
    return admit


def corridor_evidence_from_z(zstack: dict, corridor,
                             lidar_strike_deg: np.ndarray | None = None,
                             lidar_coh01: np.ndarray | None = None) -> dict[str, float]:
    """Weighted robust-z mean across the 1D core trace of a corridor plus flank contrast."""
    if corridor.npix == 0:
        return {n: 0.0 for n in zstack}
    br0, br1, bc0, bc1 = corridor.bbox
    w_map = corridor.local_weight
    core = corridor.local_mask & (w_map >= 0.70)
    if not core.any():
        core = corridor.local_mask
    flank = (~corridor.local_mask)
    out = {}
    for n, z in zstack.items():
        sub = z[br0:br1, bc0:bc1]
        vc = sub[core].astype(np.float32)
        vc = vc[np.isfinite(vc)]
        out[n] = float(vc.mean()) if vc.size else 0.0
    # Flank-differenced radiometric K/Th contrast (rejects broad pluton background)
    if "rad_kth_contrast" in zstack:
        sub_r = zstack["rad_kth_contrast"][br0:br1, bc0:bc1].astype(np.float32)
        rc = sub_r[core]; rc = rc[np.isfinite(rc)]
        rf = sub_r[flank]; rf = rf[np.isfinite(rf)]
        out["rad_kth_local_excess"] = float(rc.mean() - rf.mean()) if (rc.size and rf.size) else 0.0
    else:
        out["rad_kth_local_excess"] = 0.0
    # Strike-concordant 1m LiDAR scarp orientation agreement
    if lidar_strike_deg is not None and lidar_coh01 is not None:
        st_sub = lidar_strike_deg[br0:br1, bc0:bc1][core]
        co_sub = lidar_coh01[br0:br1, bc0:bc1][core]
        ok = np.isfinite(st_sub) & (co_sub > 0.25)
        if ok.any():
            az = corridor.pair.mean_az
            diff = np.abs(st_sub[ok] - az) % 180.0
            diff = np.minimum(diff, 180.0 - diff)
            align = np.cos(np.radians(diff)) ** 2 * co_sub[ok]
            out["lidar_strike_concordance"] = float(align.mean())
        else:
            out["lidar_strike_concordance"] = 0.0
    else:
        out["lidar_strike_concordance"] = 0.0
    # Joint multi-modality phase coherence along the core trace
    g_core = np.maximum(
        zstack["grav_upward_edge"][br0:br1, bc0:bc1][core].astype(np.float32),
        zstack["grav_hg_s2"][br0:br1, bc0:bc1][core].astype(np.float32),
    )
    m_core = np.maximum(
        zstack["mag_upward_edge"][br0:br1, bc0:bc1][core].astype(np.float32),
        zstack["mag_low_rtp_res"][br0:br1, bc0:bc1][core].astype(np.float32),
    )
    s_core = np.maximum(
        np.nan_to_num(zstack["lidar_scarp"][br0:br1, bc0:bc1][core].astype(np.float32), nan=-1.0),
        np.nan_to_num(zstack["elev_curv_ridge"][br0:br1, bc0:bc1][core].astype(np.float32), nan=-1.0),
    )
    n_mod = (np.nan_to_num(g_core, nan=-1.0) > 0.35).astype(int) + \
            (np.nan_to_num(m_core, nan=-1.0) > 0.35).astype(int) + \
            (np.nan_to_num(s_core, nan=-1.0) > 0.35).astype(int)
    out["joint_phase_coherence"] = float((n_mod >= 2).mean()) if n_mod.size else 0.0
    return out


def corridor_evidence(corridor, stats: dict[str, LayerStats], pad: int = 4,
                      shape: tuple[int, int] | None = None) -> dict[str, float]:
    """Windowed fallback evidence computation."""
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


def straight_step(field: np.ndarray, sigma: float = 1.5, coh_sigma: float = 2.0) -> np.ndarray:
    """Structure-tensor coherence weighted step magnitude (NaN-preserving outside finite support)."""
    from .data import fill_nearest

    nan_mask = ~np.isfinite(field)
    filled = fill_nearest(field.astype(np.float32))
    sm = ndi.gaussian_filter(filled, sigma=sigma)
    gy, gx = np.gradient(sm)
    mag = np.hypot(gx, gy)
    jxx = ndi.gaussian_filter(gx * gx, sigma=coh_sigma)
    jyy = ndi.gaussian_filter(gy * gy, sigma=coh_sigma)
    jxy = ndi.gaussian_filter(gx * gy, sigma=coh_sigma)
    trace = jxx + jyy + 1e-12
    coh = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0)) / trace
    out = (mag * coh).astype(np.float32)
    out[nan_mask] = np.nan
    return out


def local_depletion(field: np.ndarray, sigma_local: float = 1.0, sigma_bg: float = 4.0) -> np.ndarray:
    """Positive where local smooth field falls below broader background (NaN-preserving)."""
    from .data import fill_nearest

    nan_mask = ~np.isfinite(field)
    filled = fill_nearest(field.astype(np.float32))
    out = (ndi.gaussian_filter(filled, sigma=sigma_bg) - ndi.gaussian_filter(filled, sigma=sigma_local)).astype(np.float32)
    out[nan_mask] = np.nan
    return out
