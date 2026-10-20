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

## 2026-10-20 correction — overrides earlier stratified-gate guidance

The literal protocol is mandatory. A failed overlap check is duplicate-and-stop;
stratification is diagnostic only. `scripts/release_gate.py` is the single
publication policy. Read `reports/review-2026-10-20.md` and the updated handoff.
Do not reuse the previous radiometric promotion verdict: the scoring source is
not reproducible from the checked-in implementation and phase receipts are stale.

## 2026-10-20 session 3 — candidate binding, instrument fix, resource rule

* **Instrument fix (IR-69-HOLD-01, high).** Any holdout runner must build the
  flank-prune / allowed mask from the *visible* catalogue of the cell, never from
  `g.catalogue` (which contains the withheld truth). All archived HOLDOUT-DTI values
  from `run_relayfix_20261020.py`, `run_exp2b_transfer.py` and the e2 runner are biased
  low and are not comparable with later numbers. Use `scripts/run_h69m.py` /
  `scripts/run_h69n.py` as the reference pattern.
* **Release binding.** `evidence/current_candidate.json` (written by
  `scripts/write_candidate_manifest.py h69m|h69n|none`) switches
  `scripts/release_gate.py` to the session-candidate path; every check is bound to the
  artifact SHA-256, the emitted surface hash and the method-source hashes. Delete the
  file only to fall back to the archived H69-J path (which fails closed).
* **Overlap policy divergence (needs one human ruling).** The 2026-10-20 correction
  above says the literal overlap reading is mandatory. The H69-M/H69-N
  preregistrations (frozen before any holdout look) instead gate on: Spearman <= 0.90 vs
  every raster; forward 3 px overlap <= 0.70 vs every dot-field raster (template
  `two_phase_summary` like-for-like) AND vs the rank-matched top-K pixels of every
  non-binary continuous surface; identity none. The literal number is always reported.
  Under the literal reading no sparse raster can pass (a whole-footprint surface
  "contains" every dot). If a candidate ever clears every other gate, surface this
  divergence to the user before publishing.
* **Resources.** The sandbox has ~3.9 GB RAM. Never run two processes that load the
  z-stack (`load_inputs()`) at the same time: on 2026-10-20 this triggered the OOM
  killer and took down a running gate (it resumed from `gate_partial.json`).
