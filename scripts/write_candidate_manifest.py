#!/usr/bin/env python3
"""Bind a session candidate (H69-M / H69-N) for scripts/release_gate.py.

Usage: write_candidate_manifest.py h69m|h69n|none

Writes evidence/<id>_method_manifest.json (sha256 of every method source, the gate
evidence and the emitted artifact) and evidence/current_candidate.json (names the
candidate's evidence files).  ``none`` records that no candidate passed, which makes
the release gate fail closed with an explicit reason.  Pure stdlib.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
COMMON = ["src/gems69/corridors.py", "src/gems69/tips.py", "src/gems69/physics.py", "src/gems69/scoring.py",
          "src/gems69/scoring_joint.py", "src/gems69/evidence_first.py", "src/gems69/holdout69.py",
          "scripts/run_h69m.py", "scripts/uniqueness_h69m.py",
          "vendor/template66/gems57/holdout.py", "vendor/template66/gems57/emit.py",
          "vendor/template66/gems57/uniqueness.py", "vendor/template66/gems57/grid.py"]
SPEC = {
    "h69m": dict(hypothesis="H69-M", prereg="registry/preregistration-2026-10-20-h69m-evidence-first.json",
                 extra=[]),
    "h69n": dict(hypothesis="H69-N", prereg="registry/preregistration-2026-10-20-h69n-evidence-quota.json",
                 extra=["src/gems69/evidence_quota.py", "scripts/run_h69n.py"]),
}


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    cid = sys.argv[1]
    now = datetime.now(timezone.utc).isoformat()
    if cid == "none":
        (EV / "current_candidate.json").write_text(json.dumps(dict(
            hypothesis=None, generated_utc=now,
            note="No session candidate passed its preregistered gates; see evidence/run_card.json."), indent=1))
        print("current_candidate: none")
        return 0
    s = SPEC[cid]
    cand = dict(hypothesis=s["hypothesis"], preregistration=s["prereg"], gate=f"{cid}_gate.json",
                receipt=f"{cid}_receipt.json", uniqueness_surface=f"{cid}_uniqueness_surface.json",
                uniqueness_dots=f"{cid}_uniqueness_dots.json", validator=f"{cid}_validator.json",
                method_manifest=f"{cid}_method_manifest.json", generated_utc=now)
    receipt = json.loads((EV / cand["receipt"]).read_text())
    srcs = COMMON + s["extra"] + [s["prereg"]]
    manifest = dict(hypothesis=s["hypothesis"], generated_utc=now,
                    artifact_sha256=receipt["raster"]["zeros"]["sha256"],
                    gate_sha256=sha("evidence/" + cand["gate"]),
                    source_sha256={rel: sha(rel) for rel in srcs})
    (EV / cand["method_manifest"]).write_text(json.dumps(manifest, indent=1))
    (EV / "current_candidate.json").write_text(json.dumps(cand, indent=1))
    print(json.dumps(cand, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
