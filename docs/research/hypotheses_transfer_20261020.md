# New candidate geological hypotheses — GEMSDOE69 post-H69-J (2026-10-20)
Generated: 2026-10-20T21:45Z — Before next implementation, 5 distinct hypotheses not yet tried in this lane
Evidence class: hypothesis proposal (no new holdout look beyond archived H69-J/transfer)
All use catalogue-geometry tip graph W 0.1–15 km, along ≤3.5W, same-dip via sub-parallel strikes (IR-69-DIP-01), not pixel statistics.

## Current baseline after H69-J promotion
- Corridor joint-convergent arm (H1): pooled DTI 0.00591±0.00125 vs control 0.00215±0.00058, Δ+0.00376±0.00148, 8 cells, 22,641 withheld px, gate PASSED (HOLDOUT-DTI, gems57 pooled hide-and-recover α0.2 β0.8 R300m seeds 20/21)
- Control: same physics layers without corridor prior, identical allocator/flank
- Leakage canary worst AUC 0.6909 (corridor_propensity) <0.90 PASS
- Hard-link recovery mean 0.86 within 300m, median 1.0
- Transfer-only variant (non-dilatational overlapping corridors, 3,151 raw pairs, 1,200 capped): pooled DTI 0.00847 vs control 0.00215 vs corridor_v1 0.00635, prompt gate PASSED, distinctness 0.26–0.28 vs prior H69 dots <0.70
- Registry worst |ρ| 0.162 <0.90, dot-field overlap 0.61 <0.70 (literal 1.0 from universal continuous_surface with support_fraction >0.20 is non-discriminating per DENSE_SUPPORT_FRACTION, reported separately)

Question: why did H33 (reported 0.2778 USER-REPORTED-NOT-ORGANIZER-CONFIRMED) score and can transfer+junction beat it? H33 used sparse dotted field on broad multi-physics lineament far from catalogue, exploiting high precision per dot. Beating it requires higher mean credit per dot via joint signatures that reject lithologic single-physics contacts.

All layers below are verified pinned mirrors (sha256 pinned, NOT organizer-authenticated) or official free sources:
- training_features.tif 19 bands (sha256 4371c82e...), source: owner mirror of DrivenData competition file login-walled, bands verified via evidence/band_metadata.json (e.g., iso_grav 13, tmi 14, basement_depth 15, cond_surf 17, geod_2ndinv 4, geod_dilat 8, geod_shear 7)
- lidar_scarp_features_u8.tif (sha256 d580bb8b...), source: derived from USGS 3DEP 1m DEM tiles (706/716 tiles, tile list OCR from competition PDF, USGS 3DEP public domain no-use-restriction)
- geodawn_rad_u8.tif (sha256 c22420f7...), source: USGS GeoDAWN DOI 10.5066/P93LGLVQ K/Th/U/TC grids, uint8-quantised 1st-99th percentile
- geodawn_extensions_u8.tif (sha256 a35a9c6d...), source: USGS GeoDAWN extensions Th/K, U/K ratios

Official verified links for manual review (checked 2026-10-20):
- USGS 3DEP: https://www.usgs.gov/3d-elevation-program (free public-domain 1m DEM, includes lidar point clouds)
- GeoDAWN: https://doi.org/10.5066/P93LGLVQ — Airborne magnetic and radiometric surveys, northwestern Great Basin (USGS data release)
- Giddens & Faulds (2025) SGP-TR-229: https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Giddens.pdf — >450 step-overs inventoried, ramps 3–3.5× longer than wide, widths 0.1–14.6 km mean 2.8 km, ~70% hard-linked
- Walker Lane dextral prior: Faulds et al. regional structural synthesis (cited in prompt); N-NE faults best oriented for dilation under WNW extension
- Competition overview: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (requires login for data, public leaderboard)
- EPSG:32611: https://epsg.io/32611 — WGS84 / UTM zone 11N
- Tversky index (DTI scorer family): https://en.wikipedia.org/wiki/Tversky_index

## Ranked new hypotheses (layer → signature → why hidden → difference → expected gain/cost)

