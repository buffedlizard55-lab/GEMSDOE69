#!/usr/bin/env python3
"""GEMSDOE69 lane runner: verify | e1 | e2 | e3 | unique | site.

e1  leakage canaries + hard-linked ramp recovery + tip-graph census
e2  hide-and-recover gate: corridor arm vs no-corridor-prior control
e3  final emission + submission write + validator + receipt
unique  full-registry lane-drift scan (751 pinned blobs)

All DTI numbers produced here are HOLDOUT-DTI (evaluator gems57 pooled-hide-v2
family; alpha 0.2, beta 0.8, 300 m triangular kernel) unless labelled otherwise.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))

EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def dump(name: str, obj) -> Path:
    p = EVIDENCE / name
    p.write_text(json.dumps(obj, indent=1, default=str))
    return p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_verify() -> int:
    import rasterio
    from gems57 import grid as tgrid

    g = tgrid.load_grid(data_dir=ROOT / "data" / "bridge")
    facts = dict(
        crs=str(g.crs), height=g.height, width=g.width,
        transform=list(g.transform)[:6], footprint_px=int(g.footprint.sum()),
        catalogue_px=int(g.catalogue.sum()),
        sha256_labels=sha256_file(ROOT / "data" / "bridge" / "labels.tif"),
        sha256_sample_submission=sha256_file(ROOT / "data" / "bridge" / "sample_submission.tif"),
        sha256_existing_faults=sha256_file(ROOT / "data" / "bridge" / "existing_faults.tif"),
        irregularity=("existing_faults.tif is byte-identical to labels.tif in every family "
                      "mirror (IR-69-DATA-01); the public labels raster IS the mapped "
                      "catalogue; scored truth is unpublished (see gems57/grid.py docstring)"),
        generated_utc=utcnow(),
    )
    dump("verify_grid.json", facts)
    with rasterio.open(ROOT / ".cache" / "gems_data" / "training_features.tif") as src:
        bands = {i + 1: d for i, d in enumerate(src.descriptions)}
    with rasterio.open(ROOT / ".cache" / "gems_data" / "external" / "lidar_scarp_features_u8.tif") as src:
        lidar = {i + 1: d for i, d in enumerate(src.descriptions)}
    dump("band_metadata.json", dict(training_features=bands, lidar_scarp=lidar,
                                    source="read from GeoTIFF band descriptions (this session)",
                                    sha256_training_features=sha256_file(
                                        ROOT / ".cache" / "gems_data" / "training_features.tif")))
    print(json.dumps(facts, indent=1))
    return 0


def _stats(footprint):
    from gems69.physics import build_layer_stats
    return build_layer_stats(footprint)


def cmd_e1() -> int:
    from gems69.holdout69 import (hardlinked_recovery, leakage_canary,
                                  load_template_grid)
    from gems69.tips import vectorize
    from gems69.corridors import build_corridors

    t0 = time.time()
    g = load_template_grid()
    stats = _stats(g.footprint)
    strands = vectorize(g.catalogue)
    corridors, pairs = build_corridors(g.catalogue, strands, g.footprint.shape)
    census = dict(catalogue_px=int(g.catalogue.sum()), n_strands=len(strands),
                  n_tip_pairs=len(pairs), n_corridors=len(corridors),
                  n_pull_apart=sum(c.subtype == "pull-apart" for c in corridors),
                  n_transfer_overlap=sum(c.subtype == "transfer-overlap" for c in corridors),
                  w_km=[round(p.w_px / 10, 2) for p in pairs][:2000])
    dump("e1_tipgraph_census.json", dict(**census, generated_utc=utcnow(),
                                          seconds=round(time.time() - t0, 1)))
    print("[e1] census:", {k: census[k] for k in
                           ("n_strands", "n_tip_pairs", "n_corridors",
                            "n_pull_apart", "n_transfer_overlap")})

    t0 = time.time()
    rec = hardlinked_recovery(g.catalogue, g.footprint.shape, stats)
    rec["evidence_class"] = "HOLDOUT-GEOMETRY"
    rec["generated_utc"] = utcnow()
    rec["seconds"] = round(time.time() - t0, 1)
    dump("e1_hardlinked_recovery.json", rec)
    print("[e1] hard-linked recovery:", {k: rec.get(k) for k in
                                         ("n_hardlinked_found", "n_tested",
                                          "mean_recovery_within_300m")})

    from gems57 import holdout as thold
    ctx = thold.build_holdout(g, seeds=(20,), modes=("all",))
    t0 = time.time()
    can = leakage_canary(ctx, stats)
    can["evidence_class"] = "LEAKAGE-CANARY"
    can["rule"] = "single-feature AUC > 0.90 on the holdout = leakage until proven otherwise"
    can["generated_utc"] = utcnow()
    can["seconds"] = round(time.time() - t0, 1)
    dump("e1_canaries.json", can)
    worst = max(((k, v) for k, v in can.items()
                 if isinstance(v, dict) and v.get("auc") is not None),
                key=lambda kv: kv[1]["auc"], default=(None, {"auc": None}))
    print("[e1] worst canary AUC:", worst)
    return 0


def cmd_e2(seeds=(20, 21), modes=("all",)) -> int:
    from gems57 import holdout as thold
    from gems69.holdout69 import (load_template_grid, pooled_from_results,
                                  run_holdout_arms)

    g = load_template_grid()
    stats = _stats(g.footprint)
    ctx = thold.build_holdout(g, seeds=seeds, modes=modes)
    t0 = time.time()
    results = run_holdout_arms(ctx, stats, modes=modes)
    cor = pooled_from_results(results, "corridor")
    ctrl = pooled_from_results(results, "control")
    dtis_cor = np.array([results[k]["corridor"]["dti"] for k in sorted(results)])
    dtis_ctrl = np.array([results[k]["control"]["dti"] for k in sorted(results)])
    d = dtis_cor - dtis_ctrl
    gate = dict(
        evidence_class="HOLDOUT-DTI",
        evaluator="vendor/template66 gems57 pooled hide-and-recover "
                  "(alpha=0.2 beta=0.8 R=300m triangular kernel; seeds=%s modes=%s)" % (list(seeds), list(modes)),
        n_cells=len(results),
        corridor_mean_dti=float(dtis_cor.mean()),
        corridor_ci95_half=1.96 * float(dtis_cor.std(ddof=1)) / np.sqrt(len(dtis_cor)),
        control_mean_dti=float(dtis_ctrl.mean()),
        control_ci95_half=1.96 * float(dtis_ctrl.std(ddof=1)) / np.sqrt(len(dtis_ctrl)),
        paired_delta_mean=float(d.mean()),
        paired_delta_ci95_half=1.96 * float(d.std(ddof=1)) / np.sqrt(len(d)),
        gate_passed=bool(d.mean() > 0 and (d > 0).sum() >= max(1, int(np.ceil(0.75 * len(d))))),
        withheld_positive_px_total=int(sum(results[k]["corridor"]["n_truth"] for k in results)),
        corridor=cor, control=ctrl,
        seconds=round(time.time() - t0, 1),
        generated_utc=utcnow(),
        note=("gate: corridor arm must beat the same pipeline without corridor priors "
              "(paired over folds); holdout DTI is a SCREEN, not a leaderboard projection "
              "(GEMSDOE32 instrument-calibration evidence: cross-family Spearman rho=0.51, p~0.09)"),
    )
    dump("e2_gate.json", gate)
    print(json.dumps({k: gate[k] for k in ("corridor_mean_dti", "control_mean_dti",
                                           "paired_delta_mean", "gate_passed",
                                           "withheld_positive_px_total")}, indent=1))
    return 0


def cmd_e3(s0: float | None = None) -> int:
    from gems57 import grid as tgrid
    from gems57.emit import greedy_allocate
    from gems69.holdout69 import corridor_pipeline, load_template_grid
    from gems69.scoring import S0_DEFAULT
    from scipy import ndimage as ndi

    s0 = S0_DEFAULT if s0 is None else s0
    g = load_template_grid()
    stats = _stats(g.footprint)
    t0 = time.time()
    pipe = corridor_pipeline(g.catalogue, g.footprint.shape, stats, max_corridors=1200)
    p = pipe["propensity"]
    flank = ndi.distance_transform_edt(~g.catalogue) > 2     # 200 m catalogue flank prune
    allowed = g.footprint & flank & (p > 0)
    K_TRUTH = 12691   # GEMSDOE32 emission_models_mc.json: receipt-derived prior (cited)
    alloc = greedy_allocate(p, allowed, K_TRUTH, floor=0.05, max_dots=250_000,
                            candidate_cap=300_000)
    dots = alloc.emitted & allowed
    n_dots = int(dots.sum())
    print(f"[e3] corridors={pipe['corridors']} dots={n_dots} "
          f"seconds={time.time() - t0:.0f}")

    values = np.zeros(g.footprint.shape, np.float32)
    values[dots] = 1.0
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    h8 = hashlib.sha256(p.tobytes()).hexdigest()[:8]
    base = f"h69-relayramp-pullapart-{n_dots}-{stamp}-{h8}"
    sub = ROOT / "submissions"
    sub.mkdir(exist_ok=True)
    rec_z = tgrid.write_submission(sub / f"{base}-zeros.tif", values, mode="zeros")
    values_nan = values.copy()
    values_nan[~g.footprint] = np.nan
    rec_n = tgrid.write_submission(sub / f"{base}-nan.tif", values_nan, mode="nan")

    from gems.validate_submission import validate
    vz = validate(sub / f"{base}-zeros.tif", reference_path=ROOT / "data" / "bridge" / "sample_submission.tif")
    vn = validate(sub / f"{base}-nan.tif", reference_path=ROOT / "data" / "bridge" / "sample_submission.tif")

    rationale = [c.rationale for c in pipe["corridors_obj"] if "score_S" in c.rationale]
    rationale.sort(key=lambda r: -r["score_S"])
    receipt = dict(
        evidence_class="SUBMISSION-RECEIPT",
        generated_utc=stamp, hypothesis_id="H69-relayramp-pullapart",
        s0_calibrated=s0, k_truth_prior=K_TRUTH,
        k_truth_source=("GEMSDOE32 evidence/emission_models_mc.json truth_px=12691, "
                        "source 'GEMSDOE25 H28 (owner-report-derived prior)'"),
        n_corridors=pipe["corridors"], n_pairs=pipe["pairs"], n_strands=pipe["strands"],
        n_dots=n_dots, catalogue_collision_px=int((dots & g.catalogue).sum()),
        raster=dict(
            zeros=dict(path=rec_z["path"], sha256=sha256_file(Path(rec_z["path"])),
                       bytes=Path(rec_z["path"]).stat().st_size),
            nan=dict(path=rec_n["path"], sha256=sha256_file(Path(rec_n["path"])),
                     bytes=Path(rec_n["path"]).stat().st_size)),
        validator=dict(zeros=vz, nan=vn),
        propensity_sha256=h8,
        top_corridors=rationale[:25],
        note=("relay-ramp/pull-apart corridors from tip graph; HG+tilt grav/mag + lidar scarp; "
              "greedy marginal-DTI; 200m flank-pruned")[:140],
    )
    dump("e3_receipt.json", receipt)
    dump("e3_validator.json", dict(zeros=vz, nan=vn, generated_utc=stamp))
    print(json.dumps({"dots": n_dots, "validator_zeros_passed": vz.get("passed"),
                      "validator_nan_passed": vn.get("passed")}, indent=1))
    return 0


def cmd_unique() -> int:
    """Full-registry lane-drift scan (surface Spearman + 3 px dot overlap)."""
    import rasterio
    from scipy import ndimage as ndi
    from scipy.stats import rankdata, spearmanr

    man = json.loads((ROOT / "registry" / "prior_rasters.json").read_text())
    reg_dir = ROOT / ".cache" / "registry"
    subs = sorted((ROOT / "submissions").glob("h69-*-zeros.tif"))
    if not subs:
        print("no submission to scan; run e3 first")
        return 1
    mine_path = subs[-1]
    with rasterio.open(mine_path) as src:
        mine = src.read(1).astype(np.float32)
    fp = np.isfinite(mine)
    mine_dots = np.isfinite(mine) & (mine > 0)
    n_my_dots = int(mine_dots.sum())
    rows, errors = [], []
    t0 = time.time()
    entries = man["rasters"]
    for n, e in enumerate(entries, 1):
        blob = e["git_blob_sha"]
        path = reg_dir / f"{blob}.tif"
        if not path.exists():
            errors.append({"blob": blob, "err": "missing"})
            continue
        try:
            with rasterio.open(path) as src:
                if (src.height, src.width) != mine.shape:
                    errors.append({"blob": blob, "err": f"shape {src.height}x{src.width}"})
                    continue
                theirs = src.read(1).astype(np.float32)
            tpos = np.isfinite(theirs) & (theirs > 0)
            n_their = int(tpos.sum())
            strat = ("universal" if n_their > 1_000_000
                     else "bigdot" if n_their > 150_000 else "dotlike")
            # surface spearman over mutually finite cells
            both = fp & np.isfinite(theirs)
            if both.sum() > 10_000 and mine[both].std() > 0 and theirs[both].std() > 0:
                rho = float(spearmanr(mine[both], theirs[both]).statistic)
            else:
                rho = None
            if n_their > 0 and n_my_dots > 0:
                near = ndi.binary_dilation(tpos, iterations=3)
                overlap = float(near[mine_dots].mean())
            else:
                overlap = 0.0
            agree = float((np.nan_to_num(mine) == np.nan_to_num(theirs)).mean())
            rows.append(dict(blob=blob, stratum=strat, their_dots=n_their,
                             rho=None if rho is None else round(rho, 4),
                             dot_overlap_3px=round(overlap, 4),
                             pixel_agreement=round(agree, 5)))
            if n % 100 == 0:
                print(f"[unique] {n}/{len(entries)} elapsed {time.time()-t0:.0f}s", flush=True)
        except Exception as exc:  # noqa: BLE001
            errors.append({"blob": blob, "err": str(exc)[:120]})
    rhos = [r["rho"] for r in rows if r["rho"] is not None]
    worst_rho = max(rhos, key=abs) if rhos else None
    worst_overlap_all = max(rows, key=lambda r: r["dot_overlap_3px"], default=None)
    dotlike = [r for r in rows if r["stratum"] == "dotlike"]
    worst_overlap_dotlike = max(dotlike, key=lambda r: r["dot_overlap_3px"], default=None)
    exact = [r for r in rows if r["pixel_agreement"] >= 0.9999]
    out = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        generated_utc=utcnow(), my_file=str(mine_path), my_dots=n_my_dots,
        my_sha256=sha256_file(mine_path),
        registry_scope="registry/prior_rasters.json (751 unique blobs, 2026-10-11 family census)",
        rho_limit=0.90, overlap_limit=0.70,
        n_registry_blobs=len(entries), n_compared=len(rows), n_errors=len(errors),
        worst_abs_spearman=None if worst_rho is None else abs(worst_rho),
        worst_rho_entry=next((r for r in rows if r["rho"] == worst_rho), None),
        worst_dot_overlap_all=worst_overlap_all,
        worst_dot_overlap_dotlike=worst_overlap_dotlike,
        n_exact_pixel_agreement_9999=len(exact),
        literal_gate=dict(
            rho_ok=bool(worst_rho is None or abs(worst_rho) <= 0.90),
            overlap_ok=bool(worst_overlap_all is None or worst_overlap_all["dot_overlap_3px"] <= 0.70),
        ),
        stratified_gate=dict(
            dotlike_overlap_ok=bool(worst_overlap_dotlike is None or
                                    worst_overlap_dotlike["dot_overlap_3px"] <= 0.70),
            note=("universal soft surfaces and dense rasters overlap ANY sparse dot field by "
                  "construction; family precedent GEMSDOE63/64 treats them as a registry-"
                  "structure condition, reported separately from the dotlike lane-drift gate"),
        ),
        errors=errors[:50], seconds=round(time.time() - t0, 1),
    )
    dump("e3_uniqueness.json", out)
    print(json.dumps({k: out[k] for k in ("worst_abs_spearman", "worst_dot_overlap_dotlike",
                                          "literal_gate", "n_errors")}, indent=1))
    return 0


def cmd_card() -> int:
    """Assemble the single JSON run card (protocol rule 5)."""
    gate = json.loads((EVIDENCE / "e2_gate.json").read_text()) if (EVIDENCE / "e2_gate.json").exists() else {}
    uniq = json.loads((EVIDENCE / "e3_uniqueness.json").read_text()) if (EVIDENCE / "e3_uniqueness.json").exists() else {}
    receipt = json.loads((EVIDENCE / "e3_receipt.json").read_text()) if (EVIDENCE / "e3_receipt.json").exists() else {}
    rec_hl = json.loads((EVIDENCE / "e1_hardlinked_recovery.json").read_text()) if (EVIDENCE / "e1_hardlinked_recovery.json").exists() else {}
    gate_ok = bool(gate.get("gate_passed"))
    lit = uniq.get("literal_gate", {})
    strat = uniq.get("stratified_gate", {})
    uniq_ok = bool(lit.get("rho_ok")) and bool(strat.get("dotlike_overlap_ok")) if uniq else False
    val_ok = bool(receipt.get("validator", {}).get("zeros", {}).get("passed"))
    verdict = "promote-candidate" if (gate_ok and uniq_ok and val_ok) else "negative"
    card = dict(
        generated_utc=utcnow(),
        lane="GEMSDOE69 relay-ramp & pull-apart corridor generator",
        hypothesis=("Hidden faults occupy relay-ramp / pull-apart corridors between step-over tips of mapped "
                    "faults; multi-physics edge evidence inside those corridors localizes them better than "
                    "pixel statistics alone."),
        mechanism=("Tip-graph step-over pairing (W 0.1-15 km, along <= 3.5W, sub-parallel strikes) -> "
                    "oblique connector + en echelon strands + pull-apart rhomb -> multi-scale HG/tilt grav+mag "
                    "(incl. magnetic lows) + lidar scarp + WNW-extension orientation score -> greedy "
                    "marginal-DTI dot placement >= 200 m off catalogue."),
        non_fault_mimic=("Linear geophysical edges that are NOT faults: lithologic/dike contacts, buried "
                         "channel margins and terrace edges in detrended elevation, and survey-line artifacts "
                         "in the airborne grids can all produce corridor-consistent HG/tilt responses."),
        holdout=({
            "instrument": ("vendor/template66 gems57 pooled hide-and-recover (alpha 0.2, beta 0.8, 300 m "
                            "triangular kernel); seeds/modes/cells as recorded"),
            "corridor_mean_dti": gate.get("corridor_mean_dti"),
            "corridor_ci95_half": gate.get("corridor_ci95_half"),
            "control_mean_dti": gate.get("control_mean_dti"),
            "paired_delta": gate.get("paired_delta_mean"),
            "withheld_positive_px_total": gate.get("withheld_positive_px_total"),
            "n_cells": gate.get("n_cells"),
            "gate_passed": gate_ok,
            "evidence_class": "HOLDOUT-DTI",
            "hardlinked_recovery_within_300m_mean": rec_hl.get("mean_recovery_within_300m"),
            "hardlinked_n_tested": rec_hl.get("n_tested"),
        } if gate else "pending"),
        correlation_overlap_vs_registry=({
            "worst_abs_spearman": uniq.get("worst_abs_spearman"),
            "worst_dot_overlap_dotlike": (uniq.get("worst_dot_overlap_dotlike") or {}).get("dot_overlap_3px"),
            "literal_gate": lit, "stratified_gate_ok": strat.get("dotlike_overlap_ok"),
            "n_compared": uniq.get("n_compared"),
        } if uniq else "pending"),
        raster=({
            "zeros_sha256": receipt.get("raster", {}).get("zeros", {}).get("sha256"),
            "zeros_path": receipt.get("raster", {}).get("zeros", {}).get("path"),
            "n_dots": receipt.get("n_dots"),
            "validator_zeros_passed": val_ok,
            "validator_nan_passed": bool(receipt.get("validator", {}).get("nan", {}).get("passed")),
        } if receipt else "pending"),
        submission_name=receipt.get("raster", {}).get("zeros", {}).get("path", "").split("/")[-1].replace(".tif", ""),
        submission_note=receipt.get("note", "")[:140],
        verdict=verdict,
        note=("verdict 'promote-candidate' means the holdout gate + registry scan + validator all passed; "
              "promotion to a scored slot is a separate selector step (protocol rule 6)"),
    )
    dump("run_card.json", card)
    print(json.dumps({"verdict": verdict, "gate_passed": gate_ok}, indent=1))
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "verify":
        return cmd_verify()
    if cmd == "e1":
        return cmd_e1()
    if cmd == "e2":
        seeds = (20,) if "--quick" in sys.argv else (20, 21)
        return cmd_e2(seeds=seeds)
    if cmd == "e3":
        s0 = float(sys.argv[2]) if len(sys.argv) > 2 else None
        return cmd_e3(s0=s0)
    if cmd == "unique":
        return cmd_unique()
    if cmd == "card":
        return cmd_card()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
