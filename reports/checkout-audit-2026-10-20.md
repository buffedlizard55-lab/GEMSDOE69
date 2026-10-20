# Checkout review — 2026-10-20

## Decision

**NEGATIVE — do not download or submit an archived TIFF.** No new scientific experiment, candidate raster, or competition submission was created in this review. The publication gate currently denies downloads. This honors the duplicate-stop rule rather than manufacturing a nominally unique file or treating a format-valid file as scientifically/release qualified.

## Three review passes

### Pass 1 — repository and status

- Read `PROMPT.md`, `README.md`, `AGENTS.md`, `HANDOFF.md`, `reports/review-2026-10-20.md`, the release gate, runner, site generator, validator, evidence, and relevant tests.
- Current branch is `arena/6792a3b3-gemsdoe69`; the checkout initially had no working-tree changes.
- `python scripts/release_gate.py` returns `verdict=negative`, `download_enabled=false`. The principal blockers are: no same-evaluator comparison against the current holdout best; literal uniqueness overlap gate failed; registry scan did not compare all entries; missing artifact-bound method manifest/canaries; and missing/current-artifact-mismatched surface and dot uniqueness phases.
- The aggregate uniqueness receipt describes 750/751 rasters compared, with one shape error. Its literal overlap gate is false. The stratified dotlike diagnostic is not a substitute under the project's explicit protocol.
- The archived TIFF's hash-bound validator receipt is internally positive, but format compliance alone is not a promotion criterion. The candidate's reported HOLDOUT-DTI belongs to an earlier run, not a new result from this checkout review.

### Pass 2 — executable checks and edge cases

- Created an ignored local `.venv`, installed declared requirements and pytest, and ran `.venv/bin/pytest -q`: **89 passed, 1 xfailed, 18 rasterio deprecation warnings**. The expected failure documents the known interval-gap geometry defect; it is not a pass for that requirement.
- Ran `scripts/validate_submission.py` on the archived all-finite TIFF. Without `GEMS_DATA`, it failed because the default `/tmp/gems_data/existing_faults.tif` is absent. Re-running with `GEMS_DATA="$PWD/data/bridge"` passed for `submissions/h69-z-radiometric-halo-31994-20261020T182654Z-31913c0c-zeros.tif` (SHA-256 `be84d6fa9efc3ec85f9532d5574e98a4e77c587db7be3d50a9392924917c78c7`). This is a local format result only, not organizer acceptance or a score.
- `scripts/audit_workspace.py` reports the full feature stack, five canonical competition inputs, and GPU are absent. It also finds `scripts/download_competition_data.sh` and `scripts/prepare_data.py` are absent in this checkout. That conflicts with older README/PROMPT boilerplate describing those exact steps as available; the current executable audit is the more specific evidence. The bridge rasters that are present do not constitute the full training feature stack or authenticated organizer download.
- Existing geometry implementation has known limitations recorded in the previous review: the interval-window condition can admit overlong gaps; Euclidean tip search can miss otherwise valid pairs; and catalogue geometry has no measured dip polarity/slip sense to establish same-dip/dextral releasing relationships. Do not silently repair and reuse old performance evidence; repair, preregister, and rerun first.

### Pass 3 — request reconciliation and recommendation

- The four queued ideas are already catalogued in `docs/hypotheses.html`. Top qualitative priority is multi-scale gravity/magnetic relay-link edge phase; it must not be implemented or scored until release stops are resolved. Candidate ranking/cost and geological mimics are described there. The radiometric contrast idea has unresolved provenance and should remain deferred.
- Why the cited H33 value may be high is discussed at `docs/why-h33-scored.html`: sparsity can improve precision under a DTI-style objective while retaining coverage, but this is a plausible mechanism, not proof of cause or a forecast. `0.2778` and the conflicting `0.3195`/`0.3774` leaderboard context are user/family-reported, not organizer-confirmed receipts in this checkout.
- No reliable claim that this project beats those values is justified. Do not make or publish another TIFF while the strict duplicate stop is in force. In particular, do not use superficial file/hash uniqueness to evade the raster-correlation/dot-overlap gate.

## Review conclusions / next work

1. Recover a provenance-complete, hash-pinned feature stack and confirm input identities against authenticated competition data; the local owner mirrors are not organizer-authenticated.
2. Reconcile the missing download/prepare scripts with the current README and handoff before advertising a reproducible end-to-end pipeline.
3. Correct geometry defects in the shared template, not a private fork; require measured dip/slip attributes before asserting same-dip dextral releasing geometry.
4. Re-run the lane from a frozen preregistration on untouched spatial blocks. Run feature-alone leakage checks first, then pooled HOLDOUT-DTI with spatial-block bootstrap CI against both the no-corridor control and the current best.
5. Perform complete registry checks on the pre-placement surface and final dots against a clearly agreed registry corpus. Do not replace the literal gate with stratified diagnostics.
6. Only after all gates pass, write the float32 submission, validate its exact bytes, bind all receipts to artifact and source hashes, regenerate the site, and then consider a separate slot-selection decision.

## Source/verification limits

No external scientific source was fetched during this checkout review. The official links and the verification/access status are recorded in `reports/review-2026-10-20.md` and `docs/sources.html`; the Giddens & Faulds statistics originated in the prompt and remain unverified locally. Competition data access remains login-walled in this environment. No current leaderboard result or organizer confirmation is claimed.
