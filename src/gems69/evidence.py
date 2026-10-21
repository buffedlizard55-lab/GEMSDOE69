"""Geophysical evidence layers used to score corridors (none is catalogue-derived).

* ``grav_edge`` / ``mag_edge`` -- multi-scale potential-field edge evidence.
  The isostatic gravity anomaly (band ``iso_grav_anom``) and the reduced-to-pole
  magnetic anomaly (band ``rtp``) are upward-continued in the wavenumber domain
  to 200 m, 600 m and 1.8 km.  At each height the total horizontal derivative
  (THDR) and the tilt angle ``atan2(VDR, THDR)`` (Miller & Singh 1994) are
  computed; edge evidence is ``rank(THDR) * (1 - |tilt| / 90 deg)`` -- strong
  lateral gradient where the tilt crosses zero, i.e. above a vertical contact.
  The multi-scale value is the maximum over heights of the per-height rank.
* ``grav_ge`` / ``grav_gn`` and ``mag_ge`` / ``mag_gn`` -- signed East/North
  directional horizontal gradient components at sigma = 3 px (300 m), scaled by
  footprint rank amplitude ``rank01(|grad|)`` along unit gradient vector
  ``(ge, gn) / |grad|``.  For a candidate corridor with unit right-normal ``n``,
  ``|ge * n_E + gn * n_N|`` isolates basement steps running *along* the corridor
  while suppressing range-front gradients crossing perpendicular to the corridor.
* ``mag_low`` -- local magnetic lows: rank of ``-(RTP - Gaussian_3km(RTP))``.
  Hydrothermal alteration destroys magnetite along permeable faults, so fault
  zones in volcanic/plutonic hosts often appear as linear magnetic lows.
* ``scarp`` -- the lidar scarp channel: ``0.45 ex_max + 0.35 step_max +
  0.20 downface_max`` of ``lidar_scarp_features_u8.tif`` (3DEP 1 m derived),
  bands selected by *name* (a sibling repo read the wrong band indices).

All layers are float16, 0 outside the footprint, cached in ``$GEMS_CACHE``.
Memory is kept below ~1 GB (2-CPU / 3 GB sandbox).
"""
from __future__ import annotations

import json
import time

import numpy as np
import scipy.fft as sfft
from scipy import ndimage as ndi

from .data import CACHE, band, external_band, fill_nearest, rank01

SCALES_PX = (2.0, 6.0, 18.0)          # 200 m, 600 m, 1.8 km upward continuation
LAYERS = ("grav_edge", "mag_edge", "mag_low", "scarp")
DIRECTIONAL_LAYERS = ("grav_ge", "grav_gn", "mag_ge", "mag_gn")
ALL_CACHE_LAYERS = LAYERS + DIRECTIONAL_LAYERS


def _wavenumbers(ph: int, pw: int) -> np.ndarray:
    ky = (np.fft.fftfreq(ph) * 2 * np.pi).astype(np.float32)[:, None]
    kx = (np.fft.rfftfreq(pw) * 2 * np.pi).astype(np.float32)[None, :]
    return np.sqrt(kx * kx + ky * ky)


