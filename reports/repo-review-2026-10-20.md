# Current repository review — 2026-10-20

## Decision

**NEGATIVE — DO NOT SUBMIT. No TIFF download is offered. No competition slot was selected or used.** The current release policy records **10 blockers**. This review made no new prediction raster and ran no new scientific experiment. The existing H69-H2 transfer-only TIFF is retained only as an audit artifact. Local format validation does not override literal duplicate, provenance, phase-order, or current-best comparison failures.

No organizer rejection or organizer score is claimed. H33's reported 0.2778 remains USER-REPORTED-NOT-ORGANIZER-CONFIRMED; the repository has no organizer receipt tying it to file bytes.

## Current artifact and HOLDOUT-DTI

- Candidate: `submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif`
- Raster SHA-256: `b44d16ce3f9a456c2c5c1a0156a873fad89baf5f50716610886f6f5cb0ffb9c1`
- Validator SHA-256: identical to the raster; one Float32 band, EPSG:32611, 3730×3292, transform `[100, 0, 243350, 0, -100, 4508550]`, finite footprint, range [0,1]. This is a local format result only.
- **HOLDOUT-DTI** evaluator `vendor/template66 gems57.holdout.build_holdout+score_cell` (alpha 0.2, beta 0.8, 300 m triangular kernel; seeds 20/21; pooled from summed TP/FP/FN); **8 cells and 22,641 withheld positive pixels**.
  - Primary pooled candidate DTI: **0.0084698305**. No absolute pooled-DTI CI is stored.
  - Mean-of-cell DTI: **0.0077375314**, normal-approximation 95% CI **[0.0057316537, 0.0097434090]**. This is not the pooled-DTI statistic or CI.
  - Paired-cell bootstrap delta versus corridor-v1: **+0.0020420**, 95% CI **[+0.0008402, +0.0030140]**.
  - Paired-cell bootstrap delta versus no-prior control: **+0.0062351**, 95% CI **[+0.0044374, +0.0078740]**.
  - These are screening results against the named arms, not organizer scores and not an artifact-bound comparison against the explicitly declared current holdout best.

## Literal uniqueness and provenance blockers

- **REGISTRY-MEASUREMENT:** both surface and final-dot phases scanned **862/862** rasters in the accessible, hash-verified public owner-repository index with no per-raster scan errors. That index is not a complete organizer registry; private, external, and never-committed rasters are out of scope.
- The worst literal 3-px dot overlap is **1.0** in the surface and final-dot phases. The protocol says any registry raster with more than 70% of candidate dots within 3 px is duplicate-and-stop. A saved-row dotlike subset diagnostic of 0.8496628 is also above threshold, but it is not used to waive or replace the literal result. Worst absolute Spearman is below 0.90; that does not override the overlap trigger.
- Surface comparisons are recorded after emission, not certified before placement. The final-dots phase is likewise not explicitly certified as after placement in its phase manifest. The strict policy fails closed on phase order.
- The transfer method manifest has a stale `src/gems69/holdout69.py` hash. The archived H69-J manifest has four stale source hashes (`scoring.py`, `corridors.py`, `physics.py`, `holdout69.py`). They were not silently repinned.
- The holdout receipt compares transfer to corridor-v1 and a no-prior control, but supplies no hash-bound paired 95% CI against a declared current holdout-best artifact. An old `current_best_beaten` boolean is insufficient.
- **Protocol timing is unverified:** the pinned preregistration records `frozen_utc=2026-10-20T20:50:00Z`, while the HOLDOUT-DTI record says `generated_utc=20261020T204429Z` (20:44:29Z). The recorded freeze is 5 minutes 31 seconds later despite text claiming it preceded the look. This discrepancy is now an explicit release blocker; no claim of preregistered evaluation is made.
- The full cached feature stack is absent (`.cache/gems_data` is missing). No restoration or external data download was attempted.

The new `scripts/release_gate.py` binds the exact candidate raster, pinned registry index, SHA-256 of every referenced evidence file, artifact receipt, holdout values, aggregate and phase scans (including decoded-array hashes), source hashes, feature-alone canaries, and validator receipt. It requires a timestamp-ordered, hash-pinned preregistration; a same-evaluator paired CI bound to both candidate and incumbent artifacts with matching cell/withheld-positive counts; each literal phase at the required order; and never allows a stratified/dotlike diagnostic to override literal failure. The CLI is read-only unless `--write-card` is explicitly supplied; that option only rebuilds the JSON card from frozen evidence and does not run science.

## Three review passes

### Pass 1 — requirements, implementation, and evidence

