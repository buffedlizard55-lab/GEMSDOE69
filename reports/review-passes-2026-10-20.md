# Historical review passes — 2026-10-20 (H69-E)

> This is the earlier H69-E experiment report and does not describe the current candidate or release status. See [`repo-review-2026-10-20.md`](repo-review-2026-10-20.md) and `evidence/run_card.json` for the reconciled current state.

## Pass 1 — implement and measure

H69-E was pre-registered in `registry/preregistration_h69e.json` before the holdout look: width-stratified tip-graph corridors (the 2026-10-12 cap had filled all 1,200 slots at W = 2.8 km), structure-tensor straightness on `cond_surf` and basement depth, K depletion and Th/K, bottom-quartile score drop, shared greedy allocator, 200 m flank.

Measured, not projected:

- Leakage canary, worst AUC 0.679. No feature above 0.90. Th/K AUC 0.473.
- Hard-linked recovery within 300 m: 0.870 (23 ramps).
- HOLDOUT-DTI, gems57 pooled hide-and-recover, alpha 0.2, beta 0.8, 300 m, seeds 20 and 21, 8 cells, 22,641 withheld positives: corridor 0.00637 ± 0.00171 vs no-prior control 0.00253 ± 0.00071. Paired Δ +0.00385 ± 0.00138. Gate vs control passed. The +0.00040 beat of the 2026-10-12 best is inside the CI.
- Surface Spearman before placement: worst |ρ| 0.429 on a 250,000-cell subsample (746 rasters). Full-dot scan: worst |ρ| 0.227.
- Dot overlap 0.841 vs 12GEMSDOE `r5-nms3-trace` (blob 98cbfc84, 103,347 dots, ρ 0.0233). Protocol rule 1 stop.
- `scripts/validate_submission.py` passed both twins. The all-finite zeros twin is the only portal-safe layout. It is not offered.

## Pass 2 — bugs and edge cases

- Local-overlap scan counted this emission's own `-nan` twin as a prior (overlap 1.0). Scanner now skips the twin. Corrected worst vs earlier GEMSDOE69 files is 0.483.
- Site builder glob `h69-*-zeros.tif` would have missed `h69e-` and could have offered an older file. Fixed.
- `scripts/validate_submission.py` looked only at `/tmp/gems_data`. It now uses `data/bridge` when `GEMS_DATA` is unset.
- Upstream `gems.validate_submission` with the training-features band-1 footprint still fails both twins (IR-69-VAL-01). Reported, not papered over.
- Pre-existing test failures left as-is: `tests/test_corridors.py` targets an older vector API (`generate`, `_pair_ok`) that this raster lane does not implement; `test_metric_consistency.py` and one template-pin test import `gems` symbols that live in `vendor/template66`, and they fail or pass depending on `sys.path` order.

## Pass 3 — against the standing prompt

- Unique raster was generated and checked against 750/751 registry blobs plus earlier GEMSDOE69 files. It is not a copy of h33 (overlap 0.316, ρ 0.227) and not a copy of this repo's earlier emissions (overlap 0.483). It still fails the 70% dot rule against one dense trace raster, so the download is withheld.
- Homepage (`/` , which is what GitHub Pages serves) and the executive summary both say NOT OK TO SUBMIT. No download link was published.
- Every score in the run card is labelled HOLDOUT-DTI or left as user-reported. No projection of 0.3195 or 0.2778 is written as a result.
- Budget: one pre-registered experiment (canary, gate, emission). No retune after the canary. No fourth experiment to dodge the overlap rule.
