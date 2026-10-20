#!/usr/bin/env python3
"""Write docs/status.json: what official data is present, and the gate state.

Official files (names as listed on the organizer's data page; the page is login-gated):
  training_features.tif, labels.tif, existing_faults.tif, sample_submission.tif,
  1m_DEM_links.csv
Provenance is NOT verified here: a present file is 'present (unverified provenance)'.
The gate is BLOCKED unless a complete holdout receipt exists in docs/receipts/.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import gate  # noqa: E402

OFFICIAL = ["training_features.tif", "labels.tif", "existing_faults.tif",
            "sample_submission.tif", "1m_DEM_links.csv"]


def main() -> int:
    data = {}
    for name in OFFICIAL:
        p = ROOT / "data" / name
        data[name] = {"present": p.exists(),
                      "bytes": p.stat().st_size if p.exists() else None,
                      "provenance": "present (unverified provenance)" if p.exists() else "missing"}
    receipts = sorted((ROOT / "docs" / "receipts").glob("*.json")) if (ROOT / "docs" / "receipts").exists() else []
    receipt = json.loads(receipts[-1].read_text()) if receipts else None
    decision = gate.decide(receipt)
    cand_name = (
        receipt.get("submission_name")
        if (receipt and decision["download_enabled"])
        else None
    )
    status = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "official_data": data,
        "all_official_files_present": all(v["present"] for v in data.values()),
        "gate": decision,
        "download_enabled": decision["download_enabled"],
        "candidate_submission": cand_name,
    }
    out = ROOT / "docs" / "status.json"
    out.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
