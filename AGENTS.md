# Lane 69 agent protocol (parallel-run protocol, verbatim intent)

1. LANE. Relay-ramp and pull-apart corridor generator: faults proposed from
   catalogue geometry (tip graph), not pixel statistics. Stay inside it.
   Duplicate check vs registry: Spearman rho > 0.90 or > 70 % of dots within
   3 px of one registry raster = duplicate; log and stop. Check on the surface
   before placement AND on the final dots.
2. REUSE. Shared template lives in vendor/template66 (GEMSDOE66 src/gems57 +
   src/gems, byte-pinned; see vendor/template66/TEMPLATE_SHA256.txt). Fix
   shared tools once, report them; never fork privately. Known drift resolved
   this session: GEMSDOE63's vendored gems57/grid.py carried an unrepinned
   REPO_ROOT fix; we restored the pinned bytes and pass data_dir explicitly.
3. LABEL EVERY NUMBER. HOLDOUT-DTI (evaluator version, n withheld positives,
   95 % CI) or ORGANIZER-CONFIRMED (submission-page receipt). Leaderboard
   values cited in the prompt are USER-REPORTED-NOT-ORGANIZER-CONFIRMED.
4. LEAKAGE CANARY. AUC > 0.90 for any single feature on the holdout = leakage
   until proven otherwise (evidence/e1_canaries.json).
5. RUN CARD. One JSON card at evidence/run_card.json + docs/run-card.html.
6. BUDGET. 3 experiments or 2 hours. Do not spend submission slots; promotion
   is a separate selector step.

## Data provenance (fail-closed)

* Competition mirrors restored by `scripts/fetch_data.py` from
  `registry/data_manifest_gemsdoe32.json`; every file sha256-verified on
  arrival. Provenance: owner-supplied public mirrors of login-walled
  DrivenData files; integrity-pinned, NOT organizer-authenticated.
* Registry rasters restored by `scripts/fetch_registry.py` from
  `registry/prior_rasters.json` (751 unique git blobs, family census
  2026-10-11); every blob verified content-addressed (git blob sha1).

## Reproduce

    python3 scripts/fetch_data.py
    python3 scripts/fetch_registry.py
    PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py verify
    PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e1
    PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e2
    PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py e3
    PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py unique
    .venv/bin/python scripts/build_site69.py
