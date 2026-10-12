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
        lit = two.get("literal_reading") or {}
        lfl = two.get("like_for_like_reading") or {}
        rho_dup = bool(rho is not None and rho > 0.90)
        # Decision rule (stated before the corpus run finished, see README): the surface phase is judged by rank
        # correlation; the dots phase by rank correlation plus 3-px overlap against registry rasters that are dot
        # fields (support <= 20% of the footprint). Literal overlap against continuous surfaces is reported, not used:
        # a raster positive on the whole footprint 'overlaps' every possible candidate (template two_phase_summary).
        ov_dup = bool(phase == "dots" and (lfl.get("worst_forward_overlap_dot_fields") or 0) > 0.70)
        uniq[phase] = dict(rasters_checked=len(rows) - len(errors), rasters_with_errors=len(errors),
                           worst_spearman=rho, worst_spearman_raster=rho_who,
                           worst_forward_overlap_3px=ov, worst_overlap_raster=ov_who,
                           worst_forward_overlap_dot_fields=lfl.get("worst_forward_overlap_dot_fields"),
                           worst_forward_overlap_dot_field_raster=lfl.get("worst_forward_overlap_dot_field_submission"),
                           dot_field_rasters=lfl.get("dot_field_rasters"), continuous_surface_rasters=lfl.get("continuous_surface_rasters"),
                           literal_overlap_firings=lit.get("forward_overlap_firings"),
                           literal_firings_all_continuous_surfaces=all(f.get("representation") == "continuous_surface"
                                                                       for f in two.get("literal_firings", [])),
                           worst_jaccard=jac, worst_jaccard_raster=jac_who,
                           identical_bytes_or_pixels=identical,
                           duplicate_by_rank_correlation=rho_dup, duplicate_by_dot_overlap_like_for_like=ov_dup,
                           duplicate_literal=bool(rho_dup or (ov is not None and ov > 0.70)),
                           duplicate=bool(rho_dup or ov_dup))
    diag = (load("e3_uniqueness.json") or {}).get("dot_overlap_firings_diagnostic") or {}
    uniq["dots"]["dot_overlap_firings_diagnostic"] = diag
    uniq["dots"]["discriminating_duplicate"] = bool(uniq["dots"]["duplicate_by_rank_correlation"] or diag.get("n_discriminating_firings", 0) > 0)
    dup = uniq["surface"]["duplicate"] or uniq["dots"]["duplicate"]
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
        "registry_uniqueness": {"index": "registry/registry_index_69.json", **uniq, "duplicate": dup,
                                "discriminating_duplicate": bool(uniq["surface"]["duplicate_by_rank_correlation"] or uniq["dots"]["discriminating_duplicate"]),
                                "template_gap_reported": ("gems57.uniqueness.representation_class classifies registry rasters by support fraction only; "
                                                          "a uniform 6-px lattice (r14_union_tips10_lat6, 3.7% support) covers ~76% of the allowed domain "
                                                          "within 3 px and fires the 70% rule for any candidate. Proposed template fix: also classify by "
                                                          "3-px halo coverage of the allowed domain and test each firing against random dots placed in the candidate's own "
                                                          "domain (if random dots also exceed 0.70 the firing is non-discriminating). Not edited locally (no private fork)."),
                                "decision_rule": ("surface phase: Spearman > 0.90 vs any raster; dots phase: Spearman > 0.90 vs any raster "
                                                  "or > 70% of dots within 3 px of one dot-field raster's dots (support <= 20% of footprint). "
                                                  "Literal overlap vs continuous surfaces reported as degenerate diagnostics.")},
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
                           ("Gate failed: the lane arm did not beat the same pipeline without corridor priors on the pre-registered "
                            "holdout (see holdout.gate)." + ((f" Independently, the final dots are a DUPLICATE under the 70% / 3-px dot-overlap "
                            f"rule: {diag.get('n_firings', 0)} firings, {diag.get('n_discriminating_firings', 0)} discriminating "
                            f"(see registry_uniqueness.dots.dot_overlap_firings_diagnostic).") if dup else "")) if not gate["passed"] else
                           "Uniqueness or validation failed."),
        "slot_policy": "Not a slot pick. Promotion is a separate selector step within the weekly cap.",
        "budget": {"experiments_used": 3, "experiments": ["E1 first test", "E2 gate", "E3 live build + uniqueness + validation"],
                   "clock_start_utc": "2026-10-12T01:39:00Z", "e1_finished_utc": e1.get("finished"),
                   "e2_finished_utc": e2.get("finished"), "limit": "3 experiments or 2 hours"},
        "reuse": {"template": "vendor/gems57 == 60GEMSDOE/src/gems57 @ 32024716 (registry/template_pin.json), unedited",
                  "used": ["holdout.buffered_component_draw", "evaluate_holdout.evaluate / pooled_summary", "emit.greedy_allocate",
                           "submission_writer.write_submission", "validate.validate", "gates.format_report",
                           "uniqueness.compare_array_to_registry / two_phase_summary"],
                  "feature_stack": "official training_features.tif (SHA-256 4371c82e...) bands read directly -- the same bytes the template cache is built from"},
    }
    (EVID / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
    print(json.dumps({k: card[k] for k in ("verdict", "verdict_reason", "submission_name", "submission_note")}, indent=1))


if __name__ == "__main__":
    main()
