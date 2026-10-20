# Candidate hypotheses for the relay-ramp / pull-apart lane (ranked before implementation)

Ranked by expected HOLDOUT-DTI improvement over the same pipeline without corridor priors, then by
implementation cost. "Expected" values are **priors written before E2**, not measurements.
Every hypothesis stays inside the assigned lane (catalogue-geometry corridors).

| Rank | Hypothesis | Layers | Physical signature | Why it could catch a fault the catalogue misses | How it differs from earlier repos | Expected gain / cost | Status |
|---|---|---|---|---|---|---|---|
| 1 | **H69-1 Relay / pull-apart / transfer + tip-splay / flank-breach corridors (the lane, arm `A_corridor`)** | INGENIOUS polylines + `DIPDIRECT`/`SLIPSENSE` (`trace_segments_utm11.csv`, `qfault_attributes.csv`); DEM (dip polarity); `iso_grav_anom`, `rtp` (multi-scale THDR + tilt, magnetic lows); lidar scarp channel | Breaching (oblique) links, en échelon strands, wing splays and flank-relay breaches inside same-dip step-overs; N–NE dilational faults inside releasing steps; horsetail splays / transfer links at strike-slip tips | Regional compilations (1:24k–1:250k) draw step-overs as disconnected strands; the minor linking faults that hard-link ~70 % of hot step-overs (Giddens & Faulds 2025) are below the compilation threshold yet are what a lidar-based expert panel adds | First **vector tip graph** in the family with recorded/inferred **dip polarity**, slip-sense-specific **releasing-step** logic, **W ≤ 15 km, \|L\| ≤ 3.5 W** rules, 3-level hierarchical empirical-Bayes calibration, and 300 m kernel-decimated greedy allocation (`tile_px = 3`) | moderate / medium | **Run (E1, E2, E3) — PASS** |
| 2 | **H69-2 Corridor prior as a boost, not a restriction (arm `AP_halo_corridor`)** | as H69-1 + distance to visible catalogue | Same as H69-1, but corridor membership multiplies a generic proximity × evidence rate across the entire allowed footprint instead of restricting dots to the corridor band | Keeps recall on hidden faults outside step-overs while still concentrating mass in corridors | No earlier repo combined a dip/sense-aware corridor class with hierarchical empirical-Bayes halo calibration | small–moderate / low | **Run as sensitivity in E2** (beats `B1_halo` by +0.0070) |
| 3 | **H69-3 Hard-link completion only** | as H69-1, restricted to *overlapping* relays with W 1–5 km and strong scarp evidence | The single breaching fault of an overlapping relay (stage-3 ramp, Peacock & Sanderson 1994) | ~70 % of >120 °C step-overs are hard-linked; overlapping, 2–4 km wide relays are the commonest hot geometry | Narrower than H69-1; tests whether the *best* corridors carry the signal | small / low | Not run (budget) |
| 4 | **H69-4 Opposite-dip accommodation zones** | as H69-1 with the same-dip rule inverted | Interbasinal highs / transfer faults between oppositely dipping normal faults (Faulds & Varga 1998) | Accommodation zones host the largest Nevada producers (McGinness Hills, Steamboat) and are drawn as terminating, unconnected faults | The lane's same-dip rule excludes them by construction | unknown / low | Not run (outside the literal lane rule) |
| 5 | **H69-5 Measured stress orientation instead of a fixed WNW azimuth** | INGENIOUS geodetic strain-rate tensors (`geodetics_INGENIOUS_regional_data`, zip SHA-256 `0dd65ccc…` pinned in `qfaults_receipt.json`) | Dilation tendency of each corridor under the local, not regional, extension direction | Walker Lane transtension rotates the extension direction locally | Earlier repos used only the scalar invariants (`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`) | small / medium (external file not in this sandbox's mirrors) | Not run — data obtainability: GDR (gdr.openei.org) is not reachable from this sandbox; the zip is pinned but no mirror copy was found |

## Pre-registered gate

`A_corridor` must beat `B1_halo` (identical evidence, calibration, flank rule and allocator, no
corridor prior) with a positive paired 95 % CI lower bound on both draws and pooled
(`registry/preregistration.json`).

## Outcome (E2, pooled over draws 20 and 21; HOLDOUT-DTI, `gems57-pooled-hide-v2`, 22,893 withheld positive pixels)

| Hypothesis / Control | Arm | HOLDOUT-DTI [95% CI] | Paired Δ vs `B1_halo` [95% CI] | Result |
|---|---|---|---|---|
| H69-1 (the lane) | `A_corridor` | **0.1347 [0.1231, 0.1463]** | **+0.0083 [+0.0039, +0.0123]** | **PASS** (positive on both draws: +0.0085 [+0.0020, +0.0149], +0.0082 [+0.0015, +0.0145]) |
| H69-2 (boost) | `AP_halo_corridor` | 0.1334 [0.1218, 0.1450] | +0.0070 [+0.0030, +0.0110] | **PASS** (sensitivity arm) |
| Gate comparator | `B1_halo` | 0.1264 [0.1151, 0.1382] | 0.0000 (reference) | Baseline (same pipeline without corridor priors) |
| Distance-only control | `C_distance` | 0.1218 [0.1109, 0.1333] | −0.0046 | Beaten by `A_corridor` (+0.0129 [+0.0086, +0.0172]) |
| Corridor random control | `R_corridor_random` | 0.1112 [0.1005, 0.1208] | −0.0152 | Beaten by `A_corridor` (+0.0235 [+0.0175, +0.0295]) |
| Evidence-only control | `B0_evidence` | 0.0823 [0.0713, 0.0936] | −0.0441 | Beaten by `A_corridor` (+0.0525 [+0.0439, +0.0609]) |

Reading: once corridor geometry includes multi-partner relay connectors (`max_partners = 4`), tip continuations / wing splays, and flank-relay breaches (`include_splays = True`, capturing 84.1 %–95.8 % of withheld truth inside the 800 m corridor band), and candidate dots are calibrated by 3-level hierarchical empirical-Bayes shrinkage and placed with 300 m kernel-radius decimation (`tile_px = 3`), the corridor lane `A_corridor` beats every comparator on the spatially-blocked hide-and-recover holdout.
