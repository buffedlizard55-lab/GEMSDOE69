# GEMSDOE69 — Two-Regime Geodesic Relay-Ramp & Pull-Apart Corridor Generator

> ## ✅ SUBMISSION STATUS: **OK TO DOWNLOAD AND SUBMIT**
>
> **All 14 fail-closed holdout, leakage-canary, 829-blob registry uniqueness, and `[0, 1]` GeoTIFF format gates PASSED (`src/gems/gate.py` &rarr; `OFFER_DOWNLOAD`).**
>
> - **1-Click Primary Submission GeoTIFF (`all-finite float32 in [0, 1]`, `32,000` dots, `0` NaNs):**
>   **[submissions/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros.tif](submissions/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros.tif)** *(also mirrored at [docs/downloads/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros.tif](docs/downloads/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros.tif))*
> - **Single-TIFF Portal ZIP Archive:** **[submissions/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros.zip](submissions/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros.zip)**
> - **Footprint-NaN Diagnostic Twin (`exact sample_submission.tif finite mask`):** [submissions/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-nan.tif](submissions/h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-nan.tif)
> - **Unique Submission Name:** `h69-tworegime-geodesic-corridor-32000-20261020T225640Z-f5cf7bb5-zeros`
> - **Copy-Paste DrivenData Note (`120 / 140` chars):**
>   `GEMSDOE69 H69-G5 two-regime geodesic relay/pull-apart corridors; 32000 greedy-DTI dots >=350m off cat; HOLDOUT-DTI 0.0813`
> - **Primary SHA-256:** `28375c975487299e8c1245c36f416b3c7d03cfa661b956ba44ca127107a81273`
> - **NaN-Twin SHA-256:** `df8cca0266142725c3b4208596aca844a6037577c83aa3e8fb2371797124cca5`
> - **GitHub Pages Site & Executive Upload Guide:** [index.html](index.html) &middot; [docs/index.html](docs/index.html) &middot; [docs/executive-summary.html](docs/executive-summary.html) &middot; [evidence/run_card.json](evidence/run_card.json)

---

## Standing Prompt (Verbatim — Read First at the Start of Every Session)

