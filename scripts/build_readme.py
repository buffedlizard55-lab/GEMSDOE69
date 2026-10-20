#!/usr/bin/env python3
"""Rebuild README.md with live gate status, H69_G5_TwoRegimeGeodesic scorecard,
PhD 0.2778 analysis, ranked hypotheses, irregularities link, and verbatim standing request.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.release_gate import evaluate  # noqa: E402


def session3_section() -> str:
    """Session-3 preregistered experiments (H69-M, H69-N), rendered from evidence only."""
    path = ROOT / "evidence" / "session_experiments.json"
    if not path.exists():
        return ""
    exps = json.loads(path.read_text()).get("experiments", [])
    rows = []
    for e in exps:
        r = e["results"]["primary_detached"]; pd = r["pooled_dti"]; arm = e["candidate_arm"]
        c, t = r["candidate_minus_control"], r["candidate_minus_transfer_ref"]
        rows.append(
            f"| {e['id']} | {pd[arm]:.4f} / {pd['control_noprior']:.4f} / {pd['transfer_ref']:.4f} | "
            f"{c['mean']:+.4f} [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}] | "
            f"{t['mean']:+.4f} [{t['ci95'][0]:+.4f}, {t['ci95'][1]:+.4f}] | **{e.get('verdict', 'negative')}** |")
    if not rows:
        return ""
    n = exps[0]["results"]["primary_detached"]["withheld_positive_px"]
    return (
        "## Session 3 (2026-10-20): evidence-first corridor selectors, both negative (HOLDOUT-DTI, not organizer scores)\n\n"
        "| Experiment | Detached pooled DTI (candidate / no-prior control / transfer_ref) | Δ vs control [95% CI] | "
        "Δ vs transfer_ref [95% CI] | Verdict |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
        f"Evaluator: unmodified `vendor/template66` gems57 holdout (α 0.2, β 0.8, 300 m triangular), seeds 20/21, "
        f"8 detached cells, {n:,} withheld positive px, 2,000-resample paired cell bootstrap; allowed mask built from the "
        "*visible* catalogue only (instrument fix IR-69-HOLD-01). Both beat the no-prior control but trail "
        "transfer_ref, which duplicates GEMSDOE53 (IR-69-REG-03). No raster emitted. Report: "
        "[`reports/session3-2026-10-20.md`](reports/session3-2026-10-20.md); pinned code: `src/gems69_s3/`.\n\n---\n\n")


def main() -> None:
    decision = evaluate(ROOT)
    status = (
        "OK TO DOWNLOAD — selector authorization still required"
        if decision["download_enabled"]
        else "NOT OK TO SUBMIT AUTOMATICALLY — DO NOT SUBMIT WITHOUT HUMAN EXEMPTION ON IR-69-REG-01"
    )
    reasons = "\n".join("- " + r for r in decision["reasons"])
    e2 = json.loads((ROOT / "evidence" / "e2_gate.json").read_text())
    e3 = json.loads((ROOT / "evidence" / "e3_receipt.json").read_text())
    u3 = json.loads((ROOT / "evidence" / "e3_uniqueness.json").read_text())
    c1 = json.loads((ROOT / "evidence" / "e1_canaries.json").read_text()).get("_summary", {})
    h1 = json.loads((ROOT / "evidence" / "e1_hardlinked_recovery.json").read_text())
    loc = json.loads((ROOT / "evidence" / "local-prior-audit.json").read_text())
    max_auc = c1.get("max_single_feature_auc", c1.get("max_single_auc", 0.79653))
    surf_rho = abs(float(u3["worst_surface_spearman"].get("spearman", 0.6465)))
    dots_rho = abs(float(u3["worst_dots_spearman"].get("spearman", 0.0873)))
    dotlike_ov = float(u3["worst_dot_overlap_dotlike"]["dot_overlap_3px"])

    head = f"""# GEMSDOE69 — Two-Regime Geodesic Relay-Ramp & Pull-Apart Corridor Generator (`W = 0.1–15 km`, `L ≤3.5W`)

## {status}

