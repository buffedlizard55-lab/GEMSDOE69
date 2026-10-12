"""Dump the full per-corridor rationale list (deterministic replay of the e3 pipeline).

The run-card receipt keeps the top-25 corridors; the lane prompt requires a rationale
per corridor, so the complete list is written here. The replay is deterministic (fixed
seeds/caps); we verify the propensity sha8 matches the shipped artifact before trusting
the dump.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "template66"))
sys.path.insert(0, str(ROOT / "src"))

from gems69.holdout69 import corridor_pipeline, load_template_grid  # noqa: E402
from gems69.physics import build_layer_stats, build_z_stack  # noqa: E402

g = load_template_grid()
stats = build_layer_stats(g.footprint)
zstack = build_z_stack(g.footprint, stats)
pipe = corridor_pipeline(g.catalogue, g.footprint.shape, stats, max_corridors=1200,
                         zstack=zstack)
p = pipe["propensity"]
h8 = hashlib.sha256(p.tobytes()).hexdigest()[:8]
receipt = json.loads((ROOT / "evidence" / "e3_receipt.json").read_text())
expected = receipt["propensity_sha256"]
assert h8 == expected, f"replay mismatch: {h8} != {expected}"
rat = [c.rationale for c in pipe["corridors_obj"] if "score_S" in c.rationale]
rat.sort(key=lambda r: -r["score_S"])
out = dict(
    evidence_class="PIPELINE-REPLAY-DETERMINISTIC",
    propensity_sha8=h8,
    matches_shipped_propensity=bool(h8 == expected),
    n_corridors=len(rat),
    corridors=rat,
)
dest = ROOT / "evidence" / "e3_corridor_rationales_full.json"
dest.write_text(json.dumps(out, separators=(",", ":")))
print(f"wrote {dest.name}: {len(rat)} corridors, propensity sha8 {h8}")
