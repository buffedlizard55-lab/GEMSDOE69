# New candidate hypotheses for GEMSDOE69 (not yet implemented in this repo)

Ranked by expected HOLDOUT-DTI improvement over the no-prior control, then by implementation cost.
"Expected" values are priors written before any holdout look, not measurements. Protocol rules:
rule 4 (leakage canary: single-feature AUC > 0.90 = leakage until proven otherwise), rule 5 (run card
with holdout DTI + 95% CI before any submission slot), rule 6 (budget: 3 experiments / 2 hours; do not
spend a submission slot on an idea that has not beaten the current holdout best).

Current holdout best for reference (evidence/e2_gate.json, HOLDOUT-DTI, gems57 pooled hide-and-recover,
alpha 0.2 beta 0.8, 300 m triangular kernel, draws 20/21):
- corridor arm: 0.0060 +/- 0.0014; control arm: 0.0021 +/- 0.0006; paired delta +0.0038 +/- 0.0015;
  gate PASSED but the absolute DTI is tiny — a screen, not a leaderboard projection (calibration
  rho~0.51, p~0.09, not significant; evidence/e0_champion_ladder_measured.json).
- Registry scan: worst |Spearman| 0.2574 (pass), dotlike dot-overlap 0.9215 vs archived GEMSDOE51
  (FAIL > 70% limit; logged as near-duplicate lane-drift per protocol rule 1).
- Verdict: NEGATIVE — no submission slot spent on this build (evidence/run_card.json).

Source of truth for all leaderboard numbers: they are USER-REPORTED-NOT-ORGANIZER-CONFIRMED; the
official public leaderboard snapshot (registry/leaderboard_snapshot_2026-10-12.json, rendered 2026-10-12)
shows #1 0.4275, #9 0.3195, and 0.2778 at rank 24 (extradr19) with no file attribution
(IR-69-02/03).

## Why h33-h33-2-b2 scored 0.2778 (GEMSDOE32 audit, measured-here from committed bytes)

h33-2-b2-zeros is 37,654 unit dots (value 1.0) from five rungs of mass removal on the h19-5
multiline-corroborated lineament field, with a 200 m catalogue flank prune. Final dots sit 1.41–2.00
px from the catalogue (min 2.24 px), median 1.97 km from it; none on the mapped catalogue; only
5.77% within 300 m of a mapped fault. At DTI = 0.2778 the metric break-even is p > alpha*DTI = 0.0556
per dot — any dot better than ~5.6% likely to touch a hidden fault within 300 m is score-positive.
The family audit estimates mean credit ~0.13–0.14 per dot (~2.4x the bar). Two mechanisms explain
the ladder: (1) dotted beats solid ribbons at fixed mass (kernel coverage at 1/3 weight per dot);
(2) known faults are masked from scoring, so dots 100–200 m from mapped traces earned below-bar mean
credit and deleting them raised the score (+0.0108, +0.0070) — new faults rarely run within
100–200 m of the published traces. So 0.2778 is near-minimal mass on a reasonably ranked *wide* field,
not proof of the right geology.

Can we beat 0.2778 / 0.3195? Mechanism: yes — any propensity that puts more dots above the
p > 0.2*DTI line raises the score (e.g. raising mean credit/dot from ~0.135 to ~0.19 at equal mass
moves the algebra toward ~0.36). Calibration: honestly uncertain — this lane's holdout screen (0.006)
does not substantiate beating it, and holdout-to-live calibration is not significant. Public board
shows better fields exist (0.3195–0.4275). Honest answer: **not on current evidence**; negative result
logged; do not spend a submission slot until a candidate beats the holdout best on a fresh run.

## Candidates

