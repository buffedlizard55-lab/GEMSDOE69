# GEMSDOE69 Three-Pass Research, Engineering & Audit Report — 2026-10-20 (`H69-K`)

## Executive Status: `NEGATIVE — DO NOT SUBMIT` (Fail-Closed Literal Policy Enforced; Zero Slots Spent)

1. **Was a genuinely new, unique, validated GeoTIFF generated in this session?** **YES.**
   - **Portal-shaped file (`all-finite float32` in `[0, 1]`, `EPSG:32611`, `3730×3292`, `100 m` grid):**
     `submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros.tif`
   - **SHA-256:** `04b75259720baa2c52b7e9c56a2b3bccc471e3500a6112e782d95422419ae67b` (`156,596` bytes; `54,471` unit dots; `0` mapped-catalogue collisions; `0` outside-footprint positives; `0` NaN).
   - **Spec-literal diagnostic twin (`NaN` outside footprint ONLY — do not upload to portal):**
     `submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-nan.tif` (`236,385` bytes; SHA-256 `493700d9...`).
   - **Submission Name (if upstream selector authorizes):** `h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros`
   - **Submission Note (`123/140` chars):** `H69-K kinematic relay/pull-apart + horsetail corridors; cross-axis grav/RTP edge; EB-calibrated greedy DTI (54471 dots)`
2. **Is it OK to download and upload to DrivenData right now?** **NO — DO NOT SUBMIT.**
   - No `.tif` or `.zip` is published in `docs/downloads/` and no competition slot was spent.
   - `H69-K` passes **every** science, leakage-canary, source-manifest, and pixel-format validator gate AND passes sparse dot-field overlap across all `≤150,000`-dot family rasters (`0.6860 ≤ 0.70`), all `≤80,000`-dot rasters (`0.6860 ≤ 0.70`), `h33-2-b2` (`0.2540`), and all `7` prior `GEMSDOE69` rasters (`≤ 0.0750`).
   - However, under `scripts/release_gate.py` (`vendor/template66/gems57/uniqueness.py` byte-pinned literal rule), `17GEMSDOE:docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` is strictly positive (`[0.8416, 1.0]`) on **all `5,167,373` of `5,167,373` footprint cells** (`evidence/e3_saturation_certificate.json`, `uncovered_allowed_pixels = 0`), forcing literal forward `3-px` overlap to `1.0000 > 0.70` for every nonempty prediction mathematically possible on the GeoDAWN grid. Rather than weakening `release_gate.py`, we strictly honor `duplicate-and-stop` and archive the verified `H69-K` GeoTIFF for upstream selector review.

---

## PhD Answer: Why Did `h33-h33-2-b2-...-zeros` Achieve `0.2778` and Can a Unique Submission Beat `0.2778` / `0.3195`?

- **Evidence labels:** `0.2778` (`h33-h33-2-b2`), `0.3195`, `0.3774`, and `0.4413` are **USER-REPORTED-NOT-ORGANIZER-CONFIRMED** (prompt highs conflict, no organizer submission receipt is checked into git, and `drivendata.org` is outside sandbox outbound network access). The checked-in public snapshot `registry/leaderboard_snapshot_2026-10-12.json` recorded rank 1 at `0.4275` and rank 9 at `0.3195` on `2026-10-12`.
- **Byte-measured anatomy (`evidence/e0_champion_ladder_measured.json`, `evidence/relayfix_champion_anatomy.json`):** `h33-h33-2-b2-zeros` contains `37,654` pixels at `1.0`, `0` on the mapped catalogue, minimum distance `2.24 px` (`224 m`) from mapped faults, median distance `1.97 km`, and only `5.77%` within `300 m`.
- **Exact metric algebra (`α = 0.2, β = 0.8, R = 300 m` triangular kernel):**
  1. **Kernel non-redundancy (`121,131 → 44,090` dots, `+0.0678` reported jump):** Truth coverage uses $\max_{p} k(d(g, p))$ while false positives sum $0.2 \sum_p (1 - m(p))$ over every predicted pixel. Replacing continuous 100 m ribbons with `~2.8 px` spaced dots cuts false-positive denominator mass ~3× while retaining >80% peak kernel coverage.
  2. **Exact marginal acceptance inequality & 200 m flank pruning (`44,090 → 37,654` dots, `+0.0178` reported jump):** Adding a unit dot with marginal uncovered truth credit $dT$ and self-credit $m$ increases DTI iff $dT > \frac{0.2\,\text{DTI}}{1 - 0.2\,\text{DTI}}(1 - m)$. At $\text{DTI} = 0.2778$, the bar scale is $c = 0.0588$. Removing `6,436` flank dots sitting `100–200 m` off already-masked catalogue faults pruned below-bar false positives.
