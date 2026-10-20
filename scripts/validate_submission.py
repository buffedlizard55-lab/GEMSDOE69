#!/usr/bin/env python3
"""Validate a GEMS submission GeoTIFF against the published format and the portal range rule.

Usage:  python scripts/validate_submission.py FILE.tif [FILE2.tif ...] [--json OUT.json]

Checks (published spec, competition page 967 "Submission format", plus the portal's
"Predicted values must be in range [0, 1]" rejection):
  * single band, float32, EPSG:32611, 3730 x 3292, transform == sample_submission.tif
  * every footprint cell finite and in [0, 1]; no +/-inf anywhere; no sentinel values
  * NaN allowed ONLY outside the footprint (published: "outside bounds null/nan")
  * no positive value outside the footprint; no positive value on the mapped catalogue
  * if the file has no NaN at all it is also run through the shared template's
    fail-closed validator (gems57.validate + gems57.gates.format_report)
Exit code 0 only if every check passes for every file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems69.data import DATA, load_grid  # noqa: E402

SENTINELS = (-3.4028234663852886e38, -9999.0, -999999.0, 3.4028234663852886e38)


def check(path: Path, grid) -> dict:
    with rasterio.open(path) as src, rasterio.open(DATA / "sample_submission.tif") as ref:
        a = src.read(1)
        meta = dict(count=src.count, dtype=src.dtypes[0], crs=str(src.crs), shape=list(src.shape),
                    transform=list(tuple(src.transform)[:6]), nodata=None if src.nodata is None else str(src.nodata),
                    bounds=list(src.bounds))
        same_transform = src.transform == ref.transform and src.bounds == ref.bounds
    fp, cat = grid.footprint, grid.catalogue
    finite = np.isfinite(a)
    same_mask_shape = a.shape == fp.shape == cat.shape
    inside = a[fp] if same_mask_shape else np.empty(0, dtype=a.dtype)
    finite_values = a[finite]
    inside_valid = bool(same_mask_shape and inside.size and np.isfinite(inside).all())
    checks = {
        "single_band": meta["count"] == 1,
        "dtype_float32": meta["dtype"] == "float32",
        "crs_epsg_32611": meta["crs"] == "EPSG:32611",
        "shape_3730x3292": meta["shape"] == [3730, 3292],
        "transform_and_bounds_match_sample_submission": bool(same_transform),
        "mask_shapes_match_raster": bool(same_mask_shape),
        "footprint_all_finite": inside_valid,
        "footprint_values_in_0_1": bool(inside_valid and inside.min() >= 0 and inside.max() <= 1),
        "no_infinite_values": bool(not np.isinf(a).any()),
        "nan_only_outside_footprint": bool(same_mask_shape and not np.isnan(inside).any()),
        "no_sentinel_values": bool(not np.isin(a[finite], SENTINELS).any()),
        "all_finite_values_in_0_1": bool(finite_values.size and finite_values.min() >= 0 and finite_values.max() <= 1),
        "no_positive_outside_footprint": bool(same_mask_shape and not (np.nan_to_num(a[~fp]) > 0).any()),
        "zero_positive_on_mapped_catalogue": bool(same_mask_shape and not (np.nan_to_num(a[cat]) > 0).any()),
    }
    rep = dict(file=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               meta=meta, n_nan=int(np.isnan(a).sum()),
               n_nan_inside_footprint=int(np.isnan(inside).sum()) if same_mask_shape else None,
               min=float(finite_values.min()) if finite_values.size else None,
               max=float(finite_values.max()) if finite_values.size else None,
               positive_pixels=int((np.nan_to_num(a) > 0).sum()),
               distinct_positive_values=sorted({float(v) for v in np.unique(a[finite & (a > 0)])})[:10],
               checks=checks)
    if not same_mask_shape:
        rep["template_validator"] = "not run: invalid raster/mask grid shape"
        checks["template_validator_passed"] = False
    elif rep["n_nan"] == 0:
        from gems57 import gates, validate
        tv = validate.validate(path, fp, cat)
        fr = gates.format_report(path, DATA / "sample_submission.tif", footprint=fp)
        rep["template_validator"] = dict(all_checks_passed=tv["all_checks_passed"], checks=tv["checks"])
        rep["template_format_report"] = dict(ok=fr["ok"], problems=fr["problems"])
        checks["template_validator_passed"] = bool(tv["all_checks_passed"] and fr["ok"])
    else:
        rep["template_validator"] = "skipped: file carries outside-footprint NaN (spec-literal twin); the template enforces an all-finite policy"
        checks["nan_mask_equals_sample_submission_nan_mask"] = bool(np.array_equal(np.isnan(a), ~fp))
    rep["all_checks_passed"] = bool(all(checks.values()))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json")
    args = ap.parse_args()
    grid = load_grid()
    reports = [check(Path(f), grid) for f in args.files]
    ok = all(r["all_checks_passed"] for r in reports)
    out = dict(validator="scripts/validate_submission.py", all_files_passed=ok, reports=reports)
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, allow_nan=False))
    for r in reports:
        bad = [k for k, v in r["checks"].items() if not v]
        print(f"{'PASS' if r['all_checks_passed'] else 'FAIL'}  {r['file']}  sha256={r['sha256'][:16]}  "
              f"positives={r['positive_pixels']}  nan={r['n_nan']}  " + (f"failed={bad}" if bad else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
