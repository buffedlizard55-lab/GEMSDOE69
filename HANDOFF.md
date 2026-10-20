# Handoff — 2026-10-20 (post-merge of parallel sessions)

Read README.md and PROMPT.md first, then reports/relayfix-2026-10-20.md.

## State: NEGATIVE — DO NOT SUBMIT (fail-closed)

Two candidates exist in `submissions/`; neither is currently downloadable:

1. **H69-J joint** (38,669 dots) — promoted by a parallel session on main
   under a stratified dotlike-overlap policy (0.61). After this session's
   R1/R2 tip-graph repairs landed, its hash-bound method manifest and
   holdout binding are stale on this tree, so `release_gate.py` fails
   closed and the site builder revoked its download. To restore: re-run
   `scripts/generate_unique_submission.py` under the repaired geometry,
   re-run holdout + both uniqueness phases on untouched blocks, rebind
   evidence, then `release_gate.py` + builders.
2. **H69-H2 transfer-only** (36,325 dots) — the current run card records
   HOLDOUT-DTI pooled 0.007738, 95% CI [0.005732, 0.009743], versus control
   0.002148 and a format-valid zeros TIFF. A separate relay-fix screen records
   0.00847 versus v1 0.00635; do not collapse the distinct archived receipts.
   Both are local screens only. The candidate fails the literal registry-overlap
   gate (1.0 universal; 0.8497 worst dotlike; rho <=0.28). Negative; evidence
   in `evidence/relayfix_*`, `evidence/*_relayfix_20261020.json`, and the run card.

## Needed upstream

The standing user protocol now makes the literal all-registry rule controlling:
there is **no local stratified/dotlike exemption**. A protocol owner may clarify
how universal-support registry rasters should be scoped, but both artifacts stay
unsubmitted unless the written rule is explicitly changed and re-applied from
pinned bytes. Exp1 findings stand: H69-F subsurface and H69-G radiometric arms
are not established; Exp1 v1 emission is a logged duplicate. Tip-graph R1/R2
repairs are on the tree. No slot was spent; negative results are deliverables.

## Latest publication audit (same date, after inherited state)

Read `reports/publication-audit-2026-10-20.md`. Repaired a merge regression that
allowed dotlike-only diagnostics to override literal all-registry overlap.
The former regression test never supplied a dotlike overlap value; expanded it.
Current release reasons now include literal duplicate-and-stop plus stale
holdout/source bindings. Independently revalidated archived H69-J pixels;
`evidence/publication_audit_validator_20261020.json` passes. No new experiment,
TIFF, registry scan, or slot was used in this audit. The final merged verification
now has 105 passing tests. Do not treat prior-session public-page fetch claims as
independent verification this audit.

## Final provenance reconciliation

`evidence/run_card.json` remains the H69-H2 transfer-only record (its TIFF SHA-256
starts `b44d16ce`), while `release_gate.py` remains the fail-closed publication
policy for the legacy aggregate H69-J receipts. The gate's CLI is audit-only and
must not rewrite the run card. `write_card()` now refuses a holdout/receipt hash
mismatch, preventing the prior H69-J-over-H69-H2 overwrite failure.

The GitHub-source audit in `reports/h33-owner-source-audit-2026-10-20.md` resolves
the H33 attribution available in this checkout: owner materials label H33-2-B2
`UNSCORED`, call 0.274673... a projection, and provide no organizer receipt. The
user-supplied 0.2778 is therefore not attributed to those bytes or called
organizer-confirmed. H33 remains learning-only.
