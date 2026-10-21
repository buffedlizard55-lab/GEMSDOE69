"""Malformed files receive negative format reports, never a success override.

Tiny synthetic grids below are validator unit fixtures, not model experiments.
The pinned scientific tools remain unchanged.
"""
from types import SimpleNamespace
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts import validate_submission as wrapper


@pytest.fixture
def tiny_grid(tmp_path, monkeypatch):
    metadata = dict(driver='GTiff', height=4, width=5, count=1, dtype='float32',
                    crs='EPSG:32611', transform=from_origin(243350, 4508550, 100, 100))
    footprint = np.ones((4, 5), bool)
    footprint[0] = False
    sample = np.where(footprint, 0, np.nan).astype(np.float32)
    with rasterio.open(tmp_path / 'sample_submission.tif', 'w', **metadata) as dst:
        dst.write(sample, 1)
    monkeypatch.setattr(wrapper, 'DATA', tmp_path)
    grid = SimpleNamespace(footprint=footprint, catalogue=np.zeros((4, 5), bool))
    return tmp_path, metadata, grid


def write(path, array, metadata):
    metadata = dict(metadata, height=array.shape[0], width=array.shape[1])
    with rasterio.open(path, 'w', **metadata) as dst:
        dst.write(array.astype('float32'), 1)


def test_wrong_shape_is_a_negative_report_not_index_error(tiny_grid):
    path, metadata, grid = tiny_grid
    candidate = path / 'wrong.tif'
    write(candidate, np.zeros((2, 3)), metadata)
    report = wrapper.check(candidate, grid)
    assert report['all_checks_passed'] is False
    assert report['checks']['mask_shapes_match_raster'] is False
    assert report['checks']['template_validator_passed'] is False
    json.dumps(report, allow_nan=False)


def test_all_nan_file_has_no_fake_range(tiny_grid):
    path, metadata, grid = tiny_grid
    candidate = path / 'empty.tif'
    write(candidate, np.full((4, 5), np.nan), metadata)
    report = wrapper.check(candidate, grid)
    assert report['all_checks_passed'] is False
    assert report['min'] is None and report['max'] is None
    assert report['checks']['footprint_all_finite'] is False
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize('value,check', [(1.01, 'all_finite_values_in_0_1'),
                                        (-.01, 'all_finite_values_in_0_1'),
                                        (float('inf'), 'no_infinite_values'),
                                        (float('nan'), 'nan_only_outside_footprint')])
def test_range_and_finiteness_faults_are_reported(tiny_grid, value, check):
    path, metadata, grid = tiny_grid
    candidate = path / 'bad.tif'
    array = np.zeros((4, 5), 'float32')
    array[2, 2] = value
    write(candidate, array, metadata)
    report = wrapper.check(candidate, grid)
    assert report['all_checks_passed'] is False
    assert report['checks'][check] is False