> Review the repo.
>
> THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.
>
> There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.
>
> Relay-ramp and pull-apart corridor generator. Propose faults from catalogue geometry rather than pixel statistics. Giddens & Faulds (2025, SGP-TR-229) inventoried >450 step-overs. Ramps are typically 3–3.5× longer than wide, with widths of 0.1–14.6 km (mean 2.8 km). About 70% of higher-temperature step-overs are hard-linked, and breaching faults range from oblique connectors to en échelon strands. In the Walker Lane, which dominates the GeoDAWN footprint, hot systems sit more often in pull-aparts and displacement-transfer zones than in normal-fault step-overs. N–NE faults are best oriented for dilation under WNW extension. Build a tip graph from catalogue polylines. For each same-dip, overlapping or underlapping tip pair with spacing W of 0.1–15 km and along-strike separation ≤ 3.5 W, emit candidate corridors (an oblique connector plus en échelon strands). Add pull-apart and transfer-zone corridors at dextral releasing steps and terminations. Score corridors by multi-scale horizontal-gradient and tilt evidence in gravity and magnetics (including magnetic lows), the lidar-scarp channel, and orientation consistency with the stress field. Place nodes inside the top corridors by calibrated greedy marginal-DTI selection. Validate by masking known linking faults in hard-linked ramps and testing recovery within 300 m. Record a per-corridor rationale (layers, signature, source) for geologist review. Gate: beat the same pipeline without corridor priors. Finish: normalize to [0,1]; write a float32 EPSG:32611 100 m GeoTIFF (NaN only outside the footprint); pass validate_submission.py; run a hash/pixel-agreement check against all prior rasters; offer the download only if the gate is met, else log the negative result.
>
> PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.
>
> 1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.
> 2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.
> 3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.
> 4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.
> 5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.
> 6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.
>
> [User-reported leaderboard context:] highest family download score h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros = 0.2778 (GEMSDOE32); competition leaderboard high scores cited by the user: 0.3774, later 0.3195 — USER-REPORTED-NOT-ORGANIZER-CONFIRMED. The question to answer every session: why did the current best score, and can a unique submission beat it? Answer with evidence classes, never projections written as scores.
>
> Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.
>
> Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.
>
> The goal of this project is to place top of the leaderboard in this competition: https://www.drivendata.org/competitions/306/competition-doe-gems/ (problem page /page/967/, about page /page/968/, data /data/ — login-walled). Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution. USGS GeoDAWN data: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and. INGENIOUS: https://gbcge.org/current-projects/ingenious/. EPSG:32611: https://epsg.io/32611. Metric background: https://en.wikipedia.org/wiki/Tversky_index.
>
> Site requirements: a GitHub Pages site with clean UI; the TIF download must be obvious at the very top of the index page, with an unambiguous OK/DO-NOT-SUBMIT banner; an executive-summary subpage explaining exactly how to submit (single-band GeoTIFF .tif or .zip with one GeoTIFF; must match the submission format's CRS, shape, geotransform; values in [0,1]; optional note ≤140 chars, e.g. "relay-ramp corridors, k=40k dots"). Include official verified links for manual review.
>
> Known limitation from prior sessions (still true): no DrivenData auth in this environment, so organizer bytes cannot be auto-downloaded; family mirrors (sha256-pinned, NOT organizer-authenticated) are used instead. Run `scripts/fetch_data.py` to restore them; large files live in `.cache/` (git-ignored).
>
> Pass protocol: Pass 1 implement and verify; Pass 2 review for bugs/missing requirements/edge cases, fix; Pass 3 re-check against this file, improve, fix. Finish with a pull request merged to main, plus suggestions and limitations for the next session.
>
> Core values (Arena): Maximize P(Win) — weigh tradeoffs, assess risk, choose the path that maximizes the probability of winning. Own the Outcome — own results end to end, treat failure as a signal, stay accountable to the final outcome.

---

## Verified Experimental Summary (3 Budgeted Experiments Completed)

Pair acceptance follows spacing W of 0.1–15 km and along-strike separation ≤3.5W (`Giddens & Faulds, 2025, SGP-TR-229`). Every metric below carries its exact evidence class:

| Measurement / Arm | Value | Evidence Class & Verification |
| :--- | :--- | :--- |
| **`H69_G5_TwoRegimeGeodesic` (Selected Primary)** | **`0.0813` (`95% CI [0.0722, 0.0905]`)** | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `n = 22,893` withheld positive px across `8` folds; **passes all 14 gates**) |
| `Control_NoCorridor` (Same physics + allocator, no corridor priors) | `0.0319` (`95% CI [0.0239, 0.0411]`) | `HOLDOUT-DTI` — **Paired $\Delta = +0.0495$ (`95% CI [+0.0395, +0.0588]`, `2.55×`)** |
| `Incumbent_PR6_Corridor` (Prior `GEMSDOE69` ellipse baseline) | `0.0431` (`95% CI [0.0350, 0.0511]`) | `HOLDOUT-DTI` — **Paired $\Delta = +0.0383$ (`95% CI [+0.0289, +0.0483]`, `1.89×`)** |
| Prior `main` `h69-z-radiometric-halo` (`PR #9`) | `0.0060 ± 0.0014` | `HOLDOUT-DTI` — **`H69_G5` achieves `13.6×` higher holdout DTI** |
| `H69_G4_SGMCReactivation` (`E2` ablation arm) | `0.0956` (`95% CI [0.0842, 0.1075]`) | `HOLDOUT-DTI` — **STOPPED & WITHDRAWN per Rule 1 (`98.56% > 70%` overlap with `GEMSDOE30`)** |
| `H69_G1_GeodesicCorridor` / `H69_G3_HydroGeotherm` / `H69_G2_NoRadMT` | `0.0899` / `0.0895` / `0.0889` | `HOLDOUT-DTI` — full multi-arm ablation in [evidence/e2_gate.json](evidence/e2_gate.json) |
| Hard-linked relay/pull-apart mask-and-recover (`E1`) | **`0.9128` (`91.3%`, `n = 19`)** | Recovery within `300 m` ([evidence/e1_hardlinked_recovery.json](evidence/e1_hardlinked_recovery.json)) |
| Normal-fault DEM hanging-wall dip polarity inference (`E1`) | **`0.9028` (`90.3%`, `n = 1,985`)** | Agreement vs USGS QFF recorded dip direction ([evidence/e1_tipgraph_census.json](evidence/e1_tipgraph_census.json)) |
| Single-feature leakage canaries (`17` channels tested, `E1`) | **`max AUC = 0.7965 <= 0.90`** | `17/17 PASS` (`dist_known_fault_px` hard-blocked; [evidence/e1_canaries.json](evidence/e1_canaries.json)) |
| Cross-repo registry uniqueness (`829` unique blobs / `826` rasters, `E3`) | **`|rho| = 0.6465 <= 0.90`, `overlap = 0.6365 <= 0.70`** | `0` exact pixel matches across all `826` rasters ([evidence/e3_uniqueness.json](evidence/e3_uniqueness.json)) |
| Family top download (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) | `0.2778` | `USER-REPORTED-NOT-ORGANIZER-CONFIRMED` ([docs/research/benchmark_02778_analysis.md](docs/research/benchmark_02778_analysis.md)) |
| Competition top leaderboard scores cited in standing prompt | `0.3774` / `0.3195` | `USER-REPORTED-NOT-ORGANIZER-CONFIRMED` |

---

## Key Repository Documents & Artifacts

- **PhD Analysis of `0.2778` (`h33-2-b2`) & Metric Derivation:** [docs/research/benchmark_02778_analysis.md](docs/research/benchmark_02778_analysis.md)
- **Ranked Pre-Implementation Geological Hypotheses (`H69-G1..G5`):** [docs/research/new_hypotheses.md](docs/research/new_hypotheses.md)
- **Complete Irregularities & Protocol Rule 1 Dispositions:** [irregularities.md](irregularities.md) &middot; [FLAGGED.md](FLAGGED.md)
- **Machine-Readable Run Card & Strict Gate Receipt:** [evidence/run_card.json](evidence/run_card.json) &middot; [docs/receipts/h69_latest_receipt.json](docs/receipts/h69_latest_receipt.json)

## Reproducible End-to-End Execution

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/fetch_data.py        # SHA-256-verified data -> .cache/gems_data/
.venv/bin/python scripts/fetch_registry.py    # All 829 prior org blobs -> .cache/registry*/
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py verify
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e1
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e2
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e3
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py card
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py site
PYTHONPATH=vendor/template66:src .venv/bin/pytest -q
```
