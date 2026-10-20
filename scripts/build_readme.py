#!/usr/bin/env python3
"""Rebuild README.md from the fail-closed policy, run card, and standing brief.

The release policy is deliberately narrower than the run card: it is the only
component allowed to publish a binary.  The run card can record an archived
negative experiment, but cannot make it downloadable.
"""
from __future__ import annotations

import json
from pathlib import Path

from release_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


def load_evidence(name: str) -> dict:
    try:
        return json.loads((ROOT / "evidence" / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def fmt(value: object, digits: int = 6) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "not recorded"


def main() -> None:
    policy = evaluate(ROOT)
    card = load_evidence("run_card.json")
    holdout = card.get("holdout", {})
    registry = card.get("correlation_overlap_vs_registry", {})
    raster = card.get("raster", {}).get("zeros", {})
    candidate = card.get("hypothesis", "archived candidate")
    name = card.get("submission_name", "not recorded")
    sha = raster.get("sha256", "not recorded")
    ci = holdout.get("ci95")
    ci_text = (
        f"[{fmt(ci[0], 6)}, {fmt(ci[1], 6)}]"
        if isinstance(ci, list) and len(ci) == 2
        else "not recorded"
    )
    release_reasons = "\n".join(f"- {reason}" for reason in policy["reasons"])
    literal = registry.get("literal_gate", {})
    overlap = (registry.get("worst_dot_overlap_all") or {}).get("dot_overlap_3px")

    status = (
        "OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE (selector authorization still required)"
        if policy["download_enabled"]
        else "NOT OK TO SUBMIT — DO NOT SUBMIT"
    )
    artifact_status = (
        "The exact hash-bound artifact is published in `docs/downloads/`."
        if policy["download_enabled"]
        else "No TIFF or ZIP is published for submission. Files in `submissions/` are audit artifacts only."
    )

    head = f"""# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {status}

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json) · [publication audit](reports/publication-audit-2026-10-20.md) · [release-gate follow-up](reports/release-gate-followup-2026-10-20.md) · [final audit](reports/final-audit-2026-10-20.md).

**Submission status:** {artifact_status}

The governing lane rule is literal: if any registry raster has rank correlation above 0.90 **or** more than 70% of final dots within 3 pixels, the candidate is a duplicate and the process stops. Dense-support / dotlike strata are useful diagnostics, but do not override the written stop rule.

**Lane geometry scope:** step-over width W = 0.1–15 km; along-strike separation ≤3.5W. Same-dip direction and dextral-releasing geometry require measured attributes, not a strike-only proxy.

### Current recorded candidate — archived H69-H2 transfer-only

`{candidate}`

- Submission name: `{name}`; zeros TIFF SHA-256: `{sha}`.
- **HOLDOUT-DTI**: {fmt(holdout.get('dti'), 6)}, 95% CI {ci_text}; evaluator `{holdout.get('evaluator_version', 'not recorded')}`; {holdout.get('withheld_positive_pixels', 'not recorded')} withheld positives across {holdout.get('n_cells', 'not recorded')} cells; comparator {fmt(holdout.get('comparator_dti'), 6)}. This is a local screen, **not** an organizer score or leaderboard projection.
- **REGISTRY-MEASUREMENT**: {registry.get('n_compared', 'not recorded')}/{registry.get('n_registry_blobs', 'not recorded')} accessible hash-verified entries, worst literal 3-pixel overlap {fmt(overlap, 4)} (limit 0.7000), literal rho pass={literal.get('rho_ok', 'not recorded')}, literal overlap pass={literal.get('overlap_ok', 'not recorded')}. The recorded transfer candidate is a duplicate-and-stop negative result; its historical holdout also used the chunked, unbuffered legacy runner documented in `evidence/relayfix_holdout_protocol_audit.json` and is not protocol-qualified, despite its local format receipt.

### Why download is locked

{release_reasons}

`release_gate.py` is intentionally fail-closed and controls publication. Its H69-J aggregate evidence is not a substitute for the H69-H2 run card, and a negative run card never authorizes a download. H69-J's local aggregate receipts are now hash-bound, but its literal all-registry overlap still fails and therefore it also cannot be published. No competition slot was used.

## What was learned without submitting

- H69-H2 transfer-only is a formatted archived artifact with a recorded HOLDOUT-DTI screen, but its literal all-registry overlap is 1.0 (and the dotlike diagnostic is also above the 0.70 stop limit). It is not offered for download.
- H69-J is a distinct joint-corridor artifact with locally hash-bound aggregate receipts. Its format and local holdout records establish neither uniqueness nor an organizer score: literal overlap remains 1.0, so it is not eligible for the separate selector.
- A separate 39,958-dot TIFF in `submissions/` (SHA-256 `287372cb3fc6d7b8bcdb6bffbf5632d92a8d1d2e0dee6c2fb884d74d10d923f4`) passes local format checks only. The current receipt, method manifest, holdout and uniqueness scans are bound to different bytes; it has no current evidence and is not downloadable.
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
GEMS_DATA="$PWD/data/bridge" PYTHONPATH=vendor/template66:src \\
  .venv/bin/python scripts/validate_submission.py \\
  submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif
PYTHONPATH=vendor/template66:src .venv/bin/pytest -q
```

`data/bridge/` is a small, integrity-pinned mirror sufficient for local format checks, not the full authenticated competition stack. A fresh scientific run requires restored pinned mirrors plus a complete registry and still must obey the literal duplicate-and-stop rule.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

"""
    (ROOT / "README.md").write_text(head + (ROOT / "PROMPT.md").read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    main()
