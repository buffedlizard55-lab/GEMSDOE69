"""Regression tests for strict publication policy, independent of geodata."""
import hashlib
import json

import pytest

from scripts import release_gate as policy


def put(root, name, obj):
    (root / 'evidence').mkdir(exist_ok=True)
    (root / 'evidence' / name).write_text(json.dumps(obj))


@pytest.fixture
def cleared(tmp_path):
    raster = tmp_path / 'candidate.tif'
    raster.write_bytes(b'test artifact: validator receipt fixture, not real geodata')
    sha = hashlib.sha256(raster.read_bytes()).hexdigest()
    checks = {k: True for k in (
        'single_band', 'dtype_float32', 'crs_epsg_32611', 'shape_3730x3292',
        'transform_and_bounds_match_sample_submission', 'footprint_all_finite',
        'footprint_values_in_0_1', 'nan_only_outside_footprint', 'no_infinite_values',
        'all_finite_values_in_0_1', 'template_validator_passed')}
    put(tmp_path, 'e2_gate.json', {'gate_passed': True, 'current_best_beaten': True,
                                  'artifact_sha256': sha})
    put(tmp_path, 'e3_uniqueness.json', dict(literal_gate=dict(rho_ok=True, overlap_ok=True),
        n_registry_blobs=1, n_compared=1, n_errors=0, my_sha256=sha))
    put(tmp_path, 'e3_receipt.json', dict(raster=dict(zeros=dict(path='candidate.tif', sha256=sha)),
        validator=dict(reports=[dict(sha256=sha, all_checks_passed=True, checks=checks)])))
    for phase in ('surface', 'dots'):
        put(tmp_path, f'e3_uniqueness_{phase}.json', {'phases': {phase: {'summary': dict(
            candidate_file_sha256=sha, stop_required=False, complete_accessible_scan=True)}}})
    code = tmp_path / 'model.py'
    code.write_text('# reproducible fixture')
    put(tmp_path, 'e3_method_manifest.json', dict(artifact_sha256=sha, feature_names=['hg'],
        source_sha256={'model.py': hashlib.sha256(code.read_bytes()).hexdigest()}))
    put(tmp_path, 'e1_canaries.json', dict(artifact_sha256=sha, hg={'auc': .6}))
    return tmp_path


def test_complete_hash_bound_receipts_pass(cleared):
    assert policy.evaluate(cleared)['download_enabled']


def test_missing_evidence_fails_closed(tmp_path):
    assert policy.evaluate(tmp_path)['verdict'] == 'negative'


@pytest.mark.parametrize('phase', ['surface', 'dots'])
def test_stale_phase_blocks(cleared, phase):
    put(cleared, f'e3_uniqueness_{phase}.json', {'phases': {phase: {'summary': dict(
        candidate_file_sha256='stale', stop_required=False, complete_accessible_scan=True)}}})
    assert not policy.evaluate(cleared)['download_enabled']


def test_stratified_gate_cannot_override_literal_failure(cleared):
    u = policy.read(cleared, 'e3_uniqueness.json')
    u['literal_gate']['overlap_ok'] = False
    u['stratified_gate'] = {'dotlike_overlap_ok': True}
    put(cleared, 'e3_uniqueness.json', u)
    assert policy.evaluate(cleared)['verdict'] == 'negative'


@pytest.mark.parametrize('change', ['missing', 'modified', 'validator', 'registry_error', 'holdout'])
def test_other_blockers(cleared, change):
    if change == 'missing':
        (cleared / 'candidate.tif').unlink()
    elif change == 'modified':
        (cleared / 'candidate.tif').write_bytes(b'changed')
    elif change == 'validator':
        r = policy.read(cleared, 'e3_receipt.json')
        r['validator']['reports'][0]['checks']['footprint_all_finite'] = False
        put(cleared, 'e3_receipt.json', r)
    elif change == 'registry_error':
        u = policy.read(cleared, 'e3_uniqueness.json')
        u['n_errors'] = 1
        put(cleared, 'e3_uniqueness.json', u)
    else:
        put(cleared, 'e2_gate.json', {'gate_passed': False})
    assert not policy.evaluate(cleared)['download_enabled']


def test_current_repo_fails_closed():
    # Session 3 (2026-10-20): evidence/current_candidate.json binds the gate to this
    # session's candidate (or records that none passed). Either way the checked-in
    # repo must not enable a download unless every hash-bound gate passed; with no
    # candidate bound it falls back to the archived H69-J path, whose manifest is stale.
    result = policy.evaluate()
    if result['download_enabled']:
        assert result['verdict'] == 'promote' and not result['reasons']
        assert result['artifact_sha256']
    else:
        assert result['verdict'] == 'negative' and result['reasons']


