# Candidate geological hypotheses — GEMSDOE69 relay-ramp lane
Generated: 2026-10-20T19:40Z — Pre-registration before implementation
Evidence class: hypothesis proposal (no holdout look yet); ranked by expected HOLDOUT-DTI improvement, then implementation cost.
All use the catalogue-geometry tip graph (W 0.1–15 km, along ≤3.5W, same-dip via sub-parallel strikes) rather than pixel statistics.

## Current baseline (HOLDOUT-DTI, evaluator gems57 pooled hide-and-recover α0.2 β0.8 R300m, seeds 20/21, 2026-10-20 run)
- Corridor arm (additive multi-scale HG/tilt+maglow+lidar+orient+geom): 0.006216±0.0014 (8 cells, 22641 withheld px)
- Control (no corridor prior, same physics composite): 0.002148±0.0006, Δ+0.004068±0.0015, gate PASSED
- Leakage canary worst AUC 0.689 (corridor_propensity), pass (<0.90)
- Hard-link recovery 0.941 within 300m (16/17 tested, ≥70%)
- Registry lane-drift scan: worst |Spearman| 0.313 <0.90 pass; dotlike 3-px overlap 0.8285 vs registry blob 23ff31cf... FAIL >0.70 → duplicate-and-stop, NEGATIVE, no download, no slot spent (evidence/run_card.json)
- Family best download h33-h33-2-b2: 0.2778 USER-REPORTED-NOT-ORGANIZER-CONFIRMED (37,654 dots, median 1.97km from catalogue)

Question: why did 0.2778 score and can we beat it? H33 is a sparse dotted field (2.8px spacing) on a wide multi-physics lineament, far from catalogue (min 2.24px), exploiting metric marginal bar p>0.0556 at DTI 0.2778. Its mean credit ~0.13–0.14/dot is 2.4× bar. Beating it requires higher mean credit per dot at same mass (~0.19/dot for ~0.36 DTI) — i.e. better ranking, not more mass. The 2026-10-20 corridor emission beat its holdout control but FAILED the uniqueness gate (0.8285 > 0.70 dotlike overlap against a dense registry fault-dot raster): corridor dots sit too close to the mapped-fault network that this registry raster blankets. To beat 0.2778 the lane needs a unique, higher-credit-per-dot field that also clears the <0.70 dot-overlap gate — e.g. one of the queued hypotheses H1–H5 that shifts credit away from catalogue-adjacent dots, validated on holdout first.

## Ranked hypotheses (layers → signature → why hidden fault → difference → expected gain/cost)

### H1 — Convergent relay-edge phase (TOP CANDIDATE)
- **Layers:** iso_grav_anom (13) + tmi (14) via HG_sigma 1/2/4 px + tilt S2 edge + provided HG/VG/TC; specifically grav_hg_s2, grav_tilt_s2, mag_hg_s2, mag_tilt_s2 + geod_2ndinv (strain curvature)
- **Physical signature:** *Joint* multi-scale horizontal-gradient ridge + tilt-zero crossing on **both** corridor margins, with opposite polarity tilt and parallel HG ridges (coincident HG maxima ≥0.5z on grav AND mag, tilt |sin| >0.6 within 2px of corridor edge, and grav/mag HG ridge orientation within 15° of corridor axis). Implementation: for each corridor, sample edge-perpendicular profiles at 5 stations along connector, test HG peak coincidence and tilt zero proximity on each side.
- **Why hidden vs catalogue:** Mapped faults already have single strong scarp/mag edge; hidden relay connectors between overlapping tip pairs produce *paired* opposing edges (two basement blocks stepping) with no central scarp — single-channel HG would miss them, joint grav+mag confirms basement offset, not surficial lithology.
- **How differs:** Current scorer takes max(grav HG) + max(mag HG) independently (OR logic); this uses min() / coincidence (AND logic) plus tilt phase, testing a *phase-consistent relay linkage*, not just high gradient magnitude.
- **Mimic:** Lithologic contacts (e.g., volcanic/plutonic intrusive margin) can produce paired HG — will be penalized if mag_low not co-located (see H2).
- **Expected DTI gain:** medium (+0.002–0.004 on holdout, ~30–60% relative) — targets precise linkage geometry, improving precision per dot; **Cost:** medium (profile sampling, no new data; ~30 min CPU)

