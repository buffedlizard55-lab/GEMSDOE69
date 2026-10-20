#!/usr/bin/env python3
"""Rebuild README status from the current run card and append the full brief."""
from __future__ import annotations

import json
from pathlib import Path

from release_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    decision = evaluate(ROOT)
    card_path = ROOT / "evidence" / "run_card.json"
    card = json.loads(card_path.read_text(encoding="utf-8")) if card_path.exists() else {}
    holdout = card.get("holdout", {})
    raster = card.get("raster", {})
    reasons = "\n".join(f"- {reason}" for reason in decision["reasons"]) or "- All publication gates passed."

    current_status = "NOT OK TO SUBMIT — DO NOT SUBMIT" if not decision["download_enabled"] else "OK TO DOWNLOAD — SELECTOR AUTHORIZATION STILL REQUIRED"
    if decision["download_enabled"]:
        publication = f"A gated download may be published for `{raster.get('path', 'candidate')}` only after the policy passes. A separate selector must authorize any competition slot."
    else:
        publication = (f"Candidate `{raster.get('path', 'unavailable')}` is archived for audit only. "
                       "There is no submission download, no offer of a TIFF, and no competition slot was used. "
                       "Local format validation is not release clearance.")

    pooled = holdout.get("pooled_dti")
    mean_cell = holdout.get("mean_of_cell_dti")
    current_holdout = (
        f"The current archived experiment is labelled **HOLDOUT-DTI** ({holdout.get('evaluator_version', 'evaluator not recorded')}; "
        f"{holdout.get('n_cells', 'unknown')} cells; {holdout.get('withheld_positive_pixels', 'unknown')} withheld positives). "
        f"Primary pooled DTI from summed TP/FP/FN: `{pooled}`; pooled absolute 95% CI: `{holdout.get('pooled_dti_ci95')}`. "
        f"Mean-of-cell DTI: `{mean_cell}` with normal-approximation CI `{holdout.get('mean_of_cell_dti_ci95_normal_approximation')}`. "
        "Paired CIs below are deltas against their named comparators, not absolute pooled-DTI CIs."
    )

    head = f'''# GEMSDOE69 — relay-ramp and pull-apart corridor lane

## {current_status}

{publication}

**Start here:** [Executive summary](docs/executive-summary.html) · [Project site](docs/index.html) · [Current JSON run card](evidence/run_card.json) · [Current holdout and release audit](reports/repo-review-2026-10-20.md).

**Lane contract:** catalogue tip-graph relay ramps / pull-aparts only; W 0.1–15 km; along-strike separation ≤3.5W. Dip direction and dextral slip sense must not be inferred from strike alone.

### Current decision

{current_holdout}

**Literal registry result** (`REGISTRY-MEASUREMENT`, not a score): accessible index {card.get('correlation_overlap_vs_registry', {}).get('registry_rasters_compared', 'unknown')} rasters; worst final-dot overlap `{(card.get('correlation_overlap_vs_registry', {}).get('worst_dot_overlap_all') or {}).get('dot_overlap_3px', 'not recorded')}`. The literal protocol requires stop if Spearman exceeds 0.90 **or** more than 70% of candidate dots are within 3 px of one raster. Stratified/dotlike diagnostics cannot waive that failure. The scanned public owner-repository index is not a complete organizer registry.

**Release blockers:**
{reasons}

### H33 and leaderboard claims

The reported H33 value **0.2778 is USER-REPORTED-NOT-ORGANIZER-CONFIRMED**: this repository has no organizer submission receipt binding that score to a file. It is not a target that this lane has demonstrated it can beat. Holdout DTI is a screening instrument, not a leaderboard projection. No fresh leaderboard fetch was performed in this review; conflicting historic/user-reported values remain unverified.

### Ranked untried work (not authorization to test)

See [three in-lane hypotheses](docs/research/untried-hypotheses-2026-10-20.md). They are qualitative priors confirmed untested **in this checkout** by source/evidence review, not global novelty claims. The preferred next hypothesis was **not tested**: the feature cache is absent, current-candidate provenance is stale, and the current-best paired comparison is missing. No new candidate or TIFF was generated.

### Reproduce status and tests (no experiment or data restore)

```sh
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/release_gate.py
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/build_site69.py
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/build_readme.py
PYTHONPATH=vendor/template66:src .venv/bin/python -m pytest -q
```

`release_gate.py` is read-only by default. `--write-card` only rebinds the existing frozen receipts into `evidence/run_card.json`; it does not rerun an experiment. The local feature cache is absent from this checkout, so the archived science is not reproducible here without separately authorized data restoration. Exact candidate bytes previously passed the local format/range validator; that does not clear uniqueness, provenance, current-best, or organizer-authentication gates.

### Review status

Three review passes are recorded in `reports/repo-review-2026-10-20.md`: requirements/status, code and evidence binding, then final adversarial re-check. No competition slot was selected or used. PR/merge status is tracked in GitHub separately from the scientific run card.

## Standing project brief — read in full at the beginning of every session

The full retained brief is included below from `PROMPT.md`; read it before taking any action.

'''
    (ROOT / "README.md").write_text(head + (ROOT / "PROMPT.md").read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    main()
