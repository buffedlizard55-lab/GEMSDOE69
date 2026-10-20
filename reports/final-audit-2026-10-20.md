# Final three-pass audit — 2026-10-20

## Executive decision

**NEGATIVE — NOT OK TO SUBMIT.** No new TIFF was generated or offered for
download in this review, and no competition slot was used. The literal
registry dot-overlap rule is a duplicate-and-stop condition. A format-valid
archived TIFF is not a substitute for that clearance.

## Pass 1 — implementation and evidence audit

- Read the standing prompt, handoff, run card, release gate, evidence receipts,
  template pins, current site, and historical artifacts.
- Rechecked the H33 premise against the current public owner repository with
  GitHub's API. The owner audit labels H33-2-B2 `UNSCORED`, labels 0.2747 a
  projection, and includes no organizer receipt. The source chain is recorded
  in `reports/h33-owner-source-audit-2026-10-20.md`.
- Confirmed the current artifact is locally format-valid in its archived
  receipt but that the holdout binding and source manifest are stale.

## Pass 2 — policy and publication defects

- Found that `scripts/release_gate.py` still allowed a stratified dotlike
  diagnostic to override a failed literal overlap gate. That contradicted the
  standing prompt and `AGENTS.md`.
- Replaced the exception with a strict requirement that both literal registry
  checks pass. The diagnostic is retained in the release reason but cannot
  enable a download.
- Strengthened the regression test so an actually qualifying stratified
  diagnostic cannot make a literal failure pass.
- Regenerated the run card and site. The banner now says that no TIFF or ZIP is
  published and explicitly forbids uploading audit artifacts.

## Pass 3 — documentation and review

- Rebuilt README and Pages content from the strict release decision.
- Marked stale H33 and pre-repair hypothesis pages as archived or replaced them
  with current pointers, removing the appearance that a projection is an
  organizer score.
- Published four ranked, in-lane hypotheses with layers, signatures,
  off-catalogue rationale, novelty, named mimics, cost, and viability limits.
  None is implemented because the duplicate stop is already active.
- Replaced the obsolete direct `why-0278` page and pre-repair research
  registers with archival pointers so they cannot be mistaken for current
  score attribution or a live experiment plan.

## Verification executed after Pass 3

| Command | Result |
| --- | --- |
| `PYTHONPATH=vendor/template66:src .venv/bin/python scripts/release_gate.py` | **negative**, `download_enabled=false`; literal dot-overlap failure, unbound holdout, and stale method-source manifest are each reported. |
| `GEMS_DATA=$PWD/data/bridge ... scripts/validate_submission.py` on H69-J zeros TIFF | **PASS**: SHA-256 `981beb5707bb9933a2cf24a615eed373dc7e7cab451954207097e1641f32eaa6`; float32, EPSG:32611, 3730×3292, range [0,1], no NaN inside footprint, 38,669 positives. Receipt: `evidence/final_audit_validator_h69j_2026-10-20.json`. |
| Same validator on transfer-only zeros TIFF | **PASS**: SHA-256 `b44d16ce3f9a456c2c5c1a0156a873fad89baf5f50716610886f6f5cb0ffb9c1`; float32, EPSG:32611, 3730×3292, range [0,1], no NaN inside footprint, 36,325 positives. Receipt: `evidence/final_audit_validator_transfer_2026-10-20.json`. |
| `PYTHONPATH=vendor/template66:src .venv/bin/python -m pytest -q` | **102 passed**; 18 upstream Rasterio `PendingDeprecationWarning`s only. |
| `.venv/bin/python scripts/audit_workspace.py` | **blocked** for a fresh root-data run: `training_features`, `labels`, `existing_faults`, `1m_DEM_links`, and `sample_submission` are not placed at the expected full-data paths. Receipt: `evidence/final_audit_workspace_2026-10-20.json`. |
| `git diff --check` | **PASS**. |
| Published-binary check | **PASS**: `docs/downloads/` contains no `.tif`, `.tiff`, or `.zip`; only an audit JSON and `.gitkeep` remain. |

The two format passes are deliberately not promotion evidence. They prove only
that archived bytes satisfy the local validator; the release gate still blocks
them. The updated `evidence/run_card.json` is the required negative JSON run
card and now labels its holdout fields as archived/unbound.

## Current blockers and next action

1. The literal all-registry overlap check fails against universal-support
   rasters. The protocol owner must define a meaningful registry support rule
   or amend the written rule; do not relax it locally.
2. A future candidate requires restored, integrity-pinned full inputs and
   untouched spatial blocks. It must then generate fresh hash-bound holdout,
   source-manifest, canary, and two-phase registry receipts.
3. Organizer-authenticated competition data and submission receipts are not
   available in this environment. Owner mirrors and owner pages are not
   organizer receipts.