### H2 — Altered fault-zone joint: HG edge + magnetic low + radiometric K depletion
- **Layers:** grav_hg_s2 + mag_hg_s2 + mag_low_tmi/rtp (from physics z-stack) + K, Th, TC from geodawn_rad_u8.tif (ext_geodawn_rad_u8, sha256 c22420f7...) + lidar_scarp
- **Physical signature:** Inside corridor interior, magnetic low (negative TMI residual, -3km Gaussian) AND K depletion ( -K_z >1.0 ) AND rim HG ridge (grav or mag HG >0.8z). Alteration destroys magnetite and leaches K from wallrock along permeable fault damage zones.
- **Why hidden:** Altered blind faults in WalkER Lane volcanics lack scarps but show demagnetization + chemistry halos even under thin alluvium; mapped faults often have no active alteration halo (healed or unaltered lithology), so this filters for *permeable* hidden pathways relevant to geothermal.
- **How differs:** Current maglow scored independently as max(E_low); here maglow only counts if *coincident* with HG rim, and adds K depletion which is entirely absent from current physics (family only used radiometrics in scarp-fusion, never as corridor-interior primary).
- **Mimic:** Sedimentary basins also produce magnetically quiet zones but have positive K (alluvial K enrichment) — K depletion veto reduces false positives.
- **Expected gain:** medium (+0.0015–0.003) — improves geothermal relevance (permeability filter); **Cost:** low-medium (need to build K/Th stats, ~20 min)

### H3 — Releasing-basin margin asymmetry (pull-apart interiors)
- **Layers:** iso_grav_anom + iso_grav_anom_hg/vg + detrended elev (det_elev 12, det_elev_slope 19) + basement_depth (15) + scarp relief/coh100 from lidar_scarp_features_u8.tif
- **Physical signature:** Inside pull-apart rhomb (dilatational subtype only): gravity curvature low (geod_2ndinv negative or iso_grav negative residual), flanked by paired parallel HG ridges (basin-bounding faults), with lidar_scarp termini at rhomb tips (scarp ends, not continuous terrace). Curvature = Laplacian of gravity/dem.
- **Why hidden:** Pull-apart basins are Walker Lane's favored hot-system hosts (prompt); their basin floors are sediment-filled with no scarp, but gravity lows + bounding faults persist; hidden basin-bounding splays missed by fault maps are detectable as *asymmetric* flanking edges, not scalar lows.
- **How differs:** Current pull-apart scorer gives all dilatational corridors flat W_geom=1.0; this tests transverse basin structure (low interior + edge pair), not just scalar score.
- **Mimic:** Paleo-lake shorelines produce lidar coherence but lack gravity low + basement step — coherence veto.
- **Expected gain:** low-medium (+0.001–0.002) — targets specific Walker Lane preference; **Cost:** medium (need curvature calc, basin depth layer)

### H4 — En echelon scarp phase coherence
- **Layers:** lidar_scarp (ex_max/step_max/downface_max composite, 1m 3DEP) + iso_grav_anom_hg + mag_tilt_s2 for orientation reference
- **Physical signature:** Staggered oriented scarp ridges (Gabor phase coherence along corridor axis, wavelength ~0.6–1.5W) — short fault strands at ±25° to connector, alternating sides, with consistent en echelon overlap. Detect via oriented ridge filter bank, measure phase coherence across connector.
- **Why hidden:** Short linking strands between step-overs are below regional mapping resolution (USGS/INGENIOUS 1:100k–1:250k) but produce centimetre-dm scarps in 1m lidar; a *staggered* pattern is diagnostic of relay breach, not continuous terrace risers or anthropogenic lineaments.
- **How differs:** Current lidar scorer averages channel magnitude (max z); this tests spatial phase staggering, vetoing uninterrupted parallel edges.
- **Mimic:** Pluvial shorelines and road cuts produce parallel continuous scarps — phase incoherence veto.
- **Expected gain:** low (+0.0005–0.0015) — recovers fine strands but adds many candidates; **Cost:** high (filter bank + phase calc, >1h)

