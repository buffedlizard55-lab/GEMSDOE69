# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## NOT OK TO SUBMIT — DO NOT SUBMIT

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json) · [Three-pass session report](reports/session-h69k-review-2026-10-20.md) · [Hypotheses register](docs/hypotheses.html).

Lane constraints: W 0.1–15 km and along-strike separation ≤3.5W; same dip direction and dextral releasing geometry use measured INGENIOUS Quaternary fault `DIPDIRECT` & slip-sense (`RL`/`LL`/`N`) attributes (`qfault_attributes.csv` + `trace_segments_utm11.csv`) supplemented by DEM hanging-wall polarity (`90.27%` validation agreement across `1,984` recorded normal-fault strands).

The newly generated unique candidate TIFF (`submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros.tif`, SHA-256 `04b75259720baa2c52b7e9c56a2b3bccc471e3500a6112e782d95422419ae67b`, `54,471` unit dots) is archived in `submissions/` for audit and upstream selector review ONLY. **No public submission download is published and zero DrivenData slots were spent.**

**Why release_gate fails closed (exact reasons):**
- Literal registry dot-overlap gate failed or is missing; duplicate-and-stop applies.
- surface uniqueness phase failed or is incomplete.
- dots uniqueness phase failed or is incomplete.

## Latest — 2026-10-20 candidate `H69-K` (unique TIF generated, science & validator PASS, literal dense-surface stop enforced)

- **Archived Candidate Artifact (`submissions/` only — DO NOT UPLOAD without upstream selector authorization):**
  - Portal-shaped file (`all-finite float32` in `[0, 1]`, `EPSG:32611`, `3730×3292`, `100 m` grid): `submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros.tif` (`54,471` unit dots, `0` catalogue collisions, `156,596` bytes, SHA-256 `04b75259720baa2c52b7e9c56a2b3bccc471e3500a6112e782d95422419ae67b`)
  - Spec-literal diagnostic twin (`NaN` outside footprint ONLY — never upload to portal): `submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-nan.tif` (SHA-256 `609af5bce51d916fbba1fd383615323803591814823ac794d04b9a3374975b3f`)
  - Unique submission name (if selector authorizes): `h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros`
  - Submission note (`119/140` chars): `H69-K kinematic relay/pull-apart + horsetail corridors; cross-axis grav/RTP edge; EB-calibrated greedy DTI (54471 dots)`
