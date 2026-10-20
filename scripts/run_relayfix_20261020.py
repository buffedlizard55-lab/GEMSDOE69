#!/usr/bin/env python3
"""Preregistered 2026-10-20 relay-fix experiment runner (see
registry/preregistration-2026-10-20-relayfix.json, frozen before any holdout
look in this session).

Subcommands:
  gate    census + hard-link recovery + 4-arm pooled holdout + canaries
  emit    full-catalogue emission of the preregistered arm -> submissions/
  unique  vendor two-phase registry scan (surface array + final dots)

All DTI arithmetic is the shared template's (vendor/template66 gems57);
nothing here re-implements the metric.  Every score written is HOLDOUT-DTI.
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
sys.path.insert(0, str(ROOT / "vendor"))

EVIDENCE = ROOT / "evidence"
TMP = Path("/tmp/gems69_relayfix")
TMP.mkdir(parents=True, exist_ok=True)
ARMS = ("control_noprior", "corridor_v1", "corridor_v2", "corridor_v3")
VERSION = {"corridor_v1": "v1", "corridor_v2": "v2", "corridor_v3": "v3"}


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


def log(msg: str) -> None:
    print(f"[{utcnow()}] {msg}", flush=True)


# ---------------------------------------------------------------- gate ----

def _auc(pos: np.ndarray, neg: np.ndarray) -> float | None:
    from scipy.stats import rankdata
    a = np.asarray(pos, np.float64); b = np.asarray(neg, np.float64)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if a.size < 10 or b.size < 10:
        return None
    r = rankdata(np.concatenate([a, b]))
    return float((r[: a.size].sum() - a.size * (a.size + 1) / 2) / (a.size * b.size))


def cmd_gate() -> int:
    from scipy import ndimage as ndi
    from gems57 import holdout as thold
    from gems57.emit import greedy_allocate
    from gems69.holdout69 import (hardlinked_recovery, load_template_grid,
                                  cell_allowed)
    from gems69.physics import (TRANSFORM_NAMES, build_layer_stats,
                                build_z_stack, corridor_evidence_from_z)
    from gems69.tips import vectorize
    from gems69.corridors import build_corridors, build_tip_pairs
    from gems69.scoring import S0_DEFAULT, build_propensity, score_corridor

    t_all = time.time()
    g = load_template_grid()
    shape = g.footprint.shape
    log("building layer stats + z stack (23 transforms)")
    stats = build_layer_stats(g.footprint)
    zstack = build_z_stack(g.footprint, stats)
    log(f"z stack ready: {sorted(zstack)}")

    # --- repaired census on the full catalogue ---
    t0 = time.time()
    strands = vectorize(g.catalogue)
    raw_pairs = build_tip_pairs(strands, g.catalogue)
    corridors, pairs = build_corridors(g.catalogue, strands, shape)
    ws = np.array([p.w_px for p in raw_pairs]) if raw_pairs else np.zeros(0)
    census = dict(evidence_class="TIPGRAPH-CENSUS-REPAIRED", repairs=["R1-interval-offset", "R2-search-radius-546px"],
                  catalogue_px=int(g.catalogue.sum()), n_strands=len(strands),
                  n_raw_tip_pairs=len(raw_pairs), n_pairs_capped=len(pairs),
                  n_corridors=len(corridors),
                  n_pull_apart=int(sum(c.subtype == "pull-apart" for c in corridors)),
                  n_transfer_overlap=int(sum(c.subtype == "transfer-overlap" for c in corridors)),
                  w_km_raw=dict(min=float(ws.min() / 10), median=float(np.median(ws) / 10),
                                mean=float(ws.mean() / 10), max=float(ws.max() / 10)) if ws.size else None,
                  max_separation_over_w=float(max((p.separation_px / p.w_px for p in raw_pairs), default=0.0)),
                  generated_utc=utcnow(), seconds=round(time.time() - t0, 1))
    dump("relayfix_census.json", census)
    log(f"census: strands={census['n_strands']} raw_pairs={census['n_raw_tip_pairs']} "
        f"corridors={census['n_corridors']} pull-apart={census['n_pull_apart']} ({census['seconds']}s)")
    del corridors, pairs, raw_pairs, strands

    # --- hard-linked recovery (repaired code path) ---
    t0 = time.time()
    rec = hardlinked_recovery(g.catalogue, shape, stats)
    rec.update(evidence_class="HOLDOUT-GEOMETRY", generated_utc=utcnow(),
               seconds=round(time.time() - t0, 1), repairs=["R1", "R2", "shared-build_tip_pairs"])
    dump("relayfix_hardlinked_recovery.json", rec)
    log(f"hardlink: found={rec.get('n_hardlinked_found')} tested={rec.get('n_tested', rec.get('n_disconnected_tested'))} "
        f"mean_recovery={rec.get('mean_recovery_within_300m')} ({rec['seconds']}s)")

    # --- pooled holdout, 4 arms, corridors rebuilt per cell from visible ---
    ctx = thold.build_holdout(g, seeds=(20, 21), modes=("all",))
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    offcat = d_cat > 2
    ctrl_layers = ["grav_hg_s2", "grav_tilt_s2", "mag_hg_s2", "mag_tilt_s2",
                   "mag_low_tmi", "mag_low_rtp", "lidar_scarp"]
    C = np.zeros(shape, np.float32)
    for name in ctrl_layers:
        z = zstack[name].astype(np.float32)
        C += np.where(np.isfinite(z), z, 0.0)
        del z
    C /= len(ctrl_layers)
    p_ctrl = (1.0 / (1.0 + np.exp(-1.5 * (C - S0_DEFAULT)))).astype(np.float32)
    p_ctrl[~g.footprint] = 0.0
    del C

    per_cell: dict[str, dict] = {}
    canary: dict[str, dict[str, list]] = {}
    rng_can = np.random.default_rng(20261020)
    for cell in ctx.cells:
        t0 = time.time()
        visible = ctx.visible(cell.key)
        strands = vectorize(visible)
        corridors, _pairs = build_corridors(visible, strands, shape)
        evid = [corridor_evidence_from_z(zstack, c) for c in corridors]
        allowed_base = cell_allowed(cell, shape) & offcat
        # truth / negative coordinates (full-grid) for canaries
        ys = slice(cell.bbox[0].start, cell.bbox[0].stop)
        ty = cell.truth_yx[0] + cell.bbox[0].start
        tx = cell.truth_yx[1] + cell.bbox[1].start
        active_full = cell_allowed(cell, shape)
        neg_pool = np.nonzero(active_full)
        is_truth = np.zeros(shape, bool); is_truth[ty, tx] = True
        neg_mask = active_full & ~is_truth
        ny_all, nx_all = np.nonzero(neg_mask)
        sel = rng_can.choice(len(ny_all), size=min(50_000, len(ny_all)), replace=False)
        ny, nx = ny_all[sel], nx_all[sel]
        del neg_pool, is_truth, neg_mask, ny_all, nx_all, active_full
        for fname in TRANSFORM_NAMES:
            z = zstack[fname]
            canary.setdefault(fname, []).append(_auc(z[ty, tx], z[ny, nx]))
        cell_out = {}
        for arm in ("corridor_v1", "corridor_v2", "corridor_v3"):
            for c, ev in zip(corridors, evid):
                score_corridor(c, ev, version=VERSION[arm])
            p = build_propensity(corridors, shape)
            canary.setdefault(f"propensity_{arm}", []).append(_auc(p[ty, tx], p[ny, nx]))
            alloc = greedy_allocate(p, allowed_base & (p > 0), cell.n_truth,
                                    floor=0.05, max_dots=250_000, candidate_cap=300_000)
            r = thold.score_cell(cell, alloc.emitted)
            cell_out[arm] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"],
                                 n_truth=cell.n_truth, n_dots=int((alloc.emitted & allowed_base).sum()))
            del p, alloc
        alloc = greedy_allocate(p_ctrl, allowed_base & (p_ctrl > 0), cell.n_truth,
                                floor=0.05, max_dots=250_000, candidate_cap=300_000)
        r = thold.score_cell(cell, alloc.emitted)
        cell_out["control_noprior"] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"],
                                           n_truth=cell.n_truth, n_dots=int((alloc.emitted & allowed_base).sum()))
        del alloc, corridors, evid, strands
        per_cell[cell.key] = cell_out
        log(f"cell {cell.key}: " + " ".join(f"{a}={cell_out[a]['dti']:.4f}" for a in ARMS)
            + f" ({time.time() - t0:.0f}s)")

    ALPHA, BETA, EPS = 0.2, 0.8, 1e-12
    def pooled(arm: str, keys) -> float:
        tp = sum(per_cell[k][arm]["tp"] for k in keys)
        fp = sum(per_cell[k][arm]["fp"] for k in keys)
        fn = sum(per_cell[k][arm]["fn"] for k in keys)
        return float(tp / (tp + ALPHA * fp + BETA * fn + EPS))
    keys = sorted(per_cell)
    pooled_dti = {a: pooled(a, keys) for a in ARMS}
    mean_dti = {a: float(np.mean([per_cell[k][a]["dti"] for k in keys])) for a in ARMS}
    rng = np.random.default_rng(20261020)
    diffs = {"v2_minus_control": [], "v2_minus_v1": [], "v3_minus_v1": [], "v1_minus_control": []}
    for _ in range(2000):
        bk = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        pv = {a: pooled(a, bk) for a in ARMS}
        diffs["v2_minus_control"].append(pv["corridor_v2"] - pv["control_noprior"])
        diffs["v2_minus_v1"].append(pv["corridor_v2"] - pv["corridor_v1"])
        diffs["v3_minus_v1"].append(pv["corridor_v3"] - pv["corridor_v1"])
        diffs["v1_minus_control"].append(pv["corridor_v1"] - pv["control_noprior"])
    boot = {k: dict(mean=float(np.mean(v)), ci95=[float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))])
            for k, v in diffs.items()}
    canary_summary = {}
    for f, aucs in canary.items():
        vals = [a for a in aucs if a is not None]
        canary_summary[f] = dict(auc_max=float(max(vals)) if vals else None,
                                 auc_median=float(np.median(vals)) if vals else None,
                                 per_cell=aucs, n_cells=len(aucs))
    worst_canary = max(((f, s["auc_max"]) for f, s in canary_summary.items() if s["auc_max"] is not None),
                       key=lambda kv: kv[1], default=(None, None))
    science_gate = bool(pooled_dti["corridor_v2"] > pooled_dti["control_noprior"]
                        and pooled_dti["corridor_v2"] > pooled_dti["corridor_v1"]
                        and boot["v2_minus_control"]["ci95"][0] > 0
                        and boot["v2_minus_v1"]["ci95"][0] > 0
                        and (worst_canary[1] is not None and worst_canary[1] <= 0.90))
    gate = dict(
        evidence_class="HOLDOUT-DTI",
        evaluator="vendor/template66 gems57.holdout.build_holdout+score_cell (alpha=0.2 beta=0.8 R=300m triangular; seeds=[20,21] modes=['all']; POOLED from summed TP/FP/FN)",
        preregistration="registry/preregistration-2026-10-20-relayfix.json",
        n_cells=len(keys), withheld_positive_px_total=int(sum(per_cell[k]["corridor_v1"]["n_truth"] for k in keys)),
        pooled_dti=pooled_dti, mean_of_cells_dti=mean_dti,
        paired_cell_bootstrap=boot, per_cell=per_cell,
        worst_canary=dict(feature=worst_canary[0], auc_max=worst_canary[1], rule="AUC>0.90 = leakage"),
        science_gate_passed=science_gate,
        emission_arm="corridor_v2" if science_gate else "corridor_v1",
        archived_comparison=dict(source="evidence/e2_gate.json (2026-10-12, buggy geometry, mean-of-cells)",
                                 corridor_mean_dti=0.005975197860273526, control_mean_dti=0.0021479253641536293,
                                 note="Different statistic (mean vs pooled) and pre-repair geometry; reported, never pooled-compared."),
        generated_utc=utcnow(), seconds=round(time.time() - t_all, 1))
    dump("relayfix_gate.json", gate)
    dump("relayfix_canaries.json", dict(evidence_class="LEAKAGE-CANARY",
                                        method="per-cell AUC vs that cell withheld truth; corridor propensities built from visible catalogue only; 50k sampled negatives/cell",
                                        features=canary_summary, worst=gate["worst_canary"],
                                        generated_utc=utcnow()))
    log(f"POOLED {pooled_dti} science_gate={science_gate} emission={gate['emission_arm']} total={gate['seconds']}s")
    return 0


# ---------------------------------------------------------------- emit ----

def cmd_emit() -> int:
    from scipy import ndimage as ndi
    from gems57 import grid as tgrid
    from gems57.emit import greedy_allocate
    from gems69.holdout69 import load_template_grid
    from gems69.physics import build_layer_stats, build_z_stack, corridor_evidence_from_z
    from gems69.tips import vectorize
    from gems69.corridors import build_corridors
    from gems69.scoring import build_propensity, score_corridor

    gate = json.loads((EVIDENCE / "relayfix_gate.json").read_text())
    arm = gate["emission_arm"]
    version = VERSION[arm]
    log(f"emission arm={arm} scoring={version} science_gate={gate['science_gate_passed']}")
    g = load_template_grid()
    shape = g.footprint.shape
    stats = build_layer_stats(g.footprint)
    zstack = build_z_stack(g.footprint, stats)
    t0 = time.time()
    strands = vectorize(g.catalogue)
    corridors, pairs = build_corridors(g.catalogue, strands, shape)
    for c in corridors:
        score_corridor(c, corridor_evidence_from_z(zstack, c), version=version)
    p = build_propensity(corridors, shape)
    p[~g.footprint] = 0.0
    # Freeze the pre-placement surface BEFORE dot placement (uniqueness phase 1).
    surf_path = TMP / f"surface_{arm}.npy"
    np.save(surf_path, p)
    surf_decoded = hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest()
    (TMP / "surface_frozen.json").write_text(json.dumps(dict(
        surface_file=str(surf_path), surface_decoded_sha256=surf_decoded,
        frozen_utc=utcnow(), arm=arm, version=version,
        n_positive=int((p > 0).sum())), indent=1))
    log(f"surface frozen: decoded_sha={surf_decoded[:16]} positives={int((p > 0).sum())} ({time.time() - t0:.0f}s)")

    flank = ndi.distance_transform_edt(~g.catalogue) > 2
    allowed = g.footprint & flank & (p > 0)
    alloc = greedy_allocate(p, allowed, 12691, floor=0.05, max_dots=250_000,
                            candidate_cap=300_000)
    dots = alloc.emitted & allowed
    n_dots = int(dots.sum())
    values = np.zeros(shape, np.float32); values[dots] = 1.0
    stamp = utcnow()
    h8 = hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()[:8]
    base = f"h69-relayfix-{version}-{n_dots}-{stamp}-{h8}"
    sub = ROOT / "submissions"; sub.mkdir(exist_ok=True)
    rec_z = tgrid.write_submission(sub / f"{base}-zeros.tif", values, mode="zeros")
    values_nan = values.copy(); values_nan[~g.footprint] = np.nan
    rec_n = tgrid.write_submission(sub / f"{base}-nan.tif", values_nan, mode="nan")
    log(f"wrote {base} dots={n_dots}")

    # per-corridor rationale (geologist review): full CSV + top-25 in receipt
    import csv as _csv
    rationale = [c.rationale for c in corridors if "score_S" in c.rationale]
    rationale.sort(key=lambda r: -r["score_S"])
    rat_path = EVIDENCE / "relayfix_corridor_rationale.csv"
    with open(rat_path, "w", newline="") as f:
        wtr = _csv.writer(f)
        wtr.writerow(["rank", "score_S", "scoring_version", "w_km", "along_km", "separation_km",
                      "overlap_km", "mean_az_deg", "dilatational", "signature", "source",
                      "E_grav", "E_mag", "E_maglow", "E_lidar", "E_subsurface", "E_radiometric",
                      "strands", "tips"])
        for i, r in enumerate(rationale):
            eg = r.get("evidence_groups", {})
            wtr.writerow([i, r.get("score_S"), r.get("scoring_version"), r.get("w_km"), r.get("along_km"),
                          r.get("separation_km"), r.get("overlap_km"), r.get("mean_az_deg"),
                          r.get("dilatational"), r.get("signature"), r.get("source"),
                          eg.get("E_grav"), eg.get("E_mag"), eg.get("E_maglow"), eg.get("E_lidar"),
                          eg.get("E_subsurface"), eg.get("E_radiometric"),
                          r.get("strands"), r.get("tips")])
    sha_z = sha256_file(Path(rec_z["path"])); sha_n = sha256_file(Path(rec_n["path"]))
    receipt = dict(
        evidence_class="SUBMISSION-RECEIPT", generated_utc=stamp,
        hypothesis_id="H69-F-subsurface-step" if version == "v2" else "H69-relaypullapart-repaired-v1",
        preregistration="registry/preregistration-2026-10-20-relayfix.json",
        emission_arm=arm, scoring_version=version, science_gate_passed=gate["science_gate_passed"],
        s0_calibrated=0.75, k_truth_prior=12691,
        k_truth_source="Archived receipt chain in evidence/e3_receipt.json (owner-report-derived prior, not a measurement)",
        n_corridors=len(corridors), n_pairs=len(pairs), n_strands=len(strands), n_dots=n_dots,
        catalogue_collision_px=int((dots & g.catalogue).sum()),
        surface=dict(decoded_sha256=surf_decoded, frozen_before_placement=True),
        raster=dict(zeros=dict(path=rec_z["path"], sha256=sha_z, bytes=Path(rec_z["path"]).stat().st_size),
                    nan=dict(path=rec_n["path"], sha256=sha_n, bytes=Path(rec_n["path"]).stat().st_size)),
        top_corridors=rationale[:25],
        submission_name=f"{base}-zeros",
        submission_note=("H69 relay-fix corridors + subsurface HG/tilt; repaired tip graph; "
                         f"{n_dots} dots")[:140],
        note="PORTAL FILE = -zeros (all-finite in [0,1]). -nan twin is diagnostic/spec-literal only; do not upload it.")
    dump("relayfix_receipt.json", receipt)
    (TMP / "emission.json").write_text(json.dumps(receipt, indent=1, default=str))
    log(f"receipt zeros sha={sha_z}")
    return 0


# -------------------------------------------------------------- unique ----

def cmd_unique() -> int:
    import rasterio
    from gems57.uniqueness import compare_array_to_registry
    from gems69.holdout69 import load_template_grid
    receipt = json.loads((EVIDENCE / "relayfix_receipt.json").read_text())
    frozen = json.loads((TMP / "surface_frozen.json").read_text())
    g = load_template_grid()
    tif = ROOT / receipt["raster"]["zeros"]["path"]
    file_sha = receipt["raster"]["zeros"]["sha256"]
    index = ROOT / "registry" / "registry_index_69.json"
    out = {}
    t_all = time.time()
    for phase, arr in (("surface", np.load(frozen["surface_file"])),
                       ("dots", None)):
        if arr is None:
            with rasterio.open(tif) as src:
                arr = src.read(1).astype(np.float32)
        t0 = time.time()
        res = compare_array_to_registry(np.asarray(arr, np.float32), index, g.footprint,
                                        file_sha256=file_sha)
        res["phase"] = phase
        rows = res.pop("rows", [])
        (EVIDENCE / f"relayfix_uniqueness_{phase}_rows.json").write_text(
            json.dumps(rows, indent=0, default=str))
        out[phase] = dict(summary=res, seconds=round(time.time() - t0, 1))
        log(f"phase {phase}: worst_rho={res.get('worst_spearman_full_footprint')} "
            f"worst_overlap={res.get('worst_dot_overlap')} stop={res.get('stop_required')} ({out[phase]['seconds']}s)")
    doc = dict(index="registry/registry_index_69.json", index_rasters=862,
               index_complete_accessible_scan=True, index_errors=[],
               order_note=("Surface array frozen to disk before dot placement "
                           f"(decoded sha256 {frozen['surface_decoded_sha256']}, {frozen['frozen_utc']}); "
                           "registry comparisons executed after emission for compute scheduling. "
                           "A duplicate verdict in either phase stops promotion."),
               phases=out, seconds=round(time.time() - t_all, 1), generated_utc=utcnow())
    dump("relayfix_uniqueness.json", doc)
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    return {"gate": cmd_gate, "emit": cmd_emit, "unique": cmd_unique}[cmd]()


if __name__ == "__main__":
    sys.exit(main())
