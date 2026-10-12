# Session log

## Session 2026-10-12 · branch `arena/18061ddd-gemsdoe69` (base `dfa2bb9`, `main`)

### What the repository contained at the start
Only `README.md` (one line: `# GEMSDOE69`). No template, no data scripts, no feature stack, no holdout code, no
prior rasters. The brief's "template" (IR-15) is not in this repo.

### Pass 1 — implement and verify
* Read the official pages: competition page 967 (S01), NLR Official Rules (S02), public leaderboard (S03),
  data page (S04, login-gated), rules page (S05), reference notebook (S06), GeoDAWN ScienceBase (S07),
  INGENIOUS DOI (S08, not resolving to data), Giddens & Faulds 2025 (S09), Faulds 2026 (S10), USGS QFD (S12).
* Read the owner's sibling repo GEMSDOE32 (S16) for claims, registry and data-provenance statements.
* Built `src/gems/metric.py` (DTI as published), `src/gems/validate_submission.py`, `src/gems/gate.py`,
  `scripts/status.py`, and tests.
* Measured the sibling's 0.2778 candidate file (analysis copy, not committed): EPSG:32611, 100 m,
  3292 × 3730, float32, binary, 37,654 ones. Both twins' sha256 match the sibling README.

### Pass 2 — review and fix
Bugs found and fixed in this pass:
1. The admission rule was first written as `Δt·(D − 0.8·T)`. The correct factor is `(1 − β) = 0.2`, so it is
   `Δt·(D − 0.2·T)`. The code and tests already used the correct form; the analysis document was corrected to
   match (`docs/research/0.2778-analysis.md` §2).
2. `index.html` linked to a page that does not exist (`leaderboard-check.html`). It now links to the markdown check.
3. The validator's footprint rule is an assumption (IR-07). It is written into the module docstring and into the
   receipt, so it is visible, and it is listed in the irregularities log.
4. Checked the sibling's hypotheses before ranking ours. Two of our draft candidates were already tested there: the dilatation-gated strain idea duplicates H32-B, and the magnetic-low corridor idea matches H32-5 (holdout 0.1383 vs 0.26, owner-reported). Both were removed from the ranking and listed as rejected, with evidence.
5. Checked the claim that the sibling's "UNSCORED" file matches the user's 0.2778 entry. It does not: the sibling
   never mentions 0.2778, and the board shows #24 `extradr19` with no file name (IR-03). The attribution is recorded
   as unverifiable, not corrected to any other value.

### Pass 3 — re-check against the brief (final)
| brief requirement | status |
|---|---|
| Put the prompt in the README and read it every session | Done (README "The mission"). Condensed; the duplicate blocks and the pasted leaderboard were removed. |
| Executive-summary page that explains how to submit, at the top of the site | Done (`docs/executive-summary.html`, linked from the site header and banner). |
| Downloadable TIF that is obvious to submit | **Not met.** No file is offered: the gate is BLOCKED (no official data, no holdout). The site says so at the top. |
| Unique name and short note | Format specified (executive summary; `gate.note_ok`, 140 chars). No file, so no name is issued. |
| Validator for the "[0,1]" error | Done (`validate_submission.py`), tested with 8 cases. The failing user file is not available (IR-13). |
| Explain why 0.2778 scored, and whether we can beat it | Done as far as the evidence allows (`0.2778-analysis.md`). Cannot beat it or prove it without labels. |
| 3–5 hypotheses, ranked, with layers, signature, overlap, cost | Done (`docs/research/hypotheses.md`). Four ranked, five rejected. |
| Validate the top candidate on the holdout before any slot | **Not run.** No labels. |
| Gate: beat the no-prior pipeline | **Not run.** |
| Run card | Done (`docs/run-card.json`). Verdict: no-promote, blocked. |
| Parallel-run lane check (correlation, overlap) | **Not run.** No raster. Textual overlap logged (IR-14). |
| Hash / pixel-agreement check against prior rasters | **Not run.** No candidate raster. |
| Irregularity log with links | Done (`docs/irregularities.md`, IR-01 … IR-25). |
| Every number labelled | Done. No number is a holdout score. |
| Pull request, then merge to main | Done. PR #1 merged (merge commit `e704246`). Pages: the API returned 403, so the source could not be set to `/docs`; PR #2 (`1609381`) adds a root redirect to `docs/index.html` so the Pages URL works. The Pages build for `main` completed. |