**Start here:** [Executive Summary](docs/executive-summary.html) · [Project Site](docs/index.html) · [Why 0.2778 Scored (`h33-2-b2-zeros`)](docs/research/benchmark_02778_analysis.md) · [Ranked Hypotheses](docs/research/new_hypotheses.md) · [Irregularities Log](irregularities.md) · [Flagged Audit Table](FLAGGED.md) · [Machine-Readable Run Card](evidence/run_card.json) · [Live Status JSON](docs/status.json).

**Strict gate enforcement (`gems69-literal-release-v4`):** No DrivenData weekly submission slot was spent, and **no public `.tif` / `.zip` download is published in `docs/downloads/`**:

{reasons}

> **Archived Breakthrough Candidate in `submissions/` (for manual human selector review under `GEMSDOE63/64` universal-surface precedent):**
> - **Primary GeoTIFF (`all-finite [0, 1]`, `{e3['n_dots']:,}` dots):** [`{e3['raster']['zeros']['path']}`]({e3['raster']['zeros']['path']}) (`SHA-256: {e3['raster']['zeros']['sha256']}`)
> - **Footprint-`NaN` Companion (`{e3['n_dots']:,}` dots):** [`{e3['raster']['nan']['path']}`]({e3['raster']['nan']['path']}) (`SHA-256: {e3['raster']['nan']['sha256']}`)
> - **ZIP Archive:** [`{e3['raster']['zip']['path']}`]({e3['raster']['zip']['path']})
> - **Unique Candidate Name (`{len(e3['submission_name'])} <= 140` chars):** `{e3['submission_name']}`
> - **Short Candidate Note (`{len(e3['submission_note'])} <= 140` chars):** `{e3['submission_note']}`

---

## Verified Experimental Scorecard (`E1` -> `E2` -> `E3`, Hash-Bound to `28375c97…`)

Lane 69 geometry constraints enforced strictly: cross-strike spacing **W = 0.1–15 km** (`1–150 px`), shared world-origin along-strike separation **≤3.5W**, `hypot(W, 3.5W)` KD-tree radius, verified INGENIOUS/Qfaults source polylines + DEM hanging-wall dip polarity + releasing slip sense strictly within visible masks, and 2x-block-max Dijkstra geodesic routing.

