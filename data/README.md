# data/ (not committed)

Place the official competition files here after logging in at DrivenData and accepting the
rules (https://www.drivendata.org/competitions/306/competition-doe-gems/data/):

- `training_features.tif`   (feature stack, EPSG:32611, 100 m)
- `labels.tif`              (training fault labels, raster)
- `existing_faults.tif`
- `sample_submission.tif`   (format template)
- `1m_DEM_links.csv`

Then run `python scripts/status.py`. Files are git-ignored on purpose: the data is licensed to
registered competitors and must not be redistributed through a public repository.