### H6 — Transfer-overlap + joint convergent edge (TOP CANDIDATE, validates to 0.00847 already)
- **Layers:** iso_grav (13) + tmi (14) via HG_s1/2/4 + tilt_s2 edge + mag_low_tmi/rtp + lidar_scarp; specifically grav_hg_s2, mag_hg_s2, mag_low_tmi, grav_tilt_s2, mag_tilt_s2
- **Physical signature:** *Overlapping* tip pairs (along >0.5W) emit narrow transfer corridors (oblique connector only, half-width clamp(W/6,1,6)px, no rhomb); scoring S = 0.35·min(E_grav,E_mag) + 0.15·max(E_grav,E_mag) + 0.15·E_low·gate(joint>0.5) + 0.15·E_lidar + 0.10·W_orient + 0.10·W_geom (AND logic). Joint grav+mag requires coincident basement offset; overlapping hard-linked relays host breaching faults even though they are contractional geometry.
- **Why hidden vs catalogue:** Mapped faults show single strong scarp edge; hidden breaching faults in overlapping hard-linked ramps are below USGS/INGENIOUS 1:100k mapping resolution but offset basement conductivity/depth and produce linear magnetic lows; they sit within 300m of masked linking faults (hardlink recovery 0.86).
- **How differs:** All prior H69 emissions were dilatational-biased (pull-apart 70% quota, width-stratified); this uses ONLY transfer-overlap corridors (3,151 deduped pairs, cap 1,200 by _priority), not tried as primary emission. Joint scoring differs from additive OR baseline.
- **Mimic:** Restraining-overlap pressure ridges and pluvial shorelines can mimic breaching lineaments; joint grav+mag vetoes single-physics lithologic contacts.
- **Expected DTI gain:** medium-high (+0.002–0.004 over H69-J, ~30–50% relative) — already measured 0.00847 vs 0.00591; **Cost:** low (geometry filter + existing z-stack, 20 min CPU)
- **External data:** none new — all layers pinned and verified (training_features 4371c82e, lidar d580bb8c)
- **Validation:** pooled HOLDOUT-DTI 0.00847 vs control 0.00215 (Δ+0.0063, bootstrap 95% CI lower bound >0 per relayfix_exp2b), canary worst AUC <0.90, hardlink recovery 0.86, distinctness 0.26–0.28 vs prior H69 dots <0.70, registry dot-field overlap 0.61 <0.70

### H7 — Radiometric depletion + conductivity step joint (altered damage zone)
- **Layers:** cond_surf (17) via cond_hg_s2 + cond_tilt_s2 + basement_depth (15) via base_hg_s2/base_tilt_s2 + geodawn_rad_u8 K+Th depletion rad_depl = -(K+Th)/2 robust-z + mag_low_tmi
- **Physical signature:** Inside corridor interior, jointly high conductivity HG ridge (cond_hg_s2 >1.0z) + radiometric depletion (rad_depl >1.0z) + magnetic low (mag_low_tmi >0.8z) with rim HG ridge. Hydrothermal alteration destroys magnetite, leaches K/Th from wallrock, and enhances conductivity via clay alteration along permeable damage zones.
- **Why hidden:** Altered blind faults in Walker Lane volcanics lack scarps (no lidar) but show demagnetization + chemistry halos under thin alluvium (1–2 km); mapped healed faults lack active halo, so this filters for permeable geothermal pathways, not just any mapped fault.
- **How differs:** Current radiometric use was additive (v3 weight 0.06) not joint; here depletion only counts if coincident with conductivity HG (AND logic + local background subtraction σ_local 2px vs σ_bg 20px), entirely absent from prior corridor scoring (family used radiometrics only in scarp-fusion vicariously).
- **Mimic:** Sedimentary basin fill produces magnetically quiet but K-enriched alluvium (positive K), vetoed by K depletion requirement; alluvial composition false positives reduced.
- **Expected gain:** medium (+0.0015–0.003) — improves geothermal relevance filter; **Cost:** low-medium (need K/Th stats, already cached geodawn_rad_u8 26MB, 20 min)
- **External data if needed:** none — geodawn_rad_u8 already fetched and verified (c22420f7, 26MB, bands K=1 Th=2 verified); no new fetch needed; official source USGS GeoDAWN DOI 10.5066/P93LGLVQ

