# Historical hypothesis preregistration — 2026-10-20 (before implementation)

> This is a pre-run archive, not current status. Some ideas were subsequently implemented, tested, or retired; the old “data present” and queue statements do not describe this checkout now. See `untried-hypotheses-2026-10-20.md` and `../../evidence/run_card.json`.

Lane constraint (parallel-run protocol rule 1): every candidate stays inside the
relay-ramp / pull-apart corridor generator — faults proposed from catalogue
geometry, scored inside corridors. "Expected gain" is a prior written before the
holdout look, never a score. Holdout reference (archived, HOLDOUT-DTI,
`evidence/e2_gate.json`, mean-of-cells instrument): corridor 0.0060 ± 0.0014 vs
no-prior control 0.0021 ± 0.0006. The 2026-10-20 review
(`reports/review-2026-10-20.md`) requires pooled DTI, repaired tip geometry,
artifact-bound canaries and literal two-phase uniqueness before any promotion.

| Rank | Hypothesis | Layer(s) | Physical signature targeted | Why it catches a catalogue-missing fault | Difference from this repo today | Expected gain / cost | Data obtainability (checked this session) |
|---|---|---|---|---|---|---|---|
| 1 | **H69-F Subsurface straight-step corroboration inside corridors** (PRIMARY, preregistered) | `cond_surf` (training band 17), `depth_to_base_surf` (band 15) | Multi-scale HG + tilt edge (`cond_hg_s2`, `cond_tilt_s2`, `base_hg_s2`, `base_tilt_s2`, robust-z mean inside corridor) | A blind breaching fault under alluvium offsets basement depth and near-surface conductivity even where lidar sees no scarp and magnetics are muted by cover — the classic Walker Lane sediment-covered step-over | `physics.py` computes HG/tilt only on gravity (`iso_grav_anom`) and magnetics (`tmi`); cond/basement enter no corridor score anywhere in this repo (family used them only as pixel scalars/plain gradients) | moderate / low | **Present**: bands verified by reading `training_features.tif` descriptions this session (sha256 `4371c82e…`); no external fetch |
| 2 | **H69-G Radiometric depletion inside corridors** (SENSITIVITY, preregistered) | GeoDAWN radiometrics K, Th (`geodawn_rad_u8.tif` bands K/Th/U/TC) | Robust-z low of `-(K+Th)/2` inside corridor (`rad_depl`) | Hydrothermal alteration along a permeable breaching fault can leach K; chemistry is independent of scarp geometry, so a sedimented fault with no edge can still show a halo | The archived H69-D receipt *claims* this channel but no checked-in code implements it (2026-10-20 review: provenance mismatch). This session implements it reproducibly or not at all; it may not select the emission arm | small–moderate / low | **Obtainable, verified**: fetched this session from the pinned family mirror (manifest `ext_geodawn_rad_u8`, sha256 `c22420f7…` matches; provenance per manifest: USGS GeoDAWN DOI 10.5066/P93LGLVQ). Named non-fault mimic: alluvial composition / lithology; K depletion is not universal |
| 3 | **H69-H Connector-axis phase coincidence (joint HG/tilt)** | `iso_grav_anom` (13), `rtp` (2) | Sample HG/tilt evidence *along the oblique connector polyline* (not corridor-area mean); require gravity and magnetic edge peaks co-located within 2 px along the axis | A real breaching fault is a lineament: its geophysical expression concentrates on the connector trace, while the current area-mean dilutes it over the whole rhomb and rewards broad anomalies with no through-going structure | All corridor scoring in this repo uses area means (`corridor_evidence_from_z`); no along-axis sampling exists | moderate / medium | Present (same stack). Queued next session (handoff queue item 1); not run this session to keep one primary comparison clean |
| 4 | **H69-I Releasing-basin margin asymmetry** | `depth_to_base_surf` (15) + corridor rhomb geometry | Rhomb interior basement-depth low (depocentre) with HG high on the rhomb rim, asymmetric toward the master strand | Pull-aparts subside: a sediment pond inside a releasing step is itself evidence of an active, unmapped border fault system, even if border traces are buried | Differs from H69-F (generic step evidence) by using the *signed interior-vs-rim pattern* tied to rhomb geometry; nothing in the repo uses interior/rim contrast | small–moderate / medium | Present. Queued; depends on H69-F transforms landing first |
| 5 | **H69-J Staggered scarp strike-coherence** | Lidar composite bands `strike`, `coh100`, `ex_max` (`lidar_scarp_features_u8.tif`) | Fraction of corridor scarp pixels whose local strike lies within ±15° of the predicted en-échelon angle (mean strike ± 25°) | En-échelon arrays inside a relay have a diagnostic oblique strike; pluvial shorelines (the named mimic) strike along contours, not at the en-échelon angle to the master faults | Current lidar channel is strike-blind (`max(ex_max, step_max, downface_max)`); the `strike`/`coh100` bands are read by no scorer in this repo | small / medium | Present (bands verified this session). Queued |
| — | H69-K Focal-mechanism nodal-plane lineaments | USGS ComCat/ANSS events + mechanisms | Epicentre lineation + nodal-plane strike clustering along corridors | Seismically active blind faults with no scarp | Family uses only pre-binned `ieq/deq` bands | unknown / medium | **DATA-BLOCKED in this sandbox**: free official source is USGS ComCat (https://earthquake.usgs.gov/), host outside the sandbox allowlist and absent from pinned mirrors. Not proposed as viable until fetched and pinned |

## Why the geometry repair precedes all of the above

Two defects in `build_tip_pairs` invalidate every archived corridor number as a
test of the lane (documented in `reports/review-2026-10-20.md`, re-derived this
session): (R1) tip-window intervals were compared in tip-local coordinates with
no tip-to-tip offset, so along-strike separation was ≈ 0 by construction and the
≤ 3.5W rule never bit (strict-xfail test: W = 5 px, gap 40 px admitted);
(R2) the KD-tree search radius (150 px) cannot reach legal pairs whose
tip-to-tip distance is up to √(150² + 525²) ≈ 546 px. The preregistered pass
(`registry/preregistration-2026-10-20-relayfix.json`) repairs both, re-measures
the archived scorer (v1) on repaired geometry, and only then asks whether H69-F
(v2) beats v1 and the no-prior control on pooled HOLDOUT-DTI.

## Validation rule (no exceptions)

Top candidate first: per-feature leakage canaries (AUC > 0.90 disqualifies),
pooled HOLDOUT-DTI with paired cell-bootstrap CI vs both comparators, surface
uniqueness before placement, dot uniqueness after, format validation on exact
bytes. A candidate that has not beaten the current same-evaluator holdout best
does not touch a submission slot; this session spends no slot in any case
(promotion is a separate selector step, protocol rule 6).
