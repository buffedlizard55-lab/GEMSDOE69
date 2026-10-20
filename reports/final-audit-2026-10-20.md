# Final three-pass audit — 2026-10-20

## Executive decision

**NEGATIVE — NOT OK TO SUBMIT.** No TIFF or ZIP is published for submission,
no new competition TIFF was generated in this review, and no DrivenData slot was
used. The literal registry dot-overlap rule is a duplicate-and-stop condition.
A locally format-valid archived file is not a substitute for uniqueness,
artifact binding, or organizer confirmation.

This report supersedes the pre-merge local final-audit wording where it described
H69-J as the run-card artifact. After reconciling current `main`,
`evidence/run_card.json` correctly remains the archived **H69-H2 transfer-only**
record; the generic release policy still evaluates legacy H69-J aggregate
receipts and stays fail-closed.

## Pass 1 — implementation and evidence audit

- Read the standing prompt, handoff, release gate, run cards, evidence receipts,
  template pins, site, and concurrent publication-audit reports.
- Rechecked the H33 premise against current public owner material through the
  GitHub API. The owner audit labels H33-2-B2 `UNSCORED`, calls
  `0.27467315976932155` a projection, and includes no organizer receipt. The
  evidence chain and byte anatomy are recorded in
  `reports/h33-owner-source-audit-2026-10-20.md`.
- Retained both archived local validator receipts: H69-J and H69-H2 transfer
  zeros TIFFs satisfy local byte-format checks. That validates neither
  scientific novelty nor a competition score.
- Reconciled the current transfer run card: its local **HOLDOUT-DTI** is
  `0.0077375314`, 95% CI `[0.0057316537, 0.0097434090]`, 22,641 withheld
  positives across 8 cells, and comparator `0.0021479254`. It is a local screen,
  not an organizer score. The same run card records literal 3-pixel registry
  overlap `1.0` (limit `0.70`) across 862 accessible hash-verified entries,
  so it is a negative duplicate-and-stop result.

## Pass 2 — policy and publication defects

- Confirmed and retained the strict rule: both literal registry checks are
  required. A favorable stratified/dotlike diagnostic cannot override a failed
  literal overlap check.
- Preserved the current-main fix making `python scripts/release_gate.py`
  audit-only: it cannot silently overwrite the H69-H2 run card with an H69-J
  summary.
- Added a second guard in `write_card()`: it refuses to rewrite
  `evidence/run_card.json` unless E2's holdout hash matches the E3 receipt
  artifact hash. A regression test covers this H69-J/H69-H2 failure mode.
- Rebuilt the README and Pages status from the strict policy. The banner says
  **NOT OK TO SUBMIT — DO NOT SUBMIT**, offers no download, and explicitly
  forbids uploading audit artifacts from `submissions/`.

## Pass 3 — documentation and request reconciliation

- Reconciled the README/site with the H69-H2 current run card while retaining the
  generic fail-closed release decision. This prevents an old aggregate receipt
  from being presented as the transfer candidate's evidence.
- Published four ranked, in-lane, **unimplemented** hypotheses with layers,
  signatures, off-catalogue rationale, novelty, named mimics, qualitative
  expected HOLDOUT-DTI effect, cost, and viability limits. The top proposal
  uses stationwise opposing-margin phase co-location, not H69-J's corridor-wide
  maxima, so it is a genuinely different future method.
- Corrected H33 pages and research pointers: the user-associated `0.2778` is
  not attributed to H33-2-B2 or called organizer-confirmed. The source audit is
  linked for manual review.
- Kept no public binary in `docs/downloads/`. Negative results remain visible,
  but no historical candidate is promoted.

## Verification executed after reconciliation

| Command | Result |
| --- | --- |
| `PYTHONPATH=vendor/template66:src .venv/bin/python scripts/release_gate.py` | **negative**, `download_enabled=false`; literal dot-overlap failure, unbound holdout, and stale method-source manifest are reported for the legacy aggregate artifact. |
| `GEMS_DATA=$PWD/data/bridge ... scripts/validate_submission.py` on H69-J zeros TIFF | **PASS**: SHA-256 `981beb5707bb9933a2cf24a615eed373dc7e7cab451954207097e1641f32eaa6`; float32, EPSG:32611, 3730×3292, range [0,1], no NaN inside footprint, 38,669 positives. Receipt: `evidence/final_audit_validator_h69j_2026-10-20.json`. |
| Same validator on H69-H2 transfer-only zeros TIFF | **PASS**: SHA-256 `b44d16ce3f9a456c2c5c1a0156a873fad89baf5f50716610886f6f5cb0ffb9c1`; float32, EPSG:32611, 3730×3292, range [0,1], no NaN inside footprint, 36,325 positives. Receipt: `evidence/final_audit_validator_transfer_2026-10-20.json`. |
| `.venv/bin/python scripts/audit_workspace.py` | **blocked** for a fresh root-data run: `training_features`, `labels`, `existing_faults`, `1m_DEM_links`, and `sample_submission` are absent from expected full-data paths. Receipt: `evidence/final_audit_workspace_2026-10-20.json`. |
| `PYTHONPATH=vendor/template66:src .venv/bin/python -m pytest -q` | **105 passed**; 18 upstream Rasterio `PendingDeprecationWarning`s only. |
| `git diff --check` | **PASS**. |
| Generated-site/no-binary assertions | **PASS**: status is negative; current run card stays H69-H2 (`b44d16ce…`); root/index/executive banners say NOT OK/DO NOT SUBMIT; `docs/downloads/` contains no `.tif`, `.tiff`, or `.zip` artifact. |
| Run-card overwrite guard | **PASS**: `scripts/make_run_card.py` exited 2 with an explicit unbound-holdout refusal; SHA-256 of the H69-H2 run card was unchanged. |

The two format passes deliberately are not promotion evidence. They prove only
that archived bytes satisfy the local validator. The H69-H2 run card remains
negative on literal uniqueness; the generic policy also fails closed, so neither
artifact is publishable.

## Current blockers and next action

1. The literal all-registry overlap check fails against universal-support
   rasters. The protocol owner must explicitly amend or clarify the written
   registry-support rule; do not relax it locally.
2. A future candidate needs restored, integrity-pinned full inputs and untouched
   spatial blocks. It must then generate fresh artifact-bound holdout,
   source-manifest, canary, pre-placement surface, and post-placement dot
   receipts.
3. Organizer-authenticated competition data and submission receipts are not
   available in this environment. Owner mirrors and owner pages are not
   organizer receipts.
4. A future run may use the shared template only after the duplicate stop is
   cleared; changing a filename or emitting another TIFF would not satisfy the
   stop rule.
