# GEMSDOE69 — STANDING PROMPT (READ FIRST AT THE START OF EVERY SESSION)

# Standing prompt (verbatim, session of 2026-10-12) — read at the start of every session

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
## Repo summary (this file)

Lane rules (from the standing prompt above): pair acceptance uses spacing W of 0.1&ndash;15 km and
along-strike separation ≤3.5W (compact form of "≤ 3.5 W"); "same dip" is proxied by sub-parallel
terminal strikes because the raster catalogue carries no dip polarity (disclosed limitation IR-69-DIP-01).

# GEMSDOE69 — Relay-ramp & pull-apart corridor lane (DOE GEMS Prize, DrivenData #306)

**Lane method:** propose hidden faults from **catalogue geometry** (tip graph of
mapped fault polylines → relay-ramp / pull-apart corridors), scored by
multi-scale horizontal-gradient + tilt evidence in gravity and magnetics
(including magnetic lows), the 1 m lidar-scarp channel, and orientation
consistency with WNW extension — then **calibrated greedy marginal-DTI dot
placement** inside the top corridors. Standing prompt: [PROMPT.md](PROMPT.md)
(read it at the start of every session).

## Site

GitHub Pages (this repo, `docs/`): **index → executive summary → submission
download → why-h33-scored → hypotheses → method → experiments → sources →
irregularities → run card**. The submission TIF and its OK/DO-NOT-SUBMIT
banner are always at the very top of `docs/index.html`.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 scripts/fetch_data.py        # sha256-pinned family mirrors -> .cache/gems_data (git-ignored)
python3 scripts/fetch_registry.py    # 751 prior-raster blobs -> .cache/registry (git-ignored)
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py verify
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e1    # canaries + hard-link recovery
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e2    # holdout gate vs no-prior control
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e3    # final emission + submission write
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py unique # registry lane-drift scan
.venv/bin/python scripts/build_site69.py                                      # rebuild docs/
```

## Layout

| path | contents |
| --- | --- |
| `vendor/template66/` | byte-pinned shared template (`TEMPLATE_SHA256.txt` verified); `gems57` = official DTI arithmetic, hide-and-recover holdout, greedy allocator, submission writer; `gems` = validator |
| `src/gems69/` | lane code: `tips.py` (strands), `corridors.py` (tip graph, step-over geometry), `physics.py` (windowed HG/tilt evidence), `scoring.py`, `holdout69.py` |
| `data/bridge/` | sha256-pinned grid files: `labels.tif`, `sample_submission.tif`, `existing_faults.tif` (see irregularity IR-69-DATA-01) |
| `registry/` | `prior_rasters.json` (751-blob family census), `data_manifest_gemsdoe32.json` (mirror manifest) |
| `evidence/` | every measurement, one JSON per step, evidence-class labelled |
| `submissions/` | validated TIF + receipt (never promoted automatically) |
| `docs/` | GitHub Pages site |
| `tests/` | unit tests for the tip-graph arithmetic |

## Evidence classes (protocol rule 3)

* **HOLDOUT-DTI** — hide-and-recover pooled DTI (alpha 0.2, beta 0.8, 300 m
  triangular kernel, evaluator `gems57` pooled hide v2 family). Always reported
  with withheld-positive count and 95% CI. A screen, never a leaderboard
  projection (cross-family Spearman vs live ≈ 0.51, p≈0.09; GEMSDOE32
  instrument-calibration evidence).
* **ORGANIZER-CONFIRMED** — only values copied from a DrivenData submission
  receipt. None exist in this repo yet (no DrivenData auth in-sandbox).
* **USER-REPORTED-NOT-ORGANIZER-CONFIRMED** — leaderboard values quoted in the
  standing prompt (0.2778, 0.3774, 0.3195, …).

## Limitations (carried from prior sessions, still true)

1. **No DrivenData auth** → organizer bytes cannot be downloaded here; the
   sha256-pinned family mirrors (themselves mirrored from earlier sessions'
   downloads of the official files) are used and are NOT organizer-authenticated.
2. **Sandbox network** is restricted to github.com / pypi.org — drivendata.org,
   USGS, Dropbox and github.io pages are not reachable from the runner; all
   external facts cited in docs were verified in earlier sessions or are quoted
   from the standing prompt with their source named.
3. `existing_faults.tif` is byte-identical to `labels.tif` in every family
   mirror (IR-69-DATA-01). The public labels raster *is* the mapped catalogue;
   the scored truth (≈12,691 px, receipt-derived estimate from GEMSDOE32
   evidence) is unpublished.
4. CPU-only box (2 cores / 3 GB RAM): the pipeline is windowed and memory-lean
   by design; no GPU training is attempted in this lane.

## Core values

Maximize P(Win). Own the Outcome — end to end, failure is a signal, negative
results are deliverables.
