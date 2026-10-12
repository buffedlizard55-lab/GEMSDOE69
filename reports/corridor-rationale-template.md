# Per-corridor rationale record

Use one copy per proposed corridor, generated **inside a specific spatial fold from the visible-fault catalogue only**. Do not create a record for a corridor that depends on a withheld segment, hidden-label data, or a catalogue feature computed before the fold split. This is a blank audit template; there are no candidate corridors in this checkout.

## Identity and fold provenance

- Candidate ID / version:
- Fold and spatial block:
- Source catalogue ID, version, and SHA-256:
- Visible parent-segment IDs (no withheld segment/tip used):
- Feature-stack version and input hashes:
- External data citations, license, tile IDs/dates/hashes (if any):

## Geometry and kinematics

- Mechanism class: relay ramp / pull-apart / displacement transfer / other (specify):
- Fault pair(s) and tip IDs:
- Catalogue support for parallelism and same dip direction:
- Dip/slip-sense attributes and source; unknown fields explicitly marked:
- Ramp width W (km), along-strike separation (km), and overlap/underlap classification:
- Geometry-rule result: W within 0.1–15 km? separation ≤3.5W? both overlap/underlap arms represented?
- Predicted connector form: oblique-slip connector / en-échelon strands / basin-bounding splay / transfer array:
- Stress/strain orientation, source, local uncertainty, and angular compatibility:

## Independent evidence (report values and direction, not only a fused score)

- Gravity: input band; sign/polarity; multiscale gradient/tilt evidence; spatial continuity; support/contradiction:
- Magnetics: input band; signed low/high; multiscale gradient/tilt evidence; spatial continuity; support/contradiction:
- Lidar/scarp: channel provenance or official 3DEP tile hashes; scarp continuity/orientation/profile; support/contradiction:
- Other competition evidence layers used, including stress orientation:
- Which evidence is independent of catalogue geometry, and which is derived from it:

## Alternative explanations and confidence

- Plausible non-fault mimic (e.g., dike/lithologic contact, basin fill, drainage/terrace, landslide, roads/earthworks):
- Specific checks that disfavor the mimic:
- Confidence: low / medium / high, with reason and uncertainty:
- Why this corridor is a better geological explanation than a nearby non-candidate:
- Expected false-positive and false-negative failure modes:

## Validation and uniqueness

- Paired fold-local HOLDOUT-DTI vs the same pipeline without corridor priors (evaluator version, withheld-positive count, 95% CI):
- Per-feature leakage-canary results (AUC and threshold disposition):
- Registry rank-correlation maximum and raster identity:
- Fraction of candidate dots within three pixels of each registry raster; any duplicate threshold crossed:
- Promotion decision (separate from candidate creation):

No numeric score is a submission score unless the project rules for its evidence class are satisfied. No corridor is promotable unless the paired holdout, leakage, registry, format, and slot-selector gates all pass.