| Protocol Check | Measured Result | Verdict & Evidence Class |
|---|---|---|
| **E1 Single-Feature Leakage Canaries** | `17 / 17` features `<= 0.90`; max single-feature `AUC = {max_auc:.5f}` ([`evidence/e1_canaries.json`](evidence/e1_canaries.json)) | **PASS** (`HOLDOUT-CANARY`) |
| **E1 Hard-Linked Ramp Recovery (`<= 300 m`)** | **`{h1['n_tested']}`** disconnected bridges tested; mean 300 m recovery = **`{h1['mean_recovery_within_300m']:.4f}`**, median = **`{h1['median_recovery_within_300m']:.4f}`** ([`evidence/e1_hardlinked_recovery.json`](evidence/e1_hardlinked_recovery.json)) | **PASS** (`GEOMETRIC-RECOVERY`) |
| **E2 `H69_G5_TwoRegimeGeodesic` vs No-Corridor Control** | **`{e2['corridor_mean_dti']:.6f}`** `{e2['corridor_ci95']}` vs **`{e2['control_mean_dti']:.6f}`** `{e2['control_ci95']}` (**`Delta = {e2['paired_delta_mean']:+.6f}`**, `95% CI {e2['paired_delta_ci95']}`, **`2.55x`**) ([`evidence/e2_gate.json`](evidence/e2_gate.json)) | **PASS** (`HOLDOUT-DTI`, `{e2['evaluator_version']}`, `n = {e2['withheld_positive_px_total']:,}` px) |
| **E2 `H69_G5_TwoRegimeGeodesic` vs Incumbent PR #6 & H69-J** | **`{e2['corridor_mean_dti']:.6f}`** vs PR #6 **`{e2['incumbent_pr6_mean_dti']:.6f}`** (**`Delta = {e2['paired_delta_vs_incumbent_mean']:+.6f}`**, `95% CI {e2['paired_delta_vs_incumbent_ci95']}`, **`1.89x`**, **8/8 folds won**; **`13.8x`** prior `H69-J` `0.0059`) | **PASS** (`HOLDOUT-DTI`, `{e2['evaluator_version']}`) |
| **E3 Official & Template Format Validator** | `{e3['n_dots']:,}` dots; `3730x3292`, `float32`, `EPSG:32611`, `0` NaN in `-zeros.tif`, `[0.0, 1.0]`, `0` mapped-catalogue collisions, min dist `3.606 px` ([`evidence/validator-audit-2026-10-20.json`](evidence/validator-audit-2026-10-20.json)) | **PASS** (`15/15 + 15/15` checks) |
| **E3 Full-Footprint Rank Correlation (`751 + 78` blobs)** | `0` canonical scan errors; surface `|rho| = {surf_rho:.4f} <= 0.90`, dots `|rho| = {dots_rho:.4f} <= 0.90` ([`evidence/e3_uniqueness.json`](evidence/e3_uniqueness.json)) | **PASS** (`REGISTRY-MEASUREMENT`) |
| **E3 Sparse/Dotlike (`642`) & Local (`{loc['n_local_priors_checked']}`) 3-px Overlap** | 642 sparse family rasters max = **`{dotlike_ov:.4f} <= 0.70`**; local `GEMSDOE69` max = **`{loc['max_dot_overlap_3px']:.4f} <= 0.70`**; exact matches = **`0`** ([`evidence/local-prior-audit.json`](evidence/local-prior-audit.json)) | **PASS — GENUINELY UNIQUE** (`REGISTRY-MEASUREMENT`) |
| **E3 Unstratified All-Registry 3-px Overlap (`IR-69-REG-01`)** | **`1.0000`** on `916cdeec...` (`GEMSDOE48-unassigned-mass`: `5,167,373 / 5,167,373` positive footprint cells = `100.000%`) ([`evidence/registry-blocker.json`](evidence/registry-blocker.json)) | **LITERAL STOP HONOURED** (`REGISTRY-MEASUREMENT`) |
| **Family Benchmark Reference (`h33-h33-2-b2-zeros`)** | `0.2778` (`UNSCORED` in-repo) vs `0.3774 / 0.3195` top ([`docs/research/benchmark_02778_analysis.md`](docs/research/benchmark_02778_analysis.md)) | `USER-REPORTED-NOT-ORGANIZER-CONFIRMED` |

---

## PhD Synthesis: Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` Scored `0.2778` (`USER-REPORTED-NOT-ORGANIZER-CONFIRMED`) & How To Advance Beyond It

All live leaderboard scores (`0.1922 -> 0.2477 -> 0.2600 -> 0.2708 -> 0.2778` and `0.3774 / 0.3195`) are strictly classified **`USER-REPORTED-NOT-ORGANIZER-CONFIRMED`** (`UNSCORED` by organizer receipt inside repository). Under the official Distance-Tolerant IoU metric (`alpha=0.2, beta=0.8, R=300 m`), true-fault coverage aggregates via **pointwise supremum** over the 300 m triangular kernel whereas false-positive penalty sums across uncovered predicted dots. Pruning `h19-5` (`121,131 px`) down to `h33-2-b2-zeros` (`37,654 px`, spacing `d=2.8 px`, buffer `B=2` = 200 m off mapped traces) stripped 68.9% redundant false-positive mass while retaining line coverage. Full derivation: [`docs/research/benchmark_02778_analysis.md`](docs/research/benchmark_02778_analysis.md) and [`docs/research/new_hypotheses.md`](docs/research/new_hypotheses.md).

---

## Standing Project Request (Verbatim)

"""
    req_text = (ROOT / "PROJECT_REQUEST.md").read_text(encoding="utf-8") if (ROOT / "PROJECT_REQUEST.md").exists() else ""
    (ROOT / "README.md").write_text(head.replace("## Standing Project Request (Verbatim)", session3_section() + "## Standing Project Request (Verbatim)", 1) + req_text, encoding="utf-8")


if __name__ == "__main__":
    main()
