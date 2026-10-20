# FLAGGED — irregularities needing human review

| ID | Finding | Severity | Disposition |
| --- | --- | --- | --- |
| IR-69-DATA-01 | `existing_faults.tif` is byte-identical to `labels.tif` (sha256 7ba308cc…) in every family mirror; the true organizer existing-faults raster is unavailable in this environment. The public labels raster doubles as the mapped catalogue; the scored hidden truth is unpublished. | medium | accepted family standard; holdout hides whole catalogue segments so the instrument stays well-defined |
| IR-69-DATA-02 | No DrivenData auth in-sandbox: organizer bytes cannot be re-downloaded; all data are sha256-pinned family mirrors (NOT organizer-authenticated). | medium | fail-closed fetch scripts verify every byte on arrival |
| IR-69-TPL-01 | Template drift found upstream: GEMSDOE63's vendored `gems57/grid.py` did not match its sha256 pin (unrepinned REPO_ROOT fix); GEMSDOE66 upstream `gems/submission_writer.py` + `validate_submission.py` are strictly stronger than GEMSDOE63's vendored copies. | low | gems57 restored to pinned bytes (data_dir passed explicitly); gems/ taken from upstream GEMSDOE66; documented here |
| IR-69-DIP-01 | Raster catalogue carries no dip polarity: the prompt's "same-dip" pairing condition is proxied by sub-parallel terminal strikes (≤30°). | low | disclosed in method; sensitivity check queued |
| IR-69-REG-01 | The literal protocol overlap gate fails closed against ANY sparse dot field: the 751-blob registry contains 27 universal soft surfaces and 134 high-density rasters that overlap every dot field by construction (family precedent GEMSDOE63/64). | medium | lane-drift gate evaluated on the dotlike stratum + surface Spearman against everything; structural condition reported literally |
| IR-69-SCORE-01 | All leaderboard values in the standing prompt (0.2778, 0.3774, 0.3195, …) are USER-REPORTED-NOT-ORGANIZER-CONFIRMED; this repo holds no organizer receipt. | info | labels applied everywhere; no projection is ever written as a score |
| IR-69-VAL-01 | Template conflict on outside-footprint policy: upstream GEMSDOE66 `gems/validate_submission.py` demands NaN-only outside the footprint (official format note), while byte-pinned `gems57/grid.py` shipping policy declares zeros (all-finite) the only submission-compatible mode — and the user-reported-scored h33-2-b2-zeros artifact was all-finite. Additionally the upstream validator's footprint proxy (training_features band 1 finite, 5,165,852 px) disagrees with the sample_submission finite mask (5,167,373 px) by ~1.5k cells. | medium | both variants are produced and compliance is re-derived against sample_submission itself (the portal contract): the -nan variant matches it exactly (NaN outside + nodata tag, prompt-mandated layout) and is PRIMARY; the all-finite -zeros variant is the portal-safe fallback per family precedent |
| IR-69-HL-01 | First hard-linked recovery design (mask corridor-interior catalogue mass, rebuild via the capped corridor builder) measured ≈3% recovery. Two defects found and fixed: (a) ramps must be scored only when the mask actually disconnects the flanks; (b) the 600-corridor cap in the rebuild displaced the target corridor among 54k competing pairs — the rebuild now re-emits the recovered pair directly. Post-fix result: mean recovery 0.846 within 300 m (median 1.0, 11/13 ramps ≥70%, 2 ramps 0%). | low | fixed in-session; the two buggy numbers (0.031, 0.045) logged here so they are never resurrected |

## IR-69-REG-02 — dot-overlap flag vs archived GEMSDOE51 dense raster (review needed)

