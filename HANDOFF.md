# Handoff — 2026-10-20 current review

Read `README.md` and the full `PROMPT.md` before taking action. Current status and evidence are in `evidence/run_card.json`, `evidence/current_candidate.json`, and `reports/repo-review-2026-10-20.md`.

## State: NEGATIVE — DO NOT SUBMIT; no TIFF download

The active candidate is the H69-H2 transfer-only artifact at `submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif` (SHA-256 `b44d16ce3f9a456c2c5c1a0156a873fad89baf5f50716610886f6f5cb0ffb9c1`). It passed the local format/range validator, but it is **not release-cleared**:

- `REGISTRY-MEASUREMENT`: the accessible index scan covers 862/862 rasters with no scan errors, but both literal phases report a maximum 3-px dot overlap of 1.0 (>0.70); duplicate-and-stop applies. A dotlike/stratified diagnostic is not an override. The accessible public owner-repository index excludes private, external, and never-committed rasters; it is not a complete organizer registry.
- Surface comparison is recorded after emission, not certified before placement. The final-dots phase is not explicitly certified as after placement in the phase manifest.
- The transfer method manifest's `src/gems69/holdout69.py` hash does not match this checkout. Do not rewrite it without reproducing the candidate with the exact source.
- HOLDOUT-DTI evidence is available against corridor-v1 and a no-prior control, but no hash-bound paired 95% CI against an explicitly declared current holdout-best artifact is present. The stale `current_best_beaten` boolean is not sufficient.
- The preregistration's `frozen_utc` is 2026-10-20T20:50:00Z, later than the holdout record's `generated_utc` (20:44:29Z). The timestamps conflict with the preregistration's text, so this holdout is not certified as preregistered.
- The full cached feature stack is absent. No new candidate was generated or tested in this review.

The archived `evidence/run_card.json` records the exact score labels, intervals, artifact hash, validator output, and fail-closed reasons. The transfer candidate's pooled score is **HOLDOUT-DTI**, not an organizer score or leaderboard projection. H33's reported 0.2778 remains USER-REPORTED-NOT-ORGANIZER-CONFIRMED because no organizer receipt binds it to file bytes.

## Other historical artifacts

- The H69-J joint candidate (38,669 dots) had been promoted under a stratified dotlike interpretation. That conflicts with the user's literal duplicate rule. Its method manifest has four source mismatches (`scoring.py`, `corridors.py`, `physics.py`, `holdout69.py`); it is not cleared.
- H69-D and H69-E have archived candidates and negative release decisions. Their old receipts are historical and are not the current best without an artifact-bound same-evaluator comparison.

## Next steps — no experiment or slot authorized by this handoff

1. Keep the literal duplicate-and-stop rule; do not weaken it or regenerate a candidate merely to get a new filename.
2. Reconcile exact source provenance and define an artifact-bound current holdout-best comparator before any new holdout claim.
3. Only with explicit data/experiment authorization, restore the pinned feature cache, verify source hashes, and preregister one untried in-lane test from `docs/research/untried-hypotheses-2026-10-20.md`.
4. If an experiment later becomes protocol-eligible, test features alone for AUC leakage, check the surface against the accessible registry **before placement**, apply the whole-segment holdout/buffer/visible-only features/exact mask, report pooled HOLDOUT-DTI with evaluator, withheld-positive count and paired CI, then check final dots. Any literal firing stops promotion.
5. Publish a TIFF only if every gate passes. No competition slot has been selected or used.
