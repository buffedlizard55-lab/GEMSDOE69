# HANDOFF — next session checklist (GEMSDOE69 lane)

Read `PROMPT.md` first. Then this file.

## State at handoff (2026-10-20)

H69-E was implemented and measured. Verdict: **negative**. Do not submit.

* Hypothesis: width-stratified relay/pull-apart corridors (not the 2.8 km-only cap), scored with structure-tensor straightness on conductivity and basement depth plus K depletion and Th/K, inside the existing tip graph.
* HOLDOUT-DTI (gems57 pooled hide-and-recover, alpha 0.2, beta 0.8, 300 m, seeds 20/21, 8 cells, 22,641 withheld positives): corridor 0.00637 ± 0.00171 vs no-prior control 0.00253 ± 0.00071. Paired Δ +0.00385 ± 0.00138. Gate vs control **passed**. Numerical beat of the 2026-10-12 best (0.00598) is **inside the CI** (Δ +0.00040).
* Leakage canary: worst AUC 0.679 (corridor propensity). New layers: cond_straight 0.515, base_straight 0.543, rad_k_depl 0.582, rad_thk 0.473. None above 0.90. Th/K is slightly anti-predictive of withheld catalogue faults.
* Hard-linked recovery within 300 m: 0.870 (23 ramps).
* Uniqueness: surface |ρ| 0.227 (pass). Dot overlap 0.841 vs 12GEMSDOE `r5-nms3-trace` (blob 98cbfc84, 103,347 dots). **Protocol rule 1 stop.** No download offered.
* Raster exists only as a logged negative artifact: `submissions/h69e-strat-straight-rad-33199-20261020T193531Z-6a60ea28-zeros.tif`, sha256 `ad03bd333dacc28ebaf474599f3fc7aabf65d181373a2afd52f5adf8fdc15045`. `scripts/validate_submission.py` passed. Do not upload it.
* Site homepage and executive summary say NOT OK TO SUBMIT. GitHub Pages is served from `/`.

## Why this does not beat 0.2778 or 0.3195

Those figures are USER-REPORTED-NOT-ORGANIZER-CONFIRMED (0.3195 is rank 9 on the 2026-10-12 public snapshot; rank 1 that day was 0.4275). This lane's holdout screen is ~0.006. That instrument does not rank live scores (family calibration ρ≈0.51, p≈0.09). A projection is not a score. The only large live lever identified in the h33 audit is higher credit per dot on a wide field, and copying that field is forbidden by the uniqueness rule (h33 overlap here was 0.316, but the dense-trace overlap was 0.841).

## Do next session (budget: 3 experiments)

1. Do not resubmit H69-E. The stop is the result.
2. If a new idea is tried, it must place dots off the 12GEMSDOE trace neighbourhood, not just off our own previous files. Check that overlap **before** placement, on a sample, so a 15-minute scan is not spent on a field that will fail.
3. Th/K (AUC 0.473) should be dropped or sign-flipped only as a new pre-registered experiment, not as a silent retune.
4. H69-B (chi / knickpoints on pinned `det_elev`) is the next queued idea that does not need new data. H69-H (USGS ComCat) is still blocked: earthquake.usgs.gov is not reachable here.
5. The holdout rewards proximity to withheld catalogue segments. The live metric, per the h33 ladder, punishes dots within ~200 m of mapped traces. A method that wins this holdout can still be the wrong live prior. Say so on the card.

## Known traps

* `.cache/` is git-ignored. `python3 scripts/fetch_data.py` and `scripts/fetch_registry.py` restore pinned bytes. GitHub API rate limit is 5,000/hour; the registry fetch needs most of it.
* `scripts/validate_submission.py` now resolves `data/bridge` when `GEMS_DATA` is unset.
* Do not treat `h69-z-radiometric-halo-31994` as a validated radiometric result (IR-69-GATE-02).