### H8 — Pull-apart basin interior gravity low + flanking magnetic edge pair (basin margin asymmetry)
- **Layers:** iso_grav (13) + iso_grav_hg (18)/vg (11) + det_elev (12)/slope (19) + basement_depth (15) + lidarscarp coh100/relief + geod_2ndinv (4) curvature
- **Physical signature:** Inside dilatational pull-apart rhomb only: gravity curvature low (geod_2ndinv negative or iso_grav negative residual vs 3km Gaussian) + paired parallel HG ridges (basin-bounding faults, grav_hg_s2 and mag_hg_s2 >0.8z on both margins) + lidar_scarp termini at rhomb tips (scarp ends, not continuous terrace). Tests transverse basin structure, not scalar low.
- **Why hidden:** Walker Lane hot systems sit more often in pull-aparts/transfer zones (prompt); basin floors are sediment-filled with no scarp, but gravity lows + basement steps persist; hidden basin-bounding splays missed by USGS maps are detectable as asymmetric flanking edges, not single lows.
- **How differs:** Current pull-apart scorer gives all dilatational corridors flat W_geom=1.0; this tests interior low + edge pair geometry (aspect ratio 3–3.5), vetoing isotropic lows.
- **Mimic:** Paleo-lake shorelines produce lidar coherence but lack gravity low + basement step — coherence veto.
- **Expected gain:** low-medium (+0.001–0.002); **Cost:** medium (need curvature calc, basin depth layer, 30 min)
- **External data:** none new — all bands in training_features pinned

### H9 — En echelon scarp phase coherence (staggered strand detector)
- **Layers:** lidar_scarp ex_max/step_max/downface_max composite (1m 3DEP via lidar_scarp_features_u8.tif) + iso_grav_hg + mag_tilt_s2 orientation reference + cond_hg_s2 veto
- **Physical signature:** Staggered oriented scarp ridges: Gabor phase coherence along corridor axis, wavelength 0.6–1.5W, short strands at ±25° to connector, alternating sides, consistent overlap 0.3–0.7W. Detect via oriented ridge filter bank (0°,22.5°,45° axial), measure phase coherence across connector (circular variance <0.3).
- **Why hidden:** Short linking strands between step-overs are below regional mapping resolution (1:100k–1:250k) but produce cm-dm scarps in 1m lidar; staggered pattern is diagnostic of relay breach, not continuous terraces or roads.
- **How differs:** Current lidar scorer averages max z magnitude; this tests spatial phase staggering, vetoing uninterrupted parallel edges.
- **Mimic:** Pluvial shorelines and anthropogenic lineaments produce parallel continuous scarps — phase incoherence veto.
- **Expected gain:** low (+0.0005–0.0015); **Cost:** high (filter bank + phase calc >1h, 2-core limit)
- **External data if needed:** USGS 3DEP 1m DEM tiles directly if lidar_scarp_features_u8 unavailable — free public domain via https://www.usgs.gov/3d-elevation-program and AWS Open Data 3DEP (https://registry.opendata.aws/usgs-lidar/); tile list from competition PDF links (Digital-elevation-model-links-JSON.pdf) — obtainable via scripts/fetch_data.sh + prepare_data.py, verified this session that 706/716 tiles exist in lidar composite

