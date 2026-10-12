# Candidate hypotheses — ranked, with overlap check and validation plan

*2026-10-12. Nothing here has been implemented or measured on official data. "Expected DTI effect" is a
**prior judgement [OPINION]**, not a projection. "Overlap" is checked against the sibling repo
`buffedlizard55-lab/GEMSDOE32` (S16, commit `b39e16e`), whose registry and docs list about 20 hypotheses and
several holdout results. Those results are **OWNER-REPORT** (the sibling's own instrument; not organizer receipts).*

## Ranking (by expected DTI improvement, then implementation cost)

| rank | ID | Hypothesis (one line) | Layers (official band names, S01 list) | Overlap with sibling work (evidence) | Cost | Expected DTI effect [OPINION] |
|---|---|---|---|---|---|---|
| 1 | **H-P** | Pull-apart basin-closure corridors at dextral releasing steps: a *closed* isostatic-gravity low with basement deepening, bounded by two strands with a releasing step, marks unmapped boundary faults. | isostatic gravity anomaly (and slope); depth to conductive base; RTP magnetics; detrended elevation (flat floor); visible catalogue polylines for step geometry | **Medium in target, low in signal.** The releasing-step target is the sibling's H32-B ("transtensional swarm", strain invariant + seismicity; reserve #2, owner-reported holdout 0.2645 vs incumbent 0.2600). H-P uses gravity closure and basement deepening, which H32-B does not. H32-C uses basement-depth *alignment*, not closure. | Medium | Medium, high uncertainty. Pull-aparts are rare (2.3% of FSS; 5.0% of ≥120 °C training sites, S10), so the candidate list is short. That suits the metric's mass discipline (0.2778-analysis.md §2). |
| 2 | **H-B** | Basement-step lineaments gated by surface quiescence: ridges of ‖∇(sediment-cover thickness)‖ with no surface scarp, which a surface catalogue cannot contain. | depth to basement (sediment-cover thickness), detrended elevation and its slope, isostatic gravity (and derivatives) | **Medium.** Sibling registered it as H61-1 ("registered; NOT validated; no slot requested"). Sibling H32-C tested basement-depth alignment, which is related. We would be the first to run H61-1 under this harness. | Medium | Low to medium. The off-catalogue argument is physically sound (S10: many faults are obscured by lake sediment), but there is no test. |
| 3 | **H-M** | Exact marginal-DTI dot admission: admit a dot only if Δt·(D−0.2T) > 0.2·T·(1−m). A method change, not a geology claim. | any score raster | **Low–medium.** Sibling H60-3 uses an approximate rule ("marginal credit < 0.2 × DTI"). Ours is exact and tested (`gems.metric.dot_is_worth_adding`). | Low (done) | Small to medium. It changes which dots are emitted, not the geological signal. |
| 4 | **H-R** | Relay-ramp corridors: an oblique connector plus en-échelon strands between tips (spacing W 0.1–15 km, along-strike ≤ 3.5W), validated by hiding known hard-linking faults and testing recovery within 300 m. **This is the brief's assigned lane.** | catalogue tip graph; gradient and scarp layers as scores | **HIGH.** Sibling H33-5 ("tip / step-over extension") is FALSIFIED as an addition arm (sibling registry). Repo names GEMSDOE33 ("analog-tip-stepover") and GEMSDOE53 ("tiprelay") are listed in the brief. | High | Unknown. The lane is crowded, so a gain would need the hard-linked masked-recovery design, which the sibling lacks. Parallel-run check required (IR-14). |

**Ranking rationale [OPINION].** H-P is ranked first because its signal (closure plus basement deepening) is not in
the sibling and it fits the regional prior in S10. H-B is second: it is a registered, untested sibling idea that
our harness would test properly. H-M is cheap and already in code, but it is an emission rule, not geology.
H-R follows the brief but is the most duplicated.

## Rejected (already tested in the sibling, or not obtainable)

| ID | Idea | Why rejected (evidence) |
|---|---|---|
| R1 | Seismicity-density lineaments from the official earthquake band | Sibling H33-E: the supplied seismic band has no fault-scale information (measured autocorrelation 0.9986 at 1 km, 0.9935 at 3 km; S16). The raw catalogue route needs earthquake.usgs.gov, which is blocked here (IR-12). |
| R2 | Tilt-angle zero-crossing edges | Sibling H62-1: FALSIFIED (ties raw; 0 of 4 blocks beaten). H61-3 (same family) is registered, not run. |
| R3 | Magnetic-low demagnetization corridors (alteration + TMI lows) | Sibling H32-5 ("Alteration & Magnetic Demagnetization"): holdout DTI 0.1383 vs current best 0.26, not promoted (OWNER-REPORT, `docs/research/validation_summary.json`). The sibling already applies Frangi/Sato ridge filters to both magnetic polarities. |
| R4 | Dilatation-gated, orientation-aware strain (H-O in an earlier draft) | Duplicates sibling H32-B, which already uses a positive-dilatation gate (Kostrov transtensional invariant, z₊(ε_kk>0)), and sibling H62-3 (raw strain prior, "live"). Not new. |
| R5 | Lidar scarp channel | Sibling H33-C measured (not promoted); H61-5 registered, data obtainability unverified. The 1 m DEM link table is part of the login-gated data (S04). |

## Validation plan (applies to the top candidate, H-P)

1. **Data gate.** Official files placed in `data/` and hashed (IR-11). Without them, nothing below runs.
2. **Spatial hide-and-recover.** Withhold whole catalogue fault segments with a buffer. Derive every catalogue-based
   feature (step geometry, closure) only from the visible faults. Mask visible faults pixel-exactly.
3. **Leakage canary.** Test each feature alone on the holdout. AUC above 0.90 means leakage until shown otherwise.
4. **Baseline.** The same pipeline without closure features. The gate needs H-P to beat it.
5. **Metric.** Pooled DTI, α = 0.2, β = 0.8, R = 300 m (`src/gems/metric.py`). Report as HOLDOUT-DTI with the
   evaluator version, the number of withheld positives, and a 95% CI (bootstrap over withheld segments).
6. **Gate.** `src/gems/gate.py`: candidate > baseline **and** candidate > current holdout best. Otherwise NEGATIVE, and
   the download stays disabled. Note: the sibling's holdout instrument is not the organizer's; we need our own
   "current holdout best" and must say which instrument it came from.
7. **Budget.** 3 experiments or 2 hours (brief). Planned: E1 = H-P vs baseline; E2 = E1 + H-M admission;
   E3 = H-B vs baseline.

## Obtainability of the sources H-P needs

| need | official source | obtainable from this sandbox? |
|---|---|---|
| features (gravity, magnetics, basement depth, elevation) | competition training file (S01, S04) | **No**: login-gated (IR-11). The user can download it after registering. |
| catalogue fault traces | competition labels (S01); USGS Quaternary Fault and Fold Database (S12) | Labels: no (login). USGS QFD: the page is reachable (verified); KML/GIS downloads are **blocked** (curl 000). The user can download them from the official page. |
| 1 m DEM | link table in the competition data (S01) | No (login). Not needed for H-P. |

No candidate has been validated. H-P is "viable in principle" because its inputs are official and listed on the
organizer's page, not because a test was run.
