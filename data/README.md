# Data placement and current availability

This directory is **not empty**. The current checkout contains only small bridge inputs (`data/bridge/existing_faults.tif`, `labels.tif`, and `sample_submission.tif`) plus `data/external/derived_sgmc_faults_100m_u8.tif`. The 19-band `training_features.tif`, 12-band LiDAR scarp descriptor stack, radiometric rasters, and `.cache/gems_data` feature cache are **absent** at this review. Do not treat the old “full feature stack restored” run notes as proof of present local availability.

The files named as competition inputs in repository manifests are **owner-supplied public mirrors**, SHA-pinned but **not organizer-authenticated**. Prior project notes report that `existing_faults.tif` is byte-identical to `labels.tif` in those mirrors; this is an irregularity, not evidence that the mirrors are the official organizer package. The true private test labels are unavailable in this checkout.

Large inputs and caches belong outside Git under the existing `.gitignore` conventions. Manifests in `registry/` record the pinned mirror metadata and provenance limitations. No feature-stack restore or external download was performed in this review. Restore inputs only after explicit authorization and the active experiment/release protocol permit it; hash-check the exact bytes and record source URL, retrieval time, original filename, SHA-256, license/terms, CRS, dimensions, transform, band names, nodata/mask behavior, and footprint definition.

`data/bridge/sample_submission.tif` was used for local format validation. A local match to that owner-supplied mirror is not proof of organizer acceptance. The current candidate remains **DO NOT SUBMIT** for independent literal uniqueness, holdout-comparator, and source-provenance failures.
