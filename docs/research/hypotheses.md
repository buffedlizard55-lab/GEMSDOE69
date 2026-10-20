# Historical candidate hypotheses for the relay-ramp / pull-apart lane (ranked before implementation)

> Archived pre-E2 register. Its data, holdout, and implementation-status statements are historical and are not the current run card or current-best evidence. See `untried-hypotheses-2026-10-20.md` for the reconciled current queue and `../../evidence/run_card.json` for current status.

Ranked by expected HOLDOUT-DTI improvement over the same pipeline without corridor priors, then by
implementation cost. "Expected" values are **priors written before E2**, not measurements.
Every hypothesis stays inside the assigned lane (catalogue-geometry corridors).

| Rank | Hypothesis | Layers | Physical signature | Why it could catch a fault the catalogue misses | How it differs from earlier repos | Expected gain / cost | Status |
|---|---|---|---|---|---|---|---|
| 1 | **H69-1 Relay / pull-apart / transfer corridors (the lane, arm `A_corridor`)** | INGENIOUS polylines + `DIPDIRECT`/`SLIPSENSE` (`trace_segments_utm11.csv`, `qfault_attributes.csv`); DEM (dip polarity); `iso_grav_anom`, `rtp` (multi-scale THDR + tilt, magnetic lows); lidar scarp channel | Breaching (oblique) links and en échelon strands inside same-dip step-overs; N–NE dilational faults inside releasing steps; horsetail splays / transfer links at strike-slip tips | Regional compilations (1:24k–1:250k) draw step-overs as disconnected strands; the minor linking faults that hard-link ~70 % of hot step-overs (Giddens & Faulds 2025) are below the compilation threshold yet are what a lidar-based expert panel adds | First **vector tip graph** in the family with recorded/inferred **dip polarity**, slip-sense-specific **releasing-step** logic and the published **W ≤ 15 km, \|L\| ≤ 3.5 W** rules. Earlier step-over attempts were raster distance fields: GEMSDOE33 `h33d-analog-tip-stepover-r30` (owner-reported 0.2632), GEMSDOE28 `h32-1-prethin-tip-euler` (0.2649), GEMSDOE53 tip-relay ridge-concord (0.0159), 60GEMSDOE `relay_bend_anatomy` H57-I2 (features, no dip/sense rules) | moderate / medium | **Run (E1, E2, E3)** |
| 2 | **H69-2 Corridor prior as a boost, not a restriction (arm `AP_halo_corridor`)** | as H69-1 + distance to visible catalogue | Same as H69-1, but corridor membership multiplies a generic proximity × evidence rate instead of forbidding dots elsewhere | Keeps recall on hidden faults outside step-overs while still concentrating mass in corridors | No earlier repo combined a dip/sense-aware corridor class with the halo calibration | small–moderate / low | **Run as sensitivity in E2** (not the gate) |
| 3 | **H69-3 Hard-link completion only** | as H69-1, restricted to *overlapping* relays with W 1–5 km and strong scarp evidence | The single breaching fault of an overlapping relay (stage-3 ramp, Peacock & Sanderson 1994) | ~70 % of >120 °C step-overs are hard-linked; overlapping, 2–4 km wide relays are the commonest hot geometry | Narrower than H69-1; tests whether the *best* corridors carry the signal | small / low | Not run (budget) |
| 4 | **H69-4 Opposite-dip accommodation zones** | as H69-1 with the same-dip rule inverted | Interbasinal highs / transfer faults between oppositely dipping normal faults (Faulds & Varga 1998) | Accommodation zones host the largest Nevada producers (McGinness Hills, Steamboat) and are drawn as terminating, unconnected faults | The lane's same-dip rule excludes them by construction | unknown / low | Not run (outside the literal lane rule) |
| 5 | **H69-5 Measured stress orientation instead of a fixed WNW azimuth** | INGENIOUS geodetic strain-rate tensors (`geodetics_INGENIOUS_regional_data`, zip SHA-256 `0dd65ccc…` pinned in `qfaults_receipt.json`) | Dilation tendency of each corridor under the local, not regional, extension direction | Walker Lane transtension rotates the extension direction locally | Earlier repos used only the scalar invariants (`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`) | small / medium (external file not in this sandbox's mirrors) | Not run — data obtainability: GDR (gdr.openei.org) is not reachable from this sandbox; the zip is pinned but no mirror copy was found |

## Pre-registered gate

`A_corridor` must beat `B1_halo` (identical evidence, calibration, flank rule and allocator, no
corridor prior) with a positive paired 95 % CI lower bound on both draws and pooled
(`registry/preregistration.json`). `AP_halo_corridor` is reported but cannot rescue a failed gate
(no post-hoc switching).

## Outcome (E2, pooled over draws 20 and 21; HOLDOUT-DTI, `gems57-pooled-hide-v2`, 22,893 withheld positive pixels)

| Hypothesis | Arm | HOLDOUT-DTI [95% CI] | Paired Δ vs `B1_halo` [95% CI] | Result |
|---|---|---|---|---|
| H69-1 (the lane) | `A_corridor` | 0.0749 [0.0647, 0.0853] | −0.0347 [−0.0410, −0.0278] | **FAIL** (negative on both draws: −0.0323, −0.0370) |
| H69-2 (boost) | `AP_halo_corridor` | 0.1061 [0.0957, 0.1171] | −0.0035 [−0.0048, −0.0020] | **FAIL** (sensitivity only) |
| — controls | `C_distance` / `R_corridor_random` / `B0_evidence` | 0.1259 / 0.1106 / 0.0380 | — | distance alone is the strongest arm |

Reading: on this instrument the withheld faults are explained by proximity to the visible catalogue; the corridor geometry
adds no ranking power beyond proximity, the geophysical evidence bins slightly reduce DTI, and confining dots to corridors
halves recall (TP_w 5,525 vs 10,204 for `B1_halo`).
