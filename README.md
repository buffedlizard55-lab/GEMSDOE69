# GEMSDOE69 — Kinematics-Resolved Relay-Ramp & Pull-Apart Corridor Generator

## NOT OK TO SUBMIT — DO NOT SUBMIT

**Start here:** [Executive summary](docs/executive-summary.html) · [Three-pass engineering & geological review](reports/review-2026-10-20.md) · [Flagged irregularities](FLAGGED.md) · [Run card](evidence/run_card.json) · [GitHub Pages site](https://buffedlizard55-lab.github.io/GEMSDOE69/).

**Gate enforcement:** No DrivenData submission slot was spent, and **no public `.tif` / `.zip` download is offered** (`docs/downloads/` contains zero downloadable artifacts). Under Parallel-Run Protocol Rule 1 & Rule 5, a negative gate verdict is a first-class deliverable:

- Literal registry uniqueness gate failed or is missing; duplicate-and-stop applies.
- surface uniqueness phase failed or is incomplete.
- dots uniqueness phase failed or is incomplete.

---

## Live Reproducible Scorecard (`E1`, `E2`, `E3` — All Checked In & Hash-Bound)

Lane geometry constraints enforced strictly: cross-strike spacing **W = 0.1–15 km** (`1–150 px`), shared world-origin along-strike separation **≤3.5W**, full `hypot(W, 3.5W)` KD-tree search radius, minimum-distance facing tip-pair deduplication, and measured Qfaults slip/dip (`SLIPSENSE`, `SECONDARY`, `DIPDIRECT`) + 100 m DEM hanging-wall polarity strictly within visible masks.

| Protocol Check | Measured Result | Verdict & Evidence Class |
|---|---|---|
| **E1A Single-Feature Canaries** | `33 / 33` features `<= 0.90`; #1 feature `corridor_multiplicity` = **`0.59082`** (up from `0.495` prior) | **PASS** (`HOLDOUT-CANARY`, `9308` px) |
| **E1B Hard-Linked Ramp Recovery** | **`781`** ramps found (up from `0`); **`0.9944`** mean 300 m recovery (`80/80` >= 70%) | **PASS** (`GEOMETRIC-RECOVERY`) |
| **E2 Primary Holdout (`mode=all`)** | **`H69-EFG`: `0.072701`** `[0.055864, 0.086004]` vs **`0.047245`** control (**`+0.025456` / `+53.9%`**, `7/8` wins, `p=1.0`) | **PASS** (`HOLDOUT-DTI`, **`9.03x`** prior `0.00805`) |
| **E2 Conservative (`mode=detached`)** | **`H69-EFG`: `0.067664`** `[0.052539, 0.081458]` vs **`0.050269`** control (**`+0.017396` / `+34.6%`**, **`8/8` quadrants won**, `p=1.0`) | **PASS** (`HOLDOUT-DTI`, `-22.5%` dot mass) |
| **E3 GeoTIFF Format & Template Validator** | `29027` dots across `3900` corridors; SHA-256 `25cdba0acab1c9ee…`; both `-zeros.tif` and `-nan.tif` validated (`R14` lattice = `False`) | **PASS** (`29/29` checks, `0` errors) |
| **E3 Registry Spearman (`751/751` blobs)** | `0` scan errors; `dots max |rho| = 0.144801`, `surface max |rho| = 0.446873` (`<= 0.90`) | **PASS** (`REGISTRY-MEASUREMENT`) |
| **E3 vs Family Champion `h33-2-b2-zeros`** | `Spearman rho = 0.008691`, **3-px dot proximity = `0.312123` (`68.79%` of H69-EFG dots lie `> 300 m` outside `h33-2-b2-zeros`!)** | **COMPLEMENTARY** (`REGISTRY-MEASUREMENT`) |
| **E3 Registry 3-px Forward Overlap** | `1.0000` vs soft surfaces; `0.8480–0.9603` vs sibling `40k–80k` scarp/corridor rasters (`> 0.70` limit) | **STOP / NEGATIVE** (Rule 1 duplicate stop) |

---

## Why `h33-2-b2-zeros` Achieved `0.2778` (`USER-REPORTED-NOT-ORGANIZER-CONFIRMED`) & How To Beat It

All live leaderboard figures (`0.1922 -> 0.2477 -> 0.2600 -> 0.2708 -> 0.2778`, plus prompt highs `0.3774 / 0.4413 / 0.3195`) are **`USER-REPORTED-NOT-ORGANIZER-CONFIRMED`**. Under exact Distance-Weighted Tversky Index (`alpha=0.2, beta=0.8, R=300 m`), kernel recall saturates via `max` while false-positive mass grows linearly in dot count `n`: pruning `h19-5` (`121,131 px`) -> `d1.5` (`60,069 px`) -> `d2.8` (`44,090 px`, retaining `84.4%` line coverage at `2.75x` lower mass) -> `B=1` (`40,199 px`) -> `B=2` (`37,654 px`, `0` dots within `200 m` of mapped faults) removed redundant halo mass without sacrificing recall.

Adding a new dot strictly improves `DTI = 0.2778` iff expected uncovered truth coverage satisfies `dT > 0.0588 * (1 - m)` truth-px/dot. Because **`68.79%` (`19,967` dots) of `H69-EFG`'s validated corridor dots sit strictly `> 300 m` outside `h33-2-b2-zeros`**, fusing only the top `1,500–2,500` non-overlapping interior breaching-relay / pull-apart dots (`E[k] >= 0.09`) into `h33-2-b2-zeros` inside the family cross-lane integrator targets real positive `dDTI` without wasting a standalone slot.

---

## Reproduce Everything End-to-End

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest scikit-learn
.venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/fetch_registry.py
.venv/bin/python -u scripts/run_e1_e2.py
.venv/bin/python -u scripts/run_e3.py
.venv/bin/python scripts/release_gate.py
.venv/bin/python scripts/build_site69.py
.venv/bin/python scripts/build_readme.py
.venv/bin/pytest -q
```

---

## Standing Project Brief — Read at the Beginning of Every Session

# Standing project brief (retained summary from 2026-10-12) — read at the start of every session

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
