#!/usr/bin/env python3
"""Re-run the leakage canary after the finite-mask fix (z stack cached)."""

if __name__ == "__main__":
    from lane_preflight import require_open_lane
    require_open_lane()
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))

from gems57 import holdout as thold  # noqa: E402
from gems69.holdout69 import leakage_canary, load_template_grid  # noqa: E402
from gems69.physics import build_layer_stats, build_z_stack  # noqa: E402

g = load_template_grid()
stats = build_layer_stats(g.footprint)
zstack = build_z_stack(g.footprint, stats)
ctx = thold.build_holdout(g, seeds=(20,), modes=("all",))
can = leakage_canary(ctx, stats, zstack=zstack)
can["evidence_class"] = "LEAKAGE-CANARY"
can["rule"] = "single-feature AUC > 0.90 on the holdout = leakage until proven otherwise"
can["generated_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evidence" / "e1_canaries.json").write_text(json.dumps(can, indent=1, default=str))
worst = max(((k, v) for k, v in can.items() if isinstance(v, dict) and v.get("auc") is not None),
            key=lambda kv: kv[1]["auc"])
print("truth_px:", can["_truth_px"], "corridors:", can["_corridors"])
print("worst canary:", worst)
for k, v in can.items():
    if isinstance(v, dict) and v.get("auc") is not None and v["auc"] > 0.9:
        print("LEAKAGE FLAG:", k, v)
