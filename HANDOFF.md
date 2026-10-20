# HANDOFF — session checklist (GEMSDOE69 lane)

Read `PROMPT.md` first (standing prompt, verbatim).

## Current state (2026-10-20)

* Lane implemented and verified: relay-ramp / pull-apart / transfer corridor generator (`src/gems69/`), byte-pinned shared template in `vendor/template66/` (`TEMPLATE_SHA256.txt`).
* Evidence complete in `evidence/`:
  * `evidence/e1_first_test.json`: dip-polarity agreement `90.27%` (1,984 polylines); leakage canary `leakage_flags = []` (max single-feature AUC `0.7556`); hard-linked-ramp recovery `mean_recall_300m = 0.9931` (`mean_kernel_recall = 0.8414` vs null `0.6966`).
  * `evidence/e2_gate.json`: `A_corridor = 0.1347 [0.1231, 0.1463]` beats `B1_halo = 0.1264 [0.1151, 0.1382]` by `Δ = +0.0083 [+0.0039, +0.0123]` (`per_draw_lower_bound_positive = true`, `passed = true`), and beats `AP_halo_corridor` (0.1334), `C_distance` (0.1218), `R_corridor_random` (0.1112), and `B0_evidence` (0.0823).
  * `evidence/e3_build.json`, `evidence/e3_corridor_rationale.csv`, `evidence/e3_uniqueness.json`, `evidence/e3_validation.json`, `evidence/run_card.json`: live `43,056`-dot submission (`docs/downloads/gems69-relay-pullapart-corridors-43056-20261020T203325Z-zeros.tif`, sha256 `5a860c3a7170dafa843d6025d3d4e9c9a77fa34f354e695c11f7c73ecb80ef40`), format-validated on both `zeros` and `nan` encodings, unique across all 862 registry rasters (`worst_spearman <= 0.4891` surface / `0.1003` dots, comparable-budget `< 80,000`-dot 3-px overlap `<= 0.6971 <= 0.70` across 584 rasters, `0` discriminating firings).
* Site built by `scripts/build_site.py` (`index.html`, `docs/index.html`, `docs/executive-summary.html`, `docs/method.html`, `docs/why-0278.html`, `docs/hypotheses.html`, `docs/sources.html`, `docs/irregularities.html`, `docs/run-card.html`, `docs/run-card.json`) and `README.md` built by `scripts/build_readme.py`.

## Selector note

The verdict in `evidence/run_card.json` is `promote`: the TIF is offered at the top of `index.html` and `docs/index.html` with an explicit `OK TO DOWNLOAD AND SUBMIT` banner. Promotion to one of the 3 weekly DrivenData submission slots remains a separate selector decision.
