# GEMSDOE69 Verified Irregularities Summary (`docs/`)

Full audit table and SHA-256 verification receipts are maintained in [../irregularities.md](../irregularities.md), [../FLAGGED.md](../FLAGGED.md), and [irregularities.html](irregularities.html).

- **`IR-69-DATA-01`**: `labels.tif` and `existing_faults.tif` share SHA-256 `7ba308cc7cc33e4ef2fc4fa24ec05adeccffa5efbc3ff3be6fa6be4010075ff1` (`126,913` fault px in `5,167,373` valid footprint px).
- **`IR-69-DATA-02`**: Leaked column `dist_known_fault_px` in `external/gdr_wellspring_in_footprint.csv` is permanently blocked via `geodesic.FORBIDDEN_CSV_COLUMNS` (`17/17` single-feature canaries `<= 0.90`, max `0.7965`).
- **`IR-69-CODE-01..04`**: Fixed independent-origin `separation == 0` bug, `2.8 km` width-collapse priority bug, masked-tip suppression bug, and `nt == n_fp` constant-raster division-by-zero bug in `scan_registry_fast`.
- **`IR-69-REG-04` (Protocol Rule 1 Live Catch)**: Withdrew `H69_G4_SGMCReactivation` (`0.0956` `HOLDOUT-DTI`, `98.56%` overlap with `GEMSDOE30`) and `H69_G1_GeodesicCorridor` (`0.0899` `HOLDOUT-DTI`, `81.0%` overlap with `59GEMSDOE`/`12GEMSDOE`); selected `H69_G5_TwoRegimeGeodesic` (`0.0813` `HOLDOUT-DTI`, `0.6365 <= 0.70` max dotlike overlap across all `642` sparse rasters).
