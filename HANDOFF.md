# Handoff — 2026-10-20 (relay-fix session)

Read README.md and PROMPT.md first, then reports/relayfix-2026-10-20.md.

## State

**NEGATIVE. DO NOT SUBMIT.** New candidate
`submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif`
(sha256 b44d16ce…) passes format validation and both preregistered science
gates (HOLDOUT-DTI pooled 0.00847 vs v1 0.00635 vs control 0.00215), but
fails the literal registry-overlap gate (1.0 vs universal surfaces; 0.8497
worst dotlike; rho ≤0.28). No download is published and no slot was spent.
Exp1's v1 emission is a logged duplicate of the Oct-12 lane raster.
H69-F subsurface and H69-G radiometric arms were not established (CIs
include 0). All numbers are HOLDOUT-DTI screens, never organizer scores.

## Publication commands

    python scripts/release_gate.py
    python scripts/build_site69.py
    python scripts/build_readme.py

## Next work, in order

1. Upstream selector: resolve the registry support definition (literal
   overlap cannot pass while whole-footprint soft surfaces are registry
   "dots"). Do not relax locally.
2. New preregistration on untouched blocks before any further holdout
   (seeds 20/21 seen). Join per-strand dip/slip from restored qfault
   traces/attributes; decide overlap-cap and outer-tip dedup semantics
   in the preregistration, not mid-run.
3. Science queue: connector-axis HG/tilt phase coincidence, releasing-
   basin asymmetry, scarp strike-coherence (register in
   docs/research/hypotheses-2026-10-20.md).
4. Refresh registry index past 2026-10-12 before any promotion attempt;
   rerun both uniqueness phases on exact final bytes.

Tests: 94 passed. Template pins verified unchanged. No DrivenData slot
is authorized. Negative results are deliverables.
