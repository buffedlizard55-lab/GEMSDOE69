# GEMSDOE69 — GEMS Prize (DOE) fault-prediction project

> **Read this section first, every session.** It is the standing brief for this repository.
> Last updated 2026-10-12. Condensed from the session prompt; the duplicated paste blocks and the pasted
> leaderboard dump were removed (the leaderboard is in [docs/leaderboard-2026-10-12.md](docs/leaderboard-2026-10-12.md)).

## Status at a glance

| item | state |
|---|---|
| Downloadable submission TIF | **Not offered.** Gate BLOCKED (see below). |
| Official training data in this checkout | **No.** Login-gated at DrivenData (IR-11). |
| Holdout DTI | **Not measured.** No labels, so no holdout. |
| DTI metric, validator, gate | Implemented and tested (`pytest`: 25 pass). |
| Explanation of the 0.2778 figure | Done: [docs/research/0.2778-analysis.md](docs/research/0.2778-analysis.md). The 0.2778 score is **not** the top score, and it cannot be linked to its file (IR-01, IR-03). |
| Executive summary (how to submit) | [docs/executive-summary.html](docs/executive-summary.html) |
| GitHub Pages site | [docs/index.html](docs/index.html) — https://buffedlizard55-lab.github.io/GEMSDOE69/ |
| Run card | [docs/run-card.json](docs/run-card.json) (verdict: no-promote, blocked) |
| Irregularities for review | [docs/irregularities.md](docs/irregularities.md) |

## The mission

**Goal.** Place at the top of the DrivenData GEMS Prize leaderboard (competition 306). The organizer's problem is to
predict **faults** that are indicative of geothermal resources in the GeoDAWN region
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). The score is a distance-weighted
Tversky index (α = 0.2, β = 0.8, R = 300 m, triangular kernel). The submission is a single-band float32 GeoTIFF
in EPSG:32611 at 100 m, values in [0, 1], NaN outside the footprint.

**What the project must do.**
1. Understand the problem, collect the data and keep it in an auditable table with official links.
2. Build and train a model; generate predictions that match the submission format.
3. Generate a **unique** submission that is easy to download and submit. It must be obvious on the site whether
   the file is safe to download and submit. Give it a unique name and a short note (≤140 characters).
4. Explain how to make a submission on an executive-summary page.
5. Research the science (geothermal favourability, step-overs and relay ramps, pull-aparts, displacement transfer
   zones, strain and gravity signatures). Propose and test hypotheses that the catalogue does not already contain,
   and record the sources for manual review.
6. Hypothesis discipline: name the layer(s), the physical signature, why the method finds a fault missing from the
   USGS/INGENIOUS catalogue, and how it differs from work already in the repo. Rank by expected DTI improvement
   and implementation cost. Validate the top candidate on the spatially blocked holdout **before** touching a
   submission slot.
7. Gate: a file is offered for download **only if** the candidate beats (a) the same pipeline without corridor or
   prior features and (b) the current holdout best. Otherwise log the negative result and do not offer the file.

**Rules for every number and claim.**
* Verify line by line against official, trusted sources, and link them for manual review.
* No hallucinations. Anything not checked is labelled NOT READ, BLOCKED or UNVERIFIED.
* Label every score as one of: `HOLDOUT-DTI` (evaluator version, number of withheld positives, 95% CI),
  `ORGANIZER-CONFIRMED` (copied from a submission-page receipt), `OFFICIAL-LEADERBOARD` (public board, team level),
  `OWNER-REPORT`, `MEASURED`, `DERIVED`, or `OPINION`. A projection is never written as a score.
* Flag every irregularity. No manual input in the pipeline; the owner runs the scripts, not the agent.
* Reuse shared tools; if a shared tool is wrong, fix it once and report it. Do not keep private forks.
* Keep competition data, large datasets and mirrors out of git (`.gitignore`).

**Parallel-run protocol (when several sessions share this prompt).** Stay in your method lane. If a raster's rank
correlation with any registry raster exceeds 0.90, or more than 70% of its dots fall within 3 px of one registry
raster's dots, log it as a duplicate and stop. Check on the surface before placement and on the final dots.
Budget: 3 experiments or 2 hours. Do not pick the weekly submission slot; promotion is a separate selector step.

**Core values (adopted for this project).**
* *Maximize P(Win)* — in every decision, weigh trade-offs and risk and choose the path that maximizes the
  probability that the project succeeds.
* *Own the Outcome* — own results end to end, act on problems when you can, and treat failure and success as signals.

**Session discipline (three passes).** Pass 1: implement and verify. Pass 2: review for bugs, missing
requirements and wrong assumptions, and fix them. Pass 3: re-check the whole result against this brief. Before
finishing, verify that the output meets the brief.

## Submission — quick path

1. Register on DrivenData and accept the rules. Put the official files in `data/` (see [data/README.md](data/README.md)).
2. `python scripts/status.py` — shows whether the gate allows a download.
3. Produce the raster; validate it:
   `python -m gems.validate_submission submission.tif --reference data/training_features.tif --json receipt.json`
4. Upload it on the competition's "New submission" page with a unique name and a note ≤140 characters.

Full steps and troubleshooting: [docs/executive-summary.html](docs/executive-summary.html).

## Repository layout

| path | purpose |
|---|---|
| `src/gems/metric.py` | DTI as published (distance-weighted Tversky), plus the exact dot-admission rule |
| `src/gems/validate_submission.py` | Checks a GeoTIFF against the organizer's format rules |
| `src/gems/gate.py` | Download gate: BLOCKED / NEGATIVE / OFFER_DOWNLOAD |
| `scripts/status.py` | Writes `docs/status.json` (official-data presence + gate) |
| `tests/` | 25 tests: metric vs brute force, admission rule vs recomputation, validator cases, gate |
| `docs/` | GitHub Pages site, sources, irregularities, research, run card, session log |
| `data/` | **Not committed.** Official competition files go here. |

## Install and test

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

## Documents

* [docs/index.html](docs/index.html) — site home (status, hypotheses, flags)
* [docs/executive-summary.html](docs/executive-summary.html) — how to submit
* [docs/sources.md](docs/sources.md) — every source, with VERIFIED / BLOCKED / FLAG status
* [docs/irregularities.md](docs/irregularities.md) — flags for review (IR-01 … IR-25)
* [docs/leaderboard-2026-10-12.md](docs/leaderboard-2026-10-12.md) — official board check
* [docs/research/0.2778-analysis.md](docs/research/0.2778-analysis.md) — why the sparse-dot file scores as it does, and what can be said
* [docs/research/hypotheses.md](docs/research/hypotheses.md) — ranked hypotheses, rejections, validation plan
* [docs/run-card.json](docs/run-card.json) — run card for the current state
* [docs/session-log.md](docs/session-log.md) — what was done, decisions, next steps, limits
