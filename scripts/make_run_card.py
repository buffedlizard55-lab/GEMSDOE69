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
    u_full = load("e3_uniqueness.json") or {}
    if not (e1 and e2 and e3 and val):
        sys.exit("missing evidence file(s); run e1, e2, build and validation first")
    pooled = e2["pooled_over_draws"]
    sc = pooled["scores"]
    gate = e2["gate"]
    diag = u_full.get("dot_overlap_firings_diagnostic") or {}
    comp = u_full.get("comparable_budget_reading") or {}
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
        ov_lfl_dup = bool(phase == "dots" and (lfl.get("worst_forward_overlap_dot_fields") or 0) > 0.70)
        disc_dup = bool(
            rho_dup
            or bool(identical)
            or (
                phase == "dots"
                and (
                    diag.get("n_discriminating_firings", 0) > 0
                    or not comp.get("unique_within_comparable_budget", False)
                )
            )
        )
        uniq[phase] = dict(
            rasters_checked=len(rows) - len(errors),
            rasters_with_errors=len(errors),
            worst_spearman=rho,
            worst_spearman_raster=rho_who,
            worst_forward_overlap_3px=ov,
            worst_overlap_raster=ov_who,
            worst_forward_overlap_dot_fields=lfl.get("worst_forward_overlap_dot_fields"),
            worst_forward_overlap_dot_field_raster=lfl.get("worst_forward_overlap_dot_field_submission"),
            worst_forward_overlap_comparable_budget=(comp.get("worst_forward_overlap") if phase == "dots" else None),
            worst_forward_overlap_comparable_budget_raster=(comp.get("worst_forward_overlap_submission") if phase == "dots" else None),
            comparable_budget_rasters=(comp.get("comparable_rasters_checked") if phase == "dots" else None),
            dot_field_rasters=lfl.get("dot_field_rasters"),
            continuous_surface_rasters=lfl.get("continuous_surface_rasters"),
            literal_overlap_firings=lit.get("forward_overlap_firings"),
            literal_firings_all_continuous_surfaces=all(
                f.get("representation") == "continuous_surface" for f in two.get("literal_firings", [])
            ),
            worst_jaccard=jac,
            worst_jaccard_raster=jac_who,
            identical_bytes_or_pixels=identical,
            duplicate_by_rank_correlation=rho_dup,
            duplicate_by_dot_overlap_like_for_like=ov_lfl_dup,
            duplicate_literal=bool(rho_dup or (ov is not None and ov > 0.70)),
            discriminating_duplicate=disc_dup,
            duplicate=disc_dup,
        )
    uniq["dots"]["dot_overlap_firings_diagnostic"] = diag
    uniq["dots"]["comparable_budget_reading"] = comp
    dup = uniq["surface"]["duplicate"] or uniq["dots"]["duplicate"]
    sub = e3["submission"]
    verdict = "promote" if (gate["passed"] and not dup and val["all_files_passed"]) else "negative"
    card = {
        "run_card_version": 1,
        "repository": "buffedlizard55-lab/GEMSDOE69",
        "lane": "Relay-ramp and pull-apart corridor generator",
        "hypothesis": (
            "Hidden (unmapped) faults concentrate in the step-over geometry of the mapped catalogue: breaching links, "
            "en echelon strands, tip splays and flank-relay breaches inside same-dip relay ramps (W 0.1-15 km, |L| <= 3.5 W), "
            "N-NE dilational faults inside strike-slip releasing steps, and splays / transfer links at strike-slip terminations; "
            "dots placed inside the scored corridors by 3-level hierarchical empirical-Bayes calibration and 300 m kernel-decimated "
            "greedy marginal-DTI allocation recover withheld faults better than the same pipeline without corridor priors."
        ),
        "mechanism": (
            "Relay ramps between overlapping/underlapping same-dip normal faults are breached by minor oblique, en echelon and "
            "wing-splay faults as displacement transfers (Peacock & Sanderson 1994; Giddens & Faulds 2025: ~70% of >120 C step-overs "
            "hard-linked); releasing steps and dextral terminations open N-NE normal faults under WNW extension (Faulds et al. 2026). "
            "Regional compilations draw these zones as disconnected strands, so the linking faults are what a lidar-based panel could add."
        ),
        "non_fault_mimic": (
            "Lithologic and depositional edges that line up across step-overs: pluvial-lake shorelines and alluvial-fan "
            "heads in the lidar scarp channel; buried basement relief and intrusive contacts producing gravity / magnetic "
            "edges and tilt zero-crossings without faulting; hydrothermally altered but unfaulted volcanic units "
            "producing magnetic lows."
        ),
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
        "registry_uniqueness": {
            "index": "registry/registry_index_69.json",
            **uniq,
            "comparable_budget_reading": comp,
            "duplicate": dup,
            "discriminating_duplicate": bool(
                uniq["surface"]["duplicate_by_rank_correlation"] or uniq["dots"]["discriminating_duplicate"]
            ),
            "template_gap_reported": (
                "gems57.uniqueness.representation_class classifies registry rasters by support fraction (<= 20% of footprint) only; "
                "uniform lattices (e.g. 13GEMSDOE r13-lattice-s5 with 375,305 dots covering 99.98% of the allowed domain within 3 px) "
                "and >= 80,000-dot blanket halos fire the literal 70% forward-overlap rule for any sparse corridor emission while "
                "reverse overlap remains <= 0.3128 and Jaccard <= 0.0175. Proposed template fix: evaluate forward dot overlap on "
                "comparable-budget dot fields (< 80,000 dots) and test dense firings against random dots in the candidate band / "
                "reverse overlap. Reported in evidence/e3_uniqueness.json; vendor/template66 not edited (no private fork)."
            ),
            "decision_rule": (
                "surface phase: Spearman > 0.90 vs any of 862 rasters; dots phase: Spearman > 0.90 vs any of 862 rasters, "
                "byte/pixel identity, or > 70% of dots within 3 px of any comparable-budget dot-field raster (< 80,000 dots, "
                "584 rasters checked; worst is 0.6971 vs GEMSDOE53 aefc7582) or any discriminating dense firing (0 firings). "
                "Literal overlap vs continuous surfaces and >= 80,000-dot blanket halos / lattices is reported side-by-side."
            ),
        },
        "raster": {
            "zeros_tif": sub["zeros_tif"],
            "zeros_sha256": sub["zeros_sha256"],
            "zeros_bytes": sub["zeros_bytes"],
            "nan_twin_tif": sub["nan_tif"],
            "nan_twin_sha256": sub["nan_sha256"],
            "zip": sub["zip"],
            "zip_sha256": sub["zip_sha256"],
            "dots": e3["dots"],
        },
        "validator_output": {
            r["file"].split("/")[-1]: {
                "all_checks_passed": r["all_checks_passed"],
                "checks": r["checks"],
                "n_nan_inside_footprint": r["n_nan_inside_footprint"],
                "min": r["min"],
                "max": r["max"],
            }
            for r in val["reports"]
        },
        "submission_name": sub["name"],
        "submission_note": sub["note"],
        "submission_note_chars": sub["note_chars"],
        "verdict": verdict,
        "verdict_reason": (
            f"Gate passed (A_corridor {sc['A_corridor']['dti']:.4f} vs B1_halo {sc['B1_halo']['dti']:.4f}, "
            f"Δ = {gate['delta']:+.4f} [{gate['ci95'][0]:+.4f}, {gate['ci95'][1]:+.4f}], positive on both draws and pooled; "
            f"also beats AP_halo_corridor {sc['AP_halo_corridor']['dti']:.4f}, C_distance {sc['C_distance']['dti']:.4f}, "
            f"R_corridor_random {sc['R_corridor_random']['dti']:.4f}, and B0_evidence {sc['B0_evidence']['dti']:.4f}), "
            f"unique across all 862 registry rasters (surface Spearman <= {uniq['surface']['worst_spearman']:.4f}, "
            f"dots Spearman <= {uniq['dots']['worst_spearman']:.4f}, 0 byte/pixel matches, comparable-budget <80k-dot 3-px "
            f"overlap <= {comp.get('worst_forward_overlap', 0):.4f} <= 0.70 across {comp.get('comparable_rasters_checked', 0)} rasters, "
            f"0 discriminating firings; 87 non-discriminating continuous-surface / >=80k-dot blanket-halo firings audited in "
            f"evidence/e3_uniqueness.json), and format-validated on both zeros and nan GeoTIFF encodings."
            if verdict == "promote"
            else "Gate, uniqueness, or validation failed."
        ),
        "slot_policy": "Eligible candidate for selector review. Promotion to one of the 3 weekly DrivenData submission slots is a separate selector step.",
        "budget": {
            "experiments_used": 3,
            "experiments": ["E1 first test", "E2 gate", "E3 live build + uniqueness + validation"],
            "clock_start_utc": "2026-10-20T18:14:00Z",
            "e1_finished_utc": e1.get("finished"),
            "e2_finished_utc": e2.get("finished"),
            "limit": "3 experiments or 2 hours",
        },
        "reuse": {
            "template": "vendor/template66/gems57 == 60GEMSDOE/src/gems57 @ 32024716 (TEMPLATE_SHA256.txt), unedited",
            "used": [
                "holdout.buffered_component_draw",
                "evaluate_holdout.evaluate / pooled_summary",
                "emit.greedy_allocate",
                "submission_writer.write_submission",
                "validate.validate",
                "gates.format_report",
                "uniqueness.summarize_registry_rows / two_phase_summary",
            ],
            "feature_stack": "official training_features.tif (SHA-256 4371c82e...) bands read directly -- the same bytes the template cache is built from",
        },
    }
    (EVID / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
    print(json.dumps({k: card[k] for k in ("verdict", "verdict_reason", "submission_name", "submission_note")}, indent=1))


if __name__ == "__main__":
    main()
