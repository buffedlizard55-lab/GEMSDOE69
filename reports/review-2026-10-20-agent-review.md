# GEMSDOE69 repository review — 2026-10-20

## Outcome

**Verdict: negative; no TIFF is cleared for download or competition submission.** The transfer-only H69-H2 candidate is formatted correctly and has a positive local holdout comparison, but the literal duplicate gate fails (3-pixel dot overlap 1.0). This is sufficient to stop under the project protocol, irrespective of the low measured Spearman correlation. The currently archived file is `submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif`; it is not promoted and no DrivenData slot was used.

## Three review passes

### Pass 1 — inventory and status

- Repository is the GEMSDOE69 relay-ramp/pull-apart lane. The complete standing brief already exists in `README.md` and `PROMPT.md`; hypotheses, scientific notes, source links, holdout code, a template-based writer, validator, registry scan, generated candidate files, and run-card evidence exist.
- The candidate reported by `evidence/run_card_relayfix_20261020.json` is H69-H2 transfer-only. Its HOLDOUT-DTI is 0.0077375314, with reported 95% CI [0.0057316537, 0.0097434090], 22,641 withheld positive pixels, 8 cells, pooled holdout comparator 0.0021479254. Evaluator: `vendor/template66/gems57.holdout.build_holdout+score_cell`, alpha 0.2, beta 0.8, 300 m triangular kernel, seeds 20/21, pooled counts. These are local holdout measurements, not organizer-confirmed competition scores.
- Registry measurement checked 862 accessible, hash-verified raster entries. Maximum absolute Spearman is 0.110311; literal maximum 3-pixel overlap is 1.0. The dot and surface phases both record duplicate/stop. Registry scope is not guaranteed to include private, unlinked, or inaccessible submissions.
- Candidate validator receipt confirms single-band float32, EPSG:32611, 3730×3292, 100 m transform, all in-footprint cells finite, and values in [0,1]. Format compliance does not cure the duplicate finding.

### Pass 2 — bugs, assumptions, and tests

- Found a reproducibility/audit bug: invoking `python scripts/release_gate.py` previously called `write_card()`, silently replacing `evidence/run_card.json` with an H69-J summary assembled from older evidence. It was corrected so the CLI only evaluates and prints the release decision; run-card generation is no longer an implicit side effect. `evidence/run_card.json` was restored to the H69-H2 artifact-bound run card.
- The generic CLI release gate still reads legacy filenames (`e2_gate.json`, `e3_receipt.json`, etc.) which are not the transfer candidate's matching files in this checkout. Consequently its printed reasons include stale holdout/source-manifest binding failures, distinct from the current run card's explicit duplicate-stop finding. This is a remaining code/data wiring inconsistency; neither path permits release. Do not interpret the generic CLI report as a recomputation of the transfer H2 experiment.
- Full tests passed after installing the repository requirements and pytest into a local ignored virtual environment: **100 passed, 18 Rasterio pending-deprecation warnings**.
- Direct validation of the H69-H2 `-zeros.tif` passed. Initial test collection failed because pytest/scikit-image/Rasterio were absent from the system Python; this was an environment dependency issue, resolved in `.venv`.

### Pass 3 — requirements and release check

- No new experiment was run: current archived evidence already contains the permitted runs, and the duplicate-and-stop rule precludes further generation in this lane.
- No submission download was made available. No claim that a 0.3195/0.2778 score was beaten is supported; organizer receipt is absent. H33's reported 0.2778 remains user-reported, and local DTI is not comparable to the organizer leaderboard metric.
- The README now accurately identifies H69-H2 and states the local holdout numbers with evidence labels, while preserving a prominent **NOT OK TO SUBMIT** warning.
- The repo's earlier 3–4 candidate hypotheses are retained in `reports/review-2026-10-20-current-session.md`; none is treated as newly validated. A later run must obey preregistration, three-experiment/two-hour cap, holdout and registry gates, and use only the shared template tools.

## Research hypotheses already recorded for future work

The current session review documents candidate options including convergent relay-link edge phase, releasing-basin margin asymmetry, en-echelon scarp phase coherence, and matched lithology radiometric contrast reversal. They name layers/signatures and distinguish their mechanisms from existing scoring. These are proposals, not validated lifts. Before any experiment, restore and hash-verify the full feature stack and resolve the duplicate gate semantics without overriding its literal threshold.

## Reproducibility

- `python scripts/release_gate.py` — negative; download disabled (legacy evidence bindings; see Pass 2).
- `.venv/bin/python scripts/validate_submission.py submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif` — PASS.
- `.venv/bin/pytest -q` — 100 passed.
- `git diff --check` — PASS.

## Official review links (not freshly fetched in this sandbox)

- Competition rules/overview: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem description: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN data release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS project: https://gbcge.org/current-projects/ingenious/
- Giddens & Faulds (2025), SGP-TR-229: https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf
- Submission-format PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf

The URLs above are for manual/source review. The repo's prior attempts document that DrivenData's data tab requires login; this session did not authenticate or retrieve new competition data.