def directional_scaled_gradient(field: np.ndarray, footprint: np.ndarray,
                                sigma_px: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Return signed ``(ge, gn)`` where ``hypot(ge, gn) == rank01(|grad_sigma(field)|)``.

    Map coordinates use ``E = +col`` and ``N = -row``, so ``dF/dE = +gx`` and
    ``dF/dN = -gy`` for ``gy, gx = np.gradient(smoothed)``.
    """
    f = fill_nearest(field).astype(np.float32)
    sm = ndi.gaussian_filter(f, sigma_px)
    del f
    gy, gx = np.gradient(sm)
    del sm
    ge = gx.astype(np.float32)
    gn = (-gy).astype(np.float32)
    del gx, gy
    mag = np.hypot(ge, gn).astype(np.float32)
    rk = rank01(mag, footprint)
    inv = np.where(mag > 1e-12, rk / np.maximum(mag, 1e-12), 0.0).astype(np.float32)
    del mag, rk
    ge *= inv
    gn *= inv
    del inv
    ge[~footprint] = 0.0
    gn[~footprint] = 0.0
    return ge, gn


def potential_field_edges(field: np.ndarray, footprint: np.ndarray,
                          scales=SCALES_PX, pad: int = 128) -> tuple[np.ndarray, dict]:
    f = fill_nearest(field).astype(np.float32)
    f -= np.float32(np.nanmean(field[footprint]))
    H, W = f.shape
    ph = sfft.next_fast_len(H + 2 * pad, real=True)
    pw = sfft.next_fast_len(W + 2 * pad, real=True)
    fp = np.pad(f, ((pad, ph - H - pad), (pad, pw - W - pad)), mode="reflect")
    del f
    F = sfft.rfft2(fp, workers=2)
    del fp
    k = _wavenumbers(ph, pw)
    best = np.zeros((H, W), np.float32)
    stats = {}
    for h in scales:
        up = F * np.exp(-k * np.float32(h))
        g = sfft.irfft2(up, s=(ph, pw), workers=2)[pad:pad + H, pad:pad + W].astype(np.float32)
        vdr = sfft.irfft2(up * k, s=(ph, pw), workers=2)[pad:pad + H, pad:pad + W].astype(np.float32)
        del up
        gy, gx = np.gradient(g)
        del g
        thdr = np.hypot(gx, gy).astype(np.float32)
        del gx, gy
        tilt = np.arctan2(vdr, thdr)
        del vdr
        edge = rank01(thdr, footprint) * (1.0 - np.abs(tilt) / np.float32(np.pi / 2))
        del thdr, tilt
        r = rank01(edge, footprint)
        stats[f"h{int(h*100)}m_mean_edge"] = float(edge[footprint].mean())
        np.maximum(best, r, out=best)
        del edge, r
    del F, k
    best[~footprint] = 0
    return best, stats


def magnetic_lows(rtp: np.ndarray, footprint: np.ndarray, sigma_px: float = 30.0) -> np.ndarray:
    f = fill_nearest(rtp).astype(np.float32)
    resid = f - ndi.gaussian_filter(f, sigma_px)
    del f
    resid[~footprint] = np.nan
    return rank01(-resid, footprint)


def scarp_channel(footprint: np.ndarray) -> np.ndarray:
    fname = "lidar_scarp_features_u8.tif"
    valid = external_band(fname, "valid", footprint)
    out = np.zeros(footprint.shape, np.float32)
    for name, w in (("ex_max", 0.45), ("step_max", 0.35), ("downface_max", 0.20)):
        a = external_band(fname, name, footprint)
        out += np.float32(w) * np.nan_to_num(a, nan=0.0) / np.float32(255.0)
        del a
    ok = footprint & np.isfinite(valid) & (np.nan_to_num(valid) > 0)
    out[~ok] = np.nan
    return rank01(out, ok)


def build_cache(grid, force: bool = False) -> dict:
    """Compute (or load) every evidence layer; returns the receipt dict."""
    CACHE.mkdir(parents=True, exist_ok=True)
    receipt_path = CACHE / "evidence_receipt.json"
    if (receipt_path.exists() and not force
            and all((CACHE / f"{n}.npy").exists() for n in ALL_CACHE_LAYERS)):
        return json.loads(receipt_path.read_text())
    fp = grid.footprint
    rec = dict(scales_px=list(SCALES_PX), layers={},
               started=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    t0 = time.time()
    g = band("iso_grav_anom", fp)
    ge, gn = directional_scaled_gradient(g, fp, sigma_px=3.0)
    np.save(CACHE / "grav_ge.npy", ge.astype(np.float16))
    np.save(CACHE / "grav_gn.npy", gn.astype(np.float16))
    del ge, gn
    e, st = potential_field_edges(g, fp)
    del g
    np.save(CACHE / "grav_edge.npy", e.astype(np.float16))
    rec["layers"]["grav_edge"] = dict(source="training_features band iso_grav_anom", **st,
                                      seconds=time.time() - t0)
    del e
    t0 = time.time()
    m = band("rtp", fp)
    me, mn = directional_scaled_gradient(m, fp, sigma_px=3.0)
    np.save(CACHE / "mag_ge.npy", me.astype(np.float16))
    np.save(CACHE / "mag_gn.npy", mn.astype(np.float16))
    del me, mn
    e, st = potential_field_edges(m, fp)
    np.save(CACHE / "mag_edge.npy", e.astype(np.float16))
    rec["layers"]["mag_edge"] = dict(source="training_features band rtp", **st,
                                     seconds=time.time() - t0)
    del e
    t0 = time.time()
    lo = magnetic_lows(m, fp)
    del m
    np.save(CACHE / "mag_low.npy", lo.astype(np.float16))
    rec["layers"]["mag_low"] = dict(
        source="training_features band rtp, 3 km Gaussian residual, negated",
        seconds=time.time() - t0)
    del lo
    t0 = time.time()
    s = scarp_channel(fp)
    np.save(CACHE / "scarp.npy", s.astype(np.float16))
    rec["layers"]["scarp"] = dict(
        source="lidar_scarp_features_u8.tif 0.45 ex_max + 0.35 step_max + 0.20 downface_max (by band name)",
        valid_fraction=float((s[fp] > 0).mean()), seconds=time.time() - t0)
    del s
    receipt_path.write_text(json.dumps(rec, indent=1))
    return rec


def load_layer(name: str) -> np.ndarray:
    return np.load(CACHE / f"{name}.npy").astype(np.float32)


def pixel_evidence(footprint: np.ndarray) -> np.ndarray:
    """Equal-weight mean of the four layers -- the corridor-free per-pixel score."""
    acc = np.zeros(footprint.shape, np.float32)
    for n in LAYERS:
        acc += load_layer(n)
    acc /= np.float32(len(LAYERS))
    acc[~footprint] = 0
    return acc
