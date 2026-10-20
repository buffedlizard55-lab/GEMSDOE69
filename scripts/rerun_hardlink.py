#!/usr/bin/env python3
"""Re-run the hard-linked ramp recovery after the disconnect-aware fix."""

if __name__ == "__main__":
    from lane_preflight import require_open_lane
    require_open_lane()
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))

from gems69.holdout69 import hardlinked_recovery, load_template_grid  # noqa: E402
from gems69.physics import build_layer_stats  # noqa: E402

g = load_template_grid()
stats = build_layer_stats(g.footprint)
rec = hardlinked_recovery(g.catalogue, g.footprint.shape, stats, max_ramps=24)
rec["evidence_class"] = "HOLDOUT-GEOMETRY"
import datetime as dt
rec["generated_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evidence" / "e1_hardlinked_recovery.json").write_text(json.dumps(rec, indent=1, default=str))
print(json.dumps({k: rec.get(k) for k in ("n_hardlinked_found", "n_disconnected_tested",
                                          "n_still_connected_after_mask",
                                          "mean_recovery_within_300m",
                                          "n_ramps_above_70pct")}, indent=1))