### H10 — Geodetic dilation-strain orientation filter (active dilation)
- **Layers:** geod_dilat (8) + geod_shear (7) + geod_2ndinv (4) from training_features + corridor mean_az + iso_grav_hg for lithologic veto
- **Physical signature:** Corridor axis N-NE (0–45° axial) AND local geodetic dilatation rate >0.5 MAD positive + shear rate alignment within 20° of corridor-perpendicular extension (WNW 112.5°). Tests corridor is currently dilating under WNW extension, creating permeability.
- **Why hidden:** Best-oriented faults dilate now even if no recent scarp; mapped N-NE faults already counted, but unmapped step-overs with same orientation + active strain are hidden geothermal targets.
- **How differs:** Current W_orient static cos² to 22.5°; this conditions on observed strain-rate field (GPS-derived), not azimuth prior alone.
- **Mimic:** Sparse GPS coverage can alias topography as dilatation — need significance weighting by geod error band (if available) or distance to GPS station.
- **Expected gain:** low (+0.0005–0.001) — strain data 10km smoothing noisy; **Cost:** low (bands already loaded)
- **External data if needed:** UNAVCO/NSF GAGE GPS velocity field and strain-rate inversion (free, https://www.unavco.org/data/gps-gnss/gps-gnss.html and https://doi.org/10.1029/2007JB005114 strain method) — but training_features already contains geod_* bands derived from same, so no new fetch needed for validation; independent validation would require Nevada Geodetic Laboratory http://geodesy.unr.edu/

## Ranking summary (expected gain vs cost, 5 new)
1. **H6 transfer + joint convergent** — medium-high gain / low cost — TOP, already validated 0.00847 > 0.00591, beats control with CI>0
2. **H7 radiometric+conductivity joint** — medium gain / low-medium cost
3. **H8 basin margin asymmetry** — low-medium gain / medium cost
4. **H10 strain orientation** — low gain / low cost (but noisy)
5. **H9 en echelon coherence** — low gain / high cost

## Validation plan for H6 (must beat current holdout best before slot)
- Implement geometry filter: keep ONLY dilatational==False (overlap >0.5W) from repaired build_tip_pairs, dedup by _pair_key, cap 1,200 by _priority
- Scoring: joint weights 0.35·min(E_grav,E_mag) + 0.15·max + 0.15·E_low·gate + 0.15·E_lidar + 0.10·W_orient + 0.10·W_geom, S0=0.75
- Run leakage canary: every z-stack feature alone + transfer propensity vs withheld truth per cell AUC; any >0.90 = leakage disqualify
- Run hide-and-recover holdout 8 cells seeds 20/21, same allocator flank 2px, pooled DTI; record corridor vs control vs corridor_v1 (current best 0.00635 pooled); require paired bootstrap 2000 lower bound >0 for transfer > control AND transfer > v1 to claim promotion; else emission is negative result
- Emission: full-catalogue transfer corridors, greedy marginal-DTI 12,691 dots prior, 2px flank prune, binary 1.0
- Uniqueness: surface-before-placement + dots-final vs registry_index_69.json 862 entries; require ρ≤0.90 and dot overlap ≤0.70 on dot fields (literal 1.0 from universal continuous_surface reported separately per DENSE_SUPPORT_FRACTION=0.20); hash/pixel-agreement check vs prior_rasters 751 blobs
- Validator: float32 EPSG:32611 100m, [0,1], NaN only outside footprint, single band, transform match sample_submission
- Only if all gates pass, promote to site download; else log negative run card (negative results are deliverables)
- Budget: 3 experiments or 2 hours; H6 is experiment 2 of 3 (Exp2b), H7 would be 3 if pursued

## External data obtainability audit (2026-10-20 live checks)
- H6–H8, H10: layers in training_features.tif (sha256 4371c82e..., 418MB, 19 bands) + lidar_scarp_features_u8.tif (d580bb8b..., 36MB) verified via scripts/fetch_data.py — no new external fetch needed, both pinned mirrors exist
- H7 radiometric: geodawn_rad_u8.tif c22420f7... + geodawn_extensions_u8 a35a9c6d... already fetched via same script, verified obtainable (USGS source DOI 10.5066/P93LGLVQ)
- H9 scarp alternative: USGS 3DEP 1m DEM via https://apps.nationalmap.gov/downloader/ and AWS Open Data — obtainable, but current lidar composite already covers 706/716 tiles, so no new data needed for validation
- All hypotheses testable with free official public-domain data; no unfetchable external required

## Irregularities flagged
- IR-69-DATA-01 existing_faults ≡ labels (byte-identical 425,830 bytes, sha256 7ba308cc...) — accepted family standard, holdout hides whole 8-connected components
- IR-69-DATA-02 No DrivenData auth — using sha256-pinned family mirrors, NOT organizer-authenticated; provenance recorded in registry/data_manifest_gemsdoe32.json
- IR-69-REG-01 universal surfaces cause literal overlap 1.0 for any sparse field — will report both literal and like-for-like via gems57.uniqueness.two_phase_summary, per family precedent GEMSDOE63/64
- IR-69-DIP-01 dip polarity unobservable — proxied by sub-parallel strike Δ≤30°, disclosed per corridor
- IR-69-VAL-01 footprint proxy disagreement ~1.5k cells between training_features band1 finite and sample_submission finite — portal contract is sample_submission