Lane-drift scan vs the 751-blob registry: surface Spearman clean (worst |rho| = 0.2574 << 0.90),
no exact pixel matches (best pixel agreement 0.9897 << 0.9999), but 92.15% (Euclidean 3 px disk)
of submission dots fall within 3 px of the dots of ONE archived raster — GEMSDOE51 `gemsdoe51-strainbudget-s1-v1.tif` (blob 23ff31cf, 95,927 dots, NOT a
scoreboard artifact). Surface correlation with that raster is rho = 0.0404, i.e. it is not a
copy; the overlap is explained by both fields concentrating on the same mapped structural trends
and by the dense raster's 3-px neighbourhoods covering a large footprint fraction. The protocol's
70% dot-overlap rule is written to fail closed, so this flag is surfaced for selector review
rather than auto-promoted; family precedent GEMSDOE63 documented the analogous condition
(0.7605 dotlike worst) and promoted with disclosure after intent checks passed.

Distribution check (evidence/e3_uniqueness_rows.json): of 570 dotlike registry rasters, 20 exceed
the 0.70 overlap line, 87 exceed 0.50, 291 exceed 0.30 — a gradient, not a single outlier near 1.0.
Combined with worst surface |rho| = 0.2574 and best pixel agreement 0.9897 (trivially high for two
sparse fields over 12.28 M cells), the pattern is consistent with shared structural concentration
(all family fields sit on the same mapped fault system), NOT with a lane-drift copy. Resolution per
family precedent: artifact offered behind a review banner; selector decision required; do not
auto-promote, do not delete (negative-result logging would overstate the finding).

## IR-69-HIST-01 — prior session ran the same lane (negative verdict) and is merged on main

Commits 1b5c36f/f3568dd/95220a6 (PR #5) contain a prior, different implementation of this lane:
885,250 dense dots, corridor arm DTI 0.0749 vs halo-control 0.1096 on 22,893 withheld px (draws
20/21, evaluator gems57-pooled-hide-v2) -> gate NOT met -> verdict NEGATIVE (no download offered),
uniqueness checked against an 862-raster registry index (registry/registry_index_69.json). That
record remains in git history and in-tree (their archive/registry index files were kept by the
merge). The 2026-10-12 session re-implemented the lane from the method paragraph (600-corridor
tip-graph pipeline, no-prior control, 751-blob registry mirror) and reached the positive results
recorded in evidence/run_card.json (promote-flagged-review). Both are legitimate records of the
same lane paragraph under different implementations/controls.

## 2026-10-20 relay-fix session additions

| ID | Finding | Severity | Disposition |
| --- | --- | --- | --- |
| IR-69-GEOM-01 | R1/R2 repaired: tip-window intervals now offset by tip-to-tip projection; search radius 546 px. Repaired census 383,827 pairs (was 212,657). Archived corridor numbers used buggy geometry and must not be pooled-compared to repaired runs. | info | fixed + tests; archived receipts retained with labels |
| IR-69-DUP-02 | Exp1 repaired-v1 emission is a near-duplicate of the archived Oct-12 lane raster (3 px overlap 0.8911, jaccard 0.7410). | medium | logged duplicate-and-stop; audit bytes only (evidence/relayfix_receipt.json) |
| IR-69-SEL-01 | Production corridor cap emitted 1200/1200 pull-apart, 0 transfer corridors; transfer-only selector (Exp2b) is the first lane emission using the transfer population. Outer-tip combinations can duplicate one step-over under different tip pairs; overlap cap 1.0W vs cited 3-3.5x ramp aspect unresolved. | medium | transfer candidate preregistered separately; selector semantics flagged for next preregistration, not silently changed |
| IR-69-REG-03 | Transfer candidate literal uniqueness: rho passes (dots 0.1103, surface 0.2708; 862/862, 0 errors) but overlap fails at 1.0 vs universal surfaces and 0.8497 worst dotlike (GEMSDOE53 80k-dot raster; 20 dotlike >0.70). Science/format/canary/manifest gates all pass; publication blocked solely by literal overlap definition. | medium | verdict negative; upstream selector must resolve registry support definition; no local override |
| IR-69-SAMPLE-01 | Mirrored sample_submission.tif positives equal the catalogue exactly (60,988 px), while the official page (fetched 2026-10-20) describes the sample as total fault absence. Footprint (finite mask) is unaffected, but mirror content cannot be organizer-authenticated here. | low | disclosed; grid contract derived from finite mask + CRS/shape/transform only |
