#!/usr/bin/env python3
"""Run Experiment 1 (Leakage Canaries + Hard-Linked Ramp Recovery) and
Experiment 2 (Paired Spatially-Blocked Holdout Gate on `all` & `detached`
+ Head-to-Head Evaluation of Archived GEMSDOE69 Rasters & GEMSDOE32 Champion).

Every holdout score emitted here is strictly HOLDOUT-DTI on the byte-pinned
shared evaluator (`gems57.holdout` / `gems57.metric`: pooled DTI, alpha=0.2,
beta=0.8, 300 m triangular kernel, 5,000-resample paired spatial-block bootstrap).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))

from gems57 import holdout as thold
from gems69.holdout69 import (
    FLANK_PX,
    cell_allowed,
    hardlinked_recovery,
    leakage_canary,
    load_template_grid,
    paired_bootstrap_diff,
    pooled_bootstrap_summary,
    run_spatial_oof_benchmark,
)
from gems69.physics import build_layer_stats, build_z_stack

EVID = ROOT / "evidence"
EVID.mkdir(exist_ok=True)


def main() -> None:
    t0 = time.time()
    print("[E1/E2] Loading shared template grid & building leak-free v2 physics z-stack...")
    grid = load_template_grid()
    fp = grid.footprint
    shape = fp.shape
    stats = build_layer_stats(fp)
    zstack = build_z_stack(fp, stats)
    print(f"[E1/E2] Built {len(zstack)}-layer physics z-stack in {time.time() - t0:.1f}s")

    # Build shared holdout context across BOTH 'all' and 'detached' modes (seeds 20, 21)
    ctx = thold.build_holdout(grid, seeds=(20, 21), modes=("all", "detached"))
    print(f"[E1/E2] Built HoldoutContext with {len(ctx.cells)} cells "
          f"(all truth={sum(c.n_truth for c in ctx.cells if c.mode=='all')}, "
          f"detached truth={sum(c.n_truth for c in ctx.cells if c.mode=='detached')})")

    # --- EXPERIMENT 1A: Single-feature leakage canaries ---
    canary_path = EVID / "e1_canaries.json"
    if canary_path.exists():
        canary = json.loads(canary_path.read_text())
        print(f"[E1A] Reusing completed canary: max={canary['_summary']['max_single_feature']} "
              f"AUC={canary['_summary']['max_single_auc']:.4f}")
    else:
        t1 = time.time()
        canary = leakage_canary(ctx, stats, zstack=zstack)
        canary_path.write_text(json.dumps(canary, indent=2))
        print(f"[E1A] Leakage canary complete in {time.time() - t1:.1f}s: "
              f"max={canary['_summary']['max_single_feature']} "
              f"AUC={canary['_summary']['max_single_auc']:.4f} "
              f"(pass={canary['_summary']['canary_pass']})")

    # --- EXPERIMENT 1B: 300 m hard-linked relay-ramp masking recovery ---
    hl_path = EVID / "e1_hardlinked_recovery.json"
    if hl_path.exists():
        hl = json.loads(hl_path.read_text())
        print(f"[E1B] Reusing completed hard-link recovery: tested={hl.get('n_tested')}, "
              f"mean_300m={hl.get('mean_recovery_within_300m')}")
    else:
        t2 = time.time()
        hl = hardlinked_recovery(
            grid.catalogue, shape, stats, max_ramps=80, w_max=60.0,
            zstack=zstack, footprint=fp,
        )
        hl_path.write_text(json.dumps(hl, indent=2))
        print(f"[E1B] Hard-linked ramp recovery complete in {time.time() - t2:.1f}s: "
              f"tested={hl.get('n_tested', 0)}, "
              f"mean_300m={hl.get('mean_recovery_within_300m')}, "
              f"median_300m={hl.get('median_recovery_within_300m')}, "
              f">=70%={hl.get('n_ramps_above_70pct')}/{hl.get('n_tested', 0)}")

    # --- EXPERIMENT 2: Paired spatially-blocked OOF benchmark ('all' + 'detached') ---
    bundle_dir = ROOT / ".cache" / "gems_data" / "derived69"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    by_mode = {}
    for m_name in ("all", "detached"):
        ckpt = EVID / f"e2_mode_{m_name}.json"
        if ckpt.exists():
            by_mode[m_name] = json.loads(ckpt.read_text())
            print(f"[E2] Reusing completed mode='{m_name}' checkpoint ({ckpt.name})", flush=True)
            continue
        t3 = time.time()
        sub_bench = run_spatial_oof_benchmark(
            ctx, stats, modes=(m_name,), flank_px=FLANK_PX, zstack=zstack,
        )
        by_mode[m_name] = sub_bench["by_mode"][m_name]
        ckpt.write_text(json.dumps(by_mode[m_name], indent=2))
        if m_name == "all":
            np.savez_compressed(
                bundle_dir / "live_oof_bundle.npz",
                X_e=np.vstack(sub_bench["live_training_data"]["X_e"]),
                X_efg=np.vstack(sub_bench["live_training_data"]["X_efg"]),
                y=np.concatenate(sub_bench["live_training_data"]["y"]),
                priors=np.array(sub_bench["live_training_data"]["priors"], dtype=np.float64),
            )
        print(f"[E2] Completed & saved mode='{m_name}' in {time.time() - t3:.1f}s", flush=True)
    bench = {"by_mode": by_mode}

    # Head-to-head score of archived GEMSDOE69 candidates & GEMSDOE32 h33-2-b2 on identical cells
    archived_eval = {}
    ref_files = {
        "prior_h69_a_35787": ROOT / "submissions" / "h69-relayramp-pullapart-35787-zeros.tif",
        "prior_h69_d_31994": ROOT / "submissions" / "h69-z-radiometric-halo-31994-zeros.tif",
        "gemsdoe32_h33_2_b2_ref": ROOT / ".cache" / "registry" / "b3460322770019b82dc7f93a17284a85d47cb4ab.tif",
    }
    for label, rpath in ref_files.items():
        if not rpath.exists():
            continue
        with rasterio.open(rpath) as src:
            arr = src.read(1)
        em = np.isfinite(arr) & (arr > 0)
        archived_eval[label] = {}
        for mode in ("all", "detached"):
            cells_m = {}
            for cell in [c for c in ctx.cells if c.mode == mode]:
                visible = ctx.visible(cell.key)
                offcat_vis = ndi.distance_transform_edt(~visible) > FLANK_PX
                allowed = cell_allowed(cell, shape) & offcat_vis
                cells_m[cell.key] = thold.score_cell(cell, em & allowed)
            archived_eval[label][mode] = dict(
                summary=pooled_bootstrap_summary(cells_m),
                raw_cells=cells_m,
            )

    all_s = bench["by_mode"]["all"]["summaries"]
    all_c = bench["by_mode"]["all"]["comparisons"]
    det_s = bench["by_mode"]["detached"]["summaries"]
    det_c = bench["by_mode"]["detached"]["comparisons"]

    # Determine best new arm strictly by HOLDOUT-DTI across 'all' and 'detached'
    best_arm = "h69_efg" if all_s["h69_efg"]["pooled_dti"] >= all_s["h69_e"]["pooled_dti"] else "h69_e"
    vs_ctrl_key = f"{best_arm}_vs_no_prior_control"

    # Also compute direct paired comparison against archived GEMSDOE69 submissions on same cells
    prior_h69_best_dti = max(
        [0.00805] + [
            archived_eval[k]["all"]["summary"]["pooled_dti"]
            for k in ("prior_h69_a_35787", "prior_h69_d_31994")
            if k in archived_eval
        ]
    )
    control_beaten = bool(
        all_c[vs_ctrl_key]["pooled_delta_dti"] > 0.0
        and all_c[vs_ctrl_key]["boot_ci95"][0] > 0.0
    )
    current_best_beaten = bool(all_s[best_arm]["pooled_dti"] > prior_h69_best_dti)

    e2_gate = dict(
        experiment="E2_paired_spatial_holdout_gate_v2",
        evidence_class="HOLDOUT-DTI",
        evaluator="vendor/gems57/holdout.py::score_cell + pooled DTI (alpha=0.2, beta=0.8, 300m triangular kernel)",
        bootstrap_resamples=5000,
        selected_variant=best_arm,
        primary_mode_all=bench["by_mode"]["all"],
        conservative_mode_detached=bench["by_mode"]["detached"],
        archived_reference_scores={
            k: {m: archived_eval[k][m]["summary"] for m in archived_eval[k]}
            for k in archived_eval
        },
        note_on_gemsdoe32_h33_2_b2=(
            "h33-2-b2-zeros explicitly masks a 200 m flank around the FULL existing_faults.tif "
            "catalogue (including the 20% withheld holdout segments!), so on a retrospective "
            "catalogue holdout its frozen live raster has zero dots inside 200 m of withheld "
            "segments by construction. Its live leaderboard report is 0.2778 "
            "(USER-REPORTED-NOT-ORGANIZER-CONFIRMED on GEMSDOE32)."
        ),
        prior_gemsdoe69_best_holdout_dti=prior_h69_best_dti,
        control_beaten=control_beaten,
        current_best_beaten=current_best_beaten,
        canary_pass=canary["_summary"]["canary_pass"],
        elapsed_seconds=round(time.time() - t0, 2),
    )
    (EVID / "e2_gate.json").write_text(json.dumps(e2_gate, indent=2))

    print("\n================ E2 GATE SUMMARY (HOLDOUT-DTI) ================")
    for mode_name, ms, mc in [("all", all_s, all_c), ("detached", det_s, det_c)]:
        print(f"Mode = {mode_name}:")
        for arm in ("h69_efg", "h69_e", "no_prior_control", "uncalibrated_corridor", "uncalibrated_control"):
            s = ms[arm]
            print(f"  {arm:24s}: pooled_dti={s['pooled_dti']:.6f}  "
                  f"95%CI={s['boot_ci95']}  dots={s['total_emitted_dots']}  truth={s['total_withheld_truth_px']}")
        for ck, cv in mc.items():
            print(f"  diff {ck:32s}: delta={cv['pooled_delta_dti']:+.6f}  "
                  f"95%CI={cv['boot_ci95']}  wins={cv['wins_over_cells']}")
    print(f"Prior GEMSDOE69 best HOLDOUT-DTI (all): {prior_h69_best_dti:.6f}")
    print(f"Selected variant: {best_arm} | control_beaten={control_beaten} | "
          f"current_best_beaten={current_best_beaten}")


if __name__ == "__main__":
    main()
