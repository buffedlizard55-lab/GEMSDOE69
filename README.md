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
