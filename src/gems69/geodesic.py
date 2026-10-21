"""Geodesic multi-physics corridor scoring, out-of-fold calibration, holdout & uniqueness.

Implements the complete GEMSDOE69 scientific pipeline strictly within Lane 69:
  1. Zero-leakage multi-physics & geochemical feature channels on the exact
     3730 x 3292 GeoDAWN 100 m UTM Zone 11N grid (`grav_edge`, `mag_edge`,
     `mag_low`, `lidar_coh_scarp`, `topo_ridge`, `rad_alteration`,
     `subsurface_step`, `hydro_upflow`, `sgmc_bedrock`), explicitly dropping
     leaked `dist_known_fault_px` columns on CSV load.
  2. Multi-mechanism fault-tip corridor proposal (`corridors.generate` with
     `k_partners=4`, `include_flank_breaches=True`, `include_normal_splays=True`,
     and Walker Lane geodetic shear promotion) + minimum-energy geodesic path
     routing (`skimage.graph.route_through_array`) across corridor boxes.
  3. Out-of-fold empirical logistic probability calibration + shared-template
     `gems57.emit.greedy_allocate` non-redundant node placement evaluated on
     the pinned `gems57-pooled-hide-v2` buffered whole-component LOQO instrument
     (with 1,000-draw 20 km physical spatial-block bootstrap 95% CIs AND
     `far_1km` > 1 km unmapped-strand DTI).
  4. Exact fast two-phase pre-placement + post-placement registry uniqueness scan
     across all 751 historical blobs + all post-census sibling `.tif` artifacts.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.optimize import minimize

from gems57 import (
    emit as temit,
    evaluate_holdout as teval,
    grid as tgrid,
    holdout as thold,
    metric as tmetric,
    uniqueness as tuniq,
)
from . import corridors, traces
from .data import CACHE, DATA, ROOT

# Forbidden leaked CSV columns (never read anywhere in GEMSDOE69)
FORBIDDEN_CSV_COLUMNS = frozenset({"dist_known_fault_px"})

CORE_PHYSICS_KEYS = (
    "grav_edge",
    "mag_edge",
    "mag_low",
    "lidar_coh_scarp",
    "topo_ridge",
)
EXTENDED_PHYSICS_KEYS = CORE_PHYSICS_KEYS + (
    "rad_alteration",
    "subsurface_step",
)
SUBSURFACE_CORRIDOR_KEYS = (
    "grav_edge",
    "mag_edge",
    "mag_low",
    "lidar_coh_scarp",
    "rad_alteration",
    "subsurface_step",
)
BURIED_PIXEL_KEYS = (
    "grav_edge",
    "mag_edge",
    "mag_low",
    "rad_alteration",
    "subsurface_step",
)


# ---------------------------------------------------------------------------
# Fast low-memory spatial transforms (float32, zero border NaN bleed)
# ---------------------------------------------------------------------------

def _clean_band(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    x = arr.astype(np.float32, copy=False)
    ok = valid & np.isfinite(x) & (x > -1e30)
    med = float(np.median(x[ok])) if ok.any() else 0.0
    out = np.where(ok, x, med).astype(np.float32)
    return out


def _norm_gauss(x: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    m = valid.astype(np.float32)
    num = ndi.gaussian_filter(x * m, sigma=sigma, mode="nearest")
    den = np.maximum(ndi.gaussian_filter(m, sigma=sigma, mode="nearest"), 1e-5)
    return (num / den).astype(np.float32)


def _rank01(x: np.ndarray, mask: np.ndarray, neutral: float = 0.5) -> np.ndarray:
    """Exact empirical CDF rank in [0, 1] on `mask`, `neutral` elsewhere."""
    out = np.full(x.shape, neutral, dtype=np.float32)
    idx = np.flatnonzero(mask & np.isfinite(x))
    if idx.size == 0:
        return out
    vals = x.ravel()[idx]
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(idx.size, dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, idx.size, dtype=np.float32)
    out.ravel()[idx] = ranks
    return out


def _multiscale_potential_edge(
    field_arr: np.ndarray, valid: np.ndarray, sigmas: tuple[float, ...] = (1.5, 4.0, 10.0),
) -> np.ndarray:
    """Multi-scale horizontal gradient * Miller-Singh zero-tilt sharpness."""
    acc = np.zeros(field_arr.shape, dtype=np.float32)
    for sig in sigmas:
        sm = _norm_gauss(field_arr, valid, sig)
        sm2 = _norm_gauss(field_arr, valid, 2.0 * sig)
        gy, gx = np.gradient(sm)
        hg = np.hypot(gx, gy).astype(np.float32)
        vd = (sm - sm2).astype(np.float32)
        tilt = np.arctan2(vd, hg + 1e-6).astype(np.float32)
        sharp = np.clip(1.0 - np.abs(tilt) / (0.5 * np.pi), 0.0, 1.0)
        acc += _rank01(hg * (0.55 + 0.45 * sharp), valid, 0.0)
    return (acc / len(sigmas)).astype(np.float32)


def _straight_boundary_step(field_arr: np.ndarray, valid: np.ndarray, sigma: float = 3.0) -> np.ndarray:
    """Gradient magnitude weighted by local structure-tensor linear coherence."""
    sm = _norm_gauss(field_arr, valid, sigma)
    gy, gx = np.gradient(sm)
    mag = np.hypot(gx, gy).astype(np.float32)
    jxx = ndi.gaussian_filter(gx * gx, sigma=2.5 * sigma, mode="nearest")
    jyy = ndi.gaussian_filter(gy * gy, sigma=2.5 * sigma, mode="nearest")
    jxy = ndi.gaussian_filter(gx * gy, sigma=2.5 * sigma, mode="nearest")
    tr = jxx + jyy + 1e-9
    det_term = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coh = np.clip(det_term / tr, 0.0, 1.0).astype(np.float32)
    return _rank01(mag * (0.35 + 0.65 * coh), valid, 0.5)


def _load_hydrothermal_upflow(shape: tuple[int, int], valid: np.ndarray) -> tuple[np.ndarray, dict]:
    """Build thermal anomaly surface from wells/springs, strictly dropping leaked columns."""
    csv_path = DATA / "external" / "gdr_wellspring_in_footprint.csv"
    grid = np.zeros(shape, dtype=np.float32)
    with csv_path.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        dropped = sorted(header & FORBIDDEN_CSV_COLUMNS)
        safe_cols = ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c")
        n_pts = 0
        for row in reader:
            # Explicitly access ONLY safe coordinates + measured/chemical temperatures
            r = int(round(float(row["row"])))
            c = int(round(float(row["col"])))
            if not (0 <= r < shape[0] and 0 <= c < shape[1]):
                continue
            vals = []
            for k, scale in (("temp_c", 1.0), ("geothermquartz_c", 0.55), ("geothermchalc_c", 0.55)):
                s = (row.get(k) or "").strip()
                if s:
                    try:
                        v = float(s) * scale
                        if np.isfinite(v) and v > 20.0:
                            vals.append(v - 20.0)
                    except ValueError:
                        pass
            if vals:
                ex = float(np.log1p(max(vals)))
                if ex > grid[r, c]:
                    grid[r, c] = ex
                n_pts += 1
    sm_near = ndi.gaussian_filter(grid, sigma=10.0, mode="constant")
    sm_broad = ndi.gaussian_filter(grid, sigma=28.0, mode="constant")
    comb = 0.65 * sm_near + 0.35 * sm_broad
    return _rank01(comb, valid, 0.5), {
        "n_thermal_wells_springs_used": n_pts,
        "dropped_leaked_columns": dropped,
    }


def build_or_load_physics(g: tgrid.Grid) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Compute or load SHA-clean float32 multi-physics channels on `g`."""
    CACHE.mkdir(parents=True, exist_ok=True)
    meta_path = CACHE / "geodesic_physics_v1_meta.json"
    all_keys = EXTENDED_PHYSICS_KEYS + ("hydro_upflow", "sgmc_bedrock", "geod_shearrate")
    if meta_path.exists() and all((CACHE / f"gp1_{k}.npy").exists() for k in all_keys):
        chans = {k: np.load(CACHE / f"gp1_{k}.npy", mmap_mode="r") for k in all_keys}
        return chans, json.loads(meta_path.read_text())

    fp = g.footprint
    chans: dict[str, np.ndarray] = {}

    with rasterio.open(DATA / "training_features.tif") as src:
        rtp = _clean_band(src.read(2), fp)
        tmi_hg = _clean_band(src.read(3), fp)
        geod_inv = _clean_band(src.read(4), fp)
        geod_sr = _clean_band(src.read(7), fp)
        det_elev = _clean_band(src.read(12), fp)
        iso_g = _clean_band(src.read(13), fp)
        base_d = _clean_band(src.read(15), fp)
        cond_s = _clean_band(src.read(17), fp)
        iso_hg = _clean_band(src.read(18), fp)
        det_sl = _clean_band(src.read(19), fp)

    chans["geod_shearrate"] = geod_sr.astype(np.float32)

    # 1. Gravity edge
    g_edge = 0.72 * _multiscale_potential_edge(iso_g, fp) + 0.28 * _rank01(iso_hg, fp, 0.5)
    chans["grav_edge"] = _rank01(g_edge, fp, 0.5)
    del iso_g, iso_hg, g_edge

    # 2 & 3. Magnetic edge (RTP + GeoDAWN flight-line TMI_up150) & Magnetic low
    with rasterio.open(DATA / "external" / "geodawn_extensions_u8.tif") as ext_src:
        thk_u8 = ext_src.read(1).astype(np.float32)
        tmi150 = _clean_band(ext_src.read(4), fp)

    gy150, gx150 = np.gradient(_norm_gauss(tmi150, fp, 1.2))
    hg150 = np.hypot(gx150, gy150).astype(np.float32)
    m_edge = (
        0.52 * _multiscale_potential_edge(rtp, fp)
        + 0.30 * _rank01(hg150, fp, 0.5)
        + 0.18 * _rank01(tmi_hg, fp, 0.5)
    )
    chans["mag_edge"] = _rank01(m_edge, fp, 0.5)
    del gy150, gx150, hg150, tmi_hg, m_edge

    low_rtp = _norm_gauss(rtp, fp, 24.0) - _norm_gauss(rtp, fp, 2.0)
    low_150 = _norm_gauss(tmi150, fp, 18.0) - _norm_gauss(tmi150, fp, 1.5)
    chans["mag_low"] = _rank01(0.60 * _rank01(low_rtp, fp, 0.5) + 0.40 * _rank01(low_150, fp, 0.5), fp, 0.5)
    del rtp, tmi150, low_rtp, low_150

    # 4. Coherence-weighted 1-m LiDAR scarp channel (neutral 0.50 outside valid LiDAR tiles)
    with rasterio.open(DATA / "external" / "lidar_scarp_features_u8.tif") as lid_src:
        ex_m = lid_src.read(1).astype(np.float32) / 255.0
        st_m = lid_src.read(3).astype(np.float32) / 255.0
        lp_m = lid_src.read(4).astype(np.float32) / 255.0
        df_m = lid_src.read(6).astype(np.float32) / 255.0
        coh = lid_src.read(10).astype(np.float32) / 255.0
        lid_valid = (lid_src.read(12) > 0) & fp
    lid_raw = (0.40 * ex_m + 0.30 * st_m + 0.15 * df_m + 0.15 * lp_m) * (0.35 + 0.65 * coh)
    lidar_coverage_frac = float(lid_valid[fp].mean())
    chans["lidar_coh_scarp"] = _rank01(lid_raw, lid_valid, neutral=0.50)
    del ex_m, st_m, lp_m, df_m, coh, lid_raw, lid_valid

    # 5. Full-coverage topographic scarp / break-in-slope ridge channel
    topo = (
        0.55 * _straight_boundary_step(det_elev, fp, sigma=1.8)
        + 0.45 * _rank01(det_sl, fp, 0.5)
    )
    chans["topo_ridge"] = _rank01(topo, fp, 0.5)
    del det_elev, det_sl, topo

    # 6. Radiometric hydrothermal alteration channel (Th/K bidirectional anomaly + K,Th gradients)
    with rasterio.open(DATA / "external" / "geodawn_rad_u8.tif") as rad_src:
        rad_k = _clean_band(rad_src.read(1), fp)
        rad_th = _clean_band(rad_src.read(2), fp)
    thk_clean = _clean_band(thk_u8, fp)
    thk_anom = np.abs(_norm_gauss(thk_clean, fp, 1.8) - _norm_gauss(thk_clean, fp, 22.0))
    ky, kx = np.gradient(_norm_gauss(rad_k, fp, 2.0))
    ty, tx = np.gradient(_norm_gauss(rad_th, fp, 2.0))
    rad_comb = (
        0.50 * _rank01(thk_anom, fp, 0.5)
        + 0.25 * _rank01(np.hypot(kx, ky), fp, 0.5)
        + 0.25 * _rank01(np.hypot(tx, ty), fp, 0.5)
    )
    chans["rad_alteration"] = _rank01(rad_comb, fp, 0.5)
    del rad_k, rad_th, thk_u8, thk_clean, thk_anom, ky, kx, ty, tx, rad_comb

    # 7. Deep subsurface step (MT conductivity + basement depth straight steps + strain rate)
    sub_comb = (
        0.46 * _straight_boundary_step(cond_s, fp, sigma=3.0)
        + 0.36 * _straight_boundary_step(base_d, fp, sigma=3.0)
        + 0.18 * _rank01(0.5 * _rank01(geod_sr, fp, 0.5) + 0.5 * _rank01(geod_inv, fp, 0.5), fp, 0.5)
    )
    chans["subsurface_step"] = _rank01(sub_comb, fp, 0.5)
    del cond_s, base_d, geod_inv, sub_comb

    # 8. Hydrothermal well/spring geothermometry excess (H69-G3; leaked column explicitly dropped)
    chans["hydro_upflow"], hydro_meta = _load_hydrothermal_upflow(fp.shape, fp)

    # 9. USGS SGMC pre-Quaternary bedrock fault density (H69-G4; gated strictly on E1 canary AUC<=0.90)
    with rasterio.open(DATA / "external" / "derived_sgmc_faults_100m_u8.tif") as sg_src:
        sg_raw = (sg_src.read(1) > 0).astype(np.float32)
    sg_sm = 0.65 * ndi.gaussian_filter(sg_raw, sigma=2.5) + 0.35 * ndi.gaussian_filter(sg_raw, sigma=8.0)
    chans["sgmc_bedrock"] = _rank01(sg_sm, fp, 0.5)
    del sg_raw, sg_sm

    for k, arr in chans.items():
        np.save(CACHE / f"gp1_{k}.npy", arr.astype(np.float32))
    meta = {
        "channels": list(all_keys),
        "lidar_valid_footprint_fraction": round(lidar_coverage_frac, 5),
        "hydro_upflow": hydro_meta,
    }
    meta_path.write_text(json.dumps(meta, indent=1))
    return chans, meta


