# Handoff — 2026-10-20 (post-merge of parallel sessions)

Read README.md and PROMPT.md first, then reports/relayfix-2026-10-20.md.

## State: NEGATIVE — DO NOT SUBMIT (fail-closed)

Three candidate TIFFs now exist in `submissions/`; none is currently downloadable:

1. **H69-J joint** (38,669 dots) — a parallel session later rebound its local
   holdout and method-source receipts, but this does **not** permit publication:
   literal all-registry 3-pixel overlap is 1.0 (limit 0.70). Earlier
   stratified-dotlike promotion language is superseded by the standing literal
   duplicate-stop rule. Its local format and HOLDOUT-DTI records remain audit
   evidence only; no download is permitted.
2. **H69-H2 transfer-only** (36,325 dots) — the current run card records
   HOLDOUT-DTI pooled 0.007738, 95% CI [0.005732, 0.009743], versus control
   0.002148 and a format-valid zeros TIFF. A separate relay-fix screen records
   0.00847 versus v1 0.00635; do not collapse the distinct archived receipts.
   Both are local screens only. The candidate fails the literal registry-overlap
   gate (1.0 universal; 0.8497 worst dotlike; rho <=0.28). Negative; evidence
   in `evidence/relayfix_*`, `evidence/*_relayfix_20261020.json`, and the run card.
3. **H69-J joint repair** (39,958 dots; SHA-256 `287372cb3fc6d7b8bcdb6bffbf5632d92a8d1d2e0dee6c2fb884d74d10d923f4`) — added to `submissions/` by merged PR #26. Its TIFF passes the local format validator, but the current receipt, method manifest, holdout, and uniqueness evidence are still bound to the separate 38,669-dot SHA `981beb...`; the 39,958-dot artifact has no artifact-bound receipts or literal two-phase scan. PR #26's body reported 751 registry-fetch errors for it. Audit-only; not downloadable.

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
Current strict release reason is literal duplicate-and-stop. H69-J's later
local evidence rebinding does not override the 1.0 literal overlap. Independently
revalidated archived H69-J pixels; `evidence/publication_audit_validator_20261020.json`
passes. No new experiment, TIFF, registry scan, or slot was used in this audit.
The final merged verification now has 106 passing tests. Do not treat
prior-session public-page fetch claims as independent verification this audit.

## Final provenance reconciliation

`evidence/run_card.json` remains the H69-H2 transfer-only record (its TIFF SHA-256
starts `b44d16ce`), while `release_gate.py` remains the fail-closed publication
policy for the separate H69-J aggregate receipts. The gate's CLI is audit-only
and must not rewrite the run card. `write_card()` now refuses an E2/receipt hash
mismatch and, by default, refuses to replace an existing card that identifies
other bytes; an explicit artifact-bound replacement is required. This prevents
the prior H69-J-over-H69-H2 overwrite failure.

The GitHub-source audit in `reports/h33-owner-source-audit-2026-10-20.md` resolves
the H33 attribution available in this checkout: owner materials label H33-2-B2
`UNSCORED`, call 0.274673... a projection, and provide no organizer receipt. The
user-supplied 0.2778 is therefore not attributed to those bytes or called
organizer-confirmed. H33 remains learning-only.

## Strict release-gate continuation — 2026-10-20

The release gate now also fails closed unless HOLDOUT-DTI has a versioned
evaluator, a positive paired 95% bootstrap CI against both the no-prior control
and current lane-best, and a SHA-bound protocol audit confirming whole-fault
withholding without chunking, at least 3 px of withheld-context buffer,
visible-only catalogue features, pixel-exact masking, and pooled DTI
(α=0.2, β=0.8, 300 m triangular kernel). The TIFF receipt must be explicitly
classified `SUBMISSION-RECEIPT`; that is a local artifact receipt, not an
organizer score. A passing result is `eligible_for_selector`, not a promotion
or a slot decision.

The current H69-J receipt has a local `SUBMISSION-RECEIPT` and a HOLDOUT-DTI
record, but no paired bootstrap intervals or artifact-bound protocol audit;
its literal registry dot overlap also fails. The H69-H2 transfer runner's
separate code review (`evidence/relayfix_holdout_protocol_audit.json`) found
chunked segments and no withheld-context buffer. Its legacy `cmd_gate` and
`cmd_emit` are now deliberately blocked. Neither candidate is downloadable;
no experiment or slot was used in this continuation. See
`reports/release-gate-followup-2026-10-20.md` for tests and review notes.
