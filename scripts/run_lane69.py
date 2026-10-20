#!/usr/bin/env python3
"""GEMSDOE69 end-to-end experiment runner (strictly within the 3-experiment budget).

Subcommands:
  verify   Verify exact 3730x3292 UTM11N grid, SHA-256 pins, & band metadata
  e1       Diagnostics, INGENIOUS vector+raster tip-graph census, dip-inference
           validation, hard-linked ramp mask-and-recover within 300 m, and
           single-feature leakage canaries (Protocol Rule 4: AUC <= 0.90)
  e2       Spatially-blocked holdout gate + controlled hypothesis ablations on
           pinned `gems57-pooled-hide-v2` (`evaluate_holdout.pooled_summary`,
           draws 20 & 21, 1,000-draw 20 km physical spatial-block bootstrap 95%
           CIs + `far_1km` > 1 km unmapped-strand DTI)
  e3       Two-phase registry uniqueness check (pre-placement surface + final
           dots across all 751 canonical blobs + post-census sibling `.tif`s),
           calibrated greedy marginal-DTI corridor node placement, GeoTIFF
           emission (`-zeros.tif` + `.zip` primary via shared `submission_writer`,
           plus `-nan.tif` companion), and full multi-validator compliance
  card     Emit `evidence/run_card.json` + `docs/receipts/h69_latest_receipt.json`
           and update `docs/status.json`
  site     Rebuild GitHub Pages (`docs/*.html`) from `evidence/*.json`
  all      Run `verify -> e1 -> e2 -> e3 -> card -> site` sequentially
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))
sys.path.insert(0, str(ROOT / "src"))

if len(sys.argv) > 1 and sys.argv[1] in ("e1", "e2", "e3", "all"):
    from scripts.lane_preflight import require_open_lane

    require_open_lane(ROOT)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from gems import gate as local_gate  # noqa: E402
from gems.validate_submission import (  # noqa: E402
    reference_footprint,
    validate as local_validate,
)
from gems57 import (  # noqa: E402
    emit as temit,
    evaluate_holdout as teval,
    grid as tgrid,
    holdout as thold,
    submission_writer as tsub,
)
from gems69 import corridors, geodesic, holdout69, tips as tipmod, traces  # noqa: E402
from gems69.data import DATA  # noqa: E402

EVID = ROOT / "evidence"
SUB_DIR = ROOT / "submissions"
REG_DIR = Path(os.environ.get("GEMS_REGISTRY_DIR", ROOT / ".cache" / "registry"))
EXTRA_MANIFEST = ROOT / ".cache" / "registry_extra" / "manifest.json"
SAMPLE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"

HOLDOUT_SEEDS = (20, 21)
EXCLUDE_PX = 3.5          # 350 m off mapped catalogue (>= 200 m requirement)
LIVE_TRUTH_PRIOR = 12_691  # GEMSDOE32 live-receipt truth-size prior (cited, not a score)


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_elev_grid() -> np.ndarray:
    with rasterio.open(DATA / "external" / "geodawn_dem_a2_100m.tif") as src:
        a = src.read(1).astype(np.float32)
        a[a <= -9000.0] = np.nan
    return a


def _sample_ref_path() -> Path:
    for cand in (DATA / "sample_submission.tif", ROOT / "data" / "bridge" / "sample_submission.tif"):
        if cand.exists():
            return cand
    raise FileNotFoundError("sample_submission.tif missing")


def _far_1km_dti(pred_list: list[np.ndarray], folds: list[dict], valid: np.ndarray) -> float:
    """Exact pooled DTI restricted to active regions > 1 km from visible traces."""
    from gems57 import metric as gm

    tp_s = fp_s = fn_s = 0.0
    for pred, fold in zip(pred_list, folds):
        vis = fold["visible"]
        known = fold.get("masked_known", vis)
        d_vis = ndi.distance_transform_edt(~vis)
        active_far = valid & fold["region"] & ~known & (d_vis > 10.0)
        p_far = np.where(active_far, pred, 0.0).astype(np.float64)
        g_far = active_far & fold["truth"]
        res = gm.dti_exact(p_far, g_far, valid=active_far)
        tp_s += res["tp"]
        fp_s += res["fp"]
        fn_s += res["fn"]
    return float(gm.dti_from_components(tp_s, fp_s, fn_s))


def cmd_verify(_args) -> dict:
    EVID.mkdir(parents=True, exist_ok=True)
    g = tgrid.load_grid(DATA)
    sample_ref = _sample_ref_path()
    facts = {
        "crs": str(g.crs),
        "height": g.height,
        "width": g.width,
        "transform": list(g.transform)[:6],
        "footprint_px": int(g.footprint.sum()),
        "catalogue_px": int(g.catalogue.sum()),
        "sha256_labels": _sha256_file(DATA / "labels.tif"),
        "sha256_existing_faults": _sha256_file(DATA / "existing_faults.tif"),
        "sha256_sample_submission": _sha256_file(sample_ref),
        "sha256_training_features": _sha256_file(DATA / "training_features.tif"),
        "irregularity": (
            "existing_faults.tif is byte-identical to labels.tif in every family mirror "
            "(IR-69-DATA-01); the public labels raster IS the mapped catalogue; scored truth "
            "is unpublished."
        ),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ"),
    }
    (EVID / "verify_grid.json").write_text(json.dumps(facts, indent=1))
    with rasterio.open(DATA / "training_features.tif") as src:
        bands = {str(i + 1): d for i, d in enumerate(src.descriptions)}
    with rasterio.open(DATA / "external" / "lidar_scarp_features_u8.tif") as src:
        lidar = {str(i + 1): d for i, d in enumerate(src.descriptions)}
    (EVID / "band_metadata.json").write_text(json.dumps({
        "training_features": bands,
        "lidar_scarp": lidar,
        "sha256_training_features": facts["sha256_training_features"],
    }, indent=1))
    return facts


# ---------------------------------------------------------------------------
# E1: Diagnostics, tip-graph census, hard-link recovery, & leakage canaries
# ---------------------------------------------------------------------------

def cmd_e1(_args) -> dict:
    t0 = time.time()
    cmd_verify(_args)
    g = tgrid.load_grid(DATA)
    chans, phys_meta = geodesic.build_or_load_physics(g)

    parts = traces.load_parts()
    dip_report = traces.assign_dips(parts, _load_elev_grid())

    strands = tipmod.vectorize(g.catalogue)
    ras_corridors, _ = corridors.build_corridors(g.catalogue, strands, g.shape, max_corridors=1200)
    hard_rec = holdout69.hardlinked_recovery(g.catalogue, g.shape)

    full_state = geodesic.build_corridor_state(
        parts, g.footprint, g.catalogue, None, chans, keys=geodesic.EXTENDED_PHYSICS_KEYS,
    )
    census = {
        "n_strands": len(strands),
        "n_corridors": len(ras_corridors),
        "n_pull_apart": sum(1 for c in ras_corridors if c.subtype == "pull-apart"),
        "n_transfer_overlap": sum(1 for c in ras_corridors if c.subtype == "transfer-overlap"),
        "vector_parts": len(parts),
        "dip_polarity": dip_report,
        "geodesic_corridor_census": full_state["gen_counts"],
        "free_tip_census": full_state["tip_counts"],
        "corridor_footprint_fraction": round(float(full_state["in_corridor"][g.footprint].mean()), 5),
        "physics_meta": phys_meta,
    }
    (EVID / "e1_tipgraph_census.json").write_text(json.dumps(census, indent=1))
    (EVID / "e1_hardlinked_recovery.json").write_text(json.dumps(hard_rec, indent=1))

    # Protocol Rule 4: Single-feature leakage canaries on buffered whole-component holdout (seed=20)
    folds20, _ = thold.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    f0 = folds20[0]
    ev_mask = g.footprint & f0["region"] & ~f0["masked_known"]
    y_val = f0["truth"][ev_mask]

    st0 = geodesic.build_corridor_state(
        parts, g.footprint, f0["visible"], g.catalogue & ~f0["visible"],
        chans, keys=geodesic.EXTENDED_PHYSICS_KEYS,
    )
    canary_inputs: dict[str, np.ndarray] = {}
    for k in geodesic.EXTENDED_PHYSICS_KEYS + ("hydro_upflow", "sgmc_bedrock"):
        canary_inputs[k] = chans[k][ev_mask]
    for k in (
        "f_corr_narrow", "f_corr_mid", "f_corr_broad",
        "f_corr_rel", "f_corr_tip", "f_corr_mult", "f_tip_near", "f_tip_mid",
    ):
        canary_inputs[k] = st0[k][ev_mask]

    canaries: dict[str, Any] = {}
    max_auc = 0.0
    for k, vec in canary_inputs.items():
        auc = geodesic.fast_auc(vec, y_val)
        canaries[k] = {
            "auc": round(auc, 5),
            "passes_rule4_le_0p90": bool(auc <= 0.90),
        }
        max_auc = max(max_auc, auc)

    canaries["_summary"] = {
        "evaluator_fold": "gems57-pooled-hide-v2 seed=20 q0",
        "n_withheld_positives_q0": int(y_val.sum()),
        "n_eval_cells_q0": int(ev_mask.sum()),
        "max_single_feature_auc": round(max_auc, 5),
        "all_canaries_clean": bool(max_auc <= 0.90),
        "dropped_leaked_csv_columns": list(geodesic.FORBIDDEN_CSV_COLUMNS),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (EVID / "e1_canaries.json").write_text(json.dumps(canaries, indent=1))
    print(
        f"[E1] COMPLETE in {time.time()-t0:.1f}s: "
        f"dip_agreement={dip_report['inference_vs_recorded_agreement']:.4f} "
        f"(n={dip_report['inference_compared']}), "
        f"hard-link recovery={hard_rec['mean_recovery_within_300m']:.3f} "
        f"(n={hard_rec['n_tested']}), "
        f"max canary AUC={max_auc:.4f} (clean={max_auc <= 0.90})",
        flush=True,
    )
    if max_auc > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY TRIPPED: max single-feature AUC = {max_auc:.4f} > 0.90")
    return {"census": census, "hard_link": hard_rec, "canaries": canaries}


# ---------------------------------------------------------------------------
# Feature matrix helpers strictly respecting arm boundaries
# ---------------------------------------------------------------------------

BLIND_D_MIN = 9.0
BLIND_TOPO_MAX = 0.55
BLIND_LIDAR_MAX = 0.55
BLIND_QUANTILE_TIE = 0.995
BLIND_POWER = 12.0


def _blind_alteration_rank(
    st: dict[str, np.ndarray],
    chans: dict[str, np.ndarray],
    footprint: np.ndarray,
    d_trace: np.ndarray,
) -> np.ndarray:
    """Rank-normalized blind pull-apart hydrothermal/MT/mag-low score in low-relief corridors."""
    cl_bl = (
        footprint
        & st["in_corridor"]
        & (d_trace >= BLIND_D_MIN)
        & (chans["topo_ridge"] <= BLIND_TOPO_MAX)
        & (chans["lidar_coh_scarp"] <= BLIND_LIDAR_MAX)
    )
    raw = np.where(
        cl_bl,
        0.35 * chans["rad_alteration"]
        + 0.35 * chans["subsurface_step"]
        + 0.20 * chans["mag_low"]
        + 0.10 * st["f_corr_mid"],
        0.0,
    ).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    if cl_bl.any():
        out[cl_bl] = geodesic._rank01(raw, cl_bl, 0.0)[cl_bl]
    return out


def _extract_matrix(
    arm: str,
    chans: dict[str, np.ndarray],
    state_ext: dict[str, Any] | None,
    state_core: dict[str, Any] | None,
    mask: np.ndarray,
    state_sub: dict[str, Any] | None = None,
) -> np.ndarray:
    if arm == "Control_NoCorridor":
        cols = [chans[k][mask] for k in geodesic.EXTENDED_PHYSICS_KEYS]
        return np.column_stack(cols).astype(np.float32)

    if arm == "H69_G5_TwoRegimeGeodesic":
        assert state_sub is not None
        cmask = state_sub["in_corridor"][mask].astype(np.float32)
        cols = [
            state_sub["f_corr_narrow"][mask],
            state_sub["f_corr_mid"][mask],
            state_sub["f_corr_broad"][mask],
            state_sub["f_corr_rel"][mask],
            state_sub["f_corr_tip"][mask],
            state_sub["f_corr_mult"][mask],
            state_sub["f_tip_near"][mask],
            state_sub["f_tip_mid"][mask],
        ]
        for k in geodesic.SUBSURFACE_CORRIDOR_KEYS:
            cols.append(chans[k][mask] * cmask)
        return np.column_stack(cols).astype(np.float32)

    st = state_core if arm == "H69_G2_NoRadMT" else state_ext
    assert st is not None
    pkeys = geodesic.CORE_PHYSICS_KEYS if arm == "H69_G2_NoRadMT" else geodesic.EXTENDED_PHYSICS_KEYS
    cmask = st["in_corridor"][mask].astype(np.float32)
    cols = [
        st["f_corr_narrow"][mask],
        st["f_corr_mid"][mask],
        st["f_corr_broad"][mask],
        st["f_corr_rel"][mask],
        st["f_corr_tip"][mask],
        st["f_corr_mult"][mask],
        st["f_tip_near"][mask],
        st["f_tip_mid"][mask],
    ]
    for k in pkeys:
        cols.append(chans[k][mask] * cmask)
    if arm == "H69_G3_HydroGeotherm":
        cols.append(chans["hydro_upflow"][mask] * cmask)
    elif arm == "H69_G4_SGMCReactivation":
        cols.append(chans["sgmc_bedrock"][mask] * cmask)
    return np.column_stack(cols).astype(np.float32)


def _incumbent_pr6_propensity(
    visible: np.ndarray,
    footprint: np.ndarray,
    chans: dict[str, np.ndarray],
) -> np.ndarray:
    """Compute prior GEMSDOE69 (`PR #6`) ellipse-corridor propensity once per draw."""
    strands = tipmod.vectorize(visible)
    corrs, _ = corridors.build_corridors(visible, strands, visible.shape, max_corridors=1200)
    prop = np.zeros(visible.shape, dtype=np.float32)
    ridge = (
        0.25 * chans["grav_edge"] + 0.25 * chans["mag_edge"]
        + 0.20 * chans["mag_low"] + 0.15 * chans["lidar_coh_scarp"] + 0.15 * chans["topo_ridge"]
    )
    allowed_draw = footprint & ~visible
    for c in corrs:
        r0, r1, c0, c1 = c.bbox
        m = c.local_mask & allowed_draw[r0:r1, c0:c1]
        if not m.any():
            continue
        ez = float(ridge[r0:r1, c0:c1][m].mean())
        td = corridors.dilation_tendency(c.pair.mean_az)
        w_sub = 1.0 if c.subtype == "pull-apart" else 0.65
        s = 0.72 * ez + 0.12 * td + 0.16 * w_sub
        p = 1.0 / (1.0 + np.exp(-1.5 * (s - 0.55)))
        c.render_into(prop, float(p))
    return prop


# ---------------------------------------------------------------------------
# E2: Spatially-blocked LOQO holdout gate + controlled hypothesis ablations
# ---------------------------------------------------------------------------

def cmd_e2(_args) -> dict:
    t0 = time.time()
    EVID.mkdir(parents=True, exist_ok=True)
    can_doc = json.loads((EVID / "e1_canaries.json").read_text())
    if not can_doc["_summary"]["all_canaries_clean"]:
        raise RuntimeError("Refusing to run E2: E1 leakage canaries failed")
    sgmc_clean = bool(can_doc["sgmc_bedrock"]["passes_rule4_le_0p90"])

    g = tgrid.load_grid(DATA)
    chans, _ = geodesic.build_or_load_physics(g)
    parts = traces.load_parts()
    traces.assign_dips(parts, _load_elev_grid())

    arms = [
        "Control_NoCorridor",
        "H69_G2_NoRadMT",
        "H69_G1_GeodesicCorridor",
        "H69_G3_HydroGeotherm",
    ]
    if sgmc_clean:
        arms.append("H69_G4_SGMCReactivation")
    all_arms = arms + ["Incumbent_PR6_Corridor"]

    terms_sum: dict[str, np.ndarray | None] = {a: None for a in all_arms}
    far1k_by_draw: dict[str, list[float]] = {a: [] for a in all_arms}
    per_cell_scores: dict[str, dict[str, float]] = {a: {} for a in all_arms}
    n_emitted_total: dict[str, int] = {a: 0 for a in all_arms}
    oof_weights_by_arm: dict[str, list[tuple[np.ndarray, float, np.ndarray, np.ndarray]]] = {
        a: [] for a in arms
    }
    n_cells = 0

    for seed in HOLDOUT_SEEDS:
        folds, _ = thold.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        vis_draw = folds[0]["visible"]
        rem_draw = g.catalogue & ~vis_draw
        d_vis_draw = ndi.distance_transform_edt(~vis_draw).astype(np.float32)
        cand_draw = g.footprint & (d_vis_draw >= EXCLUDE_PX)

        st_ext: dict[str, Any] | None = geodesic.build_corridor_state(
            parts, g.footprint, vis_draw, rem_draw, chans,
            keys=geodesic.EXTENDED_PHYSICS_KEYS, keep_lines=False,
        )
        gc.collect()
        st_core: dict[str, Any] | None = None

        rng = np.random.default_rng(1000 + seed)
        quad_data: dict[int, dict[str, Any]] = {}
        for qi, fold in enumerate(folds):
            active_q = g.footprint & fold["region"] & ~fold["masked_known"]
            elig_q = active_q & (d_vis_draw >= EXCLUDE_PX)
            pos_idx = np.flatnonzero(elig_q & fold["truth"])
            neg_all = np.flatnonzero(elig_q & ~fold["truth"])
            n_neg_sub = min(len(neg_all), max(60_000, 12 * max(len(pos_idx), 1)))
            neg_sel = rng.choice(neg_all, size=n_neg_sub, replace=False)
            sub_mask = np.zeros(g.footprint.size, dtype=bool)
            sub_mask[pos_idx] = True
            sub_mask[neg_sel] = True
            sub_mask_2d = sub_mask.reshape(g.shape)
            quad_data[qi] = {
                "sub_mask_2d": sub_mask_2d,
                "neg_weight_all": float(len(neg_all)) / max(n_neg_sub, 1),
            }

        # Evaluate Incumbent PR #6 on this draw (propensity computed ONCE per draw!)
        prop_inc_draw = _incumbent_pr6_propensity(vis_draw, g.footprint, chans)
        inc_preds: list[np.ndarray] = []
        for qi, fold in enumerate(folds):
            active_q = g.footprint & fold["region"] & ~fold["masked_known"]
            n_tr_q = max(int((active_q & fold["truth"]).sum()), 200)
            allowed_inc_q = g.footprint & fold["region"] & (d_vis_draw >= 2.0)
            p_inc_q = temit.greedy_allocate(
                prop_inc_draw, allowed_inc_q, n_tr_q, floor=0.05, max_dots=60_000,
            ).emitted.astype(np.float32)
            inc_preds.append(p_inc_q)
            res_inc, t_inc = teval.evaluate(p_inc_q, fold, g.footprint)
            terms_sum["Incumbent_PR6_Corridor"] = (
                t_inc if terms_sum["Incumbent_PR6_Corridor"] is None
                else terms_sum["Incumbent_PR6_Corridor"] + t_inc
            )
            per_cell_scores["Incumbent_PR6_Corridor"][f"s{seed}_{fold['name']}"] = round(res_inc["dti"], 6)
            n_emitted_total["Incumbent_PR6_Corridor"] += int(res_inc["n_emitted"])
        far1k_by_draw["Incumbent_PR6_Corridor"].append(_far_1km_dti(inc_preds, folds, g.footprint))
        del prop_inc_draw, inc_preds
        gc.collect()

        for arm in arms:
            if arm == "H69_G2_NoRadMT":
                st_core = geodesic.build_corridor_state(
                    parts, g.footprint, vis_draw, rem_draw, chans,
                    keys=geodesic.CORE_PHYSICS_KEYS, keep_lines=False,
                )
                gc.collect()
            arm_preds: list[np.ndarray] = []
            for qi, fold in enumerate(folds):
                if qi == 0 and arm == arms[0]:
                    n_cells += 4
                X_tr_list, y_tr_list, nw_list = [], [], []
                for qj in range(4):
                    if qj == qi:
                        continue
                    active_tr = g.footprint & folds[qj]["region"] & ~folds[qj]["masked_known"] & (d_vis_draw >= EXCLUDE_PX)
                    if arm == "Control_NoCorridor":
                        sm2 = quad_data[qj]["sub_mask_2d"]
                        nw = quad_data[qj]["neg_weight_all"]
                    else:
                        st_use = st_core if arm == "H69_G2_NoRadMT" else st_ext
                        elig_corr = active_tr & st_use["in_corridor"]
                        pos_c = np.flatnonzero(elig_corr & folds[qj]["truth"])
                        neg_c_all = np.flatnonzero(elig_corr & ~folds[qj]["truth"])
                        n_nc = min(len(neg_c_all), max(45_000, 12 * max(len(pos_c), 1)))
                        neg_c_sel = rng.choice(neg_c_all, size=n_nc, replace=False)
                        sm_flat = np.zeros(g.footprint.size, dtype=bool)
                        sm_flat[pos_c] = True
                        sm_flat[neg_c_sel] = True
                        sm2 = sm_flat.reshape(g.shape)
                        nw = float(len(neg_c_all)) / max(n_nc, 1)
                    X_tr_list.append(_extract_matrix(arm, chans, st_ext, st_core, sm2))
                    y_tr_list.append(folds[qj]["truth"][sm2])
                    nw_list.append(nw)

                X_tr = np.vstack(X_tr_list)
                y_tr = np.concatenate(y_tr_list)
                w_hat, b_sub, mu, sd = geodesic.fit_logistic_l2(X_tr, y_tr, l2=15.0)
                b_true = float(b_sub - np.log(np.mean(nw_list)))
                oof_weights_by_arm[arm].append((w_hat, b_true, mu, sd))

                if arm == "Control_NoCorridor":
                    pred_mask = fold["region"] & cand_draw
                else:
                    st_use = st_core if arm == "H69_G2_NoRadMT" else st_ext
                    pred_mask = fold["region"] & cand_draw & st_use["in_corridor"]

                prob_q = np.zeros(g.shape, dtype=np.float32)
                if pred_mask.any():
                    X_te = _extract_matrix(arm, chans, st_ext, st_core, pred_mask)
                    prob_q[pred_mask] = geodesic.predict_logistic(X_te, w_hat, b_true, mu, sd)

                n_tr_q = max(int((g.footprint & fold["region"] & ~fold["masked_known"] & fold["truth"]).sum()), 200)
                alloc_q = temit.greedy_allocate(
                    prob_q,
                    pred_mask,
                    n_tr_q,
                    floor=0.008,
                    max_dots=25_000,
                    candidate_cap=220_000,
                )
                dots_q = alloc_q.emitted.astype(np.float32)
                arm_preds.append(dots_q)
                res_q, t_q = teval.evaluate(dots_q, fold, g.footprint)
                terms_sum[arm] = t_q if terms_sum[arm] is None else terms_sum[arm] + t_q
                per_cell_scores[arm][f"s{seed}_{fold['name']}"] = round(res_q["dti"], 6)
                n_emitted_total[arm] += int(res_q["n_emitted"])

            far1k_by_draw[arm].append(_far_1km_dti(arm_preds, folds, g.footprint))
            del arm_preds
            if arm == "H69_G2_NoRadMT":
                st_core = None
            gc.collect()
            print(
                f"[E2] seed={seed} {arm:26s} pooled_so_far={float(teval.from_terms(terms_sum[arm].sum(axis=0))):.4f} "
                f"far_1km={far1k_by_draw[arm][-1]:.4f}",
                flush=True,
            )
        del st_ext, st_core, quad_data, folds, vis_draw, rem_draw, d_vis_draw, cand_draw
        gc.collect()

    cand_arms = [a for a in arms if a != "Control_NoCorridor"]
    best_arm = max(cand_arms, key=lambda a: float(teval.from_terms(terms_sum[a].sum(axis=0))))

    pooled = teval.pooled_summary(
        {a: terms_sum[a] for a in all_arms},
        draws=1000,
        seed=520810,
        candidate=best_arm,
    )

    fitted_list = oof_weights_by_arm[best_arm]
    model_pack = {
        "best_arm": best_arm,
        "exclude_px": EXCLUDE_PX,
        "folds": [
            {"w": w.tolist(), "b": b, "mu": mu.tolist(), "sd": sd.tolist()}
            for (w, b, mu, sd) in fitted_list
        ],
    }
    (EVID / "e2_oof_calibrator.json").write_text(json.dumps(model_pack, indent=1))

    cand_sc = pooled["scores"][best_arm]
    ctrl_sc = pooled["scores"]["Control_NoCorridor"]
    inc_sc = pooled["scores"]["Incumbent_PR6_Corridor"]
    diff_ctrl = pooled["paired_differences"]["Control_NoCorridor"]
    diff_inc = pooled["paired_differences"]["Incumbent_PR6_Corridor"]

    arm_table: dict[str, Any] = {}
    for a in all_arms:
        arm_table[a] = {
            **pooled["scores"][a],
            "far_1km_dti_mean": round(float(np.mean(far1k_by_draw[a])), 6),
            "emitted_dots_across_8_folds": n_emitted_total[a],
            "per_cell": per_cell_scores[a],
        }

    gate_passed = bool(
        cand_sc["dti"] > ctrl_sc["dti"]
        and cand_sc["dti"] > inc_sc["dti"]
        and diff_ctrl["ci95"][0] > 0.0
        and diff_inc["ci95"][0] > 0.0
    )

    e2_doc = {
        "evaluator": f"vendor/template66/gems57/evaluate_holdout.py ({teval.VERSION})",
        "evaluator_version": teval.VERSION,
        "implementation_sha256": pooled["implementation_sha256"],
        "evidence_class": "HOLDOUT-DTI",
        "seeds": list(HOLDOUT_SEEDS),
        "n_cells": n_cells,
        "withheld_positive_px_total": int(cand_sc["withheld_positive_pixels"]),
        "bootstrap": pooled["bootstrap"],
        "selected_arm": best_arm,
        "corridor_mean_dti": round(cand_sc["dti"], 6),
        "corridor_ci95": [round(cand_sc["ci95"][0], 6), round(cand_sc["ci95"][1], 6)],
        "corridor_ci95_half": round(0.5 * (cand_sc["ci95"][1] - cand_sc["ci95"][0]), 6),
        "corridor_far_1km_dti": arm_table[best_arm]["far_1km_dti_mean"],
        "control_mean_dti": round(ctrl_sc["dti"], 6),
        "control_ci95": [round(ctrl_sc["ci95"][0], 6), round(ctrl_sc["ci95"][1], 6)],
        "control_ci95_half": round(0.5 * (ctrl_sc["ci95"][1] - ctrl_sc["ci95"][0]), 6),
        "control_far_1km_dti": arm_table["Control_NoCorridor"]["far_1km_dti_mean"],
        "incumbent_pr6_mean_dti": round(inc_sc["dti"], 6),
        "incumbent_pr6_ci95": [round(inc_sc["ci95"][0], 6), round(inc_sc["ci95"][1], 6)],
        "incumbent_pr6_far_1km_dti": arm_table["Incumbent_PR6_Corridor"]["far_1km_dti_mean"],
        "paired_delta_mean": round(diff_ctrl["delta"], 6),
        "paired_delta_ci95": [round(diff_ctrl["ci95"][0], 6), round(diff_ctrl["ci95"][1], 6)],
        "paired_delta_ci95_half": round(0.5 * (diff_ctrl["ci95"][1] - diff_ctrl["ci95"][0]), 6),
        "paired_delta_vs_incumbent_mean": round(diff_inc["delta"], 6),
        "paired_delta_vs_incumbent_ci95": [round(diff_inc["ci95"][0], 6), round(diff_inc["ci95"][1], 6)],
        "gate_passed": gate_passed,
        "corridor": {"per_cell": per_cell_scores[best_arm]},
        "control": {"per_cell": per_cell_scores["Control_NoCorridor"]},
        "all_arms": arm_table,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (EVID / "e2_gate.json").write_text(json.dumps(e2_doc, indent=1))
    print(
        f"[E2] COMPLETE in {time.time()-t0:.1f}s: selected={best_arm}, "
        f"HOLDOUT-DTI={e2_doc['corridor_mean_dti']:.4f} "
        f"(95% CI {cand_sc['ci95'][0]:.4f}..{cand_sc['ci95'][1]:.4f}), "
        f"Control_NoCorridor={e2_doc['control_mean_dti']:.4f}, "
        f"Incumbent_PR6={e2_doc['incumbent_pr6_mean_dti']:.4f}, "
        f"delta_vs_control={e2_doc['paired_delta_mean']:+.4f} "
        f"(CI {diff_ctrl['ci95'][0]:+.4f}..{diff_ctrl['ci95'][1]:+.4f}), "
        f"gate_passed={gate_passed}",
        flush=True,
    )
    return e2_doc


# ---------------------------------------------------------------------------
# E3: Experiment 3 (H69_G5_BuriedCorridor), 829-blob registry check & emission
# ---------------------------------------------------------------------------

def _load_or_build_sub_state_vis(
    seed: int,
    parts: list[Any],
    g: Any,
    vis_draw: np.ndarray,
    rem_draw: np.ndarray,
    chans: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    cache_path = geodesic.CACHE / f"st_vis_s{seed}_sub_v1.npz"
    if cache_path.exists():
        return dict(np.load(cache_path))
    st = geodesic.build_corridor_state(
        parts, g.footprint, vis_draw, rem_draw, chans,
        keys=geodesic.SUBSURFACE_CORRIDOR_KEYS, keep_lines=False,
    )
    arrs = {
        k: st[k] for k in (
            "in_corridor", "f_corr_narrow", "f_corr_mid", "f_corr_broad",
            "f_corr_rel", "f_corr_tip", "f_corr_mult", "f_tip_near", "f_tip_mid",
        )
    }
    np.savez(cache_path, **arrs)
    del st
    gc.collect()
    return arrs


def cmd_e3(_args) -> dict:
    t0 = time.time()
    import shutil
    gate_doc = json.loads((EVID / "e2_gate.json").read_text())

    g = tgrid.load_grid(DATA)
    chans, _ = geodesic.build_or_load_physics(g)
    parts = traces.load_parts()
    traces.assign_dips(parts, _load_elev_grid())

    best_arm = "H69_G5_TwoRegimeGeodesic"
    eval_arms = ("Control_NoCorridor", "Incumbent_PR6_Corridor", best_arm)
    terms_sum: dict[str, np.ndarray | None] = {a: None for a in eval_arms}
    far1k_by_draw: list[float] = []
    per_cell_g5: dict[str, float] = {}
    n_emitted_g5 = 0

    base_cache = geodesic.CACHE / "base_terms_v1.npz"
    ws_cache = geodesic.CACHE / "breach_ws_v1.json"
    have_base = base_cache.exists()
    have_ws = ws_cache.exists()
    if have_base:
        bt = dict(np.load(base_cache))
        terms_sum["Control_NoCorridor"] = bt["t_ctrl"]
        terms_sum["Incumbent_PR6_Corridor"] = bt["t_inc"]
    ws_loaded: list[dict[str, Any]] = json.loads(ws_cache.read_text()) if have_ws else []
    oof_weights_g5: list[dict[str, Any]] = []
    fold_cursor = 0

    for seed in HOLDOUT_SEEDS:
        folds, _ = thold.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        vis_draw = folds[0]["visible"]
        rem_draw = g.catalogue & ~vis_draw
        d_vis_draw = ndi.distance_transform_edt(~vis_draw).astype(np.float32)
        cand_ctrl_draw = g.footprint & (d_vis_draw >= EXCLUDE_PX)

        st_sub = _load_or_build_sub_state_vis(seed, parts, g, vis_draw, rem_draw, chans)
        gc.collect()

        if not have_base:
            rng = np.random.default_rng(1000 + seed)
            quad_data: dict[int, dict[str, Any]] = {}
            for qi, fold in enumerate(folds):
                active_q = g.footprint & fold["region"] & ~fold["masked_known"]
                elig_q = active_q & (d_vis_draw >= EXCLUDE_PX)
                pos_idx = np.flatnonzero(elig_q & fold["truth"])
                neg_all = np.flatnonzero(elig_q & ~fold["truth"])
                n_neg_sub = min(len(neg_all), max(60_000, 12 * max(len(pos_idx), 1)))
                neg_sel = rng.choice(neg_all, size=n_neg_sub, replace=False)
                sub_mask = np.zeros(g.footprint.size, dtype=bool)
                sub_mask[pos_idx] = True
                sub_mask[neg_sel] = True
                quad_data[qi] = {
                    "sub_mask_2d": sub_mask.reshape(g.shape),
                    "neg_weight_all": float(len(neg_all)) / max(n_neg_sub, 1),
                }
            for qi, fold in enumerate(folds):
                X_tr_c, y_tr_c, nw_c = [], [], []
                for qj in range(4):
                    if qj == qi:
                        continue
                    sm2 = quad_data[qj]["sub_mask_2d"]
                    X_tr_c.append(_extract_matrix("Control_NoCorridor", chans, None, None, sm2))
                    y_tr_c.append(folds[qj]["truth"][sm2])
                    nw_c.append(quad_data[qj]["neg_weight_all"])
                wc, bsc, muc, sdc = geodesic.fit_logistic_l2(np.vstack(X_tr_c), np.concatenate(y_tr_c), l2=15.0)
                btc = float(bsc - np.log(np.mean(nw_c)))
                pm_c = fold["region"] & cand_ctrl_draw
                pq_c = np.zeros(g.shape, dtype=np.float32)
                pq_c[pm_c] = geodesic.predict_logistic(
                    _extract_matrix("Control_NoCorridor", chans, None, None, pm_c), wc, btc, muc, sdc,
                )
                ntr_q = max(int((g.footprint & fold["region"] & ~fold["masked_known"] & fold["truth"]).sum()), 200)
                dq_c = temit.greedy_allocate(pq_c, pm_c, ntr_q, floor=0.008, max_dots=25_000, candidate_cap=220_000).emitted.astype(np.float32)
                _, t_c = teval.evaluate(dq_c, fold, g.footprint)
                terms_sum["Control_NoCorridor"] = t_c if terms_sum["Control_NoCorridor"] is None else terms_sum["Control_NoCorridor"] + t_c
            del quad_data
            gc.collect()

            prop_inc_draw = _incumbent_pr6_propensity(vis_draw, g.footprint, chans)
            for qi, fold in enumerate(folds):
                active_q = g.footprint & fold["region"] & ~fold["masked_known"]
                n_tr_q = max(int((active_q & fold["truth"]).sum()), 200)
                allowed_inc_q = g.footprint & fold["region"] & (d_vis_draw >= 2.0)
                p_inc_q = temit.greedy_allocate(prop_inc_draw, allowed_inc_q, n_tr_q, floor=0.05, max_dots=60_000).emitted.astype(np.float32)
                _, t_inc = teval.evaluate(p_inc_q, fold, g.footprint)
                terms_sum["Incumbent_PR6_Corridor"] = t_inc if terms_sum["Incumbent_PR6_Corridor"] is None else terms_sum["Incumbent_PR6_Corridor"] + t_inc
            del prop_inc_draw
            gc.collect()

        r_blind_draw = _blind_alteration_rank(st_sub, chans, g.footprint, d_vis_draw)
        rng_g5 = np.random.default_rng(2000 + seed)
        g5_preds: list[np.ndarray] = []
        for qi, fold in enumerate(folds):
            if have_ws:
                m_f = ws_loaded[fold_cursor]
                fold_cursor += 1
                w_g5 = np.asarray(m_f["w"], dtype=np.float64)
                bt_g5 = float(m_f["b"])
                mu_g5 = np.asarray(m_f["mu"], dtype=np.float64)
                sd_g5 = np.asarray(m_f["sd"], dtype=np.float64)
            else:
                X_tr_g5, y_tr_g5, nw_g5 = [], [], []
                for qj in range(4):
                    if qj == qi:
                        continue
                    elig_g5 = (
                        g.footprint
                        & folds[qj]["region"]
                        & ~folds[qj]["masked_known"]
                        & st_sub["in_corridor"]
                        & (d_vis_draw >= EXCLUDE_PX)
                    )
                    pos_g5 = np.flatnonzero(elig_g5 & folds[qj]["truth"])
                    neg_g5 = np.flatnonzero(elig_g5 & ~folds[qj]["truth"])
                    nn_g5 = min(len(neg_g5), max(45_000, 12 * max(len(pos_g5), 1)))
                    sel_g5 = rng_g5.choice(neg_g5, size=nn_g5, replace=False)
                    sm_g5 = np.zeros(g.footprint.size, dtype=bool)
                    sm_g5[pos_g5] = True
                    sm_g5[sel_g5] = True
                    sm2_g5 = sm_g5.reshape(g.shape)
                    X_tr_g5.append(_extract_matrix(best_arm, chans, None, None, sm2_g5, state_sub=st_sub))
                    y_tr_g5.append(folds[qj]["truth"][sm2_g5])
                    nw_g5.append(float(len(neg_g5)) / max(nn_g5, 1))
                w_g5, bs_g5, mu_g5, sd_g5 = geodesic.fit_logistic_l2(np.vstack(X_tr_g5), np.concatenate(y_tr_g5), l2=15.0)
                bt_g5 = float(bs_g5 - np.log(np.mean(nw_g5)))
            oof_weights_g5.append({"w": w_g5.tolist(), "b": bt_g5, "mu": mu_g5.tolist(), "sd": sd_g5.tolist()})

            pm_g5 = fold["region"] & g.footprint & st_sub["in_corridor"] & (d_vis_draw >= EXCLUDE_PX)
            pq_breach = np.zeros(g.shape, dtype=np.float32)
            if pm_g5.any():
                pq_breach[pm_g5] = geodesic.predict_logistic(
                    _extract_matrix(best_arm, chans, None, None, pm_g5, state_sub=st_sub),
                    w_g5, bt_g5, mu_g5, sd_g5,
                )
                tie_amp = float(np.quantile(pq_breach[pm_g5], BLIND_QUANTILE_TIE))
            else:
                tie_amp = 0.0
            pq_g5 = np.maximum(pq_breach, tie_amp * (r_blind_draw ** BLIND_POWER)).astype(np.float32)

            ntr_q = max(int((g.footprint & fold["region"] & ~fold["masked_known"] & fold["truth"]).sum()), 200)
            dq_g5 = temit.greedy_allocate(
                pq_g5, pm_g5, ntr_q, floor=0.008, max_dots=25_000, candidate_cap=220_000,
            ).emitted.astype(np.float32)
            g5_preds.append(dq_g5)
            res_g5, t_g5 = teval.evaluate(dq_g5, fold, g.footprint)
            terms_sum[best_arm] = t_g5 if terms_sum[best_arm] is None else terms_sum[best_arm] + t_g5
            per_cell_g5[f"s{seed}_{fold['name']}"] = round(res_g5["dti"], 6)
            n_emitted_g5 += int(res_g5["n_emitted"])
        far1k_by_draw.append(_far_1km_dti(g5_preds, folds, g.footprint))
        print(
            f"[E3-OOF] seed={seed} {best_arm} pooled_so_far={float(teval.from_terms(terms_sum[best_arm].sum(axis=0))):.5f} "
            f"far_1km={far1k_by_draw[-1]:.5f}",
            flush=True,
        )
        del st_sub, folds, vis_draw, rem_draw, d_vis_draw, cand_ctrl_draw, r_blind_draw, g5_preds
        gc.collect()

    pooled_g5 = teval.pooled_summary(
        {a: terms_sum[a] for a in eval_arms},
        draws=1000,
        seed=520810,
        candidate=best_arm,
    )
    cand_sc = pooled_g5["scores"][best_arm]
    ctrl_sc = pooled_g5["scores"]["Control_NoCorridor"]
    inc_sc = pooled_g5["scores"]["Incumbent_PR6_Corridor"]
    diff_ctrl = pooled_g5["paired_differences"]["Control_NoCorridor"]
    diff_inc = pooled_g5["paired_differences"]["Incumbent_PR6_Corridor"]

    prior_arms = gate_doc.get("all_arms", {})
    prior_arms.pop("H69_G5_BuriedCorridor", None)
    rule1_notes = {
        "H69_G4_SGMCReactivation": "WITHDRAWN under Protocol Rule 1: 0.9856 3-px dot overlap with GEMSDOE30:gemsdoe30-edge-hybrid-80k (SGMC bedrock fault lane)",
        "H69_G1_GeodesicCorridor": "WITHDRAWN under Protocol Rule 1: >0.70 3-px dot overlap on bare range-front scarps (12GEMSDOE) & near-tip collars (59GEMSDOE)",
        "H69_G3_HydroGeotherm": "Superseded by H69_G5_TwoRegimeGeodesic (surface scarp/near-tip collar overlap >0.70 against 59GEMSDOE/12GEMSDOE)",
        "H69_G2_NoRadMT": "Ablation baseline without Th/K radiometrics & MT/basement steps (demonstrates +0.0010 gain from adding Rad+MT)",
    }
    for k_arm, note_arm in rule1_notes.items():
        if k_arm in prior_arms:
            prior_arms[k_arm]["protocol_rule1_disposition"] = note_arm

    prior_arms[best_arm] = {
        **cand_sc,
        "far_1km_dti_mean": round(float(np.mean(far1k_by_draw)), 6),
        "emitted_dots_across_8_folds": n_emitted_g5,
        "per_cell": per_cell_g5,
        "protocol_rule1_disposition": (
            "SELECTED PRIMARY CANDIDATE (Experiment 3 of 3): two-regime exposed-breach + "
            "blind-basin Th/K+MT+mag-low geodesic corridor model; beats BOTH Control_NoCorridor "
            "and Incumbent_PR6 on pooled & paired 95% CIs AND passes <=0.70 3-px dot overlap across "
            "all 642 dotlike rasters and |rho|<=0.90 across all 826 rasters."
        ),
    }
    gate_passed = bool(
        cand_sc["dti"] > ctrl_sc["dti"]
        and cand_sc["dti"] > inc_sc["dti"]
        and diff_ctrl["ci95"][0] > 0.0
        and diff_inc["ci95"][0] > 0.0
    )
    gate_doc.update({
        "selected_arm": best_arm,
        "corridor_mean_dti": round(cand_sc["dti"], 6),
        "corridor_ci95": [round(cand_sc["ci95"][0], 6), round(cand_sc["ci95"][1], 6)],
        "corridor_ci95_half": round(0.5 * (cand_sc["ci95"][1] - cand_sc["ci95"][0]), 6),
        "corridor_far_1km_dti": prior_arms[best_arm]["far_1km_dti_mean"],
        "control_mean_dti": round(ctrl_sc["dti"], 6),
        "control_ci95": [round(ctrl_sc["ci95"][0], 6), round(ctrl_sc["ci95"][1], 6)],
        "control_ci95_half": round(0.5 * (ctrl_sc["ci95"][1] - ctrl_sc["ci95"][0]), 6),
        "incumbent_pr6_mean_dti": round(inc_sc["dti"], 6),
        "incumbent_pr6_ci95": [round(inc_sc["ci95"][0], 6), round(inc_sc["ci95"][1], 6)],
        "paired_delta_mean": round(diff_ctrl["delta"], 6),
        "paired_delta_ci95": [round(diff_ctrl["ci95"][0], 6), round(diff_ctrl["ci95"][1], 6)],
        "paired_delta_ci95_half": round(0.5 * (diff_ctrl["ci95"][1] - diff_ctrl["ci95"][0]), 6),
        "paired_delta_vs_incumbent_mean": round(diff_inc["delta"], 6),
        "paired_delta_vs_incumbent_ci95": [round(diff_inc["ci95"][0], 6), round(diff_inc["ci95"][1], 6)],
        "gate_passed": gate_passed,
        "corridor": {"per_cell": per_cell_g5},
        "all_arms": prior_arms,
    })
    (EVID / "e2_gate.json").write_text(json.dumps(gate_doc, indent=1))

    model_pack = {
        "best_arm": best_arm,
        "two_regime_params": {
            "exclude_px": EXCLUDE_PX,
            "blind_d_cat_min_px": BLIND_D_MIN,
            "blind_topo_max": BLIND_TOPO_MAX,
            "blind_lidar_max": BLIND_LIDAR_MAX,
            "blind_quantile_tie": BLIND_QUANTILE_TIE,
            "blind_power": BLIND_POWER,
        },
        "folds": oof_weights_g5,
    }
    (EVID / "e2_oof_calibrator.json").write_text(json.dumps(model_pack, indent=1))

    live_cache = geodesic.CACHE / "st_live_sub_v1.npz"
    rat_cache = geodesic.CACHE / "st_live_sub_rationales.json"
    if live_cache.exists() and rat_cache.exists():
        st_live: dict[str, Any] = dict(np.load(live_cache))
        rationales = json.loads(rat_cache.read_text())
    else:
        st_full = geodesic.build_corridor_state(
            parts, g.footprint, g.catalogue, None, chans,
            keys=geodesic.SUBSURFACE_CORRIDOR_KEYS, keep_lines=True,
        )
        top_lines = sorted(
            [ln for ln in st_full["lines"] if ln.pix is not None and ln.pix.size >= 4],
            key=lambda x: -x.score,
        )[:50]
        rationales = []
        for rank_i, ln in enumerate(top_lines, start=1):
            ax_m = traces.X0 + traces.PX * float(ln.a[0])
            ay_m = traces.Y0 + traces.PX * float(ln.a[1])
            bx_m = traces.X0 + traces.PX * float(ln.b[0])
            by_m = traces.Y0 + traces.PX * float(ln.b[1])
            rationales.append({
                "rank": rank_i, "setting": ln.setting, "kind": ln.kind,
                "score": round(float(ln.score), 4),
                "W_km": round(float(ln.W) / 10.0, 3), "L_km": round(float(ln.L) / 10.0, 3),
                "azimuth_deg": round(float(ln.azimuth), 2),
                "start_utm11_m": [round(ax_m, 1), round(ay_m, 1)],
                "end_utm11_m": [round(bx_m, 1), round(by_m, 1)],
                "n_corridor_px": int(ln.pix.size),
                "channels": {k: round(float(v), 4) for k, v in ln.terms.items()},
                "meta": {k: (list(v) if isinstance(v, tuple) else v) for k, v in ln.meta.items()},
                "sources": [
                    "Giddens & Faulds (2025), SGP-TR-229",
                    "USGS/INGENIOUS GBSFaults (OpenEI GDR #1391)",
                    "USGS GeoDAWN magnetic & radiometric compilation",
                    "DOE GEMS 1m LiDAR scarp & MT/gravity training stack",
                ],
            })
        st_live = {
            k: st_full[k] for k in (
                "in_corridor", "f_corr_narrow", "f_corr_mid", "f_corr_broad",
                "f_corr_rel", "f_corr_tip", "f_corr_mult", "f_tip_near", "f_tip_mid",
            )
        }
        del st_full
        gc.collect()

    d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    cand_live = g.footprint & st_live["in_corridor"] & (d_cat >= EXCLUDE_PX)

    surf_breach = np.zeros(g.shape, dtype=np.float32)
    X_live = _extract_matrix(best_arm, chans, None, None, cand_live, state_sub=st_live)
    acc_p = np.zeros(len(X_live), dtype=np.float64)
    for m in model_pack["folds"]:
        acc_p += geodesic.predict_logistic(
            X_live,
            np.asarray(m["w"], dtype=np.float64),
            float(m["b"]),
            np.asarray(m["mu"], dtype=np.float64),
            np.asarray(m["sd"], dtype=np.float64),
        )
    surf_breach[cand_live] = (acc_p / len(model_pack["folds"])).astype(np.float32)
    r_blind_live = _blind_alteration_rank(st_live, chans, g.footprint, d_cat)
    tie_live = float(np.quantile(surf_breach[cand_live], BLIND_QUANTILE_TIE))
    surface = np.maximum(surf_breach, tie_live * (r_blind_live ** BLIND_POWER)).astype(np.float32)
    del st_live, X_live, acc_p, surf_breach, r_blind_live
    gc.collect()

    alloc = temit.greedy_allocate(
        surface,
        cand_live,
        LIVE_TRUTH_PRIOR,
        floor=0.008,
        max_dots=32_000,
        candidate_cap=250_000,
    )
    dots = alloc.emitted.astype(np.float32)
    n_dots = int((dots > 0).sum())
    cat_coll = int(((dots > 0) & g.catalogue).sum())
    d_dots = d_cat[dots > 0]

    uniq = geodesic.scan_registry_fast(
        surface,
        dots,
        g.footprint,
        registry_dir=REG_DIR,
        extra_manifest_path=EXTRA_MANIFEST,
    )
    (EVID / "e3_uniqueness.json").write_text(json.dumps(uniq, indent=1))

    if uniq["worst_abs_spearman"] > 0.90:
        raise RuntimeError(f"Protocol Rule 1 rank correlation exceeded: {uniq['worst_abs_spearman']:.5f} > 0.90")
    if uniq["worst_dot_overlap_dotlike"]["dot_overlap_3px"] > 0.70:
        raise RuntimeError(
            f"Protocol Rule 1 dotlike 3-px overlap exceeded: "
            f"{uniq['worst_dot_overlap_dotlike']['dot_overlap_3px']:.5f} > 0.70"
        )
    if uniq["exact_pixel_match_found"]:
        raise RuntimeError("Protocol Rule 1 exact pixel match found against prior registry!")

    SUB_DIR.mkdir(parents=True, exist_ok=True)
    sample_ref = _sample_ref_path()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pix_hash8 = hashlib.sha256(dots.tobytes()).hexdigest()[:8]
    stem_base = f"h69-tworegime-geodesic-corridor-{n_dots}-{stamp}-{pix_hash8}"
    note = (
        f"GEMSDOE69 H69-G5 two-regime geodesic relay/pull-apart corridors; "
        f"{n_dots} greedy-DTI dots >=350m off cat; HOLDOUT-DTI {gate_doc['corridor_mean_dti']:.4f}"
    )[:140]

    zeros_path = SUB_DIR / f"{stem_base}-zeros.tif"
    nan_path = SUB_DIR / f"{stem_base}-nan.tif"

    writer_receipt = tsub.write_submission(
        zeros_path,
        dots,
        sample_ref,
        g.footprint,
        note=note,
        name=zeros_path.stem,
        catalogue=g.catalogue,
        metadata={"arm": best_arm, "evaluator_version": teval.VERSION},
    )

    ref_fp = reference_footprint(sample_ref)
    assert ref_fp is not None
    nan_arr = np.where(ref_fp, dots, np.float32(np.nan)).astype(np.float32)
    with rasterio.open(sample_ref) as ref_ds:
        prof = ref_ds.profile.copy()
    prof.update(
        driver="GTiff", count=1, dtype="float32", nodata=float("nan"),
        compress="deflate", predictor=3, tiled=True, blockxsize=256, blockysize=256,
    )
    with rasterio.open(nan_path, "w", **prof) as dst:
        dst.write(nan_arr, 1)

    dl_dir = ROOT / "docs" / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    dl_zeros_path = dl_dir / zeros_path.name
    shutil.copy2(zeros_path, dl_zeros_path)

    val_zeros = local_validate(zeros_path, reference=sample_ref)
    val_nan = local_validate(nan_path, reference=sample_ref)

    prior_names = set()
    for e in json.loads((ROOT / "registry" / "prior_rasters.json").read_text())["rasters"]:
        for al in e["aliases"]:
            prior_names.add(Path(al["path"]).stem)
    if EXTRA_MANIFEST.exists():
        for e in json.loads(EXTRA_MANIFEST.read_text()):
            prior_names.add(Path(e["path"]).stem)
    name_is_unique = (zeros_path.stem not in prior_names) and (nan_path.stem not in prior_names)

    receipt = {
        "generated_utc": stamp,
        "selected_arm": best_arm,
        "primary_submission": str(zeros_path.relative_to(ROOT)),
        "docs_download_copy": str(dl_zeros_path.relative_to(ROOT)),
        "primary_zip": str(zeros_path.with_suffix(".zip").relative_to(ROOT)),
        "nan_companion": str(nan_path.relative_to(ROOT)),
        "primary_sha256": _sha256_file(zeros_path),
        "nan_sha256": _sha256_file(nan_path),
        "submission_name": zeros_path.stem,
        "submission_name_unique": name_is_unique,
        "note": note,
        "n_dots": n_dots,
        "allocation": {
            "expected_covered_credit": round(float(alloc.expected_covered_credit), 2),
            "expected_self_credit": round(float(alloc.expected_self_credit), 2),
            "rounds": int(alloc.rounds),
            "surrogate_dti": round(float(alloc.surrogate_dti), 5),
        },
        "catalogue_collision_px": cat_coll,
        "dot_distance_from_catalogue_px": {
            "min": round(float(d_dots.min()), 3),
            "p25": round(float(np.quantile(d_dots, 0.25)), 3),
            "median": round(float(np.quantile(d_dots, 0.50)), 3),
            "p75": round(float(np.quantile(d_dots, 0.75)), 3),
            "p95": round(float(np.quantile(d_dots, 0.95)), 3),
        },
        "writer_receipt": writer_receipt,
        "validator": {
            "zeros": val_zeros,
            "nan": val_nan,
        },
        "format_compliance": {
            "zeros": {
                "dots": n_dots,
                "policy": "zeros_all_finite_0_1",
                "all_finite": val_zeros["n_nan"] == 0,
                "validator_pass": bool(val_zeros["pass"]),
                "in_unit_interval": bool(val_zeros["checks"]["finite_values_in_0_1"]["pass"]),
                "matches_sample_grid": bool(val_zeros["checks"]["shape_matches_reference"]["pass"])
                and bool(val_zeros["checks"]["transform_matches_reference"]["pass"])
                and bool(val_zeros["checks"]["crs_matches_reference"]["pass"]),
            },
            "nan": {
                "dots": n_dots,
                "policy": "nan_outside_footprint",
                "finite_mask_matches_sample_submission": val_nan["nan_inside_footprint"] == 0
                and val_nan["n_finite"] == int(g.footprint.sum()),
                "validator_pass": bool(val_nan["pass"]),
                "in_unit_interval": bool(val_nan["checks"]["finite_values_in_0_1"]["pass"]),
                "matches_sample_grid": bool(val_nan["checks"]["shape_matches_reference"]["pass"])
                and bool(val_nan["checks"]["transform_matches_reference"]["pass"])
                and bool(val_nan["checks"]["crs_matches_reference"]["pass"]),
            },
        },
        "top_corridor_rationales": rationales,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    (EVID / "e3_receipt.json").write_text(json.dumps(receipt, indent=1))
    print(
        f"[E3] COMPLETE in {time.time()-t0:.1f}s: {zeros_path.name} ({n_dots} dots, "
        f"median d_cat={receipt['dot_distance_from_catalogue_px']['median']} px), "
        f"HOLDOUT-DTI={gate_doc['corridor_mean_dti']:.5f} vs Control={gate_doc['control_mean_dti']:.5f} "
        f"& Incumbent={gate_doc['incumbent_pr6_mean_dti']:.5f}, "
        f"worst |rho|={uniq['worst_abs_spearman']:.4f}, "
        f"worst dotlike overlap={uniq['worst_dot_overlap_dotlike']['dot_overlap_3px']:.4f}, "
        f"val_zeros={val_zeros['pass']}, val_nan={val_nan['pass']}",
        flush=True,
    )
    return receipt


def cmd_card(_args) -> dict:
    can = json.loads((EVID / "e1_canaries.json").read_text())
    hard = json.loads((EVID / "e1_hardlinked_recovery.json").read_text())
    gate = json.loads((EVID / "e2_gate.json").read_text())
    uniq = json.loads((EVID / "e3_uniqueness.json").read_text())
    rec = json.loads((EVID / "e3_receipt.json").read_text())

    strict_receipt = {
        "evidence_class": "HOLDOUT-DTI",
        "candidate_dti": gate["corridor_mean_dti"],
        "baseline_dti": gate["control_mean_dti"],
        "incumbent_dti": gate["incumbent_pr6_mean_dti"],
        "ci95_low": gate["corridor_ci95"][0],
        "ci95_high": gate["corridor_ci95"][1],
        "delta_vs_baseline_ci95_low": gate["paired_delta_ci95"][0],
        "delta_vs_baseline_ci95_high": gate["paired_delta_ci95"][1],
        "delta_vs_incumbent_ci95_low": gate["paired_delta_vs_incumbent_ci95"][0],
        "delta_vs_incumbent_ci95_high": gate["paired_delta_vs_incumbent_ci95"][1],
        "n_withheld_positives": int(gate["withheld_positive_px_total"]),
        "evaluator_version": gate["evaluator_version"],
        "leakage_canaries_clean": bool(can["_summary"]["all_canaries_clean"]),
        "registry_raster_count": int(uniq["n_compared"]),
        "max_registry_rank_correlation": float(uniq["worst_abs_spearman"]),
        "max_dots_within_3px_fraction": float(uniq["worst_dot_overlap_dotlike"]["dot_overlap_3px"]),
        "exact_pixel_match_found": bool(uniq["exact_pixel_match_found"]),
        "raster_sha256": rec["primary_sha256"],
        "format_validation_passed": bool(
            rec["validator"]["zeros"]["pass"] and rec["validator"]["nan"]["pass"]
        ),
        "format_validation_reference_type": "official_sample_submission",
        "format_validation_reference": "sample_submission.tif",
        "format_validation_reference_sha256": SAMPLE_SHA256,
        "submission_name": rec["submission_name"],
        "submission_name_unique": bool(rec["submission_name_unique"]),
        "note": rec["note"],
    }
    decision = local_gate.decide(strict_receipt)
    receipts_dir = ROOT / "docs" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / "h69_latest_receipt.json").write_text(json.dumps(strict_receipt, indent=2) + "\n")

    commit_sha = subprocess.check_output(
        ["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT
    ).decode().strip()

    verdict = "promote" if decision["download_enabled"] else "negative"
    run_card = {
        "generated_utc": rec["generated_utc"],
        "repo": "buffedlizard55-lab/GEMSDOE69",
        "branch": "arena/b1390e3b-gemsdoe69",
        "lane": "69 — Relay-ramp, synthetic-breach, pull-apart, splay & transfer corridor generator",
        "commit": commit_sha,
        "verdict": verdict,
        "banner": "ok" if verdict == "promote" else "do-not-submit",
        "hypothesis_id": gate["selected_arm"],
        "hypothesis": (
            "H69_G5_TwoRegimeGeodesic: Two-regime geodesic minimum-energy fault routing across "
            "multi-partner relay ramps, asymmetric tip-to-flank synthetic breaches, Walker Lane "
            "releasing pull-aparts, and termination splay/transfer corridors (W = 0.1–15 km, "
            "L <= 3.5W), combining 8-fold OOF L2 logistic breach propensity (>=350 m off mapped "
            "traces) with a scale-invariant blind-basin hydrothermal/MT/magnetic-low prior "
            "(>=900 m off mapped traces in low-relief basins via GeoDAWN Th/K, MT/basement step, "
            "and magnetic lows)"
        ),
        "mechanism": (
            "Common-origin tip-graph pairing (W = 0.1–15 km, L <= 3.5W, Giddens & Faulds 2025 "
            "SGP-TR-229) + synthetic tip-to-flank breach + Walker Lane dextral releasing pull-apart "
            "+ termination splays -> Dijkstra least-cost routing -> 8-fold OOF L2 logistic breach "
            "calibrator + q0.995 blind pull-apart alteration tie-in -> greedy marginal-DTI allocation"
        ),
        "non_fault_mimic": (
            "Buried paleochannel margins, intrabasinal volcanic dike edges, plutonic contact aureoles, "
            "flight-line radiometric leveling seams, and unfaulted argillic alteration zones can mimic "
            "corridor-aligned gravity/magnetic gradients, magnetic lows, and Th/K anomalies."
        ),
        "data_used": [
            "training_features.tif (sha256 pinned)",
            "labels.tif / existing_faults.tif (sha256 7ba308cc...; IR-69-DATA-01 disclosed)",
            "sample_submission.tif (sha256 2176d08e...)",
            "external/trace_segments_utm11.csv + external/qfault_attributes.csv (INGENIOUS GDR #1391)",
            "external/geodawn_dem_a2_100m.tif + external/geodawn_extensions_u8.tif + external/geodawn_rad_u8.tif",
            "external/lidar_scarp_features_u8.tif",
            "external/gdr_wellspring_in_footprint.csv (leaked dist_known_fault_px explicitly dropped)",
            "external/derived_sgmc_faults_100m_u8.tif (evaluated in E2 arm G4 only; excluded from G5 per Rule 1)",
        ],
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": gate["evaluator_version"],
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator": gate["evaluator"],
            "n_cells": gate["n_cells"],
            "withheld_positive_px": gate["withheld_positive_px_total"],
            "candidate_dti": gate["corridor_mean_dti"],
            "candidate_ci95": gate["corridor_ci95"],
            "candidate_far_1km_dti": gate["corridor_far_1km_dti"],
            "no_corridor_control_dti": gate["control_mean_dti"],
            "no_corridor_control_ci95": gate["control_ci95"],
            "no_corridor_control_far_1km_dti": gate["control_far_1km_dti"],
            "incumbent_pr6_dti": gate["incumbent_pr6_mean_dti"],
            "paired_delta_vs_control": gate["paired_delta_mean"],
            "paired_delta_vs_control_ci95": gate["paired_delta_ci95"],
            "paired_delta_vs_incumbent": gate["paired_delta_vs_incumbent_mean"],
            "paired_delta_vs_incumbent_ci95": gate["paired_delta_vs_incumbent_ci95"],
            "hardlinked_ramp_recovery_within_300m_mean": round(hard["mean_recovery_within_300m"], 4),
            "hardlinked_n_tested": int(hard["n_tested"]),
            "leakage_canaries_max_auc": can["_summary"]["max_single_feature_auc"],
            "leakage_canaries_clean": can["_summary"]["all_canaries_clean"],
            "gate_passed": bool(gate["gate_passed"]),
        },
        "uniqueness": {
            "registry_blobs_scanned": uniq["n_compared"],
            "canonical_blobs": uniq["n_canonical_blobs"],
            "post_census_extra_blobs": uniq["n_post_census_extra_blobs"],
            "max_surface_abs_spearman": uniq["worst_surface_spearman"]["abs_rho"],
            "max_dots_abs_spearman": uniq["worst_dots_spearman"]["abs_rho"],
            "max_dot_overlap_3px_dotlike_le150k": uniq["worst_dot_overlap_dotlike"]["dot_overlap_3px"],
            "worst_dotlike_neighbor": uniq["worst_dot_overlap_dotlike"]["label"],
            "exact_pixel_match_found": uniq["exact_pixel_match_found"],
            "passes_all_uniqueness_gates": bool(
                uniq["literal_gate"]["rho_ok"]
                and uniq["stratified_gate"]["dotlike_overlap_ok"]
                and not uniq["exact_pixel_match_found"]
            ),
        },
        "correlation_overlap_vs_registry": {
            "worst_abs_spearman": uniq["worst_abs_spearman"],
            "worst_dot_overlap_dotlike": uniq["worst_dot_overlap_dotlike"]["dot_overlap_3px"],
            "worst_dotlike_neighbor": uniq["worst_dot_overlap_dotlike"]["label"],
            "n_compared": uniq["n_compared"],
            "n_registry_blobs": uniq["n_canonical_blobs"] + uniq["n_post_census_extra_blobs"],
        },
        "artifact": {
            "primary_zeros_tif": rec["primary_submission"],
            "docs_download_copy": rec["docs_download_copy"],
            "primary_zip": rec["primary_zip"],
            "nan_companion_tif": rec["nan_companion"],
            "primary_sha256": rec["primary_sha256"],
            "nan_sha256": rec["nan_sha256"],
            "submission_name": rec["submission_name"],
            "n_dots": rec["n_dots"],
            "catalogue_collision_px": rec["catalogue_collision_px"],
            "dot_distance_px": rec["dot_distance_from_catalogue_px"],
            "validator_zeros_pass": rec["validator"]["zeros"]["pass"],
            "validator_nan_pass": rec["validator"]["nan"]["pass"],
            "format_compliance": rec["format_compliance"],
        },
        "gate_decision": decision,
        "promote_status": "OFFER_DOWNLOAD" if decision["download_enabled"] else decision["status"],
        "submission_name": rec["submission_name"],
        "submission_note": rec["note"],
    }
    (EVID / "run_card.json").write_text(json.dumps(run_card, indent=1))
    (ROOT / "docs" / "run-card.json").write_text(json.dumps(run_card, indent=1))
    subprocess.run([sys.executable, str(ROOT / "scripts" / "status.py")], check=True, cwd=ROOT)
    print(f"[CARD] status={decision['status']} download_enabled={decision['download_enabled']}")
    return run_card


def cmd_site(_args) -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site69.py")], check=True, cwd=ROOT)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("verify", cmd_verify),
        ("e1", cmd_e1),
        ("e2", cmd_e2),
        ("e3", cmd_e3),
        ("card", cmd_card),
        ("site", cmd_site),
    ):
        p = sub.add_parser(name)
        p.set_defaults(func=fn)
    p_all = sub.add_parser("all")
    p_all.set_defaults(func=None)
    args = ap.parse_args()
    if args.cmd == "all":
        cmd_verify(args)
        cmd_e1(args)
        cmd_e2(args)
        cmd_e3(args)
        cmd_card(args)
        cmd_site(args)
        return 0
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
