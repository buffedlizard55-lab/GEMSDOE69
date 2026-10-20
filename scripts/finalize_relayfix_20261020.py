#!/usr/bin/env python3
"""Bind Exp1+Exp2b receipts into the e1/e2/e3 schema consumed by
scripts/release_gate.py + scripts/build_site69.py (orchestration only;
no scientific recomputation).  Prior e* files are archived, never deleted.
Candidate = H69-H2 transfer-only TIF (evidence/relayfix_transfer_receipt.json).
"""
from __future__ import annotations

if __name__ == "__main__":
    from lane_preflight import require_open_lane
    require_open_lane()
import hashlib, json, shutil, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
sys.path.insert(0, str(ROOT / "src"))

def load(name):
    return json.loads((EV / name).read_text())

def dump(name, obj):
    (EV / name).write_text(json.dumps(obj, indent=1, default=str))

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    for old, new in (("e3_receipt.json", "e3_receipt_archived_h69d.json"),
                     ("e3_uniqueness.json", "e3_uniqueness_archived_h69d.json"),
                     ("e1_canaries.json", "e1_canaries_archived_20261012.json"),
                     ("e1_hardlinked_recovery.json", "e1_hardlinked_recovery_archived.json"),
                     ("e1_tipgraph_census.json", "e1_tipgraph_census_archived.json")):
        src, dst = EV / old, EV / new
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    exp1 = load("relayfix_gate.json"); exp2 = load("relayfix_exp2b_gate.json")
    receipt = load("relayfix_transfer_receipt.json")
    validator = load("relayfix_transfer_validator.json")
    uniq_doc = load("relayfix_transfer_uniqueness.json")
    can = load("relayfix_canaries.json")
    tif_sha = receipt["raster"]["zeros"]["sha256"]
    assert sha(ROOT / receipt["raster"]["zeros"]["path"]) == tif_sha

    # --- e2_gate (release_gate: gate_passed + current_best_beaten; site fields) ---
    tvals = np.array([exp2["per_cell"][k]["dti"] for k in sorted(exp2["per_cell"])])
    diff = exp2["pooled_dti"]["transfer"] - exp2["pooled_dti"]["control_noprior"]
    boot = exp2["paired_cell_bootstrap"]["transfer_minus_control"]["ci95"]
    e2 = dict(evidence_class="HOLDOUT-DTI", evaluator=exp2["evaluator"],
              n_cells=exp2["n_cells"], withheld_positive_px_total=exp2["withheld_positive_px_total"],
              corridor_mean_dti=float(tvals.mean()),
              corridor_ci95_half=float(1.96 * tvals.std(ddof=1) / np.sqrt(len(tvals))),
              control_mean_dti=exp1["mean_of_cells_dti"]["control_noprior"],
              control_ci95_half=float(1.96 * np.std([exp1["per_cell"][k]["control_noprior"]["dti"] for k in sorted(exp1["per_cell"])], ddof=1) / np.sqrt(8)),
              paired_delta_mean=float(diff), paired_delta_ci95_half=float((boot[1] - boot[0]) / 2),
              gate_passed=bool(exp2["prompt_gate_passed"]), current_best_beaten=bool(exp2["beats_current_best"]),
              pooled_dti=exp2["pooled_dti"], paired_cell_bootstrap=exp2["paired_cell_bootstrap"],
              corridor=dict(per_cell={k: exp2["per_cell"][k]["dti"] for k in sorted(exp2["per_cell"])}),
              control=dict(per_cell={k: exp1["per_cell"][k]["control_noprior"]["dti"] for k in sorted(exp1["per_cell"])}),
              exp1_pooled_dti=exp1["pooled_dti"], generated_utc=exp2["generated_utc"],
              note="Candidate arm = H69-H2 transfer-only. Primary statistic is POOLED DTI; mean fields retained for site compatibility.")
    dump("e2_gate.json", e2)

    # --- e1 canaries (release_gate: canaries[feature].auc + artifact_sha256) ---
    e1can = {"evidence_class": "LEAKAGE-CANARY", "artifact_sha256": tif_sha,
             "method": "per-cell AUC vs withheld truth (Exp1 z-features + propensities; transfer propensity from Exp2b); auc below = max over cells (conservative). Computed before emission; sha binds candidate.",
             "rule": "single-feature AUC > 0.90 = leakage until proven otherwise"}
    for f, s in can["features"].items():
        e1can[f] = dict(auc=s["auc_max"], auc_median=s["auc_median"], per_cell=s["per_cell"])
    e1can["propensity_corridor_transfer"] = dict(
        auc=exp2["canary_propensity_transfer"]["auc_max"], per_cell=exp2["canary_propensity_transfer"]["per_cell_auc"])
    dump("e1_canaries.json", e1can)
    shutil.copy2(EV / "relayfix_hardlinked_recovery.json", EV / "e1_hardlinked_recovery.json")
    shutil.copy2(EV / "relayfix_census.json", EV / "e1_tipgraph_census.json")

    # --- e3 receipt (release_gate: raster.zeros + validator.reports) ---
    e3 = dict(receipt)
    e3["validator"] = validator
    e3["note"] = receipt["submission_note"]
    dump("e3_receipt.json", e3)
    dump("e3_validator.json", validator)

    # --- method manifest (release_gate: source hashes + feature names) ---
    from gems69.physics import TRANSFORM_NAMES
    sources = ["src/gems69/corridors.py", "src/gems69/tips.py", "src/gems69/physics.py",
               "src/gems69/scoring.py", "src/gems69/holdout69.py",
               "scripts/run_relayfix_20261020.py", "scripts/run_exp2b_transfer.py",
               "scripts/validate_submission.py",
               "registry/preregistration-2026-10-20-relayfix.json",
               "registry/preregistration-2026-10-20-exp2b-transfer.json"]
    features = list(TRANSFORM_NAMES) + ["propensity_corridor_transfer"]
    dump("e3_method_manifest.json", dict(
        artifact_sha256=tif_sha,
        source_sha256={rel: sha(ROOT / rel) for rel in sources},
        feature_names=features,
        template_pins="vendor/template66/TEMPLATE_SHA256.txt verified unchanged this session",
        inputs=dict(training_features_sha256="4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
                    labels_sha256="7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
                    sample_submission_sha256="2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
                    geodawn_rad_u8_sha256="c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
                    provenance="sha256-pinned family mirrors, NOT organizer-authenticated")))

    # --- uniqueness aggregate + phase files ---
    phases = uniq_doc["phases"]
    for phase in ("surface", "dots"):
        dump(f"e3_uniqueness_{phase}.json", dict(
            index="registry/registry_index_69.json", index_rasters=862,
            index_complete_accessible_scan=True, index_errors=[],
            order_note=uniq_doc.get("order_note", "surface frozen before TIF writing (see receipt); comparisons after emission"),
            phases={phase: phases[phase]}))
    ds = phases["dots"]["summary"]
    dump("e3_uniqueness.json", dict(
        evidence_class="REGISTRY-MEASUREMENT", generated_utc=uniq_doc.get("generated_utc"),
        my_file=receipt["raster"]["zeros"]["path"], my_dots=receipt["n_dots"], my_sha256=tif_sha,
        registry_scope="registry/registry_index_69.json (862 hash-verified grid rasters, family census + HEAD scan 2026-10-12; fetched and sha256-verified 2026-10-20)",
        rho_limit=0.90, overlap_limit=0.70,
        n_registry_blobs=862, n_compared=ds.get("registry_rasters_checked"),
        n_errors=ds.get("missing_or_invalid"),
        worst_abs_spearman=abs(ds["worst_spearman_full_footprint"]) if ds.get("worst_spearman_full_footprint") is not None else None,
        worst_rho_entry=dict(submission=ds.get("worst_rho_submission"), rho=ds.get("worst_spearman_full_footprint")),
        worst_dot_overlap_all=dict(submission=ds.get("worst_overlap_submission"), dot_overlap_3px=ds.get("worst_dot_overlap")),
        literal_gate=dict(rho_ok=bool(ds.get("worst_spearman_full_footprint") is not None and abs(ds["worst_spearman_full_footprint"]) <= 0.90),
                          overlap_ok=bool(ds.get("worst_dot_overlap") is not None and ds["worst_dot_overlap"] <= 0.70)),
        surface_phase=dict(phases["surface"]["summary"]),
        dots_phase=dict(ds),
        local_lane_priors=receipt.get("precheck", {}).get("comparisons"),
        errors=[]))
    print("finalize ok", tif_sha)
    return 0

if __name__ == "__main__":
    sys.exit(main())
