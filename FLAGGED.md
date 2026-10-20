# FLAGGED ITEMS — Explicit Protocol Rule 1, Rule 3 & Rule 4 Dispositions

1. **STOPPED & WITHDRAWN CROSS-LANE CANDIDATES (`Protocol Rule 1` — `evidence/e2_gate.json`):**
   - `H69_G4_SGMCReactivation` achieved **`0.0956` `HOLDOUT-DTI`** (`95% CI [0.0842, 0.1075]`), **but failed Protocol Rule 1** with **`0.9856 > 0.70`** 3-px dot overlap against `buffedlizard55-lab/GEMSDOE30:docs/downloads/gemsdoe30-edge-hybrid-80k.tif` (`SGMC` pre-Quaternary bedrock fault lane). **Withdrawn immediately; NOT emitted as a submission.**
   - `H69_G1_GeodesicCorridor` (`0.0899` `HOLDOUT-DTI`) and `H69_G3_HydroGeotherm` (`0.0895` `HOLDOUT-DTI`) concentrated dots along near-tip collars and bare range-front scarps (`> 0.70` overlap with `59GEMSDOE` / `12GEMSDOE`). **Withdrawn; replaced in Experiment 3 by `H69_G5_TwoRegimeGeodesic` (`0.0813` `HOLDOUT-DTI`, `0.6365 <= 0.70` max dotlike overlap across all `642` sparse rasters, `0.6465 <= 0.90` max `|Spearman rho|` across all `826` rasters).**
2. **BLOCKED LEAKAGE COLUMN (`Protocol Rule 4`):**
   - `external/gdr_wellspring_in_footprint.csv` contains column `dist_known_fault_px`. Reading this column is hard-blocked in `src/gems69/geodesic.py` (`FORBIDDEN_CSV_COLUMNS`).
3. **IDENTICAL OFFICIAL LABEL & EXISTING-FAULT RASTERS (`IR-69-DATA-01`):**
   - `labels.tif` and `existing_faults.tif` have identical SHA-256 `7ba308cc7cc33e4ef2fc4fa24ec05adeccffa5efbc3ff3be6fa6be4010075ff1`.
4. **UNVERIFIABLE LOGIN-GATED CLAIMS (`Protocol Rule 3`):**
   - DrivenData leaderboard figures (`0.3774`, `0.3195`, and `h33-2-b2` `0.2778`) are strictly tagged `USER-REPORTED-NOT-ORGANIZER-CONFIRMED` throughout all JSON, Markdown, and HTML files. No weekly submission slots were spent (`submission_slots_used = 0`).