### H5 — Orientation-filtered geodetic dilation consistency
- **Layers:** geod_dilaterate (8), geod_shearrate (7), geod_2ndinv (4) from training_features + corridor mean_az
- **Physical signature:** Corridor axis N–NE (0–45° axial) AND local geodetic dilatation rate >0.5 MAD positive, shear rate alignment within 20° of corridor-perpendicular extension. Tests that corridor is currently dilating under WNW extension.
- **Why hidden:** Best-oriented faults dilate now, creating permeability even if no recent scarp; mapped N–NE faults already counted, but *unmapped* step-overs with same orientation + active strain are hidden geothermal targets.
- **How differs:** Current W_orient is static (cos² to 22.5°); this conditions on observed strain-rate field, not just azimuth prior.
- **Mimic:** Topographic artefacts can mimic dilatation where GPS coverage sparse — need dilatation significance weighting.
- **Expected gain:** low (+0.0005–0.001) — strain data noisy, 10km smoothing; **Cost:** low (bands already loaded)

## Ranking summary (expected gain vs cost)
1. **H1 convergent edge phase** — medium gain / medium cost — TOP, implement first
2. **H2 altered joint (HG+maglow+K)** — medium gain / low-medium cost
3. **H3 pull-apart asymmetry** — low-medium gain / medium cost
4. **H4 en echelon coherence** — low gain / high cost
5. **H5 strain orientation** — low gain / low cost (but noisy)

## Validation plan (protocol 5, must beat current holdout best before slot)
- Implement H1 as new scoring mode in src/gems69/scoring_joint.py (joint grav+mag min + tilt coincidence)
- Run leakage canary (AUC>0.90 = leakage) on full feature stack including new joint score
- Run hide-and-recover holdout (same 8 cells, seeds 20/21, same allocator, same flank prune) — record HOLDOUT-DTI +95% CI vs no-prior control AND vs current holdout best (0.0060±0.0014)
- If paired Δ >0 and corridor mean > current best (or > control with p<0.05), proceed to emission (K_truth=12691, 2px flank prune, greedy marginal-DTI) and format validation
- Then full registry uniqueness (surface pre-placement + dots final) via gems57.uniqueness two-phase summary; require rho≤0.90 and dot-field overlap≤0.70 (literal reported separately)
- Only if all gates pass, promote to site download; else log negative with run card (negative results are deliverables)
- Budget: 3 experiments or 2 hours; this is experiment 1 of 3

## External data obtainability
- H1–H3, H5: all layers already pinned in .cache/gems_data/training_features.tif (sha256 4371c82e...) and lidar_scarp_features_u8.tif (d580bb8b...), verified this session — no new external fetch needed
- H2 radiometric: ext_geodawn_rad_u8.tif already fetched and verified (c22420f7..., 26MB, bands K/Th/U/TC) — obtainable via scripts/fetch_data.py; verified obtainable
- H2 ratio ext_geodawn_extensions_u8.tif (ThK etc) also verified (a35a9c6d...)
- No new unfetchable data required; all hypotheses testable with pinned mirrors

## Irregularities flagged
- existing_faults ≡ labels (IR-69-DATA-01) — accepted family standard, holdout hides whole segments
- No DrivenData auth (IR-69-DATA-02) — using sha256-pinned mirrors, not organizer-authenticated
- Registry universal surfaces cause literal overlap gate to fire for any sparse field (IR-69-REG-01) — will report both literal and like-for-like readings per gems57.uniqueness two_phase_summary; disclosure in run card
- Tip dip polarity not observable — proxied by sub-parallel strike Δ≤30° (IR-69-DIP-01)
- Template drift resolved (IR-69-TPL-01)
