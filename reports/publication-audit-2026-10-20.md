# Publication audit — 2026-10-20

> **Historical-state note:** this audit correctly recorded the state at its run
> time. A later parallel merge rebound H69-J's local aggregate receipts, but
> that did not change the controlling literal overlap of 1.0. Read
> [`final-audit-2026-10-20.md`](final-audit-2026-10-20.md) for the reconciled
> current state; H69-J remains **NOT OK TO SUBMIT**.

## Decision: NEGATIVE — DO NOT SUBMIT

No new experiment, TIFF, or competition slot was used in this audit. The existing
candidate has a recorded literal duplicate result. Generating another file merely
to change its hash would not satisfy scientific uniqueness and would violate the
mandatory duplicate-and-stop instruction. Existing TIFFs remain audit artifacts.

### Pass 1 — implementation and independent checks

- Read AGENTS.md, README.md, PROMPT.md, HANDOFF.md, relayfix report, publication
  code, tests, and the archived evidence before making changes.
- Found a merge regression in `scripts/release_gate.py`: a documented
  dotlike-only pass with overlap ≤0.70 could override literal overlap failure.
  Removed that exception. The user requires comparison against **any** registry
  raster. Universal continuous surfaces may make this rule unachievable, but
  that is not permission to redefine it locally.
- Expanded the regression test to cover an actual dotlike diagnostic (0.61),
  the boundary (0.70), zero, and missing diagnostics. The previous test omitted
  the diagnostic value and therefore never exercised the exception.
- Independently ran `scripts/validate_submission.py` on H69-J. It passes all
  format checks: float32, single band, EPSG:32611, 3730×3292, transform
  (100,0,243350,0,-100,4508550), all finite in [0,1], no NaN inside footprint,
  no positive pixels on the mapped catalogue. SHA-256:
  `981beb5707bb9933a2cf24a615eed373dc7e7cab451954207097e1641f32eaa6`.
  Receipt: `evidence/publication_audit_validator_20261020.json`.

### Pass 2 — evidence and edge-case review

- H69-J's archived all-registry overlap is 1.0; dotlike-only 0.61 does not
  waive that failure. No full registry scan was rerun in this audit: cached
  registry rasters and the physics stack are not present in this fresh checkout.
- H69-J holdout/source bindings are stale on the repaired source tree. This
  remains a separate release blocker, even if uniqueness were resolved.
- Archived phase summaries claim 862 rasters while the aggregate H69-J receipt
  describes 751. The surface receipt also repeats the file hash as a decoded
  hash. These are provenance irregularities, not fresh evidence of clearance;
  revalidate from original bytes before any future promotion.
- Corrected README language claiming a passed gate and treating dense-surface
  failure as non-blocking. Updated the site to distinguish archived evidence
  from independent checks in this audit and corrected the submission-note key.
- Replaced an overconfident run-card statement that joint geophysics excludes
  non-fault contacts: intrusive contacts and basin margins can affect both
  gravity and magnetics. Geological specificity is not proven by coincidence.

### Pass 3 — original-request reconciliation

- Rebuilt the run card, README, site and root landing page from the strict
  publication policy. No submission download is offered. The existing executive
  summary describes the conditional submission procedure; no file is approved.
- Queued hypotheses are in `docs/research/hypotheses-2026-10-20.md` and
  `docs/hypotheses.html`: connector-axis HG/tilt coincidence, releasing-basin
  margin asymmetry, en-echelon scarp phase coherence, and flank-normalized
  radiometric contrast. They are qualitative research rankings, not predicted
  DTI gains. They were not implemented here because duplicate-and-stop applies.
- No claim that the full request is scientifically complete: a unique,
  gate-passing submission has **not** been obtained. No leaderboard superiority
  is established. Negative results are deliverables under the supplied protocol.

## Why the reported H33 score is not proof of geological superiority

The owner-reported 0.2778 is not an organizer-confirmed receipt bound to a file.
The archived anatomy (`evidence/e0_champion_ladder_measured.json` and
`evidence/relayfix_champion_anatomy.json`) is consistent with reducing redundant
prediction mass through sparse off-catalogue emission. A distance-tolerant metric
can reward this without establishing that each dot is a geothermal vent. Fault
inference is the competition target; vent discovery is a later scientific task.
Without hidden labels, controlled ablations and an authenticated receipt, we
cannot establish why H33 achieved that particular score or promise to beat it.

Archived HOLDOUT-DTI for H69-J: vendor/template66 gems57 hide-and-recover,
22,641 withheld positive pixels, 8 repeated cells, 0.005912664,
95% CI [0.004666694, 0.007158635], comparator 0.002147925. The interval is
an archived normal approximation, not an independent spatial-block bootstrap;
current source binding fails. It is not an organizer score or projection.

## Sources and access boundary

Checked through GitHub API in this audit:

- Organizer reference repository, HEAD
  [aebe92f](https://github.com/drivendataorg/gems-prize-reference-solution/commit/aebe92f7c8a990f0e3443451b7a825d9afd6336b).
- Family H33 page source, main commit
  [98901f3](https://github.com/buffedlizard55-lab/GEMSDOE32/commit/98901f3130e8704f4254f173784589e63f000673).
  Owner-authored information, not an organizer submission receipt.
- This repository's Pages API reports legacy publication from main, root `/`;
  the root landing page leads to `docs/index.html`. Live deployment must still
  complete after merge; API configuration alone does not prove rendering.

Manual-review sources, **not fetched in this audit** (hosts outside outbound
allowlist): [official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[GDR 1391](https://gdr.openei.org/submissions/1391),
[competition report](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
Giddens & Faulds geometry statistics remain prompt-supplied citations, not
independently verified facts in this audit. Conflicting user-supplied leaderboard
figures are not treated as current organizer-confirmed scores.

## Next session, in order

1. Protocol owner must resolve the all-registry dense-support overlap rule;
   retain negative status until then. Do not silently threshold priors or change
   what constitutes a dot.
2. Reconcile the registry census and rebuild genuine pre-placement surface and
   final-dot receipts from pinned bytes. Refresh beyond the archived census.
3. Join measured per-strand dip and slip attributes; otherwise label same-dip
   and dextral releasing steps as unverified proxies, not observed structures.
4. Preregister untouched spatial blocks; rebuild feature-alone canaries and
   pooled holdout with paired spatial-block bootstrap against both the no-prior
   baseline and current best, using one shared evaluator, bound to current code.
5. Only after all gates pass, create a uniquely named TIFF, bind exact bytes to
   validation and uniqueness receipts, publish its download, and request selector
   authorization within the organizer's current weekly cap. No automatic upload.

This lane is CPU-capable; a GPU is not the blocker. Organizer-authenticated data,
submission receipts, unrestricted official-source access, and resolution of the
literal uniqueness rule are unavailable here. Pinned GitHub mirrors offer
integrity checking, not organizer authentication. Never request credentials in chat.

## Merge reconciliation

A parallel review landed on main while this audit PR was open. It independently
fixed the same literal-overlap loophole. Preserved its separate rho/overlap
reasons and review report, combined the diagnostic-value regression coverage,
and regenerated publication outputs after merging main into this session branch.