- **Can a unique submission beat `0.2778` / `0.3195`?** Thinning `H33` further cannot produce a large jump and violates uniqueness. Reaching `0.32–0.40+` requires higher truth credit per dot on unmapped basin-interior step-over, pull-apart, and splay structures (`H69-K` places `74.6%` of its mass outside `300 m` of `H33`, `Spearman ρ = +0.0064`). Only an organizer receipt from an authorized weekly slot can confirm live leaderboard lift.

---

## Five Candidate Lane-69 Geological Hypotheses (Ranked Before Holdout Look)

1. **`H69-K` (Rank 1 — Implemented & Validated):** Kinematics-resolved polyline tip graph joining recorded INGENIOUS `DIPDIRECT` & slip sense (`RL`/`LL`/`N`) + validated DEM hanging-wall polarity (`90.27%` accuracy), emitting synthetic relay connectors, pull-apart rhomb sidewalls, cross-ramp breaches, en échelon strands, overlapping tip-to-flank relays, and tensile horsetail splays; scored by cross-corridor directional potential-field gradients ($|\nabla F_{300\text{m}} \cdot \hat{n}_c|$ on `iso_grav_anom` and `rtp` + multi-scale upward-continued tilt edges + `3 km` RTP demagnetization lows + `1 m` 3DEP scarp + WNW dilation tendency) with out-of-fold 3-level empirical-Bayes calibration and decimated greedy marginal-DTI allocation.
2. **`H69-L` (Rank 2 — Queued):** Upward-continuation depth-persistence ratio ($\text{THDR}_{1800\text{m}} / \text{THDR}_{200\text{m}}$ on `rtp` and `iso_grav_anom`, normalized by `depth_to_base_surf`) along step-over connectors to separate basement-cutting geothermal conduits from thin surficial lava lobes.
3. **`H69-M` (Rank 3 — Queued):** Flank-normalized bilateral alteration contrast comparing corridor core (`d ≤ 2 px`) directly against matched host wallrock (`4 ≤ d ≤ 10 px`) in RTP demagnetization and `Th/K` (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`), eliminating regional lithologic variance.
4. **`H69-N` (Rank 4 — Queued):** Longitudinal relay-ramp tilt gradient (`det_elev`, `det_elev_slope`) paired with transverse Laplacian inflection maxima (`lapneg_max`, `lappos_max` in `lidar_scarp_features_u8.tif`) to detect monoclinal flexural warps undergoing incipient breach.
5. **`H69-O` (Rank 5 — Queued):** Local geodetic strain-rate tensor coupling (`geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`) + microseismic proximity (`deq_n100a15`, `ieq_n100a15`) weighting active transtensional step-overs.

---

## Summary of Three Verification Passes

### Pass 1 — Implementation, Root-Cause Bug Discovery, and Controlled Holdout Execution
- Merged latest `origin/main` (`6b055f3`, PR #21), restored all `9/9` SHA-256-pinned GeoDAWN/3DEP/INGENIOUS inputs (`scripts/restore_data.py` + `scripts/fetch_data.py`), and restored all `862/862` registry rasters (`0` errors).
- Discovered and fixed **two severe bugs** that depressed all prior checked-in GEMSDOE69 runs to `0.0059–0.0085` `HOLDOUT-DTI`:
  1. **`IR-69-17` (`src/gems69/holdout69.py`):** `run_holdout_arms` computed `offcat = edt(~ctx.grid.catalogue) > 2` and `leakage_canary` evaluated `ctx.grid.catalogue` (containing hidden target faults!), carving 200 m exclusion holes around every target fault. Repaired to use strictly per-cell `ctx.visible(key)`.
  2. **`IR-69-CALIB-01` (`calibrate.py`, `pipeline.py`):** Uncalibrated `sigmoid(1.5*(S - 0.75))` yielded $E[k] \ge 1.0$ everywhere so $1 - k_{\text{self}} = 0$ collapsed `greedy_allocate`'s marginal bar to `0`. Replaced with 3-stage out-of-fold empirical-Bayes calibration.
- Executed `H69-K` strictly within the 3-experiment budget on byte-pinned `vendor/template66/gems57`:
  - **Untouched draws `[22, 23]` (`HOLDOUT-DTI`, `8` folds, `22,641` withheld positives):** `A_corridor = 0.1439` (`[0.1325, 0.1553]`) vs `B1_halo = 0.1406` (`+0.0033` pooled; **wins `7/8` folds**, paired fold `Δ = +0.0042 ± 0.0035`, `95% CI [+0.0007, +0.0076]`; single-seed sub-block bootstrap `[-0.0007, +0.0072]`).
  - **Benchmark draws `[20, 21]` (`HOLDOUT-DTI`, `8` folds, `22,893` withheld positives):** `A_corridor = 0.1492` vs `B1_halo = 0.1421` (**wins `8/8` folds**, paired `Δ = +0.0071`, spatial-block bootstrap `95% CI [+0.0030, +0.0112]`).
  - **Combined 16 folds (`45,534` withheld positives):** **wins `15/16` folds** (`p = 0.00052`), pooled `0.1465` vs `0.1413` (`+0.0052`, paired `95% CI [+0.0030, +0.0080]`).
  - **Hard-link 300 m masking recovery:** **`1.0000`** across all `69` admissible ramps (null `0.9524`).
  - **Leakage canaries (`14` features):** max AUC **`0.7751 ≤ 0.90`** (`0` flags).

### Pass 2 — Adversarial Code, Registry, and Site Review
- Caught and fixed live-catalogue candidate volume inflation (`61.1%` footprint coverage across un-filtered splays) by enforcing top-corridor selection (`score ≥ p72`, `34,518` corridors covering `15.34% < 20%` of footprint, `54,471` unit dots).
- Scanned **all `924` unique SHA-256-verified EPSG:32611 family rasters** (`862` base + `62` newly published post-Oct-12 rasters across `GEMSDOE63..74`, `0` errors) on both pre-placement `surface` (frozen before placement) and final `dots`: `0` byte/pixel matches; surface `|ρ| = 0.3011 ≤ 0.90`; dots `|ρ| = 0.1149 ≤ 0.90`; `≤150k` dotlike overlap `0.6860 ≤ 0.70`; `≤80k` overlap `0.6860 ≤ 0.70`; vs `H33` overlap `0.2540`; vs all `7` prior `GEMSDOE69` files `≤ 0.0750`.
- Fixed hardcoded `H69-J` strings in `scripts/release_gate.py` (`write_card`) while keeping `python scripts/release_gate.py` side-effect-free audit-only; fixed hardcoded `0.4413` live-fetch claims in `scripts/build_site69.py`; upgraded `scripts/build_readme.py` and `scripts/fetch_registry.py`.

### Pass 3 — End-to-End Verification Against Original Prompt & Repository Contracts
- Re-sealed `evidence/e3_method_manifest.json` against exact final source SHA-256s, generated `evidence/run_card.json`, rebuilt `README.md`, `index.html`, and all `9` pages in `docs/`.
- Verified `vendor/template66/TEMPLATE_SHA256.txt` (`11/11` files byte-identical), `scripts/validate_submission.py` (`PASS` on both `-zeros.tif` and `-nan.tif`), `scripts/release_gate.py` (cleanly fails closed solely on the 3 literal dense-surface keys), `.venv/bin/pytest -q` (`108 passed`), and `git diff --check` (clean).

---

## Remaining Work & Limitations for Next Session

1. **Upstream Selector Decision (Primary Blocker):** Amend the shared registry uniqueness policy in `vendor/template66` to evaluate `3-px` dot overlap against sparse predictions (`support_fraction ≤ 0.20`) while keeping full-footprint Spearman rank correlation across all continuous soft surfaces. Once authorized, `submissions/h69k-kinematic-directional-54471-20261020T234210Z-2e7341e9-zeros.tif` is already validated and ready for selector slot allocation.
2. **Organizer Data Authentication:** When authenticated access to DrivenData's data tab is available on an unrestricted machine, verify SHA-256 parity between organizer `existing_faults.tif` / `sample_submission.tif` and our pinned mirrors (`IR-69-DATA-01`, `IR-69-DATA-02`).
3. **Next Science Iteration (on fresh untouched seeds `[24, 25]`):** Test queued Hypothesis `H69-L` (upward-continued depth-persistence ratio across step-over connectors) and `H69-M` (wallrock-normalized radiometric/RTP contrast).
