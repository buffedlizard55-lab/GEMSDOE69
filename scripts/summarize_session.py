#!/usr/bin/env python3
"""Summarise this session's preregistered experiments into evidence/session_experiments.json.

Reads evidence/h69m_gate.json and evidence/h69n_gate.json (whichever exist) and the
uniqueness phase files.  Copies numbers verbatim from those receipts and attaches the
evidence label required by the protocol (HOLDOUT-DTI: evaluator, withheld positives,
95 % CI).  Pure stdlib; computes nothing new.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
EXPS = [("h69m", "H69-M", "h69m_evidence_first", "h69m"), ("h69n", "H69-N", "h69n_evidence_quota", "h69n")]


def load(name):
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else None


def main() -> int:
    out = []
    for cid, hyp, arm, pfx in EXPS:
        g = load(f"{cid}_gate.json")
        if not g:
            continue
        res = {}
        for ep in ("primary_detached", "secondary_all"):
            r = g["results"][ep]
            res[ep] = dict(cells=len(r["cells"]), withheld_positive_px=r["withheld_positive_px"],
                           pooled_dti=r["pooled_dti"],
                           candidate_minus_control=r[f"{pfx}_minus_control"],
                           candidate_minus_transfer_ref=r[f"{pfx}_minus_transfer_ref"],
                           transfer_ref_minus_control=r["transfer_ref_minus_control"])
        surf = load(f"{cid}_uniqueness_surface.json") or {}
        out.append(dict(
            id=hyp, preregistration=g["preregistration"], evidence_class="HOLDOUT-DTI",
            evaluator=g["evaluator"], candidate_arm=arm, results=res,
            prompt_gate_passed=g["prompt_gate_passed"], current_best_beaten=g["current_best_beaten"],
            canary_ok=g["canary_ok"],
            canary_worst_auc_top5=sorted(g["canary_worst_auc"].items(), key=lambda kv: -kv[1])[:5],
            surface_uniqueness=dict(worst_spearman=surf.get("worst_spearman"),
                                    worst_spearman_submission=surf.get("worst_spearman_submission"),
                                    compared=surf.get("corpus", {}).get("compared"),
                                    stop_required=surf.get("stop_required")) if surf else None,
            verdict="promote-to-emission" if (g["prompt_gate_passed"] and g["current_best_beaten"]
                                              and g["canary_ok"]) else "negative"))
    doc = dict(generated_utc=datetime.now(timezone.utc).isoformat(), experiments=out,
               note=("Numbers copied from the gate receipts. HOLDOUT-DTI on catalogue hide-and-recover cells is "
                     "NOT comparable to live leaderboard values (different truth: withheld mapped segments vs "
                     "expert-labelled new faults)."))
    (EV / "session_experiments.json").write_text(json.dumps(doc, indent=1))
    for e in out:
        p = e["results"]["primary_detached"]
        print(e["id"], e["verdict"], json.dumps(p["pooled_dti"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
