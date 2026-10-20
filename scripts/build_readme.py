#!/usr/bin/env python3
"""Rebuild README.md from the fail-closed release decision and standing brief.

This intentionally does not reinterpret archived science evidence.  It only
summarises its provenance so a format-valid historical TIFF cannot be mistaken
for a current, submit-ready artifact.
"""
from __future__ import annotations

import json
from pathlib import Path

from release_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


def load_evidence(name: str) -> dict:
    try:
        return json.loads((ROOT / "evidence" / name).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def number(value: object, digits: int = 6) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "not recorded"


def main() -> None:
    decision = evaluate(ROOT)
    gate = load_evidence("e2_gate.json")
    uniq = load_evidence("e3_uniqueness.json")
    receipt = load_evidence("e3_receipt.json")
    raster = receipt.get("raster", {}).get("zeros", {})
    artifact_name = Path(raster.get("path", "no-artifact")).name
    artifact_sha = raster.get("sha256", "not recorded")
    reasons = "\n".join(f"- {reason}" for reason in decision["reasons"])

    status = (
        "OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE (selector authorization still required)"
        if decision["download_enabled"]
        else "NOT OK TO SUBMIT — DO NOT SUBMIT"
    )
    artifact_status = (
        f"The exact hash-bound TIFF `{artifact_name}` is published in `docs/downloads/`."
        if decision["download_enabled"]
        else "No TIFF or ZIP is published for submission. Files in `submissions/` are audit artifacts only."
    )

    archived_holdout = (
        "ARCHIVED HOLDOUT-DTI (not artifact-bound on this checkout): "
        f"corridor mean {number(gate.get('corridor_mean_dti'))}, "
        f"95% CI half-width {number(gate.get('corridor_ci95_half'))}, "
        f"control mean {number(gate.get('control_mean_dti'))}, "
        f"{gate.get('n_cells', 'not recorded')} cells, "
        f"{gate.get('withheld_positive_px_total', 'not recorded')} withheld positive pixels."
    )
    literal = uniq.get("literal_gate", {})
    registry = (
        "REGISTRY-MEASUREMENT (archived): "
        f"worst absolute Spearman {number(uniq.get('worst_abs_spearman'), 3)}; "
        f"literal rho pass={literal.get('rho_ok', 'not recorded')}; "
        f"literal overlap pass={literal.get('overlap_ok', 'not recorded')}."
    )

    head = f"""# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {status}

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json) · [latest audit](reports/final-audit-2026-10-20.md).

**Submission status:** {artifact_status}

The governing lane rule is literal: if any registry raster has rank correlation above 0.90 **or** more than 70% of final dots within 3 pixels, the candidate is a duplicate and the process stops. Dense-support / dotlike strata are useful diagnostics, but do not override this release decision.

**Lane geometry scope:** step-over width W = 0.1–15 km; along-strike separation ≤3.5W. Same-dip direction and dextral-releasing geometry require measured attributes, not a strike-only proxy.

### Why download is locked

{reasons}

The historical candidate's zeros-TIFF SHA-256 is `{artifact_sha}`. Its local format receipt can establish byte-level format only; it cannot cure an unbound holdout, a stale method manifest, or a failed literal uniqueness gate. No competition slot was used by this repository state.

## What was learned without submitting

- {archived_holdout}
- {registry}
- The H69-J joint-corridor artifact is **not a current promotion**: its method-source and holdout bindings are stale after the tip-graph repair, and the literal overlap gate is independently failing.
- The transfer-only artifact is a distinct negative result. Its archived HOLDOUT-DTI screen exceeded its stated internal comparator, but its literal all-registry overlap was 1.0 and its worst dotlike overlap was 0.8497; therefore it is also not offered.
- No new TIFF is generated in this review: emitting another candidate after a duplicate-and-stop result would violate the parallel-run protocol and would not make it submission-ready.

## H33 result review — correction to the premise

The cited H33 `h33-h33-2-b2` bytes are useful **for learning only**, never as an input or template for this lane. A fresh owner-repository source audit found that the current GEMSDOE32 owner audit calls this exact H33-2-B2 file **UNSCORED** and labels 0.2747 as a projection, while the owner page identifies the 0.2708 base as the already-scored fallback. Its manifest contains no organizer receipt for H33-2-B2. Thus the user-supplied 0.2778 cannot be attributed to these bytes from verified evidence. The measured structure is a sparse catalogue-flank removal from an existing field, not proof of a new geological discovery. See [the source audit](reports/h33-owner-source-audit-2026-10-20.md) and [the owner audit JSON on GitHub](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json).

## Candidate research queue (not implemented in this review)

The lane's ranked, in-scope hypotheses are documented in [Hypotheses](docs/hypotheses.html): (1) opposing-margin relay-link profile phase, (2) releasing-basin margin asymmetry, (3) en-échelon scarp phase coherence, and (4) matched-flank radiometric contrast reversal. All require a fresh preregistration, feature-alone leakage canaries, untouched spatial blocks, a literal pre-placement registry scan, and an identical post-placement scan. None is a score projection or slot authorization.

## Reproduce the publication audit

```sh
python scripts/release_gate.py
python scripts/build_site69.py
python scripts/build_readme.py
```

For format validation and tests, create an ignored environment and install the declared dependencies:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
GEMS_DATA="$PWD/data/bridge" PYTHONPATH=vendor/template66:src \
  .venv/bin/python scripts/validate_submission.py \
  submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-zeros.tif
PYTHONPATH=vendor/template66:src .venv/bin/pytest -q
```

`data/bridge/` is a small, integrity-pinned mirror sufficient for local format checks, not the full authenticated competition stack. A fresh scientific run requires restored pinned mirrors plus a complete registry and still must obey the literal duplicate-and-stop rule.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

"""
    (ROOT / "README.md").write_text(head + (ROOT / "PROMPT.md").read_text())


if __name__ == "__main__":
    main()
