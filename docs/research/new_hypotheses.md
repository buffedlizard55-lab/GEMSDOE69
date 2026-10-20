# Pre-Registered Geological Hypotheses — GEMSDOE69 (Pre-Holdout Registration)

Registered **before** running the session's 3-experiment budget (`E1` diagnostics/canaries, `E2` spatially-blocked holdout gate + controlled ablations, `E3` pre-placement + post-placement uniqueness scan & GeoTIFF packaging). All hypotheses remain strictly inside **Lane 69** (catalogue step-over / pull-apart / splay / transfer corridor proposal + multi-physics scoring + greedy marginal-DTI node placement).

---

## Rank 1 — `H69-G1`: Geodesic Breaching & Multi-Physics Ridge Localization Across Multi-Partner Relay, Tip-to-Flank Synthetic Breach, Pull-Apart, Splay & Transfer Corridors

- **Layers used:**
  - *Catalogue geometry (strictly visible traces only on each holdout fold):* `external/trace_segments_utm11.csv` (`84,331` segments, `1,126` records) + `external/qfault_attributes.csv` (`DIPDIRECT`, `SLIPSENSE`) + `external/geodawn_dem_a2_100m.tif` (hanging-wall topographic polarity where `DIPDIRECT` is unrecorded) + `training_features.tif` band 7 (`geod_shearrate`, Walker Lane shear promotion).
  - *Potential fields & high-resolution GeoDAWN extensions:* `training_features.tif` `iso_grav_anom` (band 13), `iso_grav_anom_hg` (band 18), `rtp` (band 2), `tmi_hg` (band 3), plus `external/geodawn_extensions_u8.tif` `TMI_up150` (band 4, 150 m upward-continued flight-line TMI).
  - *Geomorphic scarp & ridge channels:* `external/lidar_scarp_features_u8.tif` (`ex_max`, `step_max`, `lapneg_max`, `downface_max`, `coh100`, `valid`) + `training_features.tif` `det_elev`, `det_elev_slope` (bands 12, 19).
  - *Geochemical alteration & deep subsurface boundary channels:* `external/geodawn_extensions_u8.tif` `ThK` (band 1) + `external/geodawn_rad_u8.tif` (`K`, `Th`, bands 1–2) + `training_features.tif` `cond_surf` (band 17, MT conductivity) & `depth_to_base_surf` (band 15, basement depth).
- **Physical feature transform:**
  1. Propose corridors across all four structural interaction regimes: up to `K=4` step-over partners per free tip (`W ∈ [0.1, 15] km`, `|L| ≤ 3.5 W`), asymmetric tip-to-flank synthetic breaches (`W ∈ [0.1, 12] km`), dextral/sinistral releasing pull-aparts (links, chords, `N22.5°E` dilational strands), and strike-slip / normal fault-tip splay & transfer corridors.
  2. Route links (`1.0–18 km`) along minimum-energy geodesic fault paths (`skimage.graph.route_through_array`) through the multi-physics cost surface $\mathcal{C}(x) = \exp(-2.2 E_{\text{multi}}(x)) + 0.08$ with $\pm 100\text{ m}$ normal ridge snapping.
  3. Score each trace across 7 zero-leakage physical channels + Andersonian dilation tendency $\cos^2(\beta)$ (`EXT_AZ = 292.5°`), calibrate pixel log-odds strictly out-of-fold, and place nodes via greedy marginal-DTI (`α = 0.2, β = 0.8, R = 300 m`) at `≥ 200 m` off known traces.
- **Why it detects faults missing from the USGS / INGENIOUS catalogue:**
  1:24,000–1:250,000 mapping stops where Holocene alluvium buries the scarp between overlapping fault tips or alongside a synthetic flanking strand. Minimum-action routing locates curved buried breaching scarps, `TMI_up150`/gravity edges, `Th/K` alteration conduits, and straight MT/basement steps across the corridor interior.
- **How it differs from all existing repo & family work:**
  PR #5 kept only 1 mutual partner per tip, excluded normal-fault terminations and tip-to-flank relays, drew blind straight lines, and lacked `TMI_up150`, `Th/K`, and MT/basement step channels; PR #6 filled flat `0.68` ellipses with a broken `_tip_window_interval` along-strike check (`IR-69-CODE-01`) and zero probability calibration (`0.0060`).
- **Data source:** All 13 SHA-256-verified layers already cached locally (`0` external fetches needed).

---

## Rank 2 — `H69-G2`: Geodesic Potential-Field & Coherence-LiDAR Corridors *Without* Radiometric Alteration & Subsurface MT/Basement Channels (Controlled Geochemical/Subsurface Ablation)

