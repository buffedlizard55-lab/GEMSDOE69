# Geothermal knowledge base — GeoDAWN / Walker Lane / GEMS competition

Accumulated, source-labelled knowledge. Every entry states where it came from:
**[OFFICIAL]** organizer/USGS product or page, **[PROMPT]** stated in the standing
prompt (Giddens & Faulds 2025 SGP-TR-229 numbers are quoted from the prompt, which
cites that report), **[MEASURED]** computed in this repo from hash-pinned bytes,
**[FAMILY]** measured by a sibling family repo (repo named), **[BLOCKED]** not
obtainable in-sandbox, with the reason.

## 1. The scoring problem

* **[OFFICIAL]** Metric: distance-weighted Tversky index, alpha=0.2, beta=0.8,
  triangular kernel R=300 m, grid EPSG:32611 100 m, float32 in [0,1]
  (DrivenData competition 306 problem page; transcribed byte-pinned in
  `vendor/template66/gems/metric.py`). FN costs 4x FP.
* **[MEASURED]** Marginal bar: one more dot raises DTI iff its kernel-weighted hit
  probability p > alpha·DTI (identity in `gems/metric.py:marginal_credit_bar`;
  at DTI 0.2778 the bar is 0.0556).
* **[MEASURED]** Grid: 3730×3292 @100 m, footprint 5,167,373 px, catalogue
  (labels≡existing_faults) 60,988 px (this session, `evidence/verify_grid.json`).
* **[FAMILY, GEMSDOE32]** Receipt-derived hidden-truth size ≈ 12,691 px with
  σ≈1.85 px location jitter (truth model prior, owner-report-derived).
* **[FAMILY, GEMSDOE32]** Cross-family instrument calibration: local holdout ranks
  live scores with Spearman ρ≈0.51 (p≈0.09, n=12) — a screen, not a predictor.

## 2. Structural geology of the target (prompt-cited + standard)

* **[PROMPT]** Giddens & Faulds (2025, SGP-TR-229) inventoried >450 step-overs in
  the region; ramps typically 3–3.5× longer than wide; widths 0.1–14.6 km, mean
  2.8 km; ≈70% of higher-temperature step-overs are hard-linked; breaching faults
  range from oblique connectors to en échelon strands.
* **[PROMPT]** Walker Lane dominates the GeoDAWN footprint; hot systems sit more
  often in pull-aparts and displacement-transfer zones than in normal-fault
  step-overs; N–NE faults are best oriented for dilation under WNW extension.
* **[MEASURED, this session]** From the pinned catalogue: 3,887 skeleton strands;
  212,657 raw geometrically-valid step-over tip pairs before dedup/priority cap
  (`evidence/e1_tipgraph_census.json`): the geometry prior is rich, not sparse.
* **[MEASURED, this session]** Hard-link validation: masking the linking catalogue
  mass of 13 disconnected hard-linked ramps and rebuilding the tip graph recovers
  84.6% of masked linking pixels within 300 m on average (median 1.0; 11/13 ramps
  ≥70%) — `evidence/e1_hardlinked_recovery.json`.

## 3. What the family has already learned (score-forming results)

* **[USER-REPORTED-NOT-ORGANIZER-CONFIRMED]** Best family download: h33-h33-2-b2
  0.2778 = 37,654 unit dots, basin-wide multi-physics lineament propensity
  (d28/h19-5 lineage), 200 m catalogue-flank prune, zeros format
  (GEMSDOE32 audit bytes vendored in this repo's docs research).
* **[FAMILY]** Dotted-thinning calibration: spacing ≈2.8 px near the 300 m kernel
  beats 1.5 px at equal physics (receipts 0.2600 vs 0.2477, prompt-quoted).
* **[FAMILY, GEMSDOE63]** CVaR-robust selection across label worlds; their full
  registry x-check showed the literal overlap gate fails closed family-wide
  against universal soft surfaces + dense rasters (registry-structure condition).
* **[FAMILY, GEMSDOE32]** catalogue_hidden proxy flaw: mass on mapped faults is
  free in the naive proxy but penalized live (strict variant charges it).

## 4. Data inventory available to this lane (all hash-verified this session)

| asset | sha256 (16) | notes |
| --- | --- | --- |
| training_features.tif (19 bands) | 4371c82e3b8339b8 | band descriptions read into evidence/band_metadata.json |
| labels.tif ≡ existing_faults.tif | 7ba308ccdc4418b3 | IR-69-DATA-01 |
| sample_submission.tif | 2176d08e485aa2cd | grid contract |
| lidar_scarp_features_u8.tif (12 bands) | d580bb8bdcdb941e | ex/step/downface/relief/coh/strike/valid |
| geodawn_rad_u8.tif (K,Th,U,TC) | c22420f75999030d | unused by family primaries — hypothesis H69-D |
| geodawn_extensions_u8.tif | a35a9c6d2a14786f | ThK/UK/UTh/TMI_up150 |
| derived_sgmc_faults_100m_u8.tif | 643cbe992ef4ba37 | 83,593 px, overlaps labels in only 3,978 px |
| gdr_wellspring/qfaults/volcanic CSVs | see manifest | GDR points inside footprint |

## 5. Open questions for next sessions

1. Does the corridor arm's holdout edge survive the conservative 'detached' folds
   (segments with no visible continuation)? — queued sensitivity run.
2. Radiometric K/Th lows inside corridors (H69-D): cheap to test next session;
   data already pinned.
3. The 0.2778 → 0.3195+ gap to user-reported leaderboard highs: the family
   instrument cannot rank across that gap (ρ≈0.51). A promotion experiment needs
   organizer receipts, i.e. actually spending a scored slot — a selector
   decision, not a lane decision.
