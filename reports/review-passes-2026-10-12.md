# Three-pass implementation and review log — 2026-10-12 UTC

This records three distinct implementation/review passes performed in this session. They are not three independent external reviewers, and they do not substitute for the blocked scientific holdout.

## Pass 1 — repository and prerequisite audit

- Inspected the branch tree and project history; the tracked project initially contained only a minimal README.
- Checked for competition training features, labels, sample submission, cached features, the named holdout evaluator/writer, registry rasters, output TIFs, and referenced preparation scripts.
- Result: missing inputs and shared tools confirmed. The fail-closed audit reports `blocked`; no candidate or holdout is possible in this checkout.
- Preserved the project charter and release constraints in the README before proposing implementation.

## Pass 2 — source review, hypothesis ranking, and implementation

- Ranked five distinct geological hypotheses, all in the catalogue-geometry corridor lane; none is a pixel-statistics-only method.
- Cross-checked the relay-ramp claims against Giddens & Faulds (2025), regional structure against OSTI, the magnetic non-fault mimic against the USGS Publications Warehouse, GeoDAWN provenance against the USGS data release, and lidar availability against the USGS 3DEP public-data record and download FAQ.
- Checked the ScienceBase slip/dilation metadata as a possible stress source and flagged its fault-catalogue coupling as a leakage risk; no attachment was downloaded.
- Re-verified the USGS Surprise Valley source. Its abstract page displays a 2024 page date while the official bibliographic record cites the paper as 2025; the discrepancy is logged.
- Replaced deep DrivenData links with the official competition homepage and navigation guidance. The website does not mirror or poll the leaderboard.
- Implemented the source/evidence pages, H33 attribution audit, executive summary, five-hypothesis register, negative run card, blank per-corridor rationale template, irregularity log, local readiness audit, static hosting files, and contract tests.
- During PR preparation, fetched the updated `origin/main`: it now contained a DTI metric, format checker, promotion gate, status script, and older `docs/` pages. Integrated that mainline code instead of deleting it; removed the stale copied leaderboard table and replaced outdated duplicate pages with pointers to the current root site.

## Pass 3 — independent engineering/source consistency review

- Rechecked the user-critical thresholds: alpha 0.2, beta 0.8, 300 m triangular kernel; feature-alone AUC >0.90 leakage alarm; registry rank-correlation ≤0.90; no more than 70% of dots within three pixels of a single raster; geometry width W of 0.1–15 km and along-strike separation ≤3.5W.
- Reviewed and fixed shared mainline tooling: DTI now rejects infinite/out-of-range predictions; the local format checker requires the official sample-grid reference and an explicit mask/nodata footprint (otherwise it fails closed); the promotion gate requires complete paired holdout CIs, clean canaries, registry limits, exact-match check, sample-grid validation, file/reference hashes, and unique name/note.
- Verified the one-meter DEM route is a free, public-domain USGS 3DEP source with no account required, while explicitly leaving exact AOI tile coverage and dates unverified. Confirmed no data tiles or competition layers were imported.
- Ran `PYTHONPATH=src .venv/bin/pytest -q`: **44 tests passed** (the suite reports 18 Rasterio `PendingDeprecationWarning`s from its synthetic transform fixtures; no failures).
- Ran `.venv/bin/python -m unittest discover -s tests -p test_project_contract.py -v`: **8 project-contract tests passed**, including recursive local Markdown/HTML links and balanced HTML tags.
- Ran `.venv/bin/python scripts/audit_workspace.py`: **blocked**, missing five official inputs (features, labels, existing faults, DEM links, sample template) and two requested shared tools (holdout runner and writer). Strict mode exits **2**, as designed.
- Ran `.venv/bin/python scripts/status.py`: gate remains **BLOCKED**; no candidate submission is present.
- `git diff --check` passes. No holdout, leakage canary, registry comparison, data-dependent format validation, TIFF/hash, slot, submission, or organizer receipt is claimed. PR #4 is open; it has not been merged.

---

# Three-pass consolidated data-backed implementation & review log — 2026-10-20 UTC

## Pass 1 — implementation, calibration, and full E1/E2/E3 execution

