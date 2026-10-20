# Handoff — 2026-10-20

Read `PROMPT.md` first. Then this file. Then `reports/review-passes-2026-10-20.md`.

## State

**NEGATIVE. DO NOT SUBMIT.** No competition slot was used. No download is published.

H69-E was implemented and measured on this branch, then merged with the fail-closed publication gate from main.

* Hypothesis: width-stratified relay/pull-apart corridors (not the 2.8 km-only cap), scored with structure-tensor straightness on conductivity and basement depth plus K depletion and Th/K.
* HOLDOUT-DTI (gems57 pooled hide-and-recover, alpha 0.2, beta 0.8, 300 m, seeds 20/21, 8 cells, 22,641 withheld positives): corridor 0.00637 ± 0.00171 vs no-prior control 0.00253 ± 0.00071. Paired Δ +0.00385 ± 0.00138. Gate vs control passed. The +0.00040 beat of the 2026-10-12 best (0.00598) is inside the CI.
* Leakage canary: worst AUC 0.679. None above 0.90. Th/K AUC 0.473.
* Hard-linked recovery within 300 m: 0.870 (23 ramps).
* Uniqueness: surface |ρ| 0.227 (pass). Dot overlap 0.841 vs 12GEMSDOE `r5-nms3-trace` (blob 98cbfc84, 103,347 dots). **Protocol rule 1 stop.**
* Raster, audit only: `submissions/h69e-strat-straight-rad-33199-20261020T193531Z-6a60ea28-zeros.tif`, sha256 `ad03bd333dacc28ebaf474599f3fc7aabf65d181373a2afd52f5adf8fdc15045`. `scripts/validate_submission.py` passed. Do not upload it.
* The earlier radiometric TIFF remains an archived negative (see `evidence/run_card_h69d_audit_20261020.json`). Do not treat `h69-z-radiometric-halo-31994` as a validated result (IR-69-GATE-02).

`scripts/release_gate.py` still fails closed. Missing hash-bound phase receipts, source manifest, and current-best binding are additional publication blockers. Do not fabricate those fields. Do not replace the literal 70% overlap rule with the stratified diagnostic.

## Publication commands

    python scripts/release_gate.py
    python scripts/build_site69.py
    python scripts/build_readme.py

## Do next session (budget: 3 experiments)

1. Do not resubmit H69-E or the radiometric TIFF.
2. A new idea must place dots off the 12GEMSDOE trace neighbourhood, not just off our own previous files. Check that overlap before placement.
3. Th/K (AUC 0.473) should be dropped or sign-flipped only as a new pre-registered experiment, not as a silent retune.
4. Queued, untested, not slot-eligible: convergent relay-link edge phase; releasing-basin margin asymmetry; en echelon scarp phase; signed radiometric contrast. H69-B (chi / knickpoints) needs no new data. H69-H (USGS ComCat) is blocked here.
5. The holdout rewards proximity to withheld catalogue segments. The live metric, per the h33 ladder, punishes dots within ~200 m of mapped traces. Say so on the card.
6. `.cache/` is git-ignored. `python3 scripts/fetch_data.py` and `scripts/fetch_registry.py` restore pinned bytes. Do not relaunch them unless the cache is gone.

User-cited 0.2778 and 0.3195 are USER-REPORTED-NOT-ORGANIZER-CONFIRMED. This lane's holdout screen is about 0.006. A projection is not a score.