## Commands run and their results
* `PYTHONPATH=src pytest -q` (venv: Python 3.11.x, numpy 2.4.6, rasterio 1.4.4, pytest) — **25 passed**.
* `python -m gems.validate_submission` on the sibling NaN-twin file (analysis copy) — all hard checks **pass**;
  grid and footprint **not checked** (no reference). Exit code 0.
* `python scripts/status.py` — `gate.status = BLOCKED`, `download_enabled = false`, all official files missing.
* Reachability (curl): `earthquake.usgs.gov`, `doi.org`, `sciencebase.gov`, `dropbox.com`, `usgs.gov`,
  `gdr.openei.org`, `epsg.io`, `drivendata.org` data — blocked or login. GitHub, PyPI and the GitHub API — reachable.

## Decisions (and why)
1. **No download offered.** The gate cannot be evaluated. A file without a holdout result would be a guess, and the
   brief says to offer a download only when the gate is met.
2. **Owner GitHub mirrors of the competition data were not used** (IR-09). They are not organizer bytes, their
   licensing is unclear, and the owner's own repo calls them unauthenticated. The sibling data is never committed here.
3. **Own minimal tools instead of a template fork** (IR-15). Nothing from the template exists here, so the tools
   are small and tested, and they follow the organizer's formulas exactly.
4. **Verdict is "no-promote (blocked)"**, not "negative". A negative result needs an evaluated gate.
5. **Lane kept, risk flagged.** The relay-ramp lane is in the brief, but the sibling has already falsified its
   closest variant (IR-14). The top hypothesis is a different lane (H-P).

## Next steps (ordered)
0. **Owner action:** set Pages source to `main` / `/docs` (the token cannot). The root redirect works until then.
1. **Owner action:** log in at DrivenData, accept the rules, and place the official files in `data/`
   (`data/README.md`). Record their names and sha256 (IR-04).
2. **Owner action:** send the file that failed "Predicted values must be in range [0, 1]" (IR-13).
3. **Owner action:** ask for the DrivenData receipt for the 0.2778 file (IR-03), and check the mirror question (IR-09).
4. **Agent, next session:** run `scripts/status.py`. If the data is present, build the H-P features from visible
   faults only, the spatially blocked holdout, the leakage canary, the no-prior baseline, and the gate.
   Budget: E1 = H-P vs baseline; E2 = E1 + H-M admission; E3 = H-B vs baseline. Write the receipt to `docs/receipts/`.
5. **Agent:** when a candidate exists, run `validate_submission.py` with the official reference grid, the hash and
   pixel-agreement check against every prior raster, and the lane correlation check (0.90 and 70% thresholds).
6. **Agent:** verify the rest of the S09 body (the length-to-width ratio, the WNW stress claim) before citing them (IR-20, IR-21).

## Limits and suggestions for the project
* **The official data is the bottleneck.** Without it, nothing in the pipeline can be tested for real. Ask the operator
  whether the official download hosts (drivendata data, dropbox, usgs.gov, doi.org, openei, epsg.io) can be
  allow-listed, or accept manual placement (IR-12).
* **The public board is not the target.** Phase 1 uses the private set; Phase 2 uses an updated set (IR-17).
  Track both the public board and the holdout.
* **The 0.2778 figure should be replaced by the receipt.** Until then, label it OWNER-REPORT, not a score.
* **Metric identity is a useful lever.** `DTI = T/(0.2T + 0.2FP + 0.8|G|)` means the emission rule is the main
  control. Use `dot_is_worth_adding` as the greedy admission test; check it against the holdout, not the public board.
* **Scorer assumptions need the organizer.** Two are unverified: that catalogue pixels are masked (IR-25), and
  that zero-filled outside-footprint cells are acceptable (IR-08).
* **Generative-AI disclosure** is required by the rules (IR-16). The owner completes it; the run card has a placeholder.
