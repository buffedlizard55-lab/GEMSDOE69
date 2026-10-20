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

## IR-69-DUP-01 — H69-E stopped as lane drift (2026-10-20)

Holdout gate passed (HOLDOUT-DTI corridor 0.00637 ± 0.00171 vs control 0.00253 ± 0.00071,
paired Δ +0.00385 ± 0.00138, gems57 pooled hide, 8 cells, 22,641 withheld positives).
`scripts/validate_submission.py` passed on both twins. Surface Spearman worst |ρ| = 0.227
(limit 0.90). Dot overlap with earlier GEMSDOE69 files is 0.483 (under 0.70).

Protocol rule 1 still fails: 84.14% of the 33,199 dots fall within 3 px of
`12GEMSDOE docs/downloads/12GEMSDOE_r5-nms3-trace_055e9aac96b8.tif`
(blob `98cbfc84a0e808733e9c5c3aad9ef07c7678a3fe`, 103,347 dots, ρ = 0.0233).
That is spatial proximity to a dense trace field, not a byte copy (pixel agreement 0.989
is the sparse-zero baseline). The rule fails closed. No download is offered. No slot is spent.

Overlap with the h33 champion blob `15781395` is 0.316 (ρ = 0.227), so this is not a copy of
the 0.2778 file either.

## IR-69-GATE-02 — H69-D radiometric label is not a validated result

`submissions/h69-z-radiometric-halo-31994-20261020T182654Z-31913c0c-zeros.tif` was receipt-labelled
H69-D, but the committed `src/gems69/physics.py` at that tree has no radiometric transform, and
`evidence/e2_gate.json` (now copied to `evidence/e2_gate_20261012_prior.json`) is the 2026-10-12
corridor run, not a radiometric holdout. Do not offer that file as a validated radiometric submission.
The 2026-10-20 session re-implements radiometrics inside H69-E and re-runs the gate before any OK banner.

## IR-69-LB-01 — user-cited 0.3195 disagrees with the in-repo public snapshot

The user states 0.3195 is the current high score. `registry/leaderboard_snapshot_2026-10-12.json`
(public leaderboard page, retrieved 2026-10-12) shows 0.4275 at rank 1 and 0.3195 at rank 9.
drivendata.org is not reachable from this sandbox, so the live board was not re-fetched. Both figures
are USER-REPORTED or snapshot-class, not organizer receipts, and neither is a score for this lane.

## IR-69-CAP-01 — the 2026-10-12 corridor cap collapsed to W = 2.8 km

`evidence/e1_tipgraph_census.json` records 1,200 corridors, all pull-aparts, and the stored widths
are 2.8 km. Sorting by |W − 2.8 km| filled the cap at the published mean and never emitted the rest
of the 0.1–15 km range the prompt requires. H69-E replaces that cap with four width bins. The old
selector remains available as `selection="mean_width"`.

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
