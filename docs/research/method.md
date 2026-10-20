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
| Relay ramp (normal / unknown sense) | facing tips (outward directions antiparallel within 35°), **same dip polarity**, W 0.1–15 km, \|L\| ≤ 3.5 W; up to `max_partners = 4` valid partners per tip | oblique tip-to-tip connector; breaching links from each tip to the partner trace; 1–3 en échelon strands across the ramp; normal-fault tip continuations (2.5 km) and wing splays (±22° to N–NE dilation strike); flank-relay breaches to the nearest 2 off-component fault traces within 6 km |
| Pull-apart (RL–RL or LL–LL) | facing tips, **releasing** step (RL right-stepping, LL left-stepping), same W and 3.5 W limits | two basin-bounding links, tip-to-tip chord, up to three strands striking 22.5° (perpendicular to WNW extension) |
| Transfer zone (RL / LL tip) | every free strike-slip tip | two horsetail splays rotated 20° and 40° into the extensional quadrant (right of the outward direction for RL, left for LL); links to the nearest two normal-fault traces within 6 km ahead / on the extensional side |

On the full catalogue the generator emits 7,171 relay pairs (**mean width 2.83 km**, median
1.92 km; 54.8 % overlapping), 1,932 releasing-step pull-aparts, 1,115 strike-slip terminations,
468 transfer links, 4,515 tip continuations, 4,515 wing splays, and 13,200 flank-relay breaches.
The published step-over population (Giddens & Faulds 2025) has mean width 2.8 km and ~50 %
overlapping (55.3 % in the western Great Basin) — a consistency check on the geometry. With
`dline ≤ 8 px` (800 m), the corridor band covers 47.8 %–65.5 % of the allowed footprint per
quadrant while capturing **84.1 %–95.8 %** of withheld truth across holdout folds.

## 3. Scoring, hierarchical empirical-Bayes calibration, and placement

* **Evidence (none catalogue-derived):** multi-scale gravity and magnetic edges (isostatic gravity
  anomaly and RTP upward-continued to 200 m / 600 m / 1.8 km; rank(THDR) × (1 − |tilt|/90°), max over
  scales), local magnetic lows (−(RTP − 3 km Gaussian)), lidar scarp channel (0.45 ex_max + 0.35
  step_max + 0.20 downface_max, by band name).
* **Orientation:** dilation tendency cos²β of each trace under WNW (292.5°) extension (maximal for
  NNE strikes).
* **Corridor score:** equal-weight mean of the five terms (pre-registered, no fitting).
* **3-level hierarchical empirical-Bayes calibration (`src/gems69/calibrate.py`):** leave-one-quadrant-out
  empirical-Bayes rate estimation `P(withheld truth | d_vis × d_line × d_tip × s_band × e_pix)` where
  1D distance rate `r1(d_vis)` shrinks toward global `p0` (`m_v = 100`), 3D geometric corridor rate
  `r_geom(d_vis, d_line, d_tip)` shrinks toward `r1(d_vis)` (`m_g = 250`), and full 5D rate
  `r_full(d_vis, d_line, d_tip, s_band, e_pix)` shrinks toward `r_geom` (`m_f = 350`). Quantile edges
  are fitted strictly on training quadrants only.
* **300 m kernel-radius decimated placement (`src/gems69/pipeline.py`):** candidates are decimated on
  3×3 pixel tiles (`tile_px = 3`, matching the 300 m triangular kernel radius so adjacent pixels do not
  stack redundant FP mass inside one kernel disk) and passed to the shared template's `emit.greedy_allocate`
  inside the corridor band (`s_band > 0`), with zero dots on or within 200 m of the catalogue (`d_vis > 2 px`).

## 4. Instruments

