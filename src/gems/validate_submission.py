"""Validate a GEMS submission GeoTIFF against the organizer's stated format.

Requirements checked (organizer page 967 'Submission format', fetched 2026-10-12):
  * single band, datatype float32
  * CRS EPSG:32611, resolution 100 m
  * same shape and geotransform as the training-data grid (when --reference is given)
  * values in [0, 1] (finite); NaN allowed ONLY outside the footprint
Footprint (ASSUMPTION, see docs/irregularities.md IR-07): a pixel is inside the footprint
when every band of the reference raster is finite and > -1e38 (the reference notebook
treats values < -1e38 as NaN).

Usage: python -m gems.validate_submission SUB.tif [--reference data/training_features.tif] [--json out.json]
Exit code 0 only if every check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

try:
    import rasterio
    from rasterio.crs import CRS
except ImportError:  # pragma: no cover
    rasterio = None

TARGET_CRS = "EPSG:32611"
TARGET_RES = 100.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reference_footprint(ref_path: Path) -> np.ndarray:
    """Boolean footprint mask on the reference grid (block-wise read, memory-safe)."""
    with rasterio.open(ref_path) as src:
        mask = np.ones((src.height, src.width), dtype=bool)
        for _, win in src.block_windows(1):
            block = src.read(window=win).astype(np.float64)
            ok = np.all(np.isfinite(block) & (block > -1e38), axis=0)
            mask[win.row_off:win.row_off + win.height, win.col_off:win.col_off + win.width] = ok
    return mask


def validate(sub_path: Path, reference: Path | None = None) -> dict:
    checks: dict[str, dict] = {}

    def check(name, ok, detail=""):
        checks[name] = {"pass": bool(ok), "detail": detail}

    if rasterio is None:
        raise RuntimeError("rasterio is required (pip install rasterio)")

    receipt: dict = {"file": str(sub_path), "sha256": sha256(sub_path),
                     "bytes": sub_path.stat().st_size}
    with rasterio.open(sub_path) as src:
        arr = src.read(1).astype(np.float64) if src.count == 1 else None
        check("single_band", src.count == 1, f"count={src.count}")
        check("dtype_float32", src.dtypes[0] == "float32", f"dtype={src.dtypes[0]}")
        check("crs_epsg32611", src.crs == CRS.from_epsg(32611), f"crs={src.crs}")
        check("resolution_100m",
              abs(abs(src.res[0]) - TARGET_RES) < 1e-6 and abs(abs(src.res[1]) - TARGET_RES) < 1e-6,
              f"res={src.res}")
        shape, transform = (src.height, src.width), src.transform
        receipt["shape"] = list(shape)
        receipt["transform"] = list(transform)[:6]
        if arr is None:
            return {"receipt": receipt, "checks": checks, "pass": False}

        finite = np.isfinite(arr)
        check("no_inf", not np.isinf(arr).any(), f"inf_count={int(np.isinf(arr).sum())}")
        vals = arr[finite]
        in_range = bool(vals.size == 0 or (vals.min() >= 0.0 and vals.max() <= 1.0))
        check("finite_values_in_0_1", in_range,
              f"min={float(vals.min()) if vals.size else None}, max={float(vals.max()) if vals.size else None}")
        receipt["n_nan"] = int((~finite).sum())
        receipt["n_finite"] = int(finite.sum())

        if reference is None:
            checks["grid_matches_reference"] = {"pass": None, "detail": "no --reference given: NOT checked"}
            checks["nan_only_outside_footprint"] = {"pass": None, "detail": "no --reference given: NOT checked"}
        else:
            with rasterio.open(reference) as ref:
                check("shape_matches_reference", (ref.height, ref.width) == shape,
                      f"sub={shape} ref={(ref.height, ref.width)}")
                same_t = all(abs(a - b) < 1e-6 for a, b in zip(transform[:6], ref.transform[:6]))
                check("transform_matches_reference", same_t,
                      f"sub={tuple(transform)[:6]} ref={tuple(ref.transform)[:6]}")
                check("crs_matches_reference", src.crs == ref.crs, f"sub={src.crs} ref={ref.crs}")
            if checks["shape_matches_reference"]["pass"] and checks["transform_matches_reference"]["pass"]:
                fp = reference_footprint(Path(reference))
                n_in_nan = int((~finite & fp).sum())
                check("nan_only_outside_footprint", n_in_nan == 0,
                      f"NaN inside footprint = {n_in_nan}; footprint px = {int(fp.sum())}")
                receipt["footprint_px"] = int(fp.sum())
                receipt["outside_footprint_nonnan_px"] = int((finite & ~fp).sum())
                checks["outside_footprint_is_nan"] = {
                    "pass": None,
                    "detail": f"finite cells outside footprint = {int((finite & ~fp).sum())} "
                              "(organizer text: outside bounds must be null or NaN; reviewed manually, IR-07)"}
            else:
                checks["nan_only_outside_footprint"] = {"pass": False, "detail": "grid mismatch"}

    receipt["checks"] = checks
    hard = [v["pass"] for v in checks.values() if v["pass"] is not None]
    receipt["pass"] = bool(hard) and all(hard)
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", type=Path)
    ap.add_argument("--reference", type=Path, default=None,
                    help="official training grid, e.g. data/training_features.tif")
    ap.add_argument("--json", type=Path, default=None, help="write receipt here")
    a = ap.parse_args(argv)
    rec = validate(a.submission, a.reference)
    text = json.dumps(rec, indent=2)
    print(text)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(text + "\n")
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