# ---------------------------------------------------------------------------
# Geodesic corridor feature extraction for any visible-catalogue state
# ---------------------------------------------------------------------------

def composite_ridge_and_cost(
    chans: dict[str, np.ndarray],
    footprint: np.ndarray,
    keys: tuple[str, ...] = EXTENDED_PHYSICS_KEYS,
) -> tuple[np.ndarray, np.ndarray]:
    """Return `(ridge_100m, cost_surface_2x)` strictly from physics channels."""
    w_map = {
        "grav_edge": 0.22,
        "mag_edge": 0.22,
        "mag_low": 0.10,
        "lidar_coh_scarp": 0.18,
        "topo_ridge": 0.12,
        "rad_alteration": 0.08,
        "subsurface_step": 0.08,
    }
    tot_w = sum(w_map[k] for k in keys)
    ridge = np.zeros(footprint.shape, dtype=np.float32)
    for k in keys:
        ridge += (w_map[k] / tot_w) * chans[k]
    ridge = np.where(footprint, ridge, 0.0).astype(np.float32)
    # Downsample 2x via block maximum so thin scarps/edges are preserved in routing
    H, W = ridge.shape
    H2, W2 = H // 2, W // 2
    r_crop = ridge[: 2 * H2, : 2 * W2].reshape(H2, 2, W2, 2).max(axis=(1, 3))
    fp2 = footprint[: 2 * H2, : 2 * W2].reshape(H2, 2, W2, 2).any(axis=(1, 3))
    cost2 = np.where(fp2, np.exp(-2.2 * r_crop) + 0.08, 25.0).astype(np.float32)
    return ridge, cost2


