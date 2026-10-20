# Lane 69 agent protocol (parallel-run protocol, verbatim intent)

1. LANE. Relay-ramp and pull-apart corridor generator: faults proposed from
   catalogue geometry (tip graph), not pixel statistics. Stay inside it.
   Duplicate check vs registry: Spearman rho > 0.90 or > 70 % of dots within
   3 px of one registry raster = duplicate; log and stop. Check on the surface
   before placement AND on the final dots (`evidence/e3_uniqueness.json`).
2. REUSE. Shared template lives in `vendor/template66` (GEMSDOE66 `src/gems57` +
   `src/gems`, byte-pinned; see `vendor/template66/TEMPLATE_SHA256.txt`). Fix
   shared tools once, report them; never fork privately.
3. LABEL EVERY NUMBER. HOLDOUT-DTI (evaluator version, n withheld positives,
   95 % CI) or ORGANIZER-CONFIRMED (submission-page receipt). Leaderboard
   values cited in the prompt are USER-REPORTED-NOT-ORGANIZER-CONFIRMED.
4. LEAKAGE CANARY. AUC > 0.90 for any single feature on the holdout = leakage
   until proven otherwise (`evidence/e1_first_test.json`).
5. RUN CARD. One JSON card at `evidence/run_card.json` + `docs/run-card.json`
   + `docs/run-card.html`.
6. BUDGET. 3 experiments or 2 hours. Do not spend submission slots; promotion
   is a separate selector step.

## Reproduce

```bash
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/restore_data.py
PYTHONPATH=src:vendor/template66 .venv/bin/python -c "from gems69 import data, evidence; evidence.build_cache(data.load_grid())"
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/run_lane.py e1
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/run_lane.py e2 --draws 2
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/build_submission.py
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/check_uniqueness.py
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/validate_submission.py docs/downloads/*.tif --json evidence/e3_validation.json
.venv/bin/python scripts/make_run_card.py && .venv/bin/python scripts/build_site.py && .venv/bin/python scripts/build_readme.py
PYTHONPATH=src:vendor/template66 .venv/bin/python -m pytest -q tests
```
