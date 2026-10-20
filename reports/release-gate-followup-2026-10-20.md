# Release-gate follow-up — 2026-10-20

## Decision

**NEGATIVE — DO NOT SUBMIT.** No new experiment, raster, registry scan, or competition slot was used in this continuation. The archived candidates remain audit-only and no TIFF/ZIP is published from `docs/downloads/`.

This continuation was made on the session's fixed branch after bringing it forward to the then-current `origin/main` commit `8c46ff2594ad1848932bb0749b167c30aad6eab3`. The existing mainline audit already enforced the literal all-registry duplicate stop; this follow-up closes additional science/provenance gaps rather than relaxing that rule.

## Three review passes

### Pass 1 — implement stricter fail-closed criteria

- `scripts/release_gate.py` now requires a versioned `HOLDOUT-DTI` evaluator, positive withheld-positive and cell counts, and positive paired-cell-bootstrap 95% CIs for both candidate-minus-no-prior-control and candidate-minus-current-lane-best. A positive flag or normal-approximation half-width alone is insufficient.
- It requires `evidence/e2_holdout_protocol_audit.json` to bind the exact candidate SHA-256 and evaluator, document whole fault segments (no chunking), at least a 3 px withheld-context buffer, visible-only catalogue features, pixel-exact visible-fault masking, pooled DTI with α=0.2, β=0.8 and the 300 m triangular kernel, and hash the reviewed evaluator sources.
- The local TIFF receipt must identify `evidence_class: SUBMISSION-RECEIPT`; this is an artifact receipt, not an organizer score. A gate pass is now `eligible_for_selector`, never a promotion or competition-slot decision.
- Hardened malformed JSON/nested fields and registry scan counts to fail closed. Added regression tests for missing/non-positive paired CIs, protocol fields/source hashes, receipt class, malformed/stale evidence, and the existing literal overlap rule.
- Blocked both commands in the historical `scripts/run_exp2b_transfer.py`: its `build_holdout()` path chunks fault branches and uses no withheld-context buffer, and its emitter could write another TIFF. The old implementation remains below the guard for audit. The legacy `scripts/build_site.py` CLI now delegates to the strict `build_site69.py`, and `scripts/status.py` uses the same release gate.
- Updated the method and irregularities pages, README builder, prompt addendum, and handoff to explain the added gates and keep the status visible.

### Pass 2 — inspect evidence and assumptions

- The mainline H69-J local receipt is bound to SHA-256 `981beb5707bb9933a2cf24a615eed373dc7e7cab451954207097e1641f32eaa6` and is classified `SUBMISSION-RECEIPT`; its local validator passes. The artifact is nevertheless blocked by the literal registry dot-overlap result (1.0), and this result cannot be overruled by a dotlike/comparable-budget stratum.
- Its archived `evidence/e2_gate.json` has `gate_passed=true` and `current_best_beaten=true`, but does **not** contain paired-cell-bootstrap 95% CIs against either the no-prior control or current lane-best. The archived repeated-cell normal-approximation half-width is not a substitute. It also lacks the new artifact-bound whole-segment protocol audit. The gate therefore refuses publication even before considering its literal duplicate stop.
- H69-H2 transfer-only is a distinct archived artifact (SHA-256 `b44d16ce3f9a456c2c5c1a0156a873fad89baf5f50716610886f6f5cb0ffb9c1`). The code-review record `evidence/relayfix_holdout_protocol_audit.json` shows that its legacy holdout split branches into chunks up to 12 px and has no withheld-segment context buffer. Its historical positive screen cannot clear the current protocol. The runner guard prevents accidentally repeating that evaluation or emission.
- A local format receipt is not an organizer-confirmed score. H33's 0.2778 remains user-reported and is not tied to an organizer receipt for the cited TIFF. The existing H33 source audit and hypotheses page remain the source for the full explanation, geological alternatives, and official/manual-review links.
- No external pages were refreshed in this continuation. Repository links are retained for manual review; no live leaderboard claim was added.

### Pass 3 — verification and release decision

- Focused release-policy suite: **37 passed**; final complete suite: **119 passed**, with 18 upstream rasterio pending-deprecation warnings.
- The release gate returns `negative`, `download_enabled=false`, and explicitly lists missing paired CIs, missing protocol audit, and the literal overlap failure.
- Site/README/status were regenerated from the strict gate (9 pages). The red `NOT OK TO SUBMIT — DO NOT SUBMIT` banner remains prominent. Independent file inventory found no TIFF or ZIP in `docs/downloads/` (a historical JSON metadata file is not a submission artifact).
- Local format validation passed for the archived H69-H2 TIFF (SHA-256 prefix `b44d16ce3f9a456c`) and H69-J TIFF (prefix `981beb5707bb9933`); these format passes do not clear science, protocol, or uniqueness gates.
- The compatibility `scripts/build_site.py` entrypoint successfully delegates to the strict site builder. `scripts/status.py` writes the same release-policy result. `git diff --check` passed.
- Pull-request actions are recorded below after repository operations.

## Remaining limitations / next safe work

- The gate's positive path is intentionally unachievable from the current receipts: a future authorized run must create exact-hash paired bootstrap evidence against both control and lane-best plus the source-hashed protocol audit. Do not reuse the historical transfer result as if it met those requirements.
- The literal 3 px threshold is controlling across all accessible indexed registry rasters. The current overlap firing requires stop; any change to the registry scope must come from the protocol owner, not a local stratified exception.
- The full feature stack is not available in this checkout, and no new holdout or TIFF was generated. The existing site lists four ranked, qualitative in-lane hypotheses, none validated in this continuation. No slot has been used.
- Existing public-source links are for manual review; the current continuation did not independently verify pages outside the network allowlist.
