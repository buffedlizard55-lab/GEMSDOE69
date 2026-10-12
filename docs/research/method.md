# Method — relay-ramp and pull-apart corridor generator

## 1. Catalogue polylines and the tip graph

* **Polylines.** The INGENIOUS Quaternary-fault export (`trace_segments_utm11.csv`, 84,331 straight
  segments) is grouped by `record_id` and split into continuous parts (13,953 parts from 1,126
  records). The join to `qfault_attributes.csv` (row index = `record_id`) was verified on slip rate
  and slip sense for 1,126 / 1,126 records, and the rasterised traces coincide with the competition
  catalogue raster (99.98 % of catalogue pixels within 100 m of a trace).
* **Dip polarity.** Recorded `DIPDIRECT` where usable (projection on the local trace normal ≥ 0.3);
  otherwise the hanging wall is taken as the topographically lower side (mean DEM at 600 m and
  1.2 km either side). The inference agrees with the recorded dip on **90.3 %** of 1,984 comparable
  polylines.
* **Free tips.** Polyline ends with no other trace within 250 m, at least 300 m inside the
  footprint, on polylines ≥ 300 m long; outward direction from the last 1 km of trace. In holdout
  runs, tips created by cutting a trace at the withheld/collar mask are excluded (IR-69-08).

## 2. Corridors (candidate fault traces)

| Setting | Pairing rule | Traces emitted |
|---|---|---|
| Relay ramp (normal / unknown sense) | facing tips (outward directions antiparallel within 35°), **same dip polarity**, W 0.1–15 km, \|L\| ≤ 3.5 W; each tip keeps only its nearest valid partner | oblique tip-to-tip connector; breaching links from each tip to the partner trace; 1–3 en échelon strands across the ramp |
| Pull-apart (RL–RL or LL–LL) | facing tips, **releasing** step (RL right-stepping, LL left-stepping), same W and 3.5 W limits | two basin-bounding links, tip-to-tip chord, up to three strands striking 22.5° (perpendicular to WNW extension) |
| Transfer zone (RL / LL tip) | every free strike-slip tip | two horsetail splays rotated 20° and 40° into the extensional quadrant (right of the outward direction for RL, left for LL); links to the nearest two normal-fault traces within 6 km ahead / on the extensional side |

On the full catalogue the generator finds 2,473 relay pairs (**mean width 2.83 km**, median
1.92 km; 54.8 % overlapping), 732 releasing-step pull-aparts and 1,115 strike-slip terminations.
The published population (Giddens & Faulds 2025) has mean width 2.8 km and ~50 % overlapping
(55.3 % in the western Great Basin) — a consistency check on the geometry, not a validation.

## 3. Scoring and placement

* **Evidence (none catalogue-derived):** multi-scale gravity and magnetic edges (isostatic gravity
  anomaly and RTP upward-continued to 200 m / 600 m / 1.8 km; rank(THDR) × (1 − |tilt|/90°), max over
  scales), local magnetic lows (−(RTP − 3 km Gaussian)), lidar scarp channel (0.45 ex_max + 0.35
  step_max + 0.20 downface_max, by band name).
* **Orientation:** dilation tendency cos²β of each trace under WNW (292.5°) extension (maximal for
  NNE strikes).
* **Corridor score:** equal-weight mean of the five terms (pre-registered, no fitting).
* **Calibration:** leave-one-quadrant-out binned rates P(withheld truth | score decile × distance to
  trace) with shrinkage; quantile edges from training quadrants only.
* **Placement:** the shared template's `emit.greedy_allocate` (exact marginal-DTI acceptance under a
  clipped-convolution surrogate) inside the corridor band only; no dot on or within 200 m of the
  catalogue.

## 4. Instruments

