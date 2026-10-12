import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems import validate_submission as vs

CRS = "EPSG:32611"


def _write(path, arr, crs=CRS, res=100.0, origin=(500000.0, 4200000.0), dtype="float32", nodata=None):
    h, w = arr.shape
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype=dtype,
                       crs=crs, transform=from_origin(origin[0], origin[1], res, res), nodata=nodata) as dst:
        dst.write(arr.astype(dtype), 1)
    return path


@pytest.fixture
def ref(tmp_path):
    arr = np.full((20, 30), 1.0, dtype=np.float32)
    arr[:3, :] = -3.4e38          # outside footprint (declared NoData sentinel)
    return _write(tmp_path / "ref.tif", arr, nodata=-3.4e38)


def _good(tmp_path, ref_arr_outside_nan=True):
    a = np.random.default_rng(0).random((20, 30)).astype(np.float32)
    a[:3, :] = np.nan
    return _write(tmp_path / "good.tif", a)


def test_good_submission_passes(tmp_path, ref):
    sub = _good(tmp_path)
    rec = vs.validate(sub, ref)
    assert rec["pass"] is True, rec["checks"]


def test_out_of_range_fails(tmp_path, ref):
    a = np.full((20, 30), 0.5, np.float32)
    a[10, 10] = 1.2
    assert vs.validate(_write(tmp_path / "hi.tif", a), ref)["pass"] is False
    a[10, 10] = -0.1
    assert vs.validate(_write(tmp_path / "lo.tif", a), ref)["pass"] is False


def test_nan_inside_footprint_fails(tmp_path, ref):
    a = np.full((20, 30), 0.5, np.float32)
    a[3:, :] = 0.5
    a[10, 10] = np.nan
    rec = vs.validate(_write(tmp_path / "nan.tif", a), ref)
    assert rec["pass"] is False
    assert rec["checks"]["nan_only_outside_footprint"]["pass"] is False


def test_wrong_crs_fails(tmp_path, ref):
    a = np.full((20, 30), 0.5, np.float32)
    rec = vs.validate(_write(tmp_path / "crs.tif", a, crs="EPSG:32610"), ref)
    assert rec["checks"]["crs_epsg32611"]["pass"] is False


def test_wrong_resolution_fails(tmp_path, ref):
    a = np.full((20, 30), 0.5, np.float32)
    rec = vs.validate(_write(tmp_path / "res.tif", a, res=50.0), ref)
    assert rec["checks"]["resolution_100m"]["pass"] is False


def test_wrong_shape_fails(tmp_path, ref):
    a = np.full((21, 30), 0.5, np.float32)
    rec = vs.validate(_write(tmp_path / "shape.tif", a), ref)
    assert rec["checks"]["shape_matches_reference"]["pass"] is False
    assert rec["pass"] is False


def test_wrong_dtype_fails(tmp_path, ref):
    a = np.full((20, 30), 0.5, np.float64)
    rec = vs.validate(_write(tmp_path / "f64.tif", a, dtype="float64"), ref)
    assert rec["checks"]["dtype_float32"]["pass"] is False


def test_reference_without_explicit_mask_fails_closed(tmp_path):
    reference = _write(tmp_path / "unmasked.tif", np.ones((20, 30), dtype=np.float32))
    submission = _good(tmp_path)
    rec = vs.validate(submission, reference)
    assert rec["pass"] is False
    assert rec["checks"]["reference_footprint_mask_available"]["pass"] is False
    assert "refusing to infer" in rec["checks"]["reference_footprint_mask_available"]["detail"]


def test_no_reference_marks_grid_unchecked(tmp_path):
    a = np.full((20, 30), 0.5, np.float32)
    rec = vs.validate(_write(tmp_path / "noref.tif", a))
    assert rec["checks"]["shape_matches_reference"]["pass"] is None
    assert rec["checks"]["nan_only_outside_footprint"]["pass"] is None
    assert rec["pass"] is False  # fail closed: exact template grid/footprint are required
