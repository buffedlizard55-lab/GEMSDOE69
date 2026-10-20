# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## NOT OK TO SUBMIT — DO NOT SUBMIT

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json) · [latest audit](reports/final-audit-2026-10-20.md).

**Submission status:** No TIFF or ZIP is published for submission. Files in `submissions/` are audit artifacts only.

The governing lane rule is literal: if any registry raster has rank correlation above 0.90 **or** more than 70% of final dots within 3 pixels, the candidate is a duplicate and the process stops. Dense-support / dotlike strata are useful diagnostics, but do not override this release decision.

**Lane geometry scope:** step-over width W = 0.1–15 km; along-strike separation ≤3.5W. Same-dip direction and dextral-releasing geometry require measured attributes, not a strike-only proxy.

### Why download is locked

- Literal registry dot-overlap gate failed or is missing; duplicate-and-stop applies. Stratified dotlike overlap is diagnostic only and cannot override the literal protocol.
- Holdout comparison is missing or not bound to the current artifact hash.
- Reproducible method source manifest is missing, stale, or not artifact-bound.

The historical candidate's zeros-TIFF SHA-256 is `981beb5707bb9933a2cf24a615eed373dc7e7cab451954207097e1641f32eaa6`. Its local format receipt can establish byte-level format only; it cannot cure an unbound holdout, a stale method manifest, or a failed literal uniqueness gate. No competition slot was used by this repository state.

## What was learned without submitting

- ARCHIVED HOLDOUT-DTI (not artifact-bound on this checkout): corridor mean 0.005913, 95% CI half-width 0.001246, control mean 0.002148, 8 cells, 22641 withheld positive pixels.
- REGISTRY-MEASUREMENT (archived): worst absolute Spearman 0.162; literal rho pass=True; literal overlap pass=False.
- The H69-J joint-corridor artifact is **not a current promotion**: its method-source and holdout bindings are stale after the tip-graph repair, and the literal overlap gate is independently failing.
- The transfer-only artifact is a distinct negative result. Its archived HOLDOUT-DTI screen exceeded its stated internal comparator, but its literal all-registry overlap was 1.0 and its worst dotlike overlap was 0.8497; therefore it is also not offered.
- No new TIFF is generated in this review: emitting another candidate after a duplicate-and-stop result would violate the parallel-run protocol and would not make it submission-ready.

## H33 result review — correction to the premise

The cited H33 `h33-h33-2-b2` bytes are useful **for learning only**, never as an input or template for this lane. A fresh owner-repository source audit found that the current GEMSDOE32 owner audit calls this exact H33-2-B2 file **UNSCORED** and labels 0.2747 as a projection, while the owner page identifies the 0.2708 base as the already-scored fallback. Its manifest contains no organizer receipt for H33-2-B2. Thus the user-supplied 0.2778 cannot be attributed to these bytes from verified evidence. The measured structure is a sparse catalogue-flank removal from an existing field, not proof of a new geological discovery. See [the source audit](reports/h33-owner-source-audit-2026-10-20.md) and [the owner audit JSON on GitHub](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json).

## Candidate research queue (not implemented in this review)

The lane's ranked, in-scope hypotheses are documented in [Hypotheses](docs/hypotheses.html): (1) opposing-margin relay-link profile phase, (2) releasing-basin margin asymmetry, (3) en-échelon scarp phase coherence, and (4) matched-flank radiometric contrast reversal. All require a fresh preregistration, feature-alone leakage canaries, untouched spatial blocks, a literal pre-placement registry scan, and an identical post-placement scan. None is a score projection or slot authorization.

## Reproduce the publication audit

```sh
python scripts/release_gate.py
python scripts/build_site69.py
python scripts/build_readme.py
```

For format validation and tests, create an ignored environment and install the declared dependencies:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
GEMS_DATA="$PWD/data/bridge" PYTHONPATH=vendor/template66:src   .venv/bin/python scripts/validate_submission.py   submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-zeros.tif
PYTHONPATH=vendor/template66:src .venv/bin/pytest -q
```

`data/bridge/` is a small, integrity-pinned mirror sufficient for local format checks, not the full authenticated competition stack. A fresh scientific run requires restored pinned mirrors plus a complete registry and still must obey the literal duplicate-and-stop rule.

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
