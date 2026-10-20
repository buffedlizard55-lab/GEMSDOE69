# Data placement and provenance

A fresh checkout **does contain** these small, tracked, hash-pinned owner-mirror grid files:

| File | SHA-256 | Purpose |
|---|---|---|
| `bridge/sample_submission.tif` | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` | Mirrored grid/footprint contract |
| `bridge/labels.tif` | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | Public catalogue mirror |
| `bridge/existing_faults.tif` | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | Byte-identical catalogue mirror |
| `external/derived_sgmc_faults_100m_u8.tif` | `643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0` | Archived external derivative; not newly authenticated |

Integrity pins prove agreement with the owner mirrors, **not organizer-authenticated origin**. Equality of labels/existing_faults alone is not proof of a defect: the official problem describes known-fault labels as public.

The full feature/LiDAR stack and complete raster-registry cache are **not present** in this fresh checkout. Large inputs, restored mirrors and temporary audits belong in ignored `.cache/`, not a new Git dataset. `scripts/fetch_data.py` and `scripts/restore_data.py` are historical restoration tools; the two older instructions named `download_competition_data.sh` and `prepare_data.py` do not exist in this checkout.

Read HANDOFF.md before restoring or running model work. The current literal duplicate stop is binding. Restoring more bytes does not authorize another scientific experiment, silently repair provenance, or qualify an archived submission.

## Public official sources checked in this review

- DrivenData problem/data pages: labels are provided in vector and raster form, along with features, sample and DEM links; the data endpoint redirects to login. No organizer-authenticated payload obtained.
- DOE GDR 1391 lists public INGENIOUS Quaternary Faults v2 and field definitions under CC BY 4.0. Resource URL metadata is verified; official ZIP bytes, joins and footprint intersection are not newly authenticated here.
- USGS GeoDAWN DOI `10.5066/P93LGLVQ` and Siler slip/dilation DOI `10.5066/P9YL58W6`: official metadata read and CC0 observed. No official raw archive downloaded to this checkout.
- The pinned mirror `qfault_attributes.csv` **does** contain `DIPDIRECT` and `SLIPSENSE`; `trace_segments_utm11.csv` has `record_id` and `sense`. They were fetched to ignored audit storage and hash-verified. The production candidate's use of an authenticated, visible-only record join was not established.

For each future input retain source, retrieval timestamp, original filename, SHA-256, license, CRS, shape, transform, band/field names, nodata/footprint definition and processing lineage. Every catalogue-derived feature and mask must be rebuilt from visible segments only during holdout; no hidden-target-dependent distance mask.
