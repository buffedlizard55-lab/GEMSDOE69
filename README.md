# GEMSDOE69 — auditable DOE GEMS fault-discovery workbench

> **Current release decision: NEGATIVE / NOT READY. There is no submission GeoTIFF in this repository. Do not download or submit a placeholder.** The holdout gate, registry-similarity checks, and format validator cannot be run because the competition rasters, cached feature stack, and requested shared tools are absent. No competition slot has been used.
>
> [Open the project status and download gate](index.html) · [Executive summary and submission instructions](executive-summary.html) · [Ranked hypotheses](hypotheses.html) · [Source register](sources.html) · [Run card](reports/run-card-2026-10-12.json)

## Standing project brief — read this section at the start of every session

Build a scientifically defensible, reproducible, and useful system for discovering **previously unmapped faults** in the DOE GEMS / GeoDAWN footprint and, only after validation, producing a unique competition-format GeoTIFF. The competition target is geological fault presence, not a geothermal vent map. Geothermal structure is the geological rationale for prioritizing possible faults; it is not itself the pixel label.

### The method lane for this project

Stay within the **catalogue-geometry relay-ramp / pull-apart / displacement-transfer corridor** approach. Build a graph from catalogue fault polylines and their tips. Where catalogue attributes support it, test parallel normal-fault pairs with the same dip direction and overlapping **and** underlapping tips. Use corridor width W in the project's 0.1–15 km search interval (the paper's measured sample spans 0.1–14.6 km, mean 2.8 km); constrain along-strike separation to ≤3.5W as a project-generation bound, not a universal geological law. Generate separate oblique-connector and en-échelon strand candidates in each corridor. Also consider dextral releasing steps, pull-aparts, terminations, and displacement-transfer corridors. Rank corridors—not isolated pixels—using multi-scale gravity and magnetic horizontal-gradient and tilt evidence (include signed magnetic lows), the available lidar-scarp channel, and stress-orientation consistency. The geological prior proposes where to inspect; it does not assert that an unobserved fault exists.

The geometric ranges and percentages in the user's research prompt are **hypothesis priors from the cited Giddens & Faulds paper**, not outcomes measured in this checkout. Check source attributes before using dip, slip-sense, or age: do not infer these from a 2-D line when the catalogue does not provide them. If an attribute is missing, record it as unknown and either test both kinematic interpretations or exclude that geometry from the kinematics-specific arm.

### Non-negotiable experiment and release protocol

1. **Reuse the shared template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do not maintain a private fork.** If a shared tool is wrong, fix it once in its actual shared template and record the upstream change. First verify that those files exist and identify the template: they do not exist in this checkout or in the official DrivenData reference-solution tree audited for this session, so this workflow is currently blocked rather than silently rebuilt.
2. Use whole withheld fault segments with a buffer. Derive every catalogue-based feature using only visible faults; mask visible faults pixel-exactly; pool DTI with alpha = 0.2, beta = 0.8, and the 300 m triangular kernel. Record evaluator version, withheld-positive count, and a segment/block-aware 95% confidence interval. A known-fault hide-and-recover result is a proxy, not proof of recovery on the competition's genuinely new faults.
3. Run a leakage canary for every feature alone on the holdout. Any feature AUC > 0.90 is treated as leakage until the feature derivation and split are demonstrated clean; do not use it in fusion before that review.
4. Compare the corridor model against the **same pipeline without corridor priors**, at matched prediction mass and using paired spatial folds. Require improvement over both that paired baseline and the current best holdout baseline. No weekly slot is eligible unless the required gate is met. A model projection is never a score.
5. Before placement and again on final dots, compare against every available prior raster. Record exact hashes/pixel-agreement, rank-correlation, and the fraction of dots within the three-pixel neighborhood. Rank-correlation must not exceed 0.90, and no more than 70% of dots may fall within 3 pixels of any one prior raster. Log the measurements; if either limit is exceeded, label the result duplicate and stop—do not relabel or ship it as unique.
6. Validate the exact bytes against the official sample grid: one band, float32, CRS/shape/transform match, probabilities in `[0, 1]` inside the footprint, and null/NaN only outside the footprint as required by the competition. Reopen and audit the written file; record SHA-256. Never claim portal acceptance without an organizer receipt.
7. Publish a per-corridor rationale (geometry, supporting layers/signature, source, confidence, and plausible non-fault mimic) for geologist review.
8. End each run with a JSON card containing hypothesis, mechanism, non-fault mimic, holdout DTI and CI (or explicit not-run status), registry comparisons, raster hash, validator result, submission name/note, and `promote` or `negative` verdict. Negative results are deliverables.
9. Respect the three-experiment / two-hour stop budget. A promotion to a competition slot is a separate selector decision; do not spend a slot merely because a raster exists.

### Core values

- **Maximize P(Win)** (“Maximize the Probability of Winning”): choose experiments by expected information and improvement per cost, preserve the submission budget, and reject attractive but unvalidated claims.
- **Own the Outcome:** report blockers, failed gates, data provenance, and irregularities plainly. Do not turn an owner projection, proxy score, or public leaderboard row into an organizer-confirmed score for a particular TIFF.

