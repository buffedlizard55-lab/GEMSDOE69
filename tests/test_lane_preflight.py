"""A recorded duplicate stops model work, not just its download link."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import numpy as np
import pytest

from scripts.lane_preflight import require_open_lane, stop_reasons
from gems57.uniqueness import dot_overlap

ROOT = Path(__file__).resolve().parents[1]


def test_universal_positive_support_blocks_every_nonempty_field():
    field = np.zeros((20, 30), np.float32)
    field[4, 5], field[8, 9] = .1, 1
    prior = np.full(field.shape, .001, np.float32)
    assert dot_overlap(field, prior) == 1.0
    assert dot_overlap(np.zeros_like(field), prior) == 0


def test_literal_stop_is_binding_even_if_stratified_diagnostic_passes(tmp_path):
    (tmp_path / 'evidence').mkdir()
    (tmp_path / 'evidence/e3_uniqueness.json').write_text(json.dumps(dict(
        literal_gate=dict(overlap_ok=False, rho_ok=True), stratified_gate=dict(dotlike_overlap_ok=True))))
    assert stop_reasons(tmp_path)
    with pytest.raises(SystemExit, match='BLOCKED'):
        require_open_lane(tmp_path)


@pytest.mark.parametrize('script,args', [
    ('generate_unique_submission.py', []), ('build_submission.py', []),
    ('run_lane.py', ['e3']), ('run_lane69.py', ['e1']),
    ('run_lane69.py', ['e2']), ('run_lane69.py', ['e3']),
    ('run_relayfix_20261020.py', ['gate']), ('run_exp2b_transfer.py', ['gate']),
    ('rerun_canary.py', []), ('rerun_hardlink.py', []), ('finalize_relayfix_20261020.py', []),
])
def test_generation_entrypoints_stop_before_writing(script, args):
    files = [*ROOT.glob('evidence/*.json'), *ROOT.glob('submissions/*.tif')]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args], cwd=ROOT,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'BLOCKED' in result.stdout + result.stderr
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert before == after