* **Hide-and-recover holdout** (template `holdout.buffered_component_draw`, two draws): whole
  8-connected catalogue components withheld (20 % of each quadrant's catalogue pixels), a 3 px
  collar removed from every catalogue-derived feature, visible faults masked pixel-exactly, pooled
  DTI by the template evaluator `gems57-pooled-hide-v2` with paired 20 km spatial-block bootstrap.
* **Leakage canary:** each feature alone, AUC of withheld-truth vs non-truth pixels.
* **Hard-link masking test:** catalogue links joining two traces are masked; the generator must
  recover them within 300 m; compared with random-azimuth traces from the same tips.

## 5. Results (generated from `evidence/*.json`)

### E1 — leakage canary (draw seed 20, pooled over quadrants)

| Feature | AUC (withheld truth vs other pixels) |
|---|---|
| `grav_edge` | 0.526 |
| `mag_edge` | 0.542 |
| `mag_low` | 0.491 |
| `scarp` | 0.585 |
| `e_pix` | 0.579 |
| `neg_dist_visible_catalogue` | 0.756 |
| `corridor_score_band` | 0.604 |
| `neg_dist_corridor_trace` | 0.724 |
| `neg_dist_visible_tip` | 0.739 |

Leakage flags (AUC > 0.90): **none**.

### E1 — hard-linked-ramp masking test

349 catalogue links joining two traces were found; 43 satisfy the relay rules after masking. Mean recovery within 300 m: **0.993** (kernel-weighted 0.841) versus **0.697** for random-azimuth traces from the same tips (links beating the null's 95th percentile: 4.7%). Rejections: {'rejected_mixed_sense': 4, 'rejected_dip': 4, 'rejected_geometry': 240, 'rejected_facing': 54, 'rejected_step_sense': 4}.

Post-hoc paired view of the same rows (no new experiment): corridor traces beat the null mean on 97.7% of the 43 admissible links (mean gain +0.297, one-sided Wilcoxon p = 8.2e-09); the 95th-percentile criterion is saturated (93% of null p95 values equal 1.0). Admissible links are short (median 0.66 km), so this geometric agreement is real but small in metric terms.

### E2 — gate (HOLDOUT-DTI, pooled over two draws)

Evaluator `gems57-pooled-hide-v2`; withheld positive pixels pooled: 22,893.

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
| `A_corridor` | 0.0749 | [0.0647, 0.0853] |
| `AP_halo_corridor` | 0.1061 | [0.0957, 0.1171] |
| `B1_halo` | 0.1096 | [0.0986, 0.1206] |
| `B0_evidence` | 0.0380 | [0.0308, 0.0451] |
| `C_distance` | 0.1259 | [0.1134, 0.1380] |
| `R_corridor_random` | 0.1106 | [0.0976, 0.1230] |

**Gate (A_corridor − B1_halo): Δ = -0.0347, 95% CI [-0.0410, -0.0278] → FAIL.**

Sensitivity (corridor prior as a boost, AP − B1): Δ = -0.0035, 95% CI [-0.0048, -0.0020].

#### Per draw and quadrant (HOLDOUT-DTI / dots)

| Draw | Arm | NW | NE | SW | SE |
|---|---|---|---|---|---|
| seed20 | `A_corridor` | 0.0554 / 27,027 | 0.0535 / 29,727 | 0.1005 / 47,279 | 0.0922 / 33,730 |
| seed20 | `AP_halo_corridor` | 0.0989 / 36,526 | 0.0931 / 40,343 | 0.1140 / 68,345 | 0.1202 / 49,736 |
| seed20 | `B1_halo` | 0.1072 / 34,027 | 0.0949 / 39,749 | 0.1145 / 67,940 | 0.1263 / 46,603 |
| seed20 | `B0_evidence` | 0.0399 / 95,933 | 0.0142 / 67,139 | 0.0343 / 51,901 | 0.0430 / 51,027 |
| seed20 | `C_distance` | 0.1210 / 24,756 | 0.1153 / 29,626 | 0.1382 / 50,434 | 0.1361 / 37,295 |
| seed20 | `R_corridor_random` | 0.0909 / 15,055 | 0.0866 / 15,873 | 0.1342 / 27,417 | 0.1288 / 18,195 |
| seed21 | `A_corridor` | 0.0584 / 26,893 | 0.0498 / 29,583 | 0.0830 / 48,742 | 0.0778 / 34,572 |
| seed21 | `AP_halo_corridor` | 0.1091 / 35,729 | 0.0802 / 39,346 | 0.1033 / 67,508 | 0.1187 / 48,531 |
| seed21 | `B1_halo` | 0.1108 / 36,278 | 0.0848 / 33,676 | 0.1049 / 70,156 | 0.1238 / 44,694 |
| seed21 | `B0_evidence` | 0.0416 / 83,981 | 0.0425 / 87,596 | 0.0312 / 50,692 | 0.0580 / 48,052 |
| seed21 | `C_distance` | 0.1272 / 24,041 | 0.0876 / 28,656 | 0.1360 / 47,533 | 0.1270 / 34,221 |
| seed21 | `R_corridor_random` | 0.0961 / 13,922 | 0.0768 / 15,832 | 0.1240 / 26,211 | 0.1132 / 18,165 |

Note on `R_corridor_random`: it was asked for as many dots as `A_corridor` in every quadrant, but 2-px Poisson-disk spacing fits only 150,670 of 277,553 (54%) inside the corridor band, so it is a density-limited random control, not a count-matched one. Its higher DTI with fewer dots is itself the evidence that the greedy over-emits inside corridors.

### E3 — live build of the lane artefact

* 33,680 dots, 0 on the catalogue, min / median / p95 distance to the catalogue 0.30 / 0.89 / 2.52 km.
* Corridors that received dots: 1,948 — by setting: {'relay': {'corridors': 1063, 'dots': 21616}, 'pullapart': {'corridors': 560, 'dots': 9432}, 'transfer': {'corridors': 325, 'dots': 2632}}. Per-corridor rationale: [`evidence/e3_corridor_rationale.csv`](https://github.com/buffedlizard55-lab/GEMSDOE69/blob/main/evidence/e3_corridor_rationale.csv).
* Live tip graph: 4,523 free tips; corridor counts 2,473 relays, 732 pull-aparts, 1,115 terminations.
* The owner-reported 0.2778 champion has 23.3% of its dots inside our corridor band (the band is 18.2% of the allowed area); 29.5% of our dots lie within 3 px of a champion dot.

### Uniqueness (862-raster corpus, `registry/registry_index_69.json`)

| Phase | Worst Spearman (limit 0.90) | Literal 3-px overlap | Overlap vs dot fields (template like-for-like) | Discriminating firings | Decision |
|---|---|---|---|---|---|
| surface | 0.284 (7GEMSDOE:downloads/gems7-halo15-gbt-v1-90fb7dc0fc1f.tif) | 1.000 (74 firings) | 1.000 (13GEMSDOE:docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif) | n/a | unique |
| dots | 0.076 (5GEMSDOE:data/derived/context_detector_prob_topo_rad.tif) | 1.000 (96 firings) | 1.000 (13GEMSDOE:docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif) | 22 | DUPLICATE |

Decision rule: surface phase: Spearman > 0.90 vs any raster; dots phase: Spearman > 0.90 vs any raster or > 70% of dots within 3 px of one dot-field raster's dots (support <= 20% of footprint). Literal overlap vs continuous surfaces reported as degenerate diagnostics.