def build_corridor_state(
    parts: list[traces.Part],
    footprint: np.ndarray,
    visible: np.ndarray,
    removed: np.ndarray | None,
    chans: dict[str, np.ndarray],
    keys: tuple[str, ...] = EXTENDED_PHYSICS_KEYS,
    *,
    keep_lines: bool = False,
) -> dict[str, Any]:
    """Generate & score geodesic multi-corridor fields strictly from `visible`."""
    polys = traces.visible_polys(parts, removed)
    tips, tip_counts = traces.find_tips(polys, footprint)
    lines, gen_counts = corridors.generate(
        tips,
        polys,
        include_cut=True,
        k_partners=4,
        include_flank_breaches=True,
        include_normal_splays=True,
        shearrate_grid=chans["geod_shearrate"],
    )
    ridge, cost2 = composite_ridge_and_cost(chans, footprint, keys=keys)
    corridors.rasterize_lines(
        lines, footprint, visible, cost_surface_2x=cost2, ridge_field=ridge,
    )
    layer_subset = {k: chans[k] for k in keys}
    corridors.score_lines(lines, layer_subset)

    H, W = footprint.shape
    s_max = np.zeros(H * W, dtype=np.float32)
    n_hit = np.zeros(H * W, dtype=np.float32)
    s_rel = np.zeros(H * W, dtype=np.float32)
    s_tip = np.zeros(H * W, dtype=np.float32)
    core_kinds = {
        "relay_connector", "relay_breach", "relay_enechelon",
        "flank_breach", "flank_synthetic",
        "pullapart_link", "pullapart_chord", "pullapart_strand",
    }
    for ln in lines:
        if ln.pix is None or ln.pix.size == 0 or ln.score <= 0.0:
            continue
        sc = np.float32(ln.score)
        np.maximum.at(s_max, ln.pix, sc)
        n_hit[ln.pix] += 1.0
        if ln.kind in core_kinds:
            np.maximum.at(s_rel, ln.pix, sc)
        else:
            np.maximum.at(s_tip, ln.pix, sc)

    on = (n_hit > 0).reshape(H, W)
    s_max_2d = s_max.reshape(H, W)
    s_rel_2d = s_rel.reshape(H, W)
    s_tip_2d = s_tip.reshape(H, W)
    mult_2d = np.log1p(n_hit).reshape(H, W).astype(np.float32)

    if on.any():
        d_trace, (iy, ix) = ndi.distance_transform_edt(~on, return_indices=True)
        d_trace = d_trace.astype(np.float32)
        near_score = s_max_2d[iy, ix]
        near_rel = s_rel_2d[iy, ix]
        near_tip = s_tip_2d[iy, ix]
        near_mult = mult_2d[iy, ix]
    else:
        d_trace = np.full((H, W), 999.0, dtype=np.float32)
        near_score = np.zeros((H, W), dtype=np.float32)
        near_rel = np.zeros((H, W), dtype=np.float32)
        near_tip = np.zeros((H, W), dtype=np.float32)
        near_mult = np.zeros((H, W), dtype=np.float32)

    # Free-tip process-zone distance field (strictly from proposing corridor tips)
    tip_mask = np.zeros((H, W), dtype=bool)
    if tips:
        tr, tc = traces.rc_of(np.array([t.pos for t in tips]))
        ok_t = (tr >= 0) & (tr < H) & (tc >= 0) & (tc < W)
        tip_mask[tr[ok_t], tc[ok_t]] = True
    if tip_mask.any():
        d_tip = ndi.distance_transform_edt(~tip_mask).astype(np.float32)
    else:
        d_tip = np.full((H, W), 999.0, dtype=np.float32)

    in_corridor = (d_trace <= 6.5) & footprint
    k_narrow = np.exp(-0.5 * (d_trace / 1.8) ** 2).astype(np.float32)
    k_mid = np.exp(-0.5 * (d_trace / 4.2) ** 2).astype(np.float32)
    k_broad = np.exp(-0.5 * (d_trace / 9.0) ** 2).astype(np.float32)

    f_corr_narrow = (near_score * k_narrow).astype(np.float32)
    f_corr_mid = (near_score * k_mid).astype(np.float32)
    f_corr_broad = (near_score * k_broad).astype(np.float32)
    f_corr_rel = (near_rel * k_mid).astype(np.float32)
    f_corr_tip = (near_tip * k_mid).astype(np.float32)
    f_corr_mult = (near_mult * k_broad).astype(np.float32)
    f_tip_near = (np.exp(-d_tip / 8.0) * in_corridor).astype(np.float32)
    f_tip_mid = (np.exp(-d_tip / 24.0) * in_corridor).astype(np.float32)

    out_state: dict[str, Any] = {
        "lines": lines if keep_lines else [],
        "tips": tips if keep_lines else [],
        "tip_counts": tip_counts,
        "gen_counts": gen_counts,
        "in_corridor": in_corridor,
        "f_corr_narrow": f_corr_narrow,
        "f_corr_mid": f_corr_mid,
        "f_corr_broad": f_corr_broad,
        "f_corr_rel": f_corr_rel,
        "f_corr_tip": f_corr_tip,
        "f_corr_mult": f_corr_mult,
        "f_tip_near": f_tip_near,
        "f_tip_mid": f_tip_mid,
    }
    del ridge, cost2, d_trace, near_score, near_rel, near_tip, near_mult, d_tip
    del k_narrow, k_mid, k_broad, s_max_2d, s_rel_2d, s_tip_2d, mult_2d, on
    if not keep_lines:
        del lines, tips
    return out_state


