# Data placement

This directory intentionally contains no competition data yet. The official DrivenData Data tab redirected to login during the 2026-10-12 UTC review. No account session was used and no protected file was downloaded.

The current project metadata references these likely official files; confirm exact names, geometry, and schema from the authenticated organizer package before using them:

- `training_features.tif` — multiband feature stack
- `labels.tif` — training fault labels
- `existing_faults.tif` — catalogue/known-fault layer
- `sample_submission.tif` — authoritative submission-grid template
- `1m_DEM_links.csv` — source list for 1 m DEM tiles

Keep all competition inputs, public mirrors, and large rasters out of Git. The root `.gitignore` excludes them; only this README is tracked. For every authorized input, record source URL, retrieval time, original filename, SHA-256, license/terms, CRS, dimensions, transform, band names, nodata/mask behavior, and footprint definition in a manifest.

The official USGS 3DEP one-meter DEM collection is a free public-domain source with no-account download, but exact tile intersection with the competition footprint and agreement with the competition link list remain unverified. A feature channel or sample file must not be assumed to exist because a prior project page mentions it.