- Read the full `README.md`/`PROMPT.md` brief, `AGENTS.md`, handoff, current and historical run cards, release policy, registry scope, candidate/phase receipts, method manifests, validator reports, data layout, and existing review notes.
- Added `evidence/current_candidate.json` to bind the exact active raster and frozen evidence files. Reworked the release policy to fail closed on literal uniqueness failures, missing/inconsistent registry counts, unverified phase order or preregistration timing, stale method-source hashes, missing artifact-bound current-best comparison, flagged canaries, or a validator mismatch.
- Rebuilt `evidence/run_card.json` only from already-existing receipts. It explicitly separates pooled DTI from mean-of-cell DTI and labels paired-delta intervals correctly.
- Corrected `scripts/audit_workspace.py` to discover bridge inputs in `data/bridge/`; updated `data/README.md` to state that the full cache is absent and the available mirrors are not organizer-authenticated.

### Pass 2 — adversarial policy and stale-publication review

- Added release-gate fixtures for a fully bound passing path and negative paths for literal overlap (including attempted stratified override), stale phases, wrong scan counts, missing current-best evidence, nonpositive paired CI, changed artifact/source hashes, validator failure, registry scan errors, and AUC > 0.90 / invalid canaries.
- Replaced the legacy `scripts/build_site.py` publication route with a compatibility wrapper to the strict site builder. The current builder revokes stale TIFF/ZIP copies when the policy is negative and uses only `evidence/current_candidate.json` if a future policy passes.
- Verified that the current policy returns `verdict=negative`, `download_enabled=false`; the site displays an unambiguous DO NOT SUBMIT banner and does not publish a TIFF.
- `PYTHONPATH=vendor/template66:src .venv/bin/pytest -q tests/test_release_gate.py`: **28 passed**. Full suite below: **110 passed, 18 warnings**. The warnings are Rasterio `PendingDeprecationWarning`s in `tests/test_validate.py`.
- No data, TIFF, or candidate was regenerated for these checks.

### Pass 3 — brief, source, status, and publication reconciliation

- Updated the README builder so the root README starts with the current status and full project brief; removed stale H69-J “promotion” and stratified-overlap claims from the active site.
- Rebuilt the current site pages from the current run card, current candidate pointer, current release decision, and current hypothesis queue. The legacy site builder now delegates to the strict builder.
- Added three ranked, qualitative in-lane hypotheses with layers, physical signatures, catalogue-missing-fault rationale, exact differences from implemented methods, named mimics, cost, and explicit source/data limits. They are confirmed unrun in this checkout, not asserted globally novel. The top hypothesis was not tested because the feature cache is absent and current-best/provenance requirements remain unresolved.
- Rewrote the H33 analysis to distinguish the unconfirmed score claim from measured family-raster anatomy and to make the metric explanation explicitly plausible, not causal. No current leaderboard result is claimed.
- Marked older hypothesis/method/review notes as historical and corrected the geothermal knowledge base's data-availability and next-step language.
- No external pages were fetched in this review. `docs/research/sources.md` records its earlier page checks as 2026-10-12; new physical interpretations in the current hypothesis queue are explicitly labelled unverified where no supporting source was independently checked.

## Final verification

- Test suite: `PYTHONPATH=vendor/template66:src .venv/bin/pytest -q` — **110 passed, 18 warnings** (Rasterio pending-deprecation warnings only).
- `git diff --check`: passed.
- Site build: 9 pages regenerated; release verdict **negative; download disabled**; `docs/downloads/` contains no TIFF/TIFF/ZIP.
- Re-ran `scripts/validate_submission.py` on the exact archived zeros TIFF with `GEMS_DATA=data/bridge`: PASS, SHA-256 matches the current-candidate pointer, 36,325 positives, zero NaNs. This is only a local format/range check.
- Recomputed the current artifact and all eight frozen-evidence SHA-256 values: all match their pointer. The read-only workspace audit remains **blocked** because `training_features.tif` and the feature cache are absent.
- PR/merge workflow state is intentionally separate from the scientific release decision; consult GitHub for the current PR status.

## Next-session constraints

1. Keep literal duplicate-and-stop; do not use dotlike/stratified metrics to waive it or rename a failed candidate.
2. Do not rewrite method hashes without reproducing an artifact from the exact recorded source.
3. Establish the artifact-bound same-evaluator current holdout-best comparator before making a best-improvement claim.
4. Restore the pinned feature stack only with authorization and after protocol requirements are met; validate source hashes and mirror limitations.
5. If a future experiment is authorized, preregister one current untried hypothesis, test every feature alone, use whole-fault-segment hide-and-recover with a buffer and exact visible-fault mask, derive catalogue features from visible faults only, report pooled HOLDOUT-DTI with evaluator/withheld-positive count/CI, and run surface uniqueness before placement plus final-dot uniqueness afterward.
6. Offer a TIFF only if every required literal, holdout, provenance, and validator gate passes. No slot is selected by the method lane.
