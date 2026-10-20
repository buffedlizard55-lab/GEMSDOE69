# Lane 69 agent protocol (parallel-run protocol, verbatim intent)

**Start every session:** read README.md, PROJECT_REQUEST.md and HANDOFF.md. Current evidence is quarantined. The legacy unique generator is retired; all model work is preflight-blocked after the recorded literal stop. Source research, validators, tests and negative-result publication remain available.

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

## Historical reproduction commands — blocked under current review

Use only the safe audit sequence in HANDOFF.md for now. The model commands below are retained historical context, not permission to bypass preflight.

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


## Latest integrity correction — 2026-10-20

- `scripts/release_gate.py` is the sole publication policy; dotlike stratification cannot override literal measurements. Numeric evidence and phase contradictions are checked, not just pass flags.
- `generate_unique_submission.py` formerly could synthesize missing canaries, borrow a holdout, and hard-code validator success. It is retired; never restore that behavior or rebind its archived claims.
- Full-catalogue flank masks and the older full-catalogue canary violate visible-only holdout derivation. No current HOLDOUT-DTI is certified.
- Official public source pages were reachable via the research fetch tool, despite shell-host limits. Use the claim-level verified source registry; do not repeat blanket claims that public pages cannot be read. Authenticated data/submissions still redirect to login.
- Attribute mirrors contain DIPDIRECT/SLIPSENSE; production integration/authentication is the gap. Same strike is not same dip, and unsigned overlap is not releasing slip sense.
- A fresh universal-support counterexample proves the literal nonempty-field gate cannot pass under the current registry/support definition. Preserve that stop; do not silently reinterpret it or waste a slot.


## Holdout and selector gates (2026-10-20 continuation)

A release-eligible artifact requires a versioned HOLDOUT-DTI evaluator, a positive
paired 95% bootstrap CI against both the no-prior control and current lane-best,
and a SHA-bound protocol audit proving whole-segment withholding, no chunking,
≥3 px withheld-context buffer, visible-only catalogue features, pixel-exact
visible-fault masking, and pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
The artifact receipt must be classified `SUBMISSION-RECEIPT` and bind the exact
TIFF bytes. Passing these gates only makes a candidate eligible for the separate
selector; it does not select a submission or spend a slot.

The historical `scripts/run_exp2b_transfer.py` gate and emitter are deliberately
blocked: they use chunked, unbuffered `build_holdout()` and cannot qualify or
emit a new TIFF. Keep the guard until a newly authorized runner uses the shared
buffered evaluator and both literal uniqueness phases pass.