def test_builder_revokes_stale_downloads(tmp_path, monkeypatch):
    from scripts import build_site69 as site
    (tmp_path / 'docs' / 'downloads').mkdir(parents=True)
    stale = tmp_path / 'docs' / 'downloads' / 'stale.tif'
    stale.write_bytes(b'stale')
    monkeypatch.setattr(site, 'ROOT', tmp_path)
    monkeypatch.setattr(site, 'DOCS', tmp_path / 'docs')
    # Direct imports in executable scripts resolve from scripts/ at runtime.
    import sys
    monkeypatch.setitem(sys.modules, 'release_gate', policy)
    banner, artifact = site.submission_banner()
    assert 'DO NOT SUBMIT' in banner
    assert artifact is None
    assert not stale.exists()
    assert 'download>' not in banner


@pytest.mark.parametrize('auc', [.91, float('nan'), None])
def test_invalid_or_flagged_canary_blocks(cleared, auc):
    c = policy.read(cleared, 'e1_canaries.json')
    c['hg']['auc'] = auc
    put(cleared, 'e1_canaries.json', c)
    assert not policy.evaluate(cleared)['download_enabled']


def test_source_mutation_blocks(cleared):
    (cleared / 'model.py').write_text('# changed method')
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('binding', [None, '', 'another-candidate'])
def test_stale_or_missing_holdout_binding_blocks(cleared, binding):
    gate = policy.read(cleared, 'e2_gate.json')
    if binding is None:
        gate.pop('artifact_sha256')
    else:
        gate['artifact_sha256'] = binding
    put(cleared, 'e2_gate.json', gate)
    decision = policy.evaluate(cleared)
    assert decision['verdict'] == 'negative'
    assert not decision['download_enabled']
    assert any('Holdout comparison' in reason for reason in decision['reasons'])


# --- session-candidate path (evidence/current_candidate.json), 2026-10-20 H69-M/H69-N ---

@pytest.fixture
def cand_root(tmp_path):
    raster = tmp_path / 'sub.tif'
    raster.write_bytes(b'candidate fixture bytes')
    sha = hashlib.sha256(raster.read_bytes()).hexdigest()
    code = tmp_path / 'm.py'
    code.write_text('# method')
    checks = {k: True for k in policy.VALIDATOR_REQUIRED}
    put(tmp_path, 'x_gate.json', dict(prompt_gate_passed=True, current_best_beaten=True, canary_ok=True))
    gate_sha = hashlib.sha256((tmp_path / 'evidence' / 'x_gate.json').read_bytes()).hexdigest()
    put(tmp_path, 'x_receipt.json', dict(surface_decoded_sha256='surf', raster=dict(zeros=dict(path='sub.tif', sha256=sha))))
    put(tmp_path, 'x_us.json', dict(stop_required=False, corpus=dict(complete_accessible_scan=True),
                                    candidate=dict(decoded_sha256='surf')))
    put(tmp_path, 'x_ud.json', dict(stop_required=False, corpus=dict(complete_accessible_scan=True),
                                    candidate=dict(file_sha256=sha)))
    put(tmp_path, 'x_val.json', dict(reports=[dict(sha256=sha, all_checks_passed=True, checks=checks)]))
    put(tmp_path, 'x_man.json', dict(artifact_sha256=sha, gate_sha256=gate_sha,
                                     source_sha256={'m.py': hashlib.sha256(code.read_bytes()).hexdigest()}))
    put(tmp_path, 'current_candidate.json', dict(hypothesis='X', gate='x_gate.json', receipt='x_receipt.json',
        uniqueness_surface='x_us.json', uniqueness_dots='x_ud.json', validator='x_val.json',
        method_manifest='x_man.json'))
    return tmp_path


def test_candidate_cleared_passes(cand_root):
    assert policy.evaluate(cand_root)['download_enabled']


def test_candidate_none_is_negative(cand_root):
    put(cand_root, 'current_candidate.json', dict(hypothesis=None))
    r = policy.evaluate(cand_root)
    assert r['verdict'] == 'negative' and not r['download_enabled']


@pytest.mark.parametrize('change', ['source', 'dots_unbound', 'gate', 'canary', 'surface_unbound', 'artifact'])
def test_candidate_blockers(cand_root, change):
    if change == 'source':
        (cand_root / 'm.py').write_text('# edited after the gate ran')
    elif change == 'dots_unbound':
        put(cand_root, 'x_ud.json', dict(stop_required=False, corpus=dict(complete_accessible_scan=True),
                                         candidate=dict(file_sha256='other')))
    elif change == 'gate':
        put(cand_root, 'x_gate.json', dict(prompt_gate_passed=True, current_best_beaten=False, canary_ok=True))
    elif change == 'canary':
        put(cand_root, 'x_gate.json', dict(prompt_gate_passed=True, current_best_beaten=True, canary_ok=False))
    elif change == 'surface_unbound':
        put(cand_root, 'x_us.json', dict(stop_required=False, corpus=dict(complete_accessible_scan=True),
                                         candidate=dict(decoded_sha256='other')))
    else:
        (cand_root / 'sub.tif').write_bytes(b'swapped')
    assert not policy.evaluate(cand_root)['download_enabled']
