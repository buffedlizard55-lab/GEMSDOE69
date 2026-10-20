import numpy as np

from gems69_s3.evidence_quota import apportion, tile_ids


class _P:
    def __init__(self, a, b):
        self.tip_a, self.tip_b = a, b


def test_apportion_sums_and_caps():
    q = apportion(np.array([10, 0, 5, 85]), 20)
    assert q.sum() == 20 and q[1] == 0 and (q <= [10, 0, 5, 85]).all()
    assert list(q) == [2, 0, 1, 17]


def test_apportion_total_exceeds_count():
    assert list(apportion(np.array([3, 4]), 100)) == [3, 4]


def test_apportion_largest_remainder_tie_by_index():
    assert list(apportion(np.array([1, 1, 1]), 2)) == [1, 1, 0]


def test_tile_ids_midpoint():
    shape = (450, 450)          # 3 x 3 tiles of 200 px
    t = tile_ids([_P((0, 0), (10, 10)), _P((190, 190), (230, 230)), _P((449, 449), (449, 449))], shape)
    assert list(t) == [0, 4, 8]
