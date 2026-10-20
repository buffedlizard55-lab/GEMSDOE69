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
    from gems69.physics import build_z_stack
    from gems69.tips import vectorize
    from gems69.corridors import build_corridors

    t0 = time.time()
    g = load_template_grid()
    stats = _stats(g.footprint)
    zstack = build_z_stack(g.footprint, stats)
    from gems69.corridors import build_tip_pairs
    strands = vectorize(g.catalogue)
    all_pairs = build_tip_pairs(strands, g.catalogue)
    corridors, pairs = build_corridors(g.catalogue, strands, g.footprint.shape)
    census = dict(catalogue_px=int(g.catalogue.sum()), n_strands=len(strands),
                  n_raw_tip_pairs=len(all_pairs),
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
    can = leakage_canary(ctx, stats, zstack=zstack)
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

    from gems69.physics import build_z_stack
    g = load_template_grid()
    stats = _stats(g.footprint)
    zstack = build_z_stack(g.footprint, stats)
    ctx = thold.build_holdout(g, seeds=seeds, modes=modes)
    t0 = time.time()
    results = run_holdout_arms(ctx, stats, modes=modes, zstack=zstack)
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


def surface_precheck(propensity: np.ndarray, footprint: np.ndarray) -> dict:
    """Rank-correlation of the pre-placement surface vs registry rasters.

    Protocol rule 1: check the surface BEFORE placement. rho > 0.90 is a
    duplicate; the caller must not emit dots.
    """
    import rasterio
    from scipy.stats import spearmanr

    man = json.loads((ROOT / "registry" / "prior_rasters.json").read_text())
    reg_dir = ROOT / ".cache" / "registry"
    # subsample mutually finite cells; rank correlation is stable at this N
    rng = np.random.default_rng(69)
    fy, fx = np.nonzero(footprint)
    sel = rng.choice(len(fy), size=min(250_000, len(fy)), replace=False)
    sy, sx = fy[sel], fx[sel]
    mine = propensity[sy, sx].astype(np.float32)
    worst = 0.0
    worst_blob = None
    n_compared = 0
    errors = 0
    t0 = time.time()
    for e in man["rasters"]:
        path = reg_dir / f"{e['git_blob_sha']}.tif"
        if not path.exists():
            errors += 1
            continue
        try:
            with rasterio.open(path) as src:
                if (src.height, src.width) != propensity.shape:
                    errors += 1
                    continue
                # windowed point reads would be slower; one band is ~50 MB
                theirs = src.read(1)
            tv = theirs[sy, sx]
            ok = np.isfinite(tv) & np.isfinite(mine)
            if ok.sum() < 1000 or mine[ok].std() == 0 or np.nanstd(tv[ok]) == 0:
                continue
            rho = float(spearmanr(mine[ok], tv[ok]).statistic)
            n_compared += 1
            if abs(rho) > abs(worst):
                worst = rho
                worst_blob = e["git_blob_sha"]
            del theirs
        except Exception:  # noqa: BLE001
            errors += 1
    return dict(
        evidence_class="REGISTRY-MEASUREMENT",
        phase="surface-before-placement",
        generated_utc=utcnow(),
        subsample=int(len(sy)),
        n_compared=n_compared,
        n_errors=errors,
        n_registry_blobs=len(man["rasters"]),
        worst_abs_spearman=abs(worst),
        worst_rho=worst,
        worst_blob=worst_blob,
        rho_ok=bool(abs(worst) <= 0.90),
        seconds=round(time.time() - t0, 1),
    )


def cmd_e3(s0: float | None = None) -> int:
    from gems57 import grid as tgrid
    from gems57.emit import greedy_allocate
    from gems69.holdout69 import corridor_pipeline, load_template_grid
    from gems69.scoring import S0_DEFAULT
    from scipy import ndimage as ndi

    s0 = S0_DEFAULT if s0 is None else s0
    from gems69.physics import build_z_stack
    g = load_template_grid()
    stats = _stats(g.footprint)
    zstack = build_z_stack(g.footprint, stats)
    t0 = time.time()
    pipe = corridor_pipeline(g.catalogue, g.footprint.shape, stats, max_corridors=1200,
                             zstack=zstack)
    p = pipe["propensity"]
    del zstack
    print(f"[e3] surface precheck corridors={pipe['corridors']} kept={pipe.get('corridors_kept')}", flush=True)
    pre = surface_precheck(p, g.footprint)
    dump("e3_surface_uniqueness.json", pre)
    print("[e3] surface", json.dumps({k: pre[k] for k in ("worst_abs_spearman", "rho_ok", "n_compared", "seconds")}), flush=True)
    if not pre["rho_ok"]:
        print("[e3] DUPLICATE on the surface; stopping before placement", flush=True)
        return 2
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
    base = f"h69e-strat-straight-rad-{n_dots}-{stamp}-{h8}"
    sub = ROOT / "submissions"
    sub.mkdir(exist_ok=True)
    rec_z = tgrid.write_submission(sub / f"{base}-zeros.tif", values, mode="zeros")
    values_nan = values.copy()
    values_nan[~g.footprint] = np.nan
    rec_n = tgrid.write_submission(sub / f"{base}-nan.tif", values_nan, mode="nan")

    from gems.validate_submission import validate
    import rasterio
    feat = ROOT / ".cache" / "gems_data" / "training_features.tif"
    vz = validate(sub / f"{base}-zeros.tif", reference_path=ROOT / "data" / "bridge" / "sample_submission.tif",
                  features_path=feat)
    vn = validate(sub / f"{base}-nan.tif", reference_path=ROOT / "data" / "bridge" / "sample_submission.tif",
                  features_path=feat)

    # --- format compliance against the submission-format raster itself ------
    # The upstream validator's footprint proxy (training_features band 1 finite)
    # differs from sample_submission's finite mask by ~1.5k cells (IR-69-VAL-01);
    # the portal contract is the sample_submission grid, so compliance is
    # re-derived from the bytes on disk against it, per template read_geotiff policy.
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ref:
        sub_finite = np.isfinite(ref.read(1))
    with rasterio.open(sub / f"{base}-zeros.tif") as src:
        zv = src.read(1)
    with rasterio.open(sub / f"{base}-nan.tif") as src:
        nv = src.read(1)
        nan_nodata = src.nodata
    zeros_compliance = dict(
        all_finite=bool(np.isfinite(zv).all()),
        range_0_1=bool((zv[np.isfinite(zv)] >= 0).all() and (zv[np.isfinite(zv)] <= 1).all()),
        dots=int((zv > 0).sum()),
        policy=("gems57/grid.py: zeros is the only submission-compatible mode; h33-2-b2-zeros "
                "(family, user-reported 0.2778) passed the portal all-finite"),
    )
    nan_compliance = dict(
        finite_mask_matches_sample_submission=bool(np.array_equal(np.isfinite(nv), sub_finite)),
        nan_only_outside_footprint=bool((~np.isfinite(nv)).astype(bool).astype(np.int8)[~sub_finite].all()),
        no_nan_inside_footprint=bool(np.isfinite(nv[sub_finite]).all()),
        range_0_1_inside=bool((nv[sub_finite] >= 0).all() and (nv[sub_finite] <= 1).all()),
        nodata_tag_is_nan=bool(nan_nodata is not None and np.isnan(nan_nodata)),
        dots=int((nv > 0).sum()),
        policy=("prompt-mandated layout: NaN only outside the footprint; matches the organizer "
                "sample_submission convention (NaN + nodata tag)"),
    )
    footprint_proxy_disagreement_px = int(np.isfinite(nv).sum() - sub_finite.sum())

    rationale = [c.rationale for c in pipe["corridors_obj"] if "score_S" in c.rationale]
    rationale.sort(key=lambda r: -r["score_S"])
    receipt = dict(
        evidence_class="SUBMISSION-RECEIPT",
        generated_utc=stamp, hypothesis_id="H69-E-stratified-straight-rad",
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
        format_compliance=dict(zeros=zeros_compliance, nan=nan_compliance,
                               upstream_footprint_proxy_disagreement_px=footprint_proxy_disagreement_px,
                               note="upstream validator footprint proxy = training_features band 1 finite; "
                                    "portal contract = sample_submission finite mask (IR-69-VAL-01)"),
        propensity_sha256=h8,
        top_corridors=rationale[:25],
        note=("H69-E width-stratified relay/pull-apart; cond+basement straight steps + K/ThK; "
              "HG+tilt+lidar; greedy DTI; 200m flank")[:140],
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
    subs = sorted((ROOT / "submissions").glob("h69*-zeros.tif"))
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
                yy, xx = np.mgrid[-3:4, -3:4]
                disk = (yy * yy + xx * xx) <= 9          # Euclidean radius 3 px (template convention)
                near = ndi.binary_dilation(tpos, structure=disk)
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
    # Own prior emissions are not in the 2026-10-11 registry. The standing
    # prompt forbids copying a previous submission, so they are scanned too.
    local_rows = []
    local_paths = list((ROOT / "submissions").glob("*.tif")) + list((ROOT / "docs" / "downloads").glob("*.tif"))
    mine_stem = mine_path.name.replace("-zeros.tif", "").replace("-nan.tif", "")
    for lp in local_paths:
        if lp.resolve() == mine_path.resolve():
            continue
        # the diagnostic twin of this same emission is not a prior submission
        if mine_stem and mine_stem in lp.name:
            continue
        if "zeros" not in lp.name and "nan" not in lp.name:
            continue
        try:
            with rasterio.open(lp) as src:
                if (src.height, src.width) != mine.shape:
                    continue
                theirs = src.read(1)
            tpos = np.isfinite(theirs) & (theirs > 0)
            if int(tpos.sum()) == 0 or n_my_dots == 0:
                continue
            yy, xx = np.mgrid[-3:4, -3:4]
            disk = (yy * yy + xx * xx) <= 9
            near = ndi.binary_dilation(tpos, structure=disk)
            local_rows.append(dict(
                path=str(lp.relative_to(ROOT)), their_dots=int(tpos.sum()),
                dot_overlap_3px=round(float(near[mine_dots].mean()), 4),
            ))
        except Exception as exc:  # noqa: BLE001
            local_rows.append(dict(path=str(lp), err=str(exc)[:160]))
    worst_local = max((r for r in local_rows if "dot_overlap_3px" in r),
                      key=lambda r: r["dot_overlap_3px"], default=None)
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
        local_prior_overlap=dict(
            n_scanned=len(local_rows),
            worst=worst_local,
            ok=bool(worst_local is None or worst_local["dot_overlap_3px"] <= 0.70),
            note="overlap of this emission's dots with earlier GEMSDOE69 submissions (not in the 2026-10-11 registry)",
        ),
        errors=errors[:50], seconds=round(time.time() - t0, 1),
    )
    dump("e3_uniqueness.json", out)
    dump("e3_uniqueness_rows.json", dict(rows=rows))
    print(json.dumps({k: out[k] for k in ("worst_abs_spearman", "worst_dot_overlap_dotlike",
                                          "literal_gate", "n_errors")}, indent=1))
    return 0


def cmd_card() -> int:
    """Apply policy; replace another artifact's card only with explicit flag."""
    from release_gate import write_card
    try:
        card = write_card(replace="--replace-artifact-bound-card" in sys.argv)
    except ValueError as exc:
        print(f"Run card unchanged: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(card["release_policy"], indent=2))
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "verify":
        return cmd_verify()
    if cmd in ("e1", "e2", "e3"):
        from lane_preflight import require_open_lane
        require_open_lane(ROOT)
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
