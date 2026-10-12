# HANDOFF — next session checklist (GEMSDOE69 lane)

Read `PROMPT.md` first (standing prompt, verbatim). Then:

## State at handoff (2026-10-12)

* Lane implemented: relay-ramp / pull-apart corridor generator (`src/gems69/`),
  byte-pinned shared template in `vendor/template66/` (sha256-verified).
* Data: sha256-pinned mirrors in `.cache/gems_data/` (re-fetch:
  `python3 scripts/fetch_data.py`); 751 registry blobs in `.cache/registry/`
  (`python3 scripts/fetch_registry.py`).
* Evidence: `evidence/verify_grid.json`, `evidence/e1_*` (census, hard-link
  recovery, canaries), `evidence/e2_gate.json`, `evidence/e3_receipt.json`,
  `evidence/e3_uniqueness.json`, `evidence/run_card.json` — check which exist;
  finish any that are missing (they are produced by
  `scripts/run_lane69.py e1|e2|e3|unique|card`).
* Site: `scripts/build_site69.py` regenerates `docs/` from evidence; the
  OK/DO-NOT-SUBMIT banner is generated from `e2_gate.json` + `e3_uniqueness.json`
  + the validator output — do not hand-edit the banner.

## Do first

1. `PYTHONPATH=vendor/template66:src .venv/bin/python scripts/run_lane69.py verify`
   — must PASS before anything else.
2. If `evidence/e2_gate.json` is missing or stale, run `e2` (≈30–40 min CPU),
   then `e3`, then `unique`, then `card`, then rebuild the site.
3. If the verdict is `promote-candidate`: the TIF is offered on the site with an
   OK banner. Promotion to a scored slot is a SELECTOR decision (weekly cap on
   the submission page) — the lane never submits itself.
4. If the verdict is `negative`: that is a deliverable — keep the evidence, log
   the reason in `FLAGGED.md`, and pick the next queued hypothesis
   (`docs/hypotheses.html`, ranked): H69-D radiometric K/Th corridor halos is
   the cheapest (data already pinned).

## Budget rule

3 experiments or 2 hours per session (protocol rule 6). Negative results are
deliverables. Never write a projection as a score.

## Known traps

* `.cache/` is git-ignored and snapshot-excluded: re-fetch after any fresh
  sandbox (fetch scripts are idempotent + hash-verified).
* The greedy allocator must receive the fold's own truth count on holdout and
  the cited |G|=12,691 prior for the final emission (see run card).
* The literal overlap gate fails closed against universal registry surfaces
  (IR-69-REG-01); use the stratified gate + surface Spearman, report literally.
