"""Submission gate: a file may be offered for download only if the holdout evidence says so.

Rule (from the project brief): offer the download only if the candidate beats
(a) the same pipeline without corridor/prior features and (b) the current holdout best.
If the receipt is missing or incomplete the status is BLOCKED (not evaluated), never OK.
"""
from __future__ import annotations

REQUIRED = ("candidate_dti", "baseline_dti", "incumbent_dti",
            "n_withheld_positives", "ci95_low", "ci95_high", "evaluator_version")
NOTE_MAX = 140  # run-card limit for the free-text note used on this project


def decide(receipt: dict | None) -> dict:
    if not receipt:
        return {"status": "BLOCKED", "download_enabled": False,
                "reason": "no holdout receipt: gate not evaluated"}
    missing = [k for k in REQUIRED if receipt.get(k) in (None, "")]
    if missing:
        return {"status": "BLOCKED", "download_enabled": False,
                "reason": f"receipt incomplete: {missing}"}
    cand, base, inc = (float(receipt[k]) for k in ("candidate_dti", "baseline_dti", "incumbent_dti"))
    if cand > base and cand > inc:
        return {"status": "OFFER_DOWNLOAD", "download_enabled": True,
                "reason": "beats no-prior baseline and current holdout best"}
    return {"status": "NEGATIVE", "download_enabled": False,
            "reason": f"gate failed: candidate {cand:.4f}, baseline {base:.4f}, incumbent {inc:.4f}"}


def note_ok(note: str) -> bool:
    return 0 < len(note) <= NOTE_MAX