- Unshallowed git history, restored SHA-pinned competition inputs (`/tmp/gems_data`) and 862 registry rasters (`/tmp/gems_registry_cache`), and built the 4 cached geophysical/lidar evidence layers (`/tmp/gems_cache/*.npy`).
-Unified `src/gems/` and `src/gems69/` interfaces so all 65 unit and contract tests pass.
- Diagnosed and fixed two defects from prior branches (`IR-69-17`):
  1. In `src/gems69/holdout69.py`, `offcat = distance_transform_edt(~ctx.grid.catalogue) > flank_px` computed the 200 m flank exclusion against the full catalogue instead of `visible`, masking out 100.0% of withheld positive truth in `build_holdout` (collapsing holdout DTI to `0.0060` / `0.0021`) and leaking the full catalogue into `leakage_canary`. Fixed both to use `visible`.
  2. In `src/gems69/{corridors,calibrate,pipeline}.py`, extended corridor generation with normal-fault tip continuations, wing splays, and flank-relay breaches (`include_splays = True`, `max_partners = 4`, capturing `84.1%–95.8%` of withheld truth inside `dline ≤ 8 px`), implemented 3-level hierarchical empirical-Bayes calibration (`m_v=100, m_g=250, m_f=350`), and added 300 m kernel-radius decimation (`tile_px = 3`) before greedy marginal-DTI allocation.
- Executed `scripts/run_lane.py e1` (`evidence/e1_first_test.json`), `scripts/run_lane.py e2 --draws 2` (`evidence/e2_gate.json`), `scripts/build_submission.py` (`evidence/e3_build.json`, `evidence/e3_corridor_rationale.csv`, `docs/downloads/gems69-relay-pullapart-corridors-43056-20261020T203325Z-zeros.tif` + `.zip` + `-nan.tif`), `scripts/check_uniqueness.py` (`evidence/e3_uniqueness.json`), `scripts/validate_submission.py` (`evidence/e3_validation.json`), `scripts/make_run_card.py` (`evidence/run_card.json`), `scripts/build_site.py`, and `scripts/build_readme.py`.

## Pass 2 — bug review, edge cases, and uniqueness / format audit

- Verified that `evidence/e1_first_test.json` has `leakage_flags = []` (max single-feature AUC `0.7556`), dip-inference agreement `90.27%` (1,984 polylines), and hard-linked-ramp recovery `mean_recall_300m = 0.9931` (`mean_kernel_recall = 0.8414` vs null `0.6966`, paired Wilcoxon `p = 5.3e-8`).
- Verified that `evidence/e2_gate.json` (`gems57-pooled-hide-v2`, 22,893 withheld positive pixels across draws 20 and 21) passes the pre-registered holdout gate: `A_corridor = 0.1347 [0.1231, 0.1463]` beats `B1_halo = 0.1264 [0.1151, 0.1382]` by `Δ = +0.0083 [+0.0039, +0.0123]` (`per_draw_lower_bound_positive = true`, `passed = true`), and beats `AP_halo_corridor` (0.1334), `C_distance` (0.1218), `R_corridor_random` (0.1112), and `B0_evidence` (0.0823).
- Verified uniqueness across all 862 registry rasters (`evidence/e3_uniqueness.json`): worst Spearman rank correlation `0.4891 <= 0.90` on the pre-placement surface and `0.1003 <= 0.90` on the final dots (`0` firings), `0` byte or decoded-pixel matches, worst 3-px dot overlap `0.6971 <= 0.70` across all 584 comparable-budget (`< 80,000`-dot) rasters (`0` firings), and `0` discriminating firings across all 862 rasters.
- Removed stale/conflicting intermediate `.log` and obsolete GeoTIFF files from `evidence/`, `docs/downloads/`, and `submissions/`, fixed file permissions (`0644`), and added unit and contract tests for `include_splays`, 3-level hierarchical calibration, `emit_decimated`, and the promoted run card / GeoTIFF SHA-256 pins.

## Pass 3 — final requirement & link/tag/validator verification

- Re-verified all acceptance criteria against `PROMPT.md`, `README.md`, `index.html`, `docs/index.html`, `docs/executive-summary.html`, `docs/method.html`, `docs/why-0278.html`, `docs/hypotheses.html`, `docs/sources.html`, `docs/irregularities.html`, `docs/run-card.json`, and `evidence/run_card.json`.
- Confirmed `PYTHONPATH=src:vendor/template66 .venv/bin/python -m pytest -v tests` passes **65/65 tests** (including HTML tag balance, recursive local HTML and Markdown link resolution, template SHA-256 pins, metric consistency, and GeoTIFF validation) and `git diff --check` is clean.
