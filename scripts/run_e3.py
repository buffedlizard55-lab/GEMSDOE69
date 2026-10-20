#!/usr/bin/env python3
"""Run Experiment 3 (Live H69-EFG Corridor Generation, Calibrated Greedy
Marginal-DTI Emission, Full 751/751 Two-Phase Registry Uniqueness Audit,
GeoTIFF Format Validation on Both -zeros and -nan Variants, Method Manifest,
and Release Gate Card Generation).
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))
sys.path.insert(0, str(ROOT / "scripts"))

import release_gate  # noqa: E402
import validate_submission  # noqa: E402
from gems57 import submission_writer as tsub  # noqa: E402
from gems57.uniqueness import JACCARD_LIMIT, OVERLAP_LIMIT, RHO_LIMIT  # noqa: E402
from gems69.data import DATA, load_grid as load_data_grid  # noqa: E402
from gems69.holdout69 import (  # noqa: E402
    CORRIDOR_COLS,
    CORE_PHYSICS_COLS,
    EXT_PHYSICS_COLS,
    FLANK_PX,
    fit_full_live_surface,
    load_template_grid,
)
from gems69.physics import build_layer_stats, build_z_stack  # noqa: E402
from gemsdoe66.uniqueness import DEFAULT_MAX_RHO, DEFAULT_MAX_WITHIN3  # noqa: E402

EVID = ROOT / "evidence"
SUBS = ROOT / "submissions"
REG_CACHE = ROOT / ".cache" / "registry"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def unit_rank_vec(vals_1d: np.ndarray) -> tuple[np.ndarray, bool]:
    r = rankdata(vals_1d, method="average").astype(np.float64)
    r -= r.mean()
    nrm = float(np.linalg.norm(r))
    if nrm <= 1e-12:
        return np.zeros_like(r), False
    r /= nrm
    return r, True


def write_geotiffs(emitted: np.ndarray, footprint: np.ndarray) -> tuple[Path, Path]:
    SUBS.mkdir(exist_ok=True)
    n_dots = int(emitted.sum())
    stem = f"h69-efg-kinematic-geodesic-{n_dots}"
    p_zeros = SUBS / f"{stem}-zeros.tif"
    p_nan = SUBS / f"{stem}-nan.tif"

    ref_path = DATA / "sample_submission.tif"
    with rasterio.open(ref_path) as ref:
        profile = ref.profile.copy()

    # 1. All-finite [-zeros.tif] matching h33-2-b2-zeros and template validator
    arr_zeros = np.where(footprint & emitted, 1.0, 0.0).astype(np.float32)
    prof_z = profile.copy()
    prof_z.update(dtype="float32", count=1, nodata=None, compress="deflate", predictor=2)
    with rasterio.open(p_zeros, "w", **prof_z) as dst:
        dst.write(arr_zeros, 1)

    # 2. Spec-literal outside-NaN twin [-nan.tif] via shared template writer / profile
    arr_nan = np.where(footprint, arr_zeros, np.nan).astype(np.float32)
    prof_n = profile.copy()
    prof_n.update(dtype="float32", count=1, nodata=float("nan"), compress="deflate", predictor=2)
    with rasterio.open(p_nan, "w", **prof_n) as dst:
        dst.write(arr_nan, 1)

    return p_zeros, p_nan


def lattice_diagnostic(emitted: np.ndarray, footprint: np.ndarray) -> dict:
    row_counts = emitted.sum(axis=1)
    col_counts = emitted.sum(axis=0)
    fp_rows = np.maximum(footprint.sum(axis=1), 1)
    fp_cols = np.maximum(footprint.sum(axis=0), 1)
    max_row_frac = float((row_counts / fp_rows).max())
    max_col_frac = float((col_counts / fp_cols).max())
    # Autocovariance check at lag 14 px (R14 lattice diagnostic)
    rc = row_counts.astype(np.float64) - row_counts.mean()
    cc = col_counts.astype(np.float64) - col_counts.mean()
    ac_r14 = float(np.dot(rc[:-14], rc[14:]) / max(np.dot(rc, rc), 1e-9))
    ac_c14 = float(np.dot(cc[:-14], cc[14:]) / max(np.dot(cc, cc), 1e-9))
    return dict(
        n_dots=int(emitted.sum()),
        max_row_fill_fraction=round(max_row_frac, 5),
        max_col_fill_fraction=round(max_col_frac, 5),
        lag14_row_autocorr=round(ac_r14, 5),
        lag14_col_autocorr=round(ac_c14, 5),
        lattice_artifact_detected=bool(max_row_frac > 0.25 or max_col_frac > 0.25),
    )


def load_registry_on_grid(
    tpath: Path, shape: tuple[int, int], dst_transform, dst_crs
) -> tuple[np.ndarray, str | None]:
    with rasterio.open(tpath) as src:
        raw = src.read(1)
        if raw.shape == shape:
            return raw.astype(np.float32), None
        # Exact georeferenced placement onto competition grid for non-3730x3292 test rasters
        out = np.zeros(shape, dtype=np.float32)
        reproject(
            source=raw.astype(np.float32),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs or dst_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
            src_nodata=src.nodata,
            dst_nodata=0.0,
        )
        note = f"reprojected_from_{raw.shape[0]}x{raw.shape[1]}"
        return out, note


def main() -> None:
    t0 = time.time()
    print("[E3] Loading template grid, v2 z-stack, and E2 live calibration bundle...", flush=True)
    grid = load_template_grid()
    fp = grid.footprint
    cat = grid.catalogue
    shape = fp.shape
    stats = build_layer_stats(fp)
    zstack = build_z_stack(fp, stats)

    bundle_path = ROOT / ".cache" / "gems_data" / "derived69" / "live_oof_bundle.npz"
    with np.load(bundle_path) as b:
        live_training_data = dict(
            X_e=[b["X_e"]],
            X_efg=[b["X_efg"]],
            y=[b["y"]],
            priors=list(b["priors"]),
        )

    # 1. Fit full-catalogue H69-EFG live surface + greedy marginal-DTI placement
    live_ckpt = ROOT / ".cache" / "gems_data" / "derived69" / "live_e3_surface.npz"
    if live_ckpt.exists() and (EVID / "e3_corridor_rationale.csv").exists():
        with np.load(live_ckpt) as lc:
            surface = lc["surface"].astype(np.float32)
            emitted = lc["emitted"].astype(bool)
            n_corrs_saved = int(lc["n_corridors"])
        print(f"[E3] Reusing live surface checkpoint: corridors={n_corrs_saved}, n_dots={int(emitted.sum())}", flush=True)
    else:
        t1 = time.time()
        live = fit_full_live_surface(
            cat, fp, stats, live_training_data,
            variant="h69_efg", flank_px=FLANK_PX, k_truth_live=85_000,
            zstack=zstack, seed=69,
        )
        surface = live["surface"]
        emitted = live["emitted"]
        corridors = live["pipe"]["corridors_obj"]
        n_corrs_saved = len(corridors)
        np.savez_compressed(live_ckpt, surface=surface, emitted=emitted, n_corridors=n_corrs_saved)
        print(f"[E3] Live surface + emission built in {time.time() - t1:.1f}s: "
              f"corridors={len(corridors)}, n_dots={live['n_dots']}", flush=True)

        # 2. Export geologist-auditable per-corridor rationale CSV & JSON
        csv_path = EVID / "e3_corridor_rationale.csv"
        full_rat = []
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow([
                "cid", "subtype", "kinematic_regime", "w_km", "along_km", "overlap_km",
                "separation_km", "dtheta_deg", "mean_az_deg", "score_S",
                "E_grav", "E_mag", "E_maglow", "E_scarp", "lidar_strike_concordance",
                "joint_phase_coherence", "E_extended", "sense_note", "dip_note", "signature",
            ])
            for c in corridors:
                r = c.rationale
                eg = r.get("evidence_groups", {})
                w.writerow([
                    c.cid, c.subtype, r.get("kinematic_regime", c.subtype),
                    r.get("w_km"), r.get("along_km"), r.get("overlap_km"),
                    r.get("separation_km"), r.get("dtheta_deg"), r.get("mean_az_deg"),
                    r.get("score_S"),
                    eg.get("E_grav"), eg.get("E_mag"), eg.get("E_maglow"), eg.get("E_scarp"),
                    eg.get("lidar_strike_concordance"), eg.get("joint_phase_coherence"),
                    eg.get("E_extended"), r.get("sense_note"), r.get("dip_note"),
                    r.get("signature"),
                ])
                full_rat.append(dict(cid=c.cid, bbox=list(c.bbox), npix=c.npix, rationale=r))
        (EVID / "e3_corridor_rationales_full.json").write_text(json.dumps(full_rat, indent=1))

    # 3. Write both GeoTIFF variants & run full format validator + R14 lattice diagnostic
    p_zeros, p_nan = write_geotiffs(emitted, fp)
    sha_zeros = sha256_file(p_zeros)
    sha_nan = sha256_file(p_nan)

    vgrid = load_data_grid()
    rep_zeros = validate_submission.check(p_zeros, vgrid)
    rep_nan = validate_submission.check(p_nan, vgrid)
    assert rep_zeros["all_checks_passed"], f"zeros failed validation: {rep_zeros}"
    assert rep_nan["all_checks_passed"], f"nan failed validation: {rep_nan}"

    val_payload = dict(
        validator="scripts/validate_submission.py",
        all_files_passed=True,
        reports=[rep_zeros, rep_nan],
    )
    (EVID / "e3_validator.json").write_text(json.dumps(val_payload, indent=2))
    (EVID / "e3_validation.json").write_text(json.dumps(val_payload, indent=2))

    lat_diag = lattice_diagnostic(emitted, fp)
    (EVID / "e3_r14_lattice_diagnostic.json").write_text(json.dumps(lat_diag, indent=2))
    print(f"[E3] Validated both GeoTIFFs PASS: zeros={p_zeros.name} ({sha_zeros[:16]}), "
          f"dots={live['n_dots']}, lattice={lat_diag['lattice_artifact_detected']}", flush=True)

    # 4. Full 751/751 zero-error two-phase uniqueness scan (BOTH surface AND final dots)
    t_u = time.time()
    with rasterio.open(DATA / "sample_submission.tif") as ref_ds:
        dst_transform, dst_crs = ref_ds.transform, ref_ds.crs

    prior_idx = json.loads((ROOT / "registry" / "prior_rasters.json").read_text())
    entries_751 = prior_idx["entries"] if "entries" in prior_idx else prior_idx["rasters"]
    assert len(entries_751) == 751, f"Expected 751 entries, found {len(entries_751)}"

    fp_flat = fp.ravel()
    surf_clean = np.where(fp & np.isfinite(surface), surface, 0.0).astype(np.float32)
    dots_clean = np.where(fp & emitted, 1.0, 0.0).astype(np.float32)
    pa_surf = surf_clean > 0
    pa_dots = dots_clean > 0
    n_surf = int(pa_surf.sum())
    n_dots = int(pa_dots.sum())

    rs_vec, rs_var = unit_rank_vec(surf_clean.ravel()[fp_flat])
    rd_vec, rd_var = unit_rank_vec(dots_clean.ravel()[fp_flat])
    dec_sha_surf = hashlib.sha256(np.ascontiguousarray(surf_clean).tobytes()).hexdigest()
    dec_sha_dots = hashlib.sha256(np.ascontiguousarray(dots_clean).tobytes()).hexdigest()

    surf_rows, dots_rows = [], []
    reprojected_notes = []

    for idx_i, ent in enumerate(entries_751):
        blob = ent.get("blob") or ent["git_blob_sha"]
        alias0 = (ent.get("aliases") or [{}])[0]
        repo_name = ent.get("repo") or alias0.get("repository", "unknown")
        rel_path = ent.get("path") or alias0.get("path", blob)
        tpath = REG_CACHE / f"{blob}.tif"
        file_sha = sha256_file(tpath)
        arr_o, note = load_registry_on_grid(tpath, shape, dst_transform, dst_crs)
        if note:
            reprojected_notes.append({"blob": blob, "repo": repo_name, "path": rel_path, "note": note})

        pb = np.isfinite(arr_o) & (arr_o > 0)
        n_other = int(pb.sum())
        o_clean = np.where(fp & np.isfinite(arr_o), arr_o, 0.0).astype(np.float32)
        dec_sha_o = hashlib.sha256(np.ascontiguousarray(o_clean).tobytes()).hexdigest()

        ro_vec, ro_var = unit_rank_vec(o_clean.ravel()[fp_flat])
        rho_s = float(rs_vec @ ro_vec) if (rs_var and ro_var) else 0.0
        rho_d = float(rd_vec @ ro_vec) if (rd_var and ro_var) else 0.0

        if n_other > 0:
            near_t = ndi.distance_transform_edt(~pb) <= 3.0
            null_w3 = float(near_t[fp].mean())
            w3_s = float(near_t[pa_surf].mean()) if n_surf else 0.0
            w3_d = float(near_t[pa_dots].mean()) if n_dots else 0.0
        else:
            null_w3 = 0.0
            w3_s = 0.0
            w3_d = 0.0

        lift_s = float(w3_s / null_w3) if null_w3 > 0 else 0.0
        lift_d = float(w3_d / null_w3) if null_w3 > 0 else 0.0

        inter_s = int((pa_surf & pb).sum())
        union_s = int((pa_surf | pb).sum())
        jac_s = float(inter_s / union_s) if union_s else 0.0

        inter_d = int((pa_dots & pb).sum())
        union_d = int((pa_dots | pb).sum())
        jac_d = float(inter_d / union_d) if union_d else 0.0

        sub_label = f"{repo_name}:{rel_path}"

        surf_rows.append(dict(
            blob=blob,
            sha256=file_sha,
            repo=repo_name,
            submission=sub_label,
            other_positive_pixels=n_other,
            spearman_full_footprint=round(rho_s, 6),
            my_dots_within_3px_of_theirs=round(w3_s, 6),
            null_within_3px_random_placement=round(null_w3, 6),
            lift_over_random=round(lift_s, 6),
            jaccard_dot_sets=round(jac_s, 6),
            identical_bytes=bool(file_sha == sha_zeros),
            identical_decoded_predictions=bool(dec_sha_o == dec_sha_surf),
            duplicate_by_rho=bool(abs(rho_s) > RHO_LIMIT),
            duplicate_by_overlap=bool(w3_s > OVERLAP_LIMIT),
            gemsdoe66_flagged=bool(abs(rho_s) > DEFAULT_MAX_RHO or (w3_s > DEFAULT_MAX_WITHIN3 and lift_s > 1.5)),
        ))
        dots_rows.append(dict(
            blob=blob,
            sha256=file_sha,
            repo=repo_name,
            submission=sub_label,
            other_positive_pixels=n_other,
            spearman_full_footprint=round(rho_d, 6),
            my_dots_within_3px_of_theirs=round(w3_d, 6),
            null_within_3px_random_placement=round(null_w3, 6),
            lift_over_random=round(lift_d, 6),
            jaccard_dot_sets=round(jac_d, 6),
            identical_bytes=bool(file_sha == sha_zeros),
            identical_decoded_predictions=bool(dec_sha_o == dec_sha_dots),
            duplicate_by_rho=bool(abs(rho_d) > RHO_LIMIT),
            duplicate_by_overlap=bool(w3_d > OVERLAP_LIMIT),
            gemsdoe66_flagged=bool(abs(rho_d) > DEFAULT_MAX_RHO or (w3_d > DEFAULT_MAX_WITHIN3 and lift_d > 1.5)),
        ))
        if (idx_i + 1) % 150 == 0 or idx_i + 1 == len(entries_751):
            print(f"  [uniqueness] scanned {idx_i + 1}/{len(entries_751)} blobs ({time.time() - t_u:.1f}s)", flush=True)

    # Save full row tables for auditability
    with open(EVID / "e3_uniqueness_surface_rows.jsonl", "w") as fs:
        for r in surf_rows:
            fs.write(json.dumps(r) + "\n")
    with open(EVID / "e3_uniqueness_dots_rows.jsonl", "w") as fd:
        for r in dots_rows:
            fd.write(json.dumps(r) + "\n")
    (EVID / "e3_uniqueness_rows.json").write_text(json.dumps(dots_rows, indent=1))

    def build_phase_doc(phase_name: str, rows: list[dict], my_cnt: int, dec_sha: str) -> dict:
        max_abs_rho_row = max(rows, key=lambda r: abs(r["spearman_full_footprint"]))
        max_ov_row = max(rows, key=lambda r: r["my_dots_within_3px_of_theirs"])
        dotlike_rows = [r for r in rows if 0 < r["other_positive_pixels"] <= 200_000]
        max_dotlike_ov = max(dotlike_rows, key=lambda r: r["my_dots_within_3px_of_theirs"])
        max_dotlike_rho = max(dotlike_rows, key=lambda r: abs(r["spearman_full_footprint"]))
        g66_flags = [r for r in rows if r["gemsdoe66_flagged"]]
        lit_flags = [r for r in rows if r["duplicate_by_rho"] or r["duplicate_by_overlap"]
                     or r["identical_bytes"] or r["identical_decoded_predictions"]]
        return {
            "phases": {
                phase_name: {
                    "summary": {
                        "candidate_file": str(p_zeros.relative_to(ROOT)),
                        "candidate_file_sha256": sha_zeros,
                        "candidate_decoded_sha256": dec_sha,
                        "my_positive_pixels": my_cnt,
                        "n_registry_blobs": 751,
                        "n_compared": len(rows),
                        "n_errors": 0,
                        "complete_accessible_scan": len(rows) == 751,
                        "max_abs_spearman": abs(max_abs_rho_row["spearman_full_footprint"]),
                        "argmax_spearman": max_abs_rho_row["submission"],
                        "literal_max_within_3px": max_ov_row["my_dots_within_3px_of_theirs"],
                        "argmax_literal_within_3px": max_ov_row["submission"],
                        "literal_duplicate_count": len(lit_flags),
                        "stop_required": len(lit_flags) > 0,
                        "dotlike_subset_le_200k": {
                            "n_rasters": len(dotlike_rows),
                            "max_within_3px": max_dotlike_ov["my_dots_within_3px_of_theirs"],
                            "argmax_within_3px": max_dotlike_ov["submission"],
                            "max_abs_spearman": abs(max_dotlike_rho["spearman_full_footprint"]),
                            "dotlike_overlap_ok": max_dotlike_ov["my_dots_within_3px_of_theirs"] <= OVERLAP_LIMIT,
                        },
                        "gemsdoe66_upstream_gate": {
                            "module": "vendor/template66/gemsdoe66/uniqueness.py",
                            "upstream_commit": "buffedlizard55-lab/GEMSDOE66@29519311",
                            "flagged_count": len(g66_flags),
                            "verdict": "UNIQUE" if not g66_flags else "DUPLICATE",
                        },
                        "reprojected_non_standard_rasters": reprojected_notes,
                    }
                }
            }
        }

    surf_doc = build_phase_doc("surface", surf_rows, n_surf, dec_sha_surf)
    dots_doc = build_phase_doc("dots", dots_rows, n_dots, dec_sha_dots)
    (EVID / "e3_uniqueness_surface.json").write_text(json.dumps(surf_doc, indent=2))
    (EVID / "e3_uniqueness_dots.json").write_text(json.dumps(dots_doc, indent=2))

    ds = dots_doc["phases"]["dots"]["summary"]
    ss = surf_doc["phases"]["surface"]["summary"]
    uniq_agg = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        my_file=str(p_zeros.relative_to(ROOT)),
        my_sha256=sha_zeros,
        n_dots=n_dots,
        n_registry_blobs=751,
        n_compared=751,
        n_errors=0,
        literal_gate=dict(
            rho_ok=bool(ds["max_abs_spearman"] <= RHO_LIMIT and ss["max_abs_spearman"] <= RHO_LIMIT),
            overlap_ok=bool(ds["literal_max_within_3px"] <= OVERLAP_LIMIT and ss["literal_max_within_3px"] <= OVERLAP_LIMIT),
            dots_max_abs_spearman=ds["max_abs_spearman"],
            surface_max_abs_spearman=ss["max_abs_spearman"],
            dots_max_within_3px=ds["literal_max_within_3px"],
            surface_max_within_3px=ss["literal_max_within_3px"],
            argmax_dots_spearman=ds["argmax_spearman"],
            argmax_dots_overlap=ds["argmax_literal_within_3px"],
            blocker_explanation=(
                "Whole-footprint continuous soft surfaces in the family registry (positive on ~100% of "
                "footprint pixels, documented upstream as IR-66-GATE-01 and in vendor/gems57/uniqueness.py) "
                "yield literal (theirs > 0) overlap = 1.000 against every possible non-empty candidate. "
                "Under strict fail-closed policy, literal duplicate-and-stop is honoured without override."
            ),
        ),
        stratified_gate=ds["dotlike_subset_le_200k"],
        gemsdoe66_upstream_gate=dict(
            surface_verdict=ss["gemsdoe66_upstream_gate"]["verdict"],
            dots_verdict=ds["gemsdoe66_upstream_gate"]["verdict"],
            surface_flagged=ss["gemsdoe66_upstream_gate"]["flagged_count"],
            dots_flagged=ds["gemsdoe66_upstream_gate"]["flagged_count"],
        ),
        top15_dots_by_spearman=sorted(dots_rows, key=lambda r: -abs(r["spearman_full_footprint"]))[:15],
        top15_dotlike_by_overlap=sorted(
            [r for r in dots_rows if 0 < r["other_positive_pixels"] <= 200_000],
            key=lambda r: -r["my_dots_within_3px_of_theirs"],
        )[:15],
    )
    (EVID / "e3_uniqueness.json").write_text(json.dumps(uniq_agg, indent=2))

    # 5. Bind artifact SHA-256 to e1_canaries.json, e2_gate.json, e3_method_manifest.json, e3_receipt.json
    can_doc = json.loads((EVID / "e1_canaries.json").read_text())
    can_doc["artifact_sha256"] = sha_zeros
    (EVID / "e1_canaries.json").write_text(json.dumps(can_doc, indent=2))

    e2_doc = json.loads((EVID / "e2_gate.json").read_text())
    all_efg = e2_doc["primary_mode_all"]["summaries"]["h69_efg"]
    all_ctl = e2_doc["primary_mode_all"]["summaries"]["no_prior_control"]
    all_cmp = e2_doc["primary_mode_all"]["comparisons"]["h69_efg_vs_no_prior_control"]
    e2_doc["gate_passed"] = bool(e2_doc["control_beaten"] and e2_doc["current_best_beaten"])
    e2_doc["corridor_pooled_dti"] = all_efg["pooled_dti"]
    e2_doc["corridor_boot_ci95"] = all_efg["boot_ci95"]
    e2_doc["control_pooled_dti"] = all_ctl["pooled_dti"]
    e2_doc["paired_delta_dti"] = all_cmp["pooled_delta_dti"]
    e2_doc["paired_boot_ci95"] = all_cmp["boot_ci95"]
    e2_doc["withheld_positive_px_total"] = all_efg["total_withheld_truth_px"]
    e2_doc["n_cells"] = all_efg["n_cells"]
    e2_doc["artifact_sha256"] = sha_zeros
    (EVID / "e2_gate.json").write_text(json.dumps(e2_doc, indent=2))

    source_files = [
        "src/gems69/data.py",
        "src/gems69/physics.py",
        "src/gems69/tips.py",
        "src/gems69/corridors.py",
        "src/gems69/scoring.py",
        "src/gems69/holdout69.py",
        "scripts/run_e1_e2.py",
        "scripts/run_e3.py",
    ]
    all_features = CORE_PHYSICS_COLS + EXT_PHYSICS_COLS + CORRIDOR_COLS
    manifest = dict(
        artifact_sha256=sha_zeros,
        variant="h69_efg",
        feature_names=all_features,
        source_sha256={rel: sha256_file(ROOT / rel) for rel in source_files},
    )
    (EVID / "e3_method_manifest.json").write_text(json.dumps(manifest, indent=2))

    sub_note = (
        f"H69-EFG kinematic geodesic relay/pull-apart + physics; "
        f"HOLDOUT-DTI 0.0727 vs 0.0472 ctrl (+53.9%); {n_dots} dots; UNSCORED"
    )[:140]
    receipt = dict(
        experiment="E3_live_build_validation_and_registry_audit",
        submission_name=p_zeros.name,
        submission_note=sub_note,
        n_corridors=n_corrs_saved,
        n_dots=n_dots,
        lattice_diagnostic=lat_diag,
        raster=dict(
            zeros=dict(path=str(p_zeros.relative_to(ROOT)), sha256=sha_zeros, bytes=p_zeros.stat().st_size),
            nan=dict(path=str(p_nan.relative_to(ROOT)), sha256=sha_nan, bytes=p_nan.stat().st_size),
        ),
        validator=val_payload,
    )
    (EVID / "e3_receipt.json").write_text(json.dumps(receipt, indent=2))

    # 6. Run official release_gate.write_card()
    card = release_gate.write_card(ROOT)
    print("\n================ RELEASE GATE DECISION ================")
    print(json.dumps(card["release_policy"], indent=2))
    print(f"[E3] Complete in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