## What is verified in this checkout (2026-10-12 UTC)

- The tracked tree initially contained only this short README. This change adds documentation, a read-only readiness audit, and standard-library contract tests. There are still no competition data files, cached stack, shared evaluation/writing pipeline, TIFF output, or prior-raster registry in this checkout.
- The user-mentioned `scripts/download_competition_data.sh`, `scripts/prepare_data.py`, `evaluate_holdout.py`, and `submission_writer.py` are absent here. The public official reference-solution tree contains its README, environment files, data placeholder, lock/config files, and reference notebook; it does **not** contain the named holdout evaluator or submission writer.
- The DrivenData data tab redirects to its login page in this environment. No DrivenData session or competition data are available here. We do not bypass authentication, ask for credentials, or substitute a mirror as if it were organizer-authenticated.
- The environment has no NumPy, Rasterio/GDAL, SciPy, GeoPandas, pytest, or NVIDIA tooling installed. Its available memory is about 3.8 GiB. No raster computation or validator run is claimed.
- If lidar is absent from the competition stack, USGS 3DEP provides public-domain 1 m bare-earth DEM tiles as GeoTIFF/IMG through a free, no-account downloader. The exact tiles, dates, and intersection with the official template have not been checked. A USGS Quaternary-fault slip/dilation release is also publicly listed for download, but its fault-linked stress/tendency fields are not an independent predictor until their geometry and leakage lineage are audited. See [Sources](sources.html) and [Irregularities](irregularities.md).
- The site is a static root-level HTML/CSS bundle with `.nojekyll`; it is ready for GitHub Pages if enabled. Pages deployment/settings were not independently verified in this session.
- The 2025 relay-ramp source supports the structural premises in the research prompt, including ramp aspect ratio, measured width range, breaching geometries, higher-temperature hard-link frequency, and the Walker Lane's different structural setting mix. Details and caveats are in [Sources](sources.html) and [Hypotheses](hypotheses.html).
- **The user-cited public value is not established as the score of the named H33 TIFF.** The GEMSDOE32 owner page labels that file `UNSCORED` and calls its own projected value a model, not a score. The official public leaderboard shows participant-level values but does not identify that TIFF or supply a file-level receipt. The live leader was above the prompt's stated current-high reference when checked. See [the audit](analysis-h33.html). No score-to-file attribution is asserted.
- The DrivenData Terms of Use prohibit automated monitoring/copying and manual monitoring/copying without prior written consent. This project therefore links to the official competition site rather than scraping or republishing a leaderboard feed. A sanctioned API or written permission is needed for an automated feed.

## Why this checkout does not offer a TIFF

The release gate is not met and the requested tools are not present. A fabricated, zero-filled, or copied prior raster would neither test the corridor hypothesis nor satisfy the uniqueness-and-validation protocol. The site therefore has no active download link and explicitly says **do not submit**. This is the correct negative result until data and a shared, reusable evaluation path are available.

The user's reported portal error, `Predicted values must be in range [0, 1]`, cannot be diagnosed from this checkout: the failed file and its receipt are not here. The official format does require in-footprint predictions in `[0, 1]`; common things to audit include a negative nodata sentinel treated as a value, raw/unscaled scores, NaN/Inf inside the footprint, and an incorrect footprint mask. These are diagnostic possibilities, **not a verified root cause**. Do not blindly clip or replace values without checking the source and exact footprint.

## Next steps, in order

1. Obtain the official competition downloads through an authorized DrivenData account and place them locally under `data/` (never commit private or large rasters). Include the exact sample-submission template and the vector/catalogue inputs needed to rebuild the tip graph.
2. Identify the real shared template that owns the cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. If it is a different repository, connect this work to that shared code; do not create a parallel evaluator or writer here.
3. Resolve the checkout's absent download/prepare scripts and missing test environment in the actual shared template. Pin source hashes and document the provenance of all inputs.
4. Register and preregister the five corridor hypotheses, then run the spatially blocked hide-and-recover holdout and the per-feature leakage canaries within the stated budget.
5. Require a positive paired gate against the same pipeline without corridor priors. Only then build a unique candidate, run the pre-placement and final-dot registry checks, validate the exact TIFF bytes, publish the rationale/run card, and expose a one-click download.
6. For an up-to-date competition status, use the official live competition page. Do not build an automated or manually mirrored score feed without written permission or a sanctioned interface.

## Project pages

- [Executive summary and submission guide](executive-summary.html)
- [Five ranked hypotheses and their holdout plans](hypotheses.html)
- [Official and primary source register](sources.html)
- [H33 score-attribution audit](analysis-h33.html)
- [Claim-by-claim geological evidence matrix](evidence.html)
- [Current negative run card](reports/run-card-2026-10-12.json)
- [Per-corridor rationale template (blank; no candidates yet)](reports/corridor-rationale-template.md)
- [Three-pass implementation and review log](reports/review-passes-2026-10-12.md)
- [Workspace readiness audit tool](scripts/audit_workspace.py)
