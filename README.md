# GEMSDOE69 — relay-ramp and pull-apart corridor lane

## NOT OK TO SUBMIT — DO NOT SUBMIT

Candidate `submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif` is archived for audit only. There is no submission download, no offer of a TIFF, and no competition slot was used. Local format validation is not release clearance.

**Start here:** [Executive summary](docs/executive-summary.html) · [Project site](docs/index.html) · [Current JSON run card](evidence/run_card.json) · [Current holdout and release audit](reports/repo-review-2026-10-20.md).

**Lane contract:** catalogue tip-graph relay ramps / pull-aparts only; W 0.1–15 km; along-strike separation ≤3.5W. Dip direction and dextral slip sense must not be inferred from strike alone.

### Current decision

The current archived experiment is labelled **HOLDOUT-DTI** (vendor/template66 gems57.holdout.build_holdout+score_cell (alpha=0.2 beta=0.8 R=300m triangular; seeds=[20,21] modes=['all']; POOLED from summed TP/FP/FN); 8 cells; 22641 withheld positives). Primary pooled DTI from summed TP/FP/FN: `0.008469830499045719`; pooled absolute 95% CI: `None`. Mean-of-cell DTI: `0.007737531380405138` with normal-approximation CI `[0.0057316537303127996, 0.009743409030497476]`. Paired CIs below are deltas against their named comparators, not absolute pooled-DTI CIs.

**Literal registry result** (`REGISTRY-MEASUREMENT`, not a score): accessible index 862 rasters; worst final-dot overlap `1.0`. The literal protocol requires stop if Spearman exceeds 0.90 **or** more than 70% of candidate dots are within 3 px of one raster. Stratified/dotlike diagnostics cannot waive that failure. The scanned public owner-repository index is not a complete organizer registry.

**Release blockers:**
- Recorded preregistration is not earlier than HOLDOUT-DTI generation; protocol order is unverified.
- No hash-bound paired HOLDOUT-DTI 95% CI proves improvement over the declared current holdout best.
- Literal registry dot-overlap is 1.000 against 17GEMSDOE:docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif; above 0.700, so duplicate-and-stop applies.
- surface uniqueness phase failed its literal duplicate gate or is missing.
- surface uniqueness phase exceeds or lacks the literal 3-px dot-overlap limit.
- surface uniqueness scan is not certified at the required before placement stage.
- dots uniqueness phase failed its literal duplicate gate or is missing.
- dots uniqueness phase exceeds or lacks the literal 3-px dot-overlap limit.
- dots uniqueness scan is not certified at the required after placement stage.
- Reproducible method source manifest is missing, stale, or not artifact-bound; source hash mismatch: src/gems69/holdout69.py.

### H33 and leaderboard claims

The reported H33 value **0.2778 is USER-REPORTED-NOT-ORGANIZER-CONFIRMED**: this repository has no organizer submission receipt binding that score to a file. It is not a target that this lane has demonstrated it can beat. Holdout DTI is a screening instrument, not a leaderboard projection. No fresh leaderboard fetch was performed in this review; conflicting historic/user-reported values remain unverified.

### Ranked untried work (not authorization to test)

See [three in-lane hypotheses](docs/research/untried-hypotheses-2026-10-20.md). They are qualitative priors confirmed untested **in this checkout** by source/evidence review, not global novelty claims. The preferred next hypothesis was **not tested**: the feature cache is absent, current-candidate provenance is stale, and the current-best paired comparison is missing. No new candidate or TIFF was generated.

### Reproduce status and tests (no experiment or data restore)

```sh
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/release_gate.py
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/build_site69.py
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/build_readme.py
PYTHONPATH=vendor/template66:src .venv/bin/python -m pytest -q
```

`release_gate.py` is read-only by default. `--write-card` only rebinds the existing frozen receipts into `evidence/run_card.json`; it does not rerun an experiment. The local feature cache is absent from this checkout, so the archived science is not reproducible here without separately authorized data restoration. Exact candidate bytes previously passed the local format/range validator; that does not clear uniqueness, provenance, current-best, or organizer-authentication gates.

### Review status

Three review passes are recorded in `reports/repo-review-2026-10-20.md`: requirements/status, code and evidence binding, then final adversarial re-check. No competition slot was selected or used. PR/merge status is tracked in GitHub separately from the scientific run card.

## Standing project brief — read in full at the beginning of every session

The full retained brief is included below from `PROMPT.md`; read it before taking any action.

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