* **Hide-and-recover holdout** (template `holdout.buffered_component_draw`, two draws): whole
  8-connected catalogue components withheld (20 % of each quadrant's catalogue pixels), a 3 px
  collar removed from every catalogue-derived feature, visible faults masked pixel-exactly, pooled
  DTI by the template evaluator `gems57-pooled-hide-v2` with paired 20 km spatial-block bootstrap.
* **Leakage canary:** each feature alone, AUC of withheld-truth vs non-truth pixels (limit 0.90).
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
| `corridor_score_band` | 0.697 |
| `neg_dist_corridor_trace` | 0.717 |
| `neg_dist_visible_tip` | 0.739 |

Leakage flags (AUC > 0.90): **none**.

### E1 — hard-linked-ramp masking test

349 catalogue links joining two traces were found; 43 satisfy the relay rules after masking. Mean recovery within 300 m: **0.993** (kernel-weighted 0.841) versus **0.697** for random-azimuth traces from the same tips (links beating the null's 95th percentile: 4.7%). Rejections: {'rejected_dip': 4, 'rejected_facing': 54, 'rejected_step_sense': 4, 'rejected_geometry': 240, 'rejected_mixed_sense': 4}.

### E2 — gate (HOLDOUT-DTI, pooled over two draws)

Evaluator `gems57-pooled-hide-v2`; withheld positive pixels pooled: 22,893.

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
| `A_corridor` | 0.1347 | [0.1231, 0.1463] |
| `AP_halo_corridor` | 0.1334 | [0.1218, 0.1450] |
| `B1_halo` | 0.1264 | [0.1151, 0.1382] |
| `B0_evidence` | 0.0823 | [0.0713, 0.0936] |
| `C_distance` | 0.1218 | [0.1109, 0.1333] |
| `R_corridor_random` | 0.1112 | [0.1005, 0.1208] |

**Gate (A_corridor − B1_halo): Δ = +0.0083, 95% CI [+0.0039, +0.0123] → PASS (positive on both draws: `per_draw_lower_bound_positive = True`).**

Sensitivity (corridor prior as a boost, AP − B1): Δ = +0.0070, 95% CI [+0.0029, +0.0112].

#### Per draw and quadrant (HOLDOUT-DTI / dots)

| Draw | Arm | NW | NE | SW | SE |
|---|---|---|---|---|---|
| seed20 | `A_corridor` | 0.1211 / 17,825 | 0.1248 / 21,938 | 0.1467 / 33,814 | 0.1574 / 25,571 |
| seed20 | `AP_halo_corridor` | 0.1208 / 18,122 | 0.1239 / 22,196 | 0.1459 / 34,086 | 0.1566 / 25,998 |
| seed20 | `B1_halo` | 0.1220 / 25,694 | 0.1112 / 32,280 | 0.1400 / 42,092 | 0.1473 / 34,394 |
| seed20 | `B0_evidence` | 0.0690 / 43,811 | 0.0512 / 36,203 | 0.0885 / 53,764 | 0.1029 / 50,658 |
| seed20 | `C_distance` | 0.1121 / 32,071 | 0.1103 / 40,776 | 0.1261 / 49,894 | 0.1488 / 37,049 |
| seed20 | `R_corridor_random` | 0.1075 / 17,825 | 0.0978 / 21,938 | 0.1172 / 33,814 | 0.1304 / 25,571 |
| seed21 | `A_corridor` | 0.1309 / 17,313 | 0.1014 / 21,690 | 0.1423 / 33,449 | 0.1336 / 24,521 |
| seed21 | `AP_halo_corridor` | 0.1264 / 18,093 | 0.1002 / 22,012 | 0.1393 / 34,296 | 0.1344 / 25,002 |
| seed21 | `B1_halo` | 0.1199 / 25,963 | 0.0958 / 33,351 | 0.1256 / 43,167 | 0.1387 / 33,410 |
| seed21 | `B0_evidence` | 0.0696 / 37,652 | 0.0695 / 39,094 | 0.0765 / 43,206 | 0.1140 / 46,044 |
| seed21 | `C_distance` | 0.1158 / 31,480 | 0.0912 / 40,151 | 0.1274 / 49,793 | 0.1360 / 37,074 |
| seed21 | `R_corridor_random` | 0.1005 / 17,313 | 0.0812 / 21,690 | 0.1165 / 33,449 | 0.1217 / 24,521 |

### E3 — live build of the lane artefact

* 43,056 dots, 0 on the catalogue, min / median / p95 distance to the catalogue 0.22 / 0.63 / 1.70 km.
* Corridors that received dots: 16,426 — by setting: {'relay': {'corridors': 12860, 'dots': 34804}, 'pullapart': {'corridors': 3003, 'dots': 7257}, 'transfer': {'corridors': 563, 'dots': 995}}. Per-corridor rationale: [`evidence/e3_corridor_rationale.csv`](https://github.com/buffedlizard55-lab/GEMSDOE69/blob/main/evidence/e3_corridor_rationale.csv).
* Live tip graph: 4,523 free tips; corridor counts 8,069 relays, 2,139 pull-aparts, 1,115 terminations, 4,523 tip continuations, 4,523 wing splays, 13,362 flank-relay breaches.
* The owner-reported 0.2778 champion has 62.0% of its dots inside our corridor band (the band is 55.0% of the allowed area); 25.7% of our dots lie within 3 px of a champion dot.

### Uniqueness (862-raster corpus, `registry/registry_index_69.json`)

| Phase | Worst Spearman (limit 0.90) | Comparable-budget (<80k dots, 584 rasters) 3-px overlap | Literal 3-px overlap (incl. continuous / >=80k-dot halos) | Discriminating firings | Decision |
|---|---|---|---|---|---|
| surface | 0.489 (GEMSDOE2:data/evidence/runs/turbo-simple-20260925T041759Z/submission.tif) | n/a (surface phase) | 1.000 (68 firings) | n/a | unique |
| dots | 0.100 (7GEMSDOE:downloads/gems7-halo15-gbt-v1-90fb7dc0fc1f.tif) | 0.6971 (GEMSDOE53:docs/submissions/gems53-h1-thin_bin_q0p1-20261008-aefc7582.tif) | 1.000 (87 firings) | 0 | unique |

Decision rule: surface phase: Spearman > 0.90 vs any of 862 rasters; dots phase: Spearman > 0.90 vs any of 862 rasters, byte/pixel identity, or > 70% of dots within 3 px of any comparable-budget dot-field raster (< 80,000 dots, 584 rasters checked; worst is 0.6971 vs GEMSDOE53 aefc7582) or any discriminating dense firing (0 firings). Literal overlap vs continuous surfaces and >= 80,000-dot blanket halos / lattices is reported side-by-side.