| Rank | Hypothesis | Layers | Physical signature (transform) | Why it catches a fault missing from the catalogue | How it differs from everything in this repo | Expected gain / cost | Status |
|------|------------|--------|-------------------------------|--------------------------------------------------|---------------------------------------------|----------------------|--------|
| F1 | **Radiometric K/Th depletion/enrichment halos inside corridor interiors** | GeoDAWN radiometrics K, Th, TC (`ext_geodawn_rad_u8`, hash-pinned in registry/data_manifest_gemsdoe32.json) + corridor masks from the existing tip graph | Robust-z LOW of K and Th within corridor masks at 1/2/4 px (hydrothermal alteration leaches K, fixes/deposits Th); multi-scale to match ramp widths 0.1–14.6 km | Alteration halos mark permeable damage zones even where no scarp or geomorphic edge survives; radiometrics see chemistry, not geometry — blind or sedimented faults in Walker Lane volcanic cover | Family used radiometrics only in scarp-fusion blends (GEMSDOE46 r11/r12); never as a corridor-interior *primary* channel; here radiometrics test geometry-proposed corridors independently of the catalogue | medium / low-medium | **QUEUED** — data obtainable via scripts/fetch_data.py (GitHub mirrors); validate on holdout before any slot |
| F2 | **Stream-profile knickpoint & chi-lineament chains at step-over mouths** | det_elev (band 12), det_elev_slope (band 19) — already pinned in training_features.tif | Along-stream chi-integral anomalies crossing corridor axes; collinearity vote of knickpoints aligned with corridor strike | Blind faults with no surface scarp still offset bedrock and knick stream profiles; a chain of collinear knickpoints across drainages is structure a scarp map cannot see | All family DEM channels are local (curvature/ridge/detrend); nothing integrates along-stream profiles | low-medium / low | **QUEUED** — pinned data; CPU-only |
| F3 | **Straight conductivity / basement-depth steps under alluvial cover** | cond_surf (band 17), basement_depth (band 15) — already pinned | Gradient magnitude x 3x3 directional coherence of gradient orientation (straight-boundary test); long straight N–NE steps | MT conductivity and basement depth image subsurface structure under alluvium where surface mapping records nothing — exactly the hidden-fault class | Family enters cond_surf / basement_depth as scalars or plain gradients only; no straight-boundary coherence test | medium / low-medium | **QUEUED** — pinned data |
| F4 | **Instrumental seismicity lineaments + focal nodal planes** | Would add USGS ComCat / ANSS event catalogue + focal mechanisms (NOT pinned; not reachable from this sandbox) | Epicentre lineament density + focal-mechanism nodal-plane strike clustering along corridor axes | Active blind low-slip faults light up seismically while leaving no scarp at the surface | Family uses pre-binned ieq/deq density bands only; no raw event catalogue or nodal planes | unknown / medium | **DATA-BLOCKED** — needs free official USGS ComCat/ANSS (earthquake.usgs.gov); not obtainable from this sandbox; do not propose as viable until fetched |

## Validation plan (protocol rule 5)

1. Fetch pinned data (scripts/fetch_data.py) for F1–F3; confirm sha256 pins.
2. Add the candidate as a holdout arm (same folds, same allocator, same flank rule as e2) and run
   `scripts/run_lane69.py e2`; record HOLDOUT-DTI + 95% CI vs the no-prior control (current best
   corridor 0.0060 +/- 0.0014).
3. Run leakage canary (AUC > 0.90 = leakage), registry lane-drift scan (rho < 0.90, dot-overlap < 0.70),
   format validation (validate_submission.py), then assemble the run card. Only a gate pass may spend a
   submission slot; promotion remains a selector decision (rule 6).

## External-data obtainability check

- USGS GeoDAWN magnetic/radiometric release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and — the pinned mirror families derive from these survey products; fetchable via scripts/fetch_data.py from GitHub mirrors in this sandbox (network restricted to github.com/pypi.org; drivendata.org, USGS and Dropbox not reachable from the runner).
- USGS ComCat/ANSS (F4): https://earthquake.usgs.gov/ — free and official, but NOT reachable from this sandbox and not in any pinned mirror; F4 is therefore blocked in this environment.
- Competition organizer bytes (training_features/labels/sample_submission): login-walled at DrivenData #306; used only as sha256-pinned family mirrors (NOT organizer-authenticated; IR-69-DATA-02).
