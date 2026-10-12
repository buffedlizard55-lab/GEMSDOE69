#!/usr/bin/env python3
"""Assemble the protocol run card (rule 5) from evidence/e1, e2, e3 and the validator output."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"


def load(name):
    p = EVID / name
    return json.loads(p.read_text()) if p.exists() else None


def worst(rows, key):
    vals = [(r.get(key), r) for r in rows if r.get(key) is not None and "error" not in r]
    if not vals:
        return None, None
    v, r = max(vals, key=lambda t: t[0])
    return v, r.get("submission")


def main():
    e1, e2, e3 = load("e1_first_test.json"), load("e2_gate.json"), load("e3_build.json")
    val = load("e3_validation.json")
    if not (e1 and e2 and e3 and val):
        sys.exit("missing evidence file(s); run e1, e2, build and validation first")
    pooled = e2["pooled_over_draws"]
    sc = pooled["scores"]
    gate = e2["gate"]
    uniq = {}
    for phase in ("surface", "dots"):
        rows = [json.loads(l) for l in (EVID / f"e3_uniqueness_{phase}_rows.jsonl").read_text().splitlines() if l.strip()]
        rho, rho_who = worst(rows, "spearman_full_footprint")
        ov, ov_who = worst(rows, "my_dots_within_3px_of_theirs")
        jac, jac_who = worst(rows, "jaccard_dot_sets")
        errors = [r for r in rows if "error" in r]
        identical = [r.get("submission") for r in rows if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
        two = e3["uniqueness"][phase].get("two_phase") or {}
        uniq[phase] = dict(rasters_checked=len(rows) - len(errors), rasters_with_errors=len(errors),
                           worst_spearman=rho, worst_spearman_raster=rho_who,
                           worst_forward_overlap_3px=ov, worst_overlap_raster=ov_who,
                           worst_jaccard=jac, worst_jaccard_raster=jac_who,
                           identical_bytes_or_pixels=identical,
                           like_for_like=two.get("like_for_like_reading"),
                           duplicate_literal=bool((rho is not None and rho > 0.90) or (ov is not None and ov > 0.70)))
    dup = uniq["surface"]["duplicate_literal"] or uniq["dots"]["duplicate_literal"]
    sub = e3["submission"]
    verdict = "promote" if (gate["passed"] and not dup and val["all_files_passed"]) else "negative"
    card = {
        "run_card_version": 1,
        "repository": "buffedlizard55-lab/GEMSDOE69",
        "lane": "Relay-ramp and pull-apart corridor generator",
        "hypothesis": ("Hidden (unmapped) faults concentrate in the step-over geometry of the mapped catalogue: breaching links and "
                       "en echelon strands inside same-dip relay ramps (W 0.1-15 km, |L| <= 3.5 W), N-NE dilational faults inside "
                       "strike-slip releasing steps, and splays / transfer links at strike-slip terminations; dots placed only inside "
                       "the best-scored corridors recover withheld faults better than the same pipeline without corridor priors."),
        "mechanism": ("Relay ramps between overlapping same-dip normal faults are breached by minor oblique and en echelon faults as "
                      "displacement transfers (Peacock & Sanderson 1994; Giddens & Faulds 2025: ~70% of >120 C step-overs hard-linked); "
                      "releasing steps and dextral terminations open N-NE normal faults under WNW extension (Faulds et al. 2026). "
                      "Regional compilations draw these zones as disconnected strands, so the linking faults are what a lidar-based "
                      "panel could add."),
        "non_fault_mimic": ("Lithologic and depositional edges that line up across step-overs: pluvial-lake shorelines and alluvial-fan "
                            "heads in the lidar scarp channel; buried basement relief and intrusive contacts producing gravity / magnetic "
                            "edges and tilt zero-crossings without faulting; hydrothermally altered but unfaulted volcanic units "
                            "producing magnetic lows."),
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": e2["evaluator_version"],
            "evaluator_hashes": e2["evaluator_hashes"],
            "draws": e2["seeds"],
            "withheld_positive_pixels_pooled": sc["A_corridor"]["withheld_positive_pixels"],
            "lane_arm_A_corridor": {"dti": sc["A_corridor"]["dti"], "ci95": sc["A_corridor"]["ci95"]},
            "gate_comparator_B1_halo": {"dti": sc["B1_halo"]["dti"], "ci95": sc["B1_halo"]["ci95"]},
            "all_arms": {k: {"dti": v["dti"], "ci95": v["ci95"]} for k, v in sc.items()},
            "gate": gate,
            "corridor_boost_sensitivity_AP_vs_B1": e2["pooled_over_draws_AP_vs_B1"]["paired_differences"]["B1_halo"],
        },
        "first_test_E1": {
            "leakage_canary_pooled_auc": e1["leakage_canary"]["seed20"]["pooled_auc"],
            "leakage_flags_auc_gt_0p90": e1["leakage_canary"]["seed20"]["leakage_flags"],
            "hardlink_masking_test": e1["hardlink_test"]["summary"],
            "dip_inference": e1["dip_receipt"],
        },
        "registry_uniqueness": {"index": "registry/registry_index_69.json", **uniq, "duplicate": dup},
        "raster": {"zeros_tif": sub["zeros_tif"], "zeros_sha256": sub["zeros_sha256"], "zeros_bytes": sub["zeros_bytes"],
                    "nan_twin_tif": sub["nan_tif"], "nan_twin_sha256": sub["nan_sha256"], "zip": sub["zip"],
                    "zip_sha256": sub["zip_sha256"], "dots": e3["dots"]},
        "validator_output": {r["file"].split("/")[-1]: {"all_checks_passed": r["all_checks_passed"], "checks": r["checks"],
                                                         "n_nan_inside_footprint": r["n_nan_inside_footprint"],
                                                         "min": r["min"], "max": r["max"]} for r in val["reports"]},
        "submission_name": sub["name"],
        "submission_note": sub["note"],
        "submission_note_chars": sub["note_chars"],
        "verdict": verdict,
        "verdict_reason": ("Gate passed, unique and valid." if verdict == "promote" else
                           "Gate failed: the lane arm did not beat the same pipeline without corridor priors on the pre-registered "
                           "holdout (see holdout.gate)." if not gate["passed"] else
                           "Uniqueness or validation failed."),
        "slot_policy": "Not a slot pick. Promotion is a separate selector step within the weekly cap.",
    }
    (EVID / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
    print(json.dumps({k: card[k] for k in ("verdict", "verdict_reason", "submission_name", "submission_note")}, indent=1))


if __name__ == "__main__":
    main()
