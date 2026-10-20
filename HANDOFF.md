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
2. **Transfer-only** (36,325 dots, this session) — passes science gates
   (HOLDOUT-DTI pooled 0.00847 vs v1 0.00635 vs control 0.00215) and format
   validation, fails the literal registry-overlap gate (1.0 universal;
   0.8497 worst dotlike; rho <=0.28). Negative; evidence in
   `evidence/relayfix_*` and `evidence/*_relayfix_20261020.json`.

## Needed upstream

One selector ruling on overlap policy: literal (this session) vs
stratified dotlike (H69-J session). Until then both stay unsubmitted.
Exp1 findings stand: H69-F subsurface and H69-G radiometric arms not
established; Exp1 v1 emission is a logged duplicate. Tip-graph R1/R2
repairs + 100 tests are on the tree. No slot was spent by this session.
Negative results are deliverables.
