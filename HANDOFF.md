# Handoff — 2026-10-20 (Post-Pass-3 Complete State)

Read `README.md` first, then `reports/review-2026-10-20.md` and `FLAGGED.md`.

## Current Status: **NOT OK TO SUBMIT — DO NOT SUBMIT** (`verdict = "negative"`, `download_enabled = false`)

All **6 scientific & engineering items** from the prior handoff are now **100% implemented, verified, and hash-bound** across Experiments `E1`, `E2`, and `E3`, and no DrivenData slot was used:

1. **All 9 code/data bugs fixed & verified (`pytest -q`: `0` failures, `0` xfails):**
   - `IR-69-LIDAR-STRIKE-01`: `lidar_scarp_features_u8.tif` Band 11 converted from image-axis orientation to compass strike `(raw * 180 / 255 + 90) % 180` (`79.04° -> 10.96°` error).
   - `IR-69-TIP-01` & `IR-69-CORR-01`: shared world-origin `_tip_window_interval`, full `hypot(W, 3.5W)` KD-tree radius, and minimum-distance facing tip-pair deduplication (`pair_catalogue(5, 40)` and `pair_catalogue(50, 160)` both pass strictly).
   - `IR-69-DIP-01`: leak-free `attach_catalogue_kinematics` joining `trace_segments_utm11.csv` + `qfault_attributes.csv` (`SLIPSENSE`, `SECONDARY`, `DIPDIRECT`) + DEM hanging-wall polarity strictly within `visible_catalogue`.
   - `IR-69-HOLDOUT-01/02/03`: fixed truth-masking flank leak (`ctx.grid.catalogue` -> `visible`), fixed canary full-catalogue input, and fixed minus-sign bug in `hardlinked_recovery` (`0 -> 781` ramps found, `99.44%` mean 300 m recovery across `80` disconnected bridges).
2. **In-Lane Science & Holdout Gate (`E1` + `E2` — ALL PASS):**
   - `E1` Canaries: `33/33` features `<= 0.90` (`corridor_multiplicity` = **`0.59082`**, #1 single predictor).
   - `E2` Primary `mode = "all"` (`22,641` withheld px): **`H69-EFG` = `0.072701`** `[0.055864, 0.086004]` vs **`no_prior_control` = `0.047245`** `[0.042280, 0.051753]` (**`+0.025456` / `+53.9%`**, `7/8` cells won, `p = 1.0000`, **`9.03x`** prior `0.008050`).
   - `E2` Conservative `mode = "detached"` (`22,619` detached px `>= 400 m`): **`H69-EFG` = `0.067664`** `[0.052539, 0.081458]` vs **`no_prior_control` = `0.050269`** (**`+0.017396` / `+34.6%`**, **`8/8` cells won**, `p = 1.0000`, `-22.5%` dot mass).
3. **Why Standalone Submission Remains Blocked (`E3` Registry Scan — `751/751` blobs, `0` errors):**
   - Validated candidate `submissions/h69-efg-kinematic-geodesic-29027-zeros.tif` (`sha256: 25cdba0acab1c9eec96f48a78f72c7621a5d7abca49440176b606a955ea0e63f`, `29/29` format checks `PASS`) passes Spearman cleanly (`max |rho| = 0.1448 <= 0.90`) and has only **`0.3121` (`31.21%`) 3-px overlap with `GEMSDOE32` `h33-2-b2-zeros`**, **but** collides `> 0.70` in 3-px forward proximity with universal soft surfaces (`1.000`) AND sibling `40k–103k`-dot scarp/corridor rasters (`GEMSDOE43` `0.848`, `GEMSDOE53` `0.908`, `GEMSDOE37` `0.960`).

## Clear Next Steps to Beat `0.2778` (`USER-REPORTED-NOT-ORGANIZER-CONFIRMED`)

1. **Cross-Lane Surgical Delta into `h33-2-b2-zeros` (Designated Integrator Repo):** Export ONLY the **`68.79%` (`19,967` dots) of `H69-EFG` corridor dots lying `> 300 m` outside `h33-2-b2-zeros`**, filter to top calibrated interior bridge credit (`E[k] > 0.08 > 0.0588` marginal threshold, `~1,500–2,500` dots), and fuse into `h33-2-b2-zeros`.
2. **External Blind-Basin Data Acquisition (Outside Sandbox):** Fetch raw 1 m USGS 3DEP tiles (`tnmaccess.nationalmap.gov`, `H69-H`) and relocated ANSS/UNR microseismicity hypocenters (`earthquake.usgs.gov`, `H69-I`) to target blind zero-scarp playas where existing scarp/halo lanes have `< 5%` density.