- **Layers used:** Identical corridor geometry, geodesic trace routing, potential-field (`iso_grav_anom`, `rtp`, `TMI_up150`), and coherence-weighted LiDAR / `det_elev` scarp channels as `H69-G1`, **omitting** `rad_alteration` (`ThK`, `K`, `Th`) and `subsurface_step` (`cond_surf`, `depth_to_base_surf`).
- **Physical feature transform:** Clean ablation isolating the out-of-fold holdout ΔDTI contributed by airborne gamma-ray hydrothermal alteration halos and deep magnetotelluric / basement steps inside step-over corridors.
- **Why it detects faults missing from the catalogue:** Potential-field density/susceptibility contrasts and coherent microtopographic scarps image sub-alluvial intrabasinal connectors directly.
- **Distinction:** Direct controlled ablation partner to `H69-G1` within the same fold loop.

---

## Rank 3 — `H69-G3`: Hydrothermal Upflow Geothermometry Up-Weighting Inside Step-Over & Pull-Apart Corridors

- **Layers used:** All `H69-G1` corridor features + thermal excess field from `external/gdr_wellspring_in_footprint.csv` (`temp_c`, `geothermquartz_c`, `geothermchalc_c` — **explicitly dropping precomputed `dist_known_fault_px` on load to prevent label leakage!**).
- **Physical feature transform:** Multi-scale (`1.2 km`, `3.0 km`) thermal anomaly excess $\max(T_{\text{meas}}, 0.5 T_{\text{quartz}}, 0.5 T_{\text{chalc}})$ interacted with corridor membership, testing Giddens & Faulds' (2025) observation that ~70% of higher-temperature step-overs are hard-linked.
- **Why it detects faults missing from the catalogue:** Hot springs and thermal wells vent directly above permeable hard-linked breaching faults even beneath young playa evaporites or sinter aprons where scarps are erased.
- **Distinction:** Never previously tested in `GEMSDOE69`; explicitly tests whether thermal upflow helps general hidden-fault DTI or over-weights hot geothermal fields relative to cool unmapped Quaternary faults.

---

## Rank 4 — `H69-G4`: Pre-Quaternary Bedrock Fault Reactivation Inside Step-Over & Transfer Corridors

- **Layers used:** `external/derived_sgmc_faults_100m_u8.tif` (USGS State Geologic Map Compilation pre-Quaternary bedrock faults, rasterized at 100 m) inside `H69-G1` step-over/transfer corridors — **strictly gated on passing single-feature Leakage Canary `AUC ≤ 0.90` in `E1` first!**
- **Physical feature transform:** 300-m kernel density of pre-Quaternary bedrock faults intersected with Quaternary step-over / displacement-transfer corridors.
- **Why it detects faults missing from the catalogue:** Many Quaternary breaching links reactivate pre-existing Mesozoic/Cenozoic bedrock structures mapped in bedrock compilation maps (`SGMC`) that have not yet been recognized as Quaternary-active in `Qfaults`.
- **Distinction:** Tests structural inheritance specifically inside catalogue step-over and transfer corridors rather as a standalone bedrock map.

---

## Rank 5 — `H69-G5` (External Data Candidate): Relocated Walker Lane / Great Basin Microseismicity Lineaments & Focal-Mechanism Nodal Planes

- **External official free public data source:** **USGS ANSS Comprehensive Earthquake Catalog (`ComCat` API)** — `https://earthquake.usgs.gov/fdsnws/event/1/` (U.S. Federal public domain, 17 U.S.C. § 105; free anonymous HTTP query by bounding box `[38.9°N..42.4°N, -120.1°W..-115.8°W]`, `M ≥ 1.0`, plus ANSS focal mechanisms).
- **Physical feature transform:** Replace the coarse pre-binned `ieq_n100a15` / `deq_n100a15` scalar density rasters (`AUC ≈ 0.52`) with 3D relocated hypocentral lineament strike fields (`RANSAC / Hough` cluster axes at depth `2–12 km`) and double-couple nodal-plane strikes inside Walker Lane pull-aparts and displacement-transfer corridors.
- **Why it detects faults missing from the catalogue:** Active low-slip-rate transtensional transfer faults in the Walker Lane (e.g., Nine Mile, Gabbs Valley, Carson Sink) illuminate sharply in relocated microseismicity decades before accumulating preservable surface scarps in unconsolidated playa sediments.
- **Sandbox status:** **`DATA-BLOCKED IN SANDBOX`** (`earthquake.usgs.gov` is outside the sandbox network allowlist `github.com / codeload.github.com / api.github.com / registry.npmjs.org / pypi.org / files.pythonhosted.org`). Documented with exact public API parameters for pre-fetch outside the sandbox.
