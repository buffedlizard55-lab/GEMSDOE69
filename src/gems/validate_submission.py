"""Fail-closed local checks for a GEMS submission GeoTIFF.

The organizer's format description is reachable from the official competition homepage
(navigate to Problem Description). This project checker is not an organizer-issued
validator and cannot certify portal acceptance.

Checks: one float32 band, EPSG:32611, 100 m pixels, exact grid match to the official
sample-submission raster, values in [0, 1], and no NaN inside an explicitly masked
reference footprint. If the reference has no explicit GDAL mask/nodata footprint, the
checker fails closed instead of guessing from an undocumented sentinel.

Usage: python -m gems.validate_submission SUB.tif --reference data/sample_submission.tif
Exit code 0 only when every required check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import MaskFlags
except ImportError:  # pragma: no cover - exercised only in installations without rasterio
    rasterio = None
    CRS = None
    MaskFlags = None

TARGET_CRS = "EPSG:32611"
TARGET_RES = 100.0
REQUIRED_CHECKS = (
    "single_band",
    "dtype_float32",
    "crs_epsg32611",
    "resolution_100m",
    "no_inf",
    "finite_values_in_0_1",
    "reference_single_band",
    "shape_matches_reference",
    "transform_matches_reference",
    "crs_matches_reference",
    "reference_footprint_mask_available",
    "nan_only_outside_footprint",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reference_footprint(ref_path: Path) -> np.ndarray | None:
    """Return the explicit reference valid-data mask; never infer a mask from values.

    Rasterio exposes nodata, alpha, and internal/per-dataset masks through
    ``mask_flag_enums`` and ``dataset_mask``. An all-valid reference has no evidence for
    where an irregular competition footprint ends, so this returns ``None`` in that case.
    """
    if rasterio is None or MaskFlags is None:
        raise RuntimeError("rasterio is required to read the reference footprint")
    with rasterio.open(ref_path) as src:
        has_explicit_mask = any(
            flag != MaskFlags.all_valid
            for band_flags in src.mask_flag_enums
            for flag in band_flags
        )
        if not has_explicit_mask:
            return None
        return src.dataset_mask() > 0


def validate(sub_path: str | Path, reference: str | Path | None = None, *,
             reference_path: str | Path | None = None,
             features_path: str | Path | None = None) -> dict[str, Any]:
    sub_path = Path(sub_path)
    if reference is None and reference_path is not None:
        reference = reference_path
    if reference is not None:
        reference = Path(reference)
    checks: dict[str, dict[str, Any]] = {}

    def check(name: str, ok: bool | None, detail: str = "") -> None:
        checks[name] = {"pass": ok, "detail": detail}

    if rasterio is None:
        raise RuntimeError("rasterio is required (install the project requirements)")
    if not sub_path.is_file():
        raise FileNotFoundError(sub_path)

    receipt: dict[str, Any] = {
        "file": str(sub_path),
        "sha256": sha256(sub_path),
        "bytes": sub_path.stat().st_size,
        "reference_file": str(reference) if reference is not None else None,
    }

    with rasterio.open(sub_path) as src:
        check("single_band", src.count == 1, f"count={src.count}")
        check("dtype_float32", src.count == 1 and src.dtypes[0] == "float32",
              f"dtypes={src.dtypes}")
        check("crs_epsg32611", src.crs == CRS.from_epsg(32611), f"crs={src.crs}")
        check(
            "resolution_100m",
            abs(abs(src.res[0]) - TARGET_RES) < 1e-6
            and abs(abs(src.res[1]) - TARGET_RES) < 1e-6,
            f"res={src.res}",
        )
        shape, transform = (src.height, src.width), src.transform
        receipt["shape"] = list(shape)
        receipt["transform"] = list(transform)[:6]

        if src.count != 1:
            check("no_inf", False, "cannot inspect values in a multiband submission")
            check("finite_values_in_0_1", False, "cannot inspect values in a multiband submission")
        else:
            arr = src.read(1).astype(np.float64)
            finite = np.isfinite(arr)
            inf_count = int(np.isinf(arr).sum())
            vals = arr[finite]
            in_range = bool(vals.size > 0 and vals.min() >= 0.0 and vals.max() <= 1.0)
            check("no_inf", inf_count == 0, f"inf_count={inf_count}")
            check(
                "finite_values_in_0_1",
                in_range,
                f"min={float(vals.min()) if vals.size else None}, "
                f"max={float(vals.max()) if vals.size else None}",
            )
            receipt["n_nan"] = int(np.isnan(arr).sum())
            receipt["n_finite"] = int(finite.sum())

            if reference is None:
                check("reference_single_band", None, "no --reference: NOT CHECKED")
                check("shape_matches_reference", None, "no --reference: NOT CHECKED")
                check("transform_matches_reference", None, "no --reference: NOT CHECKED")
                check("crs_matches_reference", None, "no --reference: NOT CHECKED")
                check("reference_footprint_mask_available", None, "no --reference: NOT CHECKED")
                check("nan_only_outside_footprint", None, "no --reference: NOT CHECKED")
            else:
                if not reference.is_file():
                    raise FileNotFoundError(reference)
                with rasterio.open(reference) as ref:
                    reference_count = ref.count
                    same_shape = (ref.height, ref.width) == shape
                    same_transform = all(
                        abs(a - b) < 1e-6
                        for a, b in zip(transform[:6], ref.transform[:6])
                    )
                    same_crs = src.crs == ref.crs
                    check("reference_single_band", reference_count == 1, f"count={reference_count}")
                    check("shape_matches_reference", same_shape,
                          f"sub={shape} ref={(ref.height, ref.width)}")
                    check("transform_matches_reference", same_transform,
                          f"sub={tuple(transform)[:6]} ref={tuple(ref.transform)[:6]}")
                    check("crs_matches_reference", same_crs,
                          f"sub={src.crs} ref={ref.crs}")

                if same_shape and same_transform and same_crs and reference_count == 1:
                    footprint = reference_footprint(reference)
                    if footprint is None:
                        check(
                            "reference_footprint_mask_available",
                            False,
                            "reference has no explicit GDAL mask/nodata; refusing to infer a footprint",
                        )
                        check(
                            "nan_only_outside_footprint",
                            None,
                            "no explicit reference footprint: NOT CHECKED",
                        )
                    else:
                        check("reference_footprint_mask_available", True,
                              "using explicit sample-reference mask/nodata")
                        nan_inside = int((np.isnan(arr) & footprint).sum())
                        check("nan_only_outside_footprint", nan_inside == 0,
                              f"NaN inside footprint={nan_inside}; footprint_px={int(footprint.sum())}")
                        receipt["footprint_px"] = int(footprint.sum())
                        receipt["nan_inside_footprint"] = nan_inside
                        receipt["nan_outside_footprint"] = int((np.isnan(arr) & ~footprint).sum())
                else:
                    check("reference_footprint_mask_available", False,
                          "grid mismatch or reference is multiband")
                    check("nan_only_outside_footprint", False, "grid mismatch or reference is multiband")

    receipt["checks"] = checks
    receipt["pass"] = all(checks.get(name, {}).get("pass") is True for name in REQUIRED_CHECKS)
    receipt["passed"] = receipt["pass"]
    receipt["status"] = "PASS" if receipt["pass"] else "BLOCKED_OR_FAILED"
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("submission", type=Path)
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="official single-band sample-submission grid/mask, e.g. data/sample_submission.tif",
    )
    parser.add_argument("--json", type=Path, default=None, help="write the local check receipt here")
    args = parser.parse_args(argv)
    receipt = validate(args.submission, args.reference)
    text = json.dumps(receipt, indent=2, allow_nan=False)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