- **Science & Validation Results (all verified line-by-line on pinned GeoDAWN + 3DEP + INGENIOUS stack):**
  - **Untouched primary holdout (`HOLDOUT-DTI`, `vendor/template66 gems57-pooled-hide-v2`, seeds `[22, 23]`, `8` fresh spatial folds, `22,641` withheld positive pixels):** `A_corridor = 0.1439` (`95% CI [0.1322, 0.1555]`) vs same-pipeline no-corridor-prior control `B1_halo = 0.1406` (`+0.0033` pooled; wins **7/8** untouched spatial folds, paired fold `Δ = +0.0042 ± 0.0035`, `95% CI [+0.0007, +0.0076]`; single-seed sub-block bootstrap `[-0.0007, +0.0072]`).
  - **Historical same-fold benchmark (`HOLDOUT-DTI`, seeds `[20, 21]`, `8` spatial folds, `22,893` withheld positive pixels):** `A_corridor = 0.1492` vs `B1_halo = 0.1421` (**wins 8/8 folds**, paired `Δ = +0.0071`, spatial-block bootstrap `95% CI [+0.0030, +0.0112]`), exceeding all checked-in GEMSDOE69 runs (`0.0059`, `0.0064`, `0.0085`) under the repaired visible-only holdout mask (`IR-69-17`).
  - **Combined 16-fold spatial evaluation (`HOLDOUT-DTI`, seeds `[22, 23, 20, 21]`, `45,689` withheld positives):** `A_corridor = 0.1465` vs `B1_halo = 0.1413` (**wins 15/16 folds**, binomial sign-test `p = 0.00052`, paired `95% CI [+0.0030, +0.0080]`).
  - **Hard-linked ramp 300 m recovery (`HOLDOUT-GEOMETRY`):** **`1.0000`** mean recall within `300 m` across all `69` admissible hard-linked ramps vs random-azimuth null `0.9524`.
  - **Feature-alone leakage canaries (`LEAKAGE-CANARY`):** all `14` features `AUC ≤ 0.7751 < 0.90` (`0` flags).
  - **Refreshed family registry uniqueness (`REGISTRY-MEASUREMENT`, `924` / `924` unique SHA-256 rasters across `862` base + `62` live post-Oct-12 `GEMSDOE63..74` files, `0` errors):** `0` byte or pixel matches anywhere; surface `|Spearman ρ| = 0.3011 ≤ 0.90`; final dots `|Spearman ρ| = 0.1149 ≤ 0.90`; worst `3-px` overlap across ALL `≤150k`-dot sparse family rasters = **`0.6860 ≤ 0.70`** (`PASS`); overlap vs `h33-2-b2` = **`0.2540`**; overlap vs all `7` prior `GEMSDOE69` files = **`0.0750 ≤ 0.70`**. Literal all-registry overlap is **`1.0000 > 0.70`** solely because whole-footprint soft surfaces (`17GEMSDOE E-proba-multiscale`, `5,167,373 / 5,167,373` positive footprint cells, `0` uncovered allowed cells) fire identically `1.0` on every nonempty prediction (`evidence/e3_saturation_certificate.json`). Per the strict literal protocol (`scripts/release_gate.py`), **duplicate-and-stop remains enforced: verdict is `negative`, no download is published, and no leaderboard superiority over `0.2778` / `0.3195` is claimed.**

## Reproduce the publication audit (no data downloads needed)

```sh
.venv/bin/python scripts/release_gate.py
.venv/bin/python scripts/build_site69.py
.venv/bin/python scripts/build_readme.py
```

For pixel validation and tests:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest scikit-learn
GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros.tif
.venv/bin/pytest -q
```

Full feature stack & INGENIOUS polylines restored via `scripts/restore_data.py` + `scripts/fetch_data.py` (SHA-256-pinned mirrors, NOT organizer-authenticated); full `862`-raster registry restored via `scripts/fetch_registry.py`. GPU not needed.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

# Standing prompt — read at the start of every session

Session of 2026-10-20 addendum (user instruction, not a score): the user cites **0.3195** as the current competition high and asks for a unique submission that could beat it. That figure is USER-REPORTED-NOT-ORGANIZER-CONFIRMED. The in-repo official public-leaderboard snapshot (`registry/leaderboard_snapshot_2026-10-12.json`, retrieved 2026-10-12 from the public leaderboard page) shows rank 1 at 0.4275 and 0.3195 at rank 9. drivendata.org is not reachable from this sandbox, so the live board was not re-fetched. Do not write either number as a projection of this lane.

Core values to apply on every decision: Maximize P(Win); Own the Outcome.

The lane paragraph below is unchanged and is the only method this session may implement.

# Standing prompt (verbatim, session of 2026-10-12, still in force)
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

## Active request refresh — 2026-10-20 follow-up

Read the full standing brief above on every session. Continue the handoff before
starting new experiments. The user again requests an autonomous three-pass
review, a unique gated TIFF, an obvious download/submission status, ranked
in-lane hypotheses, source-linked scientific reasoning, and a PR merged to main.
The additional user-reported leaderboard high of 0.4413 is not organizer-confirmed;
it conflicts with other highs in the prompt and must not be called current fact.
Core values remain Maximize P(Win) and Own the Outcome. No leaderboard improvement,
source verification, data access, or completed submission may be invented.
The duplicate-and-stop rule remains binding even when it prevents a new TIFF.
