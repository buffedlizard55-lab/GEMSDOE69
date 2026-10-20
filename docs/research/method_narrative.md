# Historical method narrative — relay-ramp and pull-apart corridor generator

> This narrative records an earlier source-rich design and is not a claim about the current `src/gems69` implementation. Its polyline/attributes and dip-inference statements require renewed provenance checks; the current code uses the raster catalogue and does not measure dip polarity or slip sense. See the current method page and `evidence/run_card.json`.

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
