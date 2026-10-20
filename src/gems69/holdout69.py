"""Holdout pipeline for Lane 69 (reuses the shared template fold instrument
byte-pinned in vendor/gems57 and vendor/template66; zero private DTI math).

Compares four strictly leak-free arms on identical spatial folds:
  * h69_e            : Core Lane-69 kinematics-resolved geodesic corridor priors
                       + core multi-physics layers (out-of-fold calibrated)
  * h69_efg          : Extended H69-E + basement/conductivity step + flank-diff
                       radiometric K/Th + physical thermal conduit priors
  * no_prior_control : Identical classifier, physics layers, allowed mask, and
                       greedy_allocate budget with ALL corridor features removed
  * corridor / control (direct propensity API preserved for unit tests & ablation)

Fixes three defects found in the prior repository pass:
  - IR-69-HOLDOUT-01: flank exclusion mask computed strictly from `visible`,
                      never from full `ctx.grid.catalogue` (which masked truth!).
  - IR-69-HOLDOUT-02: `leakage_canary` builds corridors strictly from `visible`
                      (`catalogue & ~hidden_draw20`), never full `catalogue`.
  - IR-69-HOLDOUT-03: `hardlinked_recovery` calls repaired `build_tip_pairs`
                      directly instead of skipping 100% of pairs on a stray sign.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from gems57 import grid as tgrid
from gems57 import holdout as thold
from gems57.emit import greedy_allocate
from gems57.metric import ALPHA, BETA, EPS

from .corridors import build_corridors, build_tip_pairs, corridor_from_pair
from .physics import (
    TRANSFORM_NAMES,
    build_admittance_surface,
    build_z_stack,
    corridor_evidence_from_z,
    load_lidar_strike_deg,
)
from .scoring import (
    S0_DEFAULT,
    build_corridor_fields,
    build_propensity,
    score_corridor,
)
from .tips import attach_catalogue_kinematics, vectorize

ROOT = Path(__file__).resolve().parents[2]
FLANK_PX = 2  # 200 m visible-catalogue flank exclusion, matching h33-2-b2

CORE_PHYSICS_COLS = [
    "grav_upward_edge", "grav_hg_s1", "grav_hg_s2", "grav_hg_s4",
    "grav_tilt_s2", "grav_hg_prov", "grav_vg_prov",
    "mag_upward_edge", "mag_hg_s1", "mag_hg_s2", "mag_hg_s4",
    "mag_tilt_s2", "mag_hg_prov", "mag_vg_prov", "tc_prov",
    "mag_low_rtp_res", "mag_low_tmi", "mag_low_rtp",
    "lidar_scarp", "elev_curv_ridge", "det_elev_slope",
    "geod_2ndinv", "geod_shear", "geod_dilat",
]
EXT_PHYSICS_COLS = [
    "basement_step", "cond_step", "rad_kth_contrast", "thermal_conduit",
]
CORRIDOR_COLS = [
    "corridor_propensity", "corridor_core_weight", "corridor_phase",
    "corridor_multiplicity", "neg_dist_corridor_trace",
]


def load_template_grid():
    return tgrid.load_grid(data_dir=ROOT / "data" / "bridge")


def _footprint_from_shape(shape):
    g = load_template_grid()
    return g.footprint


def corridor_pipeline(
    catalogue: np.ndarray,
    shape: tuple[int, int],
    stats: dict,
    max_corridors: int = 2200,
    zstack: dict | None = None,
    footprint: np.ndarray | None = None,
    include_extended: bool = True,
    admit: np.ndarray | None = None,
    lidar_orient: tuple[np.ndarray, np.ndarray] | None = None,
    both_variants: bool = False,
) -> dict:
    """Leak-free visible-catalogue -> tip kinematics -> geodesic corridors -> score."""
    if footprint is None:
        footprint = _footprint_from_shape(shape)
    if zstack is None:
        zstack = build_z_stack(footprint, stats)
    t0 = time.time()
    strands = vectorize(catalogue)
    kin = attach_catalogue_kinematics(strands, catalogue)
    if admit is None:
        admit = build_admittance_surface(zstack, footprint)
    if lidar_orient is None:
        lidar_orient = load_lidar_strike_deg(footprint)
    st_deg, coh01 = lidar_orient
    corridors, pairs = build_corridors(
        catalogue, strands, shape, max_corridors=max_corridors,
        kinematics=kin, admittance=admit, include_terminations=True,
        max_terminations=700,
    )
    evs = [corridor_evidence_from_z(zstack, c, st_deg, coh01) for c in corridors]
    fields_e = None
    if both_variants:
        for c, ev in zip(corridors, evs):
            score_corridor(c, ev, include_extended=False)
        fields_e = build_corridor_fields(corridors, shape)
    for c, ev in zip(corridors, evs):
        score_corridor(c, ev, include_extended=include_extended)
    fields = build_corridor_fields(corridors, shape)
    return dict(
        strands=len(strands),
        pairs=len(pairs),
        corridors=len(corridors),
        propensity=fields["corridor_propensity"],
        fields=fields,
        fields_e=fields_e if both_variants else fields,
        corridors_obj=corridors,
        admittance=admit,
        score_seconds=round(time.time() - t0, 2),
    )


def emit_dots(p: np.ndarray, allowed: np.ndarray, k_truth: int,
              floor: float = 0.008, max_dots: int = 250_000) -> np.ndarray:
    """Calibrated greedy marginal-DTI dot placement (shared template allocator)."""
    alloc = greedy_allocate(
        np.asarray(p, np.float32), allowed, int(max(k_truth, 1)),
        floor=floor, max_dots=max_dots, candidate_cap=350_000,
    )
    return alloc.emitted


def cell_allowed(cell, shape) -> np.ndarray:
    full = np.zeros(shape, bool)
    full[cell.bbox] = cell.active
    return full


def _extract_matrix(
    zstack: dict, cfields: dict | None, phys_cols: list[str],
    ys: np.ndarray, xs: np.ndarray,
) -> np.ndarray:
    cols = []
    for name in phys_cols:
        v = zstack[name][ys, xs].astype(np.float32)
        cols.append(np.where(np.isfinite(v), v, np.nan))
    if cfields is not None:
        for name in CORRIDOR_COLS:
            cols.append(cfields[name][ys, xs].astype(np.float32))
    return np.column_stack(cols)


def _fit_oof_calibrator(X_tr: np.ndarray, y_tr: np.ndarray, true_prior: float, seed: int = 69):
    clf = HistGradientBoostingClassifier(
        max_iter=95,
        learning_rate=0.055,
        max_leaf_nodes=23,
        min_samples_leaf=120,
        l2_regularization=6.0,
        random_state=seed,
    )
    clf.fit(X_tr, y_tr)
    sample_prior = float(np.clip(y_tr.mean(), 1e-6, 1.0 - 1e-6))
    odds_scale = (true_prior / max(1.0 - true_prior, 1e-6)) / (sample_prior / (1.0 - sample_prior))
    return clf, float(odds_scale)


def _predict_calibrated(clf, odds_scale: float, X: np.ndarray) -> np.ndarray:
    raw = np.clip(clf.predict_proba(X)[:, 1], 1e-6, 1.0 - 1e-6)
    odds = (raw / (1.0 - raw)) * odds_scale
    return (odds / (1.0 + odds)).astype(np.float32)


def _predict_allowed_chunked(
    clf, odds_scale: float, zstack: dict, cfields_crop: dict | None,
    bbox: tuple[slice, slice], phys_cols: list[str],
    ay: np.ndarray, ax: np.ndarray, shape: tuple[int, int], step: int = 220_000,
) -> np.ndarray:
    out = np.zeros(shape, np.float32)
    r0 = bbox[0].start
    c0 = bbox[1].start
    for i0 in range(0, len(ay), step):
        ys_c, xs_c = ay[i0:i0 + step], ax[i0:i0 + step]
        cols = []
        for name in phys_cols:
            v = zstack[name][ys_c, xs_c].astype(np.float32)
            cols.append(np.where(np.isfinite(v), v, np.nan))
        if cfields_crop is not None:
            ly_c, lx_c = ys_c - r0, xs_c - c0
            for name in CORRIDOR_COLS:
                cols.append(cfields_crop[name][ly_c, lx_c].astype(np.float32))
        Xc = np.column_stack(cols)
        out[ys_c, xs_c] = _predict_calibrated(clf, odds_scale, Xc)
    return out


def pooled_bootstrap_summary(
    per_cell: dict[str, dict], n_boot: int = 5000, seed: int = 69,
) -> dict:
    """Exact pooled DTI + 5,000-resample spatial-block bootstrap 95% CI."""
    keys = sorted(per_cell.keys())
    tps = np.array([per_cell[k]["tp"] for k in keys], float)
    fps = np.array([per_cell[k]["fp"] for k in keys], float)
    fns = np.array([per_cell[k]["fn"] for k in keys], float)
    dtis = np.array([per_cell[k]["dti"] for k in keys], float)
    tp_s, fp_s, fn_s = float(tps.sum()), float(fps.sum()), float(fns.sum())
    pooled = float(tp_s / (tp_s + ALPHA * fp_s + BETA * fn_s + EPS))

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    b_tp = tps[idx].sum(axis=1)
    b_fp = fps[idx].sum(axis=1)
    b_fn = fns[idx].sum(axis=1)
    b_dti = b_tp / (b_tp + ALPHA * b_fp + BETA * b_fn + EPS)
    lo, hi = np.percentile(b_dti, [2.5, 97.5])
    return dict(
        pooled_dti=round(pooled, 6),
        mean_cell_dti=round(float(dtis.mean()), 6),
        std_cell_dti=round(float(dtis.std(ddof=1)) if len(dtis) > 1 else 0.0, 6),
        boot_ci95=[round(float(lo), 6), round(float(hi), 6)],
        pooled_tp=round(tp_s, 3),
        pooled_fp=round(fp_s, 3),
        pooled_fn=round(fn_s, 3),
        total_withheld_truth_px=int(sum(per_cell[k]["n_truth"] for k in keys)),
        total_emitted_dots=int(sum(per_cell[k]["n_emitted"] for k in keys)),
        n_cells=len(keys),
        per_cell_dti={k: round(float(per_cell[k]["dti"]), 6) for k in keys},
    )


def paired_bootstrap_diff(
    cell_a: dict[str, dict], cell_b: dict[str, dict], n_boot: int = 5000, seed: int = 69,
) -> dict:
    """Paired spatial-block bootstrap CI for pooled DTI(arm_a) - DTI(arm_b)."""
    keys = sorted(cell_a.keys())
    tpa = np.array([cell_a[k]["tp"] for k in keys], float)
    fpa = np.array([cell_a[k]["fp"] for k in keys], float)
    fna = np.array([cell_a[k]["fn"] for k in keys], float)
    tpb = np.array([cell_b[k]["tp"] for k in keys], float)
    fpb = np.array([cell_b[k]["fp"] for k in keys], float)
    fnb = np.array([cell_b[k]["fn"] for k in keys], float)

    da = float(tpa.sum() / (tpa.sum() + ALPHA * fpa.sum() + BETA * fna.sum() + EPS))
    db = float(tpb.sum() / (tpb.sum() + ALPHA * fpb.sum() + BETA * fnb.sum() + EPS))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    ba = tpa[idx].sum(1) / (tpa[idx].sum(1) + ALPHA * fpa[idx].sum(1) + BETA * fna[idx].sum(1) + EPS)
    bb = tpb[idx].sum(1) / (tpb[idx].sum(1) + ALPHA * fpb[idx].sum(1) + BETA * fnb[idx].sum(1) + EPS)
    diff = ba - bb
    lo, hi = np.percentile(diff, [2.5, 97.5])
    cell_diffs = [cell_a[k]["dti"] - cell_b[k]["dti"] for k in keys]
    return dict(
        pooled_delta_dti=round(da - db, 6),
        boot_ci95=[round(float(lo), 6), round(float(hi), 6)],
        p_a_gt_b=round(float((diff > 0).mean()), 4),
        wins_over_cells=f"{sum(d > 0 for d in cell_diffs)}/{len(keys)}",
        per_cell_delta={k: round(float(cell_a[k]["dti"] - cell_b[k]["dti"]), 6) for k in keys},
    )


def run_spatial_oof_benchmark(
    ctx,
    stats: dict,
    modes: tuple[str, ...] = ("all", "detached"),
    flank_px: int = FLANK_PX,
    zstack: dict | None = None,
    neg_per_cell: int = 30_000,
    seed: int = 69,
) -> dict:
    """Run leak-free Leave-One-Quadrant-Out calibration + evaluation across modes.

    Every catalogue-derived corridor feature on cell `c` uses ONLY `ctx.visible(c.key)`
    and `offcat_vis = dist(visible_c) > flank_px` (never `ctx.grid.catalogue`).
    """
    fp = ctx.grid.footprint
    shape = fp.shape
    if zstack is None:
        zstack = build_z_stack(fp, stats)

    arms = ("h69_e", "h69_efg", "no_prior_control", "uncalibrated_corridor", "uncalibrated_control")
    out_by_mode: dict[str, dict] = {}
    trained_live_data = {"X_e": [], "X_efg": [], "y": [], "priors": []}

    # Precompute uncalibrated direct-physics control surface (legacy comparison)
    ctrl_layers = [
        "grav_upward_edge", "grav_hg_s2", "grav_tilt_s2",
        "mag_upward_edge", "mag_hg_s2", "mag_low_rtp_res", "lidar_scarp",
    ]
    C = np.zeros(shape, np.float32)
    for name in ctrl_layers:
        z = zstack[name].astype(np.float32)
        C += np.where(np.isfinite(z), z, 0.0)
    C /= len(ctrl_layers)
    p_ctrl_raw = np.where(fp, 1.0 / (1.0 + np.exp(-1.5 * (C - S0_DEFAULT))), 0.0).astype(np.float32)

    admit = build_admittance_surface(zstack, fp)
    lidar_orient = load_lidar_strike_deg(fp)

    for mode in modes:
        mode_cells = [c for c in ctx.cells if c.mode == mode]
        seeds_present = sorted({c.seed for c in mode_cells})
        per_arm_cells: dict[str, dict[str, dict]] = {a: {} for a in arms}
        cell_cache = {}

        # Step 1: leak-free per-cell feature extraction strictly from `visible`
        import gc
        for cell in mode_cells:
            t_c = time.time()
            visible = ctx.visible(cell.key)
            offcat_vis = ndi.distance_transform_edt(~visible) > flank_px
            allowed = cell_allowed(cell, shape) & offcat_vis
            truth = np.zeros(shape, bool)
            truth[cell.bbox][cell.truth_yx] = True
            truth &= allowed

            pipe_efg = corridor_pipeline(
                visible, shape, stats, zstack=zstack, footprint=fp,
                include_extended=True, admit=admit, lidar_orient=lidar_orient,
                both_variants=True,
            )

            py, px = np.nonzero(truth)
            ny_all, nx_all = np.nonzero(allowed & ~truth)
            rng = np.random.default_rng(seed * 1000 + cell.seed * 10 + cell.fold)
            take = min(neg_per_cell, len(ny_all))
            sel = rng.choice(len(ny_all), size=take, replace=False)
            sy = np.concatenate([py, ny_all[sel]])
            sx = np.concatenate([px, nx_all[sel]])
            y_sub = np.concatenate([np.ones(len(py), np.int32), np.zeros(take, np.int32)])
            true_prior = float(max(len(py), 1) / max(int(allowed.sum()), 1))

            X_e_sub = _extract_matrix(zstack, pipe_efg["fields_e"], CORE_PHYSICS_COLS, sy, sx)
            X_efg_sub = _extract_matrix(
                zstack, pipe_efg["fields"], CORE_PHYSICS_COLS + EXT_PHYSICS_COLS, sy, sx,
            )
            X_ctrl_sub = _extract_matrix(
                zstack, None, CORE_PHYSICS_COLS + EXT_PHYSICS_COLS, sy, sx,
            )

            # Evaluate uncalibrated arms right now so full-grid fields can be freed immediately
            p_uc = pipe_efg["propensity"]
            em_uc = emit_dots(p_uc, allowed & (p_uc > 0), cell.n_truth, floor=0.05)
            per_arm_cells["uncalibrated_corridor"][cell.key] = thold.score_cell(cell, em_uc)
            em_u0 = emit_dots(p_ctrl_raw, allowed & (p_ctrl_raw > 0), cell.n_truth, floor=0.05)
            per_arm_cells["uncalibrated_control"][cell.key] = thold.score_cell(cell, em_u0)

            # Store ONLY compact float16 crops inside `cell.bbox` (~14 MB vs 680 MB)
            fields_e_crop = {
                k: pipe_efg["fields_e"][k][cell.bbox].astype(np.float16) for k in CORRIDOR_COLS
            }
            fields_efg_crop = {
                k: pipe_efg["fields"][k][cell.bbox].astype(np.float16) for k in CORRIDOR_COLS
            }
            del pipe_efg, visible, offcat_vis, truth, p_uc, em_uc, em_u0
            gc.collect()

            cell_cache[cell.key] = dict(
                cell=cell, allowed_crop=allowed[cell.bbox].copy(), true_prior=true_prior,
                fields_e_crop=fields_e_crop, fields_efg_crop=fields_efg_crop,
                X_e=X_e_sub, X_efg=X_efg_sub, X_ctrl=X_ctrl_sub, y=y_sub,
            )
            if mode == "all":
                trained_live_data["X_e"].append(X_e_sub)
                trained_live_data["X_efg"].append(X_efg_sub)
                trained_live_data["y"].append(y_sub)
                trained_live_data["priors"].append(true_prior)
            print(f"  [cell {cell.key}] features extracted in {time.time() - t_c:.1f}s", flush=True)

        # Step 2: Leave-One-Quadrant-Out fit on {J != Q} -> chunked predict & emit on Q
        for s_val in seeds_present:
            s_cells = [c for c in mode_cells if c.seed == s_val]
            for test_cell in s_cells:
                tr_keys = [c.key for c in s_cells if c.fold != test_cell.fold]
                tc = cell_cache[test_cell.key]
                allowed = np.zeros(shape, bool)
                allowed[test_cell.bbox] = tc["allowed_crop"]
                ay, ax = np.nonzero(allowed)
                prior_tr = float(np.mean([cell_cache[k]["true_prior"] for k in tr_keys]))

                # Arm 1: H69-E
                clf_e, os_e = _fit_oof_calibrator(
                    np.vstack([cell_cache[k]["X_e"] for k in tr_keys]),
                    np.concatenate([cell_cache[k]["y"] for k in tr_keys]),
                    prior_tr, seed=seed,
                )
                p_e = _predict_allowed_chunked(
                    clf_e, os_e, zstack, tc["fields_e_crop"],
                    test_cell.bbox, CORE_PHYSICS_COLS, ay, ax, shape,
                )
                em_e = emit_dots(p_e, allowed, test_cell.n_truth)
                per_arm_cells["h69_e"][test_cell.key] = thold.score_cell(test_cell, em_e)
                del p_e, em_e

                # Arm 2: H69-EFG
                clf_efg, os_efg = _fit_oof_calibrator(
                    np.vstack([cell_cache[k]["X_efg"] for k in tr_keys]),
                    np.concatenate([cell_cache[k]["y"] for k in tr_keys]),
                    prior_tr, seed=seed,
                )
                p_efg = _predict_allowed_chunked(
                    clf_efg, os_efg, zstack, tc["fields_efg_crop"],
                    test_cell.bbox, CORE_PHYSICS_COLS + EXT_PHYSICS_COLS, ay, ax, shape,
                )
                em_efg = emit_dots(p_efg, allowed, test_cell.n_truth)
                per_arm_cells["h69_efg"][test_cell.key] = thold.score_cell(test_cell, em_efg)
                del p_efg, em_efg

                # Arm 3: No-Corridor-Prior Control (identical classifier & physics!)
                clf_c, os_c = _fit_oof_calibrator(
                    np.vstack([cell_cache[k]["X_ctrl"] for k in tr_keys]),
                    np.concatenate([cell_cache[k]["y"] for k in tr_keys]),
                    prior_tr, seed=seed,
                )
                p_ctrl = _predict_allowed_chunked(
                    clf_c, os_c, zstack, None,
                    test_cell.bbox, CORE_PHYSICS_COLS + EXT_PHYSICS_COLS, ay, ax, shape,
                )
                em_ctrl = emit_dots(p_ctrl, allowed, test_cell.n_truth)
                per_arm_cells["no_prior_control"][test_cell.key] = thold.score_cell(test_cell, em_ctrl)
                del p_ctrl, em_ctrl
                print(
                    f"  [oof {test_cell.key}] E={per_arm_cells['h69_e'][test_cell.key]['dti']:.4f} "
                    f"EFG={per_arm_cells['h69_efg'][test_cell.key]['dti']:.4f} "
                    f"CTRL={per_arm_cells['no_prior_control'][test_cell.key]['dti']:.4f}",
                    flush=True,
                )
        del cell_cache
        gc.collect()

        summaries = {a: pooled_bootstrap_summary(per_arm_cells[a], seed=seed) for a in arms}
        comparisons = {
            "h69_e_vs_no_prior_control": paired_bootstrap_diff(
                per_arm_cells["h69_e"], per_arm_cells["no_prior_control"], seed=seed,
            ),
            "h69_efg_vs_no_prior_control": paired_bootstrap_diff(
                per_arm_cells["h69_efg"], per_arm_cells["no_prior_control"], seed=seed,
            ),
            "h69_efg_vs_h69_e": paired_bootstrap_diff(
                per_arm_cells["h69_efg"], per_arm_cells["h69_e"], seed=seed,
            ),
            "uncalibrated_corridor_vs_control": paired_bootstrap_diff(
                per_arm_cells["uncalibrated_corridor"], per_arm_cells["uncalibrated_control"], seed=seed,
            ),
        }
        out_by_mode[mode] = dict(summaries=summaries, comparisons=comparisons)

    return dict(by_mode=out_by_mode, live_training_data=trained_live_data)


def fit_full_live_surface(
    catalogue: np.ndarray,
    footprint: np.ndarray,
    stats: dict,
    live_training_data: dict,
    variant: str = "h69_efg",
    flank_px: int = FLANK_PX,
    k_truth_live: int = 92_000,
    zstack: dict | None = None,
    seed: int = 69,
) -> dict:
    """Build full-catalogue corridors + calibrated pre-placement surface + dots."""
    shape = footprint.shape
    if zstack is None:
        zstack = build_z_stack(footprint, stats)
    use_ext = variant == "h69_efg"
    phys_cols = CORE_PHYSICS_COLS + (EXT_PHYSICS_COLS if use_ext else [])
    X_key = "X_efg" if use_ext else "X_e"

    pipe = corridor_pipeline(
        catalogue, shape, stats, max_corridors=3200,
        zstack=zstack, footprint=footprint, include_extended=use_ext,
    )
    offcat = ndi.distance_transform_edt(~catalogue) > flank_px
    allowed = footprint & (~catalogue) & offcat
    live_prior = float(k_truth_live / max(int(allowed.sum()), 1))

    X_tr = np.vstack(live_training_data[X_key])
    y_tr = np.concatenate(live_training_data["y"])
    clf, odds_scale = _fit_oof_calibrator(X_tr, y_tr, live_prior, seed=seed)

    ay, ax = np.nonzero(allowed)
    surface = np.zeros(shape, np.float32)
    # Chunk prediction across allowed pixels to keep peak RAM tiny (< 400 MB)
    step = 250_000
    for i0 in range(0, len(ay), step):
        ys_c, xs_c = ay[i0:i0 + step], ax[i0:i0 + step]
        Xc = _extract_matrix(zstack, pipe["fields"], phys_cols, ys_c, xs_c)
        surface[ys_c, xs_c] = _predict_calibrated(clf, odds_scale, Xc)

    emitted = emit_dots(surface, allowed, k_truth_live, floor=0.010, max_dots=55_000)
    return dict(
        variant=variant,
        pipe=pipe,
        surface=surface,
        emitted=emitted,
        allowed=allowed,
        n_dots=int(emitted.sum()),
    )


def run_holdout_arms(
    ctx, stats, modes=("all",), flank_px: int = FLANK_PX,
    s0: float | None = None, zstack: dict | None = None,
):
    """Backward-compatible wrapper returning calibrated corridor vs no-prior control."""
    bench = run_spatial_oof_benchmark(ctx, stats, modes=tuple(modes), flank_px=flank_px, zstack=zstack)
    results = {}
    for m in modes:
        s_cor = bench["by_mode"][m]["summaries"]["h69_efg"]["per_cell_dti"]
        s_ctl = bench["by_mode"][m]["summaries"]["no_prior_control"]["per_cell_dti"]
        for k in s_cor:
            cell = ctx.cell(k)
            results[k] = dict(
                corridor=dict(dti=s_cor[k], n_truth=cell.n_truth),
                control=dict(dti=s_ctl[k], n_truth=cell.n_truth),
            )
    return results


def pooled_from_results(results: dict, arm: str) -> dict:
    dtis = np.array([results[k][arm]["dti"] for k in sorted(results)])
    return dict(
        mean_dti=float(dtis.mean()),
        std_dti=float(dtis.std(ddof=1)) if len(dtis) > 1 else 0.0,
        ci95_half=1.96 * float(dtis.std(ddof=1)) / np.sqrt(len(dtis)) if len(dtis) > 1 else 0.0,
        n_cells=len(dtis),
        per_cell={k: results[k][arm]["dti"] for k in sorted(results)},
        n_truth=[results[k][arm]["n_truth"] for k in sorted(results)],
    )


def leakage_canary(
    ctx, stats, max_neg: int = 200_000, seed: int = 69, zstack: dict | None = None,
) -> dict:
    """Single-feature Mann-Whitney AUC vs withheld truth (draw 20, mode 'all').

    Fixes IR-69-HOLDOUT-02: builds all corridor features strictly from `visible`
    (`ctx.grid.catalogue & ~hidden_draw20`), NEVER full `ctx.grid.catalogue`.
    """
    fp = ctx.grid.footprint
    shape = fp.shape
    if zstack is None:
        zstack = build_z_stack(fp, stats)
    cells = [c for c in ctx.cells if "draw20" in c.key and c.mode == "all"]
    hidden_all = np.zeros(shape, bool)
    truth = np.zeros(shape, bool)
    active = np.zeros(shape, bool)
    for cell in cells:
        h = ctx.hidden_by_cell[cell.key]
        hidden_all |= h
        full_active = cell_allowed(cell, shape)
        truth |= h & full_active
        active |= full_active

    visible_draw20 = ctx.grid.catalogue & ~hidden_all
    offcat_vis = ndi.distance_transform_edt(~visible_draw20) > FLANK_PX
    eval_mask = active & offcat_vis
    truth_eval = truth & eval_mask
    neg_pool = np.nonzero(eval_mask & ~truth_eval)
    rng = np.random.default_rng(seed)
    n_neg = min(max_neg, len(neg_pool[0]))
    sel = rng.choice(len(neg_pool[0]), size=n_neg, replace=False)
    ny, nx = neg_pool[0][sel], neg_pool[1][sel]
    ty, tx = np.nonzero(truth_eval)

    cor_pipe = corridor_pipeline(visible_draw20, shape, stats, zstack=zstack, footprint=fp)
    cfields = cor_pipe["fields"]

    def auc(vals_t: np.ndarray, vals_n: np.ndarray) -> float | None:
        a = np.asarray(vals_t, np.float64)
        b = np.asarray(vals_n, np.float64)
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if a.size < 10 or b.size < 10:
            return None
        allv = np.concatenate([a, b])
        order = np.argsort(allv, kind="mergesort")
        sorted_v = allv[order]
        change = np.flatnonzero(np.diff(sorted_v) != 0) + 1
        starts = np.concatenate([[0], change])
        ends = np.concatenate([change, [len(sorted_v)]])
        ranks = np.arange(1, len(sorted_v) + 1, dtype=np.float64)
        avg = np.empty_like(ranks)
        cum = np.cumsum(ranks)
        sums = cum[ends - 1] - np.where(starts > 0, cum[starts - 1], 0.0)
        for s0_, e0_, sm in zip(starts, ends, sums):
            avg[s0_:e0_] = sm / (e0_ - s0_)
        avg_rank = np.empty_like(avg)
        avg_rank[order] = avg
        rank_sum_t = avg_rank[: a.size].sum()
        return float((rank_sum_t - a.size * (a.size + 1) / 2.0) / (a.size * b.size))

    out = {}
    for name in list(zstack.keys()):
        z = zstack[name]
        out[name] = dict(
            auc=round(auc(z[ty, tx], z[ny, nx]), 5),
            n_pos=int(len(ty)), n_neg=int(n_neg),
        )
    for name in CORRIDOR_COLS:
        f = cfields[name]
        out[name] = dict(
            auc=round(auc(f[ty, tx], f[ny, nx]), 5),
            n_pos=int(len(ty)), n_neg=int(n_neg),
        )
    max_feat, max_auc = max(
        ((k, v["auc"]) for k, v in out.items() if v["auc"] is not None),
        key=lambda kv: kv[1],
    )
    out["_summary"] = dict(
        max_single_feature=max_feat,
        max_single_auc=max_auc,
        canary_pass=bool(max_auc <= 0.90),
        truth_px=int(len(ty)),
        corridors_built=cor_pipe["corridors"],
        catalogue_used="visible_only (existing_faults & ~hidden_draw20)",
    )
    return out


def hardlinked_recovery(
    catalogue: np.ndarray,
    shape: tuple[int, int],
    stats: dict,
    max_ramps: int = 80,
    w_max: float = 60.0,
    zstack: dict | None = None,
    footprint: np.ndarray | None = None,
) -> dict:
    """Mask known breaching/linking faults in mapped hard-linked relay ramps and
    measure 300 m (3 px) recovery when rebuilt strictly from remaining visible faults.

    Fixes IR-69-HOLDOUT-03 (prior stray minus sign `overlap > -OVERLAP_RATIO * cross`
    skipped 100% of candidate ramps).
    """
    if footprint is None:
        footprint = _footprint_from_shape(shape)
    if zstack is None:
        zstack = build_z_stack(footprint, stats)
    admit = build_admittance_surface(zstack, footprint)

    strands = vectorize(catalogue)
    kin = attach_catalogue_kinematics(strands, catalogue)
    smap = {s.sid: s for s in strands}
    virtual = build_tip_pairs(
        strands, catalogue, w_max=w_max, kinematics=kin, allow_same_component=True,
    )
    comp_full, _ = ndi.label(catalogue, structure=np.ones((3, 3), int))
    same_comp = [
        p for p in virtual
        if comp_full[p.tip_a] == comp_full[p.tip_b] and comp_full[p.tip_a] > 0
    ]

    recs = []
    still_connected = 0
    for cid, vp in enumerate(same_comp[: max_ramps * 4]):
        if len(recs) >= max_ramps:
            break
        sa, sb = smap[vp.strand_a], smap[vp.strand_b]
        flank = np.zeros(shape, bool)
        flank[sa.ys, sa.xs] = True
        flank[sb.ys, sb.xs] = True
        cor = corridor_from_pair(cid, vp, strands, shape, admittance=admit)
        r0, r1, c0, c1 = cor.bbox
        box_mask = np.zeros(shape, bool)
        box_mask[r0:r1, c0:c1] = True
        flank_thick = ndi.binary_dilation(flank, structure=np.ones((3, 3), bool), iterations=1)
        linking = box_mask & catalogue & ~flank_thick
        if linking.sum() < 4:
            continue
        visible2 = catalogue & ~linking
        comp2, _ = ndi.label(visible2, structure=np.ones((3, 3), int))
        ca2 = int(comp2[sa.ys[len(sa.ys) // 2], sa.xs[len(sa.xs) // 2]])
        cb2 = int(comp2[sb.ys[len(sb.ys) // 2], sb.xs[len(sb.xs) // 2]])
        if ca2 == 0 or cb2 == 0:
            continue
        if ca2 == cb2:
            still_connected += 1
            continue

        # Rebuild strictly inside a local padded tile around the ramp for speed & exactness
        pad = 90
        tr0, tr1 = max(0, r0 - pad), min(shape[0], r1 + pad)
        tc0, tc1 = max(0, c0 - pad), min(shape[1], c1 + pad)
        vis_tile = visible2[tr0:tr1, tc0:tc1]
        adm_tile = admit[tr0:tr1, tc0:tc1]
        strands2 = vectorize(vis_tile)
        corrs2, _ = build_corridors(
            vis_tile, strands2, vis_tile.shape, max_corridors=400,
            admittance=adm_tile, include_terminations=True,
        )
        rebuilt = np.zeros(vis_tile.shape, bool)
        for c2 in corrs2:
            rr, cc = c2.bbox[0], c2.bbox[2]
            rebuilt[rr:c2.bbox[1], cc:c2.bbox[3]] |= (c2.local_weight >= 0.55)

        link_tile = linking[tr0:tr1, tc0:tc1]
        ly, lx = np.nonzero(link_tile)
        if len(ly) == 0:
            continue
        if rebuilt.any():
            d = ndi.distance_transform_edt(~rebuilt)
            within3 = float((d[ly, lx] <= 3.0).mean())
        else:
            within3 = 0.0
        recs.append(dict(
            w_px=round(vp.w_px, 2),
            linking_px=int(len(ly)),
            within_3px=round(within3, 4),
            subtype=cor.subtype,
            rebuilt_corridors=len(corrs2),
        ))

    if not recs:
        return dict(
            n_hardlinked_found=len(same_comp),
            n_disconnected_tested=0,
            n_still_connected_after_mask=still_connected,
        )
    within = np.array([r["within_3px"] for r in recs], float)
    return dict(
        n_hardlinked_found=len(same_comp),
        n_tested=len(recs),
        n_disconnected_tested=len(recs),
        n_still_connected_after_mask=still_connected,
        mean_recovery_within_300m=round(float(within.mean()), 4),
        median_recovery_within_300m=round(float(np.median(within)), 4),
        frac_ramps_above_70pct=round(float((within >= 0.70).mean()), 4),
        n_ramps_above_70pct=int((within >= 0.70).sum()),
        ramps=recs,
    )
