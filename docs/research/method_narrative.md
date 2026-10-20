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