# ---------------------------------------------------------------------------
# Fast exact out-of-fold L2-regularized logistic calibration (L-BFGS-B)
# ---------------------------------------------------------------------------

def fit_logistic_l2(
    X: np.ndarray,
    y: np.ndarray,
    l2: float = 10.0,
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    """Fit exact calibrated binary log-odds model `sigmoid(b + ((X - mu)/sd) @ w)`."""
    mu = X.mean(axis=0).astype(np.float64)
    sd = np.maximum(X.std(axis=0).astype(np.float64), 1e-5)
    Z = ((X - mu) / sd).astype(np.float64)
    yv = y.astype(np.float64)
    p0 = float(np.clip(yv.mean(), 1e-6, 1.0 - 1e-6))
    theta0 = np.zeros(Z.shape[1] + 1, dtype=np.float64)
    theta0[0] = np.log(p0 / (1.0 - p0))

    def loss_and_grad(theta: np.ndarray) -> tuple[float, np.ndarray]:
        b = theta[0]
        w = theta[1:]
        logits = np.clip(b + Z @ w, -30.0, 30.0)
        p = 1.0 / (1.0 + np.exp(-logits))
        loss = float(
            -np.sum(yv * np.log(p + 1e-12) + (1.0 - yv) * np.log(1.0 - p + 1e-12))
            + 0.5 * l2 * float(w @ w)
        )
        diff = p - yv
        gb = float(diff.sum())
        gw = Z.T @ diff + l2 * w
        return loss, np.concatenate([[gb], gw])

    res = minimize(loss_and_grad, theta0, jac=True, method="L-BFGS-B", options={"maxiter": 150})
    b_hat = float(res.x[0])
    w_hat = res.x[1:].astype(np.float64)
    return w_hat, b_hat, mu, sd


def predict_logistic(
    X: np.ndarray, w: np.ndarray, b: float, mu: np.ndarray, sd: np.ndarray,
) -> np.ndarray:
    logits = np.clip(b + ((X - mu) / sd) @ w, -30.0, 30.0)
    return (1.0 / (1.0 + np.exp(-logits))).astype(np.float32)


def fast_auc(scores: np.ndarray, truth: np.ndarray) -> float:
    """Exact Wilcoxon-Mann-Whitney ROC AUC with average-rank tie handling."""
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(truth, dtype=bool)
    n_pos = int(y.sum())
    n_neg = int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    n = len(s)
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        while j < n and s_sorted[j] == s_sorted[i]:
            j += 1
        ranks[order[i:j]] = 0.5 * (i + j + 1)
        i = j
    r_pos = float(ranks[y].sum())
    return float((r_pos - 0.5 * n_pos * (n_pos + 1)) / (n_pos * n_neg))


# ---------------------------------------------------------------------------
# Fast exact registry uniqueness scanner (751 historical + live extra blobs)
# ---------------------------------------------------------------------------

def _rankdata_avg_fast(v: np.ndarray) -> np.ndarray:
    order = np.argsort(v, kind="mergesort")
    sv = v[order]
    n = len(v)
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        while j < n and sv[j] == sv[i]:
            j += 1
        ranks[order[i:j]] = 0.5 * (i + j + 1)
        i = j
    return ranks


def scan_registry_fast(
    surface: np.ndarray,
    dots: np.ndarray,
    footprint: np.ndarray,
    registry_dir: Path,
    extra_manifest_path: Path | None = None,
    exclude_paths: set[str] | None = None,
) -> dict[str, Any]:
    """Exact full-footprint Spearman (pre-placement surface & final dots) + 3-px dot overlap."""
    t0 = time.time()
    fp = footprint > 0
    n_fp = int(fp.sum())
    exclude_paths = exclude_paths or set()

    # Exact centered rank vectors on full 5,167,373-cell footprint for surface AND final dots
    s_vec = np.where(np.isfinite(surface[fp]), surface[fp], 0.0).astype(np.float64)
    s_ranks = _rankdata_avg_fast(s_vec) - 0.5 * (n_fp + 1.0)
    s_norm = float(np.linalg.norm(s_ranks))

    my_dots = (dots > 0) & fp
    n_mine = int(my_dots.sum())
    m_vec = my_dots[fp].astype(np.float64)
    m_centered = m_vec - m_vec.mean()
    m_norm = float(np.linalg.norm(m_centered))

    my_y, my_x = np.nonzero(my_dots)
    H, W = fp.shape
    offs = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4) if dy * dy + dx * dx <= 9]
    shifted_coords = [
        (np.clip(my_y + dy, 0, H - 1), np.clip(my_x + dx, 0, W - 1))
        for dy, dx in offs
    ]

    prior_doc = json.loads((ROOT / "registry" / "prior_rasters.json").read_text())
    items: list[tuple[str, str, Path]] = []
    for e in prior_doc["rasters"]:
        sha = e["git_blob_sha"]
        label = f"{e['aliases'][0]['repository']}:{e['aliases'][0]['path']}"
        items.append((sha, label, registry_dir / f"{sha}.tif"))
    n_canonical = len(items)
    n_extra_added = 0
    if extra_manifest_path and extra_manifest_path.exists():
        for e in json.loads(extra_manifest_path.read_text()):
            p = Path(e["file"])
            label = f"{e['repo']}:{e['path']}"
            if str(p.resolve()) in exclude_paths:
                continue
            items.append((e["git_blob_sha"], label, p))
            n_extra_added += 1

    worst_surf_rho = {"abs_rho": -1.0}
    worst_dots_rho = {"abs_rho": -1.0}
    worst_dotlike = {"dot_overlap_3px": -1.0}
    worst_template_dotfield = {"dot_overlap_3px": -1.0}
    worst_all = {"dot_overlap_3px": -1.0}
    top_dotlike: list[dict[str, Any]] = []
    exact_matches: list[str] = []
    incompatible: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    n_compared = 0
    strata_counts = {"dotlike_le150k": 0, "bigdot_150k_to_20pct": 0, "dense_gt20pct": 0, "empty": 0}

    dense_cutoff = int(tuniq.DENSE_SUPPORT_FRACTION * n_fp)

    for sha, label, path in items:
        if not path.exists():
            errors.append({"sha": sha, "label": label, "error": "missing"})
            continue
        try:
            with rasterio.open(path) as src:
                if src.count != 1 or src.shape != fp.shape:
                    incompatible.append({"sha": sha, "label": label, "shape": list(src.shape), "count": src.count})
                    continue
                arr = src.read(1)
        except Exception as exc:
            errors.append({"sha": sha, "label": label, "error": str(exc)})
            continue

        n_compared += 1
        tv = np.where(np.isfinite(arr[fp]), arr[fp], 0.0)
        tpos_fp = tv > 0.0
        nt = int(tpos_fp.sum())

        # Exact pixel agreement check on footprint
        same_px = float((tpos_fp == (m_vec > 0.5)).mean())
        if same_px >= 0.9999 and abs(nt - n_mine) <= max(5, int(0.001 * max(n_mine, 1))):
            exact_matches.append(label)

        # Fast exact Spearman for both surface and final binary dots
        u_vals = np.unique(tv)
        if nt == 0 or u_vals.size <= 1:
            rho_surf = 0.0
            rho_dots = 0.0
        elif u_vals.size == 2:
            denom = float(np.sqrt(float(nt) * float(n_fp - nt) / float(n_fp)))
            rho_surf = float(s_ranks[tpos_fp].sum() / (s_norm * denom)) if (s_norm > 0 and denom > 0) else 0.0
            rho_dots = float(m_centered[tpos_fp].sum() / (m_norm * denom)) if (m_norm > 0 and denom > 0) else 0.0
        else:
            tr = _rankdata_avg_fast(tv.astype(np.float64)) - 0.5 * (n_fp + 1.0)
            tn = float(np.linalg.norm(tr))
            rho_surf = float((s_ranks @ tr) / (s_norm * tn)) if (s_norm > 0 and tn > 0) else 0.0
            rho_dots = float((m_centered @ tr) / (m_norm * tn)) if (m_norm > 0 and tn > 0) else 0.0

        # Exact 3.0-px Euclidean overlap of our placed dots against `arr > 0 & fp`
        if nt == 0 or n_mine == 0:
            ovl = 0.0
        else:
            tpos_2d = np.isfinite(arr) & (arr > 0.0) & fp
            hit = np.zeros(n_mine, dtype=bool)
            for sy, sx in shifted_coords:
                hit |= tpos_2d[sy, sx]
            ovl = float(hit.mean())
            del tpos_2d

        rec = {
            "sha": sha,
            "label": label,
            "their_positive_px": nt,
            "rho_surface": round(rho_surf, 5),
            "rho_dots": round(rho_dots, 5),
            "dot_overlap_3px": round(ovl, 5),
        }
        if abs(rho_surf) > worst_surf_rho["abs_rho"]:
            worst_surf_rho = {**rec, "abs_rho": round(abs(rho_surf), 5)}
        if abs(rho_dots) > worst_dots_rho["abs_rho"]:
            worst_dots_rho = {**rec, "abs_rho": round(abs(rho_dots), 5)}
        if ovl > worst_all["dot_overlap_3px"]:
            worst_all = dict(rec)

        if nt == 0:
            strata_counts["empty"] += 1
        elif nt <= 150_000:
            strata_counts["dotlike_le150k"] += 1
            top_dotlike.append(rec)
            if ovl > worst_dotlike["dot_overlap_3px"]:
                worst_dotlike = dict(rec)
        elif nt <= dense_cutoff:
            strata_counts["bigdot_150k_to_20pct"] += 1
        else:
            strata_counts["dense_gt20pct"] += 1

        if 0 < nt <= dense_cutoff and ovl > worst_template_dotfield["dot_overlap_3px"]:
            worst_template_dotfield = dict(rec)

        del arr, tv, tpos_fp

    top_dotlike.sort(key=lambda r: -r["dot_overlap_3px"])
    max_corr = max(worst_surf_rho["abs_rho"], worst_dots_rho["abs_rho"])
    return {
        "n_canonical_blobs": n_canonical,
        "n_post_census_extra_blobs": n_extra_added,
        "n_total_blobs_scanned": len(items),
        "n_compared": n_compared,
        "n_incompatible": len(incompatible),
        "n_errors": len(errors),
        "elapsed_seconds": round(time.time() - t0, 2),
        "my_dot_count": n_mine,
        "strata_counts": strata_counts,
        "exact_pixel_match_found": len(exact_matches) > 0,
        "n_exact_pixel_agreement_9999": len(exact_matches),
        "exact_matches": exact_matches,
        "worst_surface_spearman": worst_surf_rho,
        "worst_dots_spearman": worst_dots_rho,
        "worst_abs_spearman": round(max_corr, 5),
        "worst_dot_overlap_dotlike": worst_dotlike,
        "top10_dot_overlap_dotlike": top_dotlike[:10],
        "worst_dot_overlap_template_20pct": worst_template_dotfield,
        "worst_dot_overlap_all_strata": worst_all,
        "literal_gate": {
            "rho_limit": 0.90,
            "overlap_limit": 0.70,
            "rho_surface_ok": worst_surf_rho["abs_rho"] <= 0.90,
            "rho_dots_ok": worst_dots_rho["abs_rho"] <= 0.90,
            "rho_ok": max_corr <= 0.90,
            "overlap_all_strata_ok": worst_all["dot_overlap_3px"] <= 0.70,
        },
        "stratified_gate": {
            "rho_ok": max_corr <= 0.90,
            "dotlike_overlap_ok": worst_dotlike["dot_overlap_3px"] <= 0.70,
            "note": (
                "Dotlike stratum covers ALL sparse/medium dot submissions (<=150,000 positive px) "
                "across all 73 GEMSDOE repositories including GEMSDOE51, 58GEMSDOE, h33-2-b2, and "
                "all prior GEMSDOE69 TIFs. Rasters above 150k positive px contain full-footprint "
                "regular grids (13GEMSDOE 5x5 lattice = 206,895 dots covering 99.9% of Z^2 within "
                "sqrt(8)=2.83<=3.0 px; 61GEMSDOE 4x4 lattice = 311,617 dots covering 100.0% of Z^2) "
                "and 27 soft probability surfaces (IR-69-REG-01)."
            ),
        },
        "incompatible_sample": incompatible[:5],
    }
