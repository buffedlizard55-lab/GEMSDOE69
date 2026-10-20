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
    evaluator = ('vendor/template66 gems57 pooled hide-and-recover; alpha=0.2 beta=0.8; '
                 '300m triangular kernel')
    holdout_source = tmp_path / 'holdout.py'
    holdout_source.write_text('# reviewed whole-segment buffered evaluator fixture')
    holdout_source_sha = hashlib.sha256(holdout_source.read_bytes()).hexdigest()
    put(tmp_path, 'e2_gate.json', {
        'evidence_class': 'HOLDOUT-DTI', 'evaluator': evaluator,
        'withheld_positive_px_total': 100, 'n_cells': 8,
        'gate_passed': True, 'current_best_beaten': True, 'artifact_sha256': sha,
        'paired_cell_bootstrap': {
            'candidate_minus_control': {'mean': .02, 'ci95': [.01, .03]},
            'candidate_minus_current_best': {'mean': .01, 'ci95': [.002, .018]},
        },
    })
    put(tmp_path, 'e2_holdout_protocol_audit.json', {
        'evidence_class': 'HOLDOUT-PROTOCOL-AUDIT', 'artifact_sha256': sha,
        'evaluator': evaluator, 'compliant': True,
        'whole_fault_segments_withheld': True, 'segment_chunking': False,
        'withheld_context_buffer_px': 3,
        'catalogue_features_from_visible_faults_only': True,
        'visible_fault_mask_pixel_exact': True, 'pooled_dti': True,
        'alpha': .2, 'beta': .8, 'kernel': 'triangular', 'radius_m': 300,
        'source_sha256': {'holdout.py': holdout_source_sha},
    })
    put(tmp_path, 'e3_uniqueness.json', dict(literal_gate=dict(rho_ok=True, overlap_ok=True),
        n_registry_blobs=1, n_compared=1, n_errors=0, my_sha256=sha))
    put(tmp_path, 'e3_receipt.json', dict(evidence_class='SUBMISSION-RECEIPT',
        raster=dict(zeros=dict(path='candidate.tif', sha256=sha)),
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
    result = policy.evaluate(cleared)
    assert result['download_enabled']
    assert result['verdict'] == 'eligible_for_selector'
    assert result['paired_ci_control_passed'] is True
    assert result['paired_ci_current_best_passed'] is True
    assert result['holdout_protocol_compliant'] is True


def test_missing_evidence_fails_closed(tmp_path):
    assert policy.evaluate(tmp_path)['verdict'] == 'negative'


@pytest.mark.parametrize('comparison', ['candidate_minus_control', 'candidate_minus_current_best'])
def test_each_paired_holdout_ci_is_required_to_be_positive(cleared, comparison):
    gate = policy.read(cleared, 'e2_gate.json')
    gate['paired_cell_bootstrap'][comparison]['ci95'] = [0.0, 0.02]
    put(cleared, 'e2_gate.json', gate)
    result = policy.evaluate(cleared)
    assert result['verdict'] == 'negative'
    assert result['download_enabled'] is False
    if comparison == 'candidate_minus_control':
        assert result['paired_ci_control_passed'] is False
        assert any('no-prior control' in reason for reason in result['reasons'])
    else:
        assert result['paired_ci_current_best_passed'] is False
        assert any('current lane-best' in reason for reason in result['reasons'])


@pytest.mark.parametrize(('field', 'value'), [
    ('whole_fault_segments_withheld', False),
    ('segment_chunking', True),
    ('withheld_context_buffer_px', 2),
    ('catalogue_features_from_visible_faults_only', False),
    ('visible_fault_mask_pixel_exact', False),
    ('alpha', 0.25),
    ('beta', 0.75),
    ('radius_m', 500),
])
def test_holdout_protocol_audit_must_match_the_required_protocol(cleared, field, value):
    audit = policy.read(cleared, 'e2_holdout_protocol_audit.json')
    audit[field] = value
    put(cleared, 'e2_holdout_protocol_audit.json', audit)
    result = policy.evaluate(cleared)
    assert result['verdict'] == 'negative'
    assert result['holdout_protocol_compliant'] is False
    assert any('whole-segment holdout protocol audit' in reason for reason in result['reasons'])


def test_holdout_protocol_source_hash_must_match(cleared):
    (cleared / 'holdout.py').write_text('# mutated evaluator')
    result = policy.evaluate(cleared)
    assert result['holdout_protocol_compliant'] is False
    assert not result['download_enabled']


def test_receipt_evidence_class_is_required(cleared):
    receipt = policy.read(cleared, 'e3_receipt.json')
    receipt['evidence_class'] = 'ORGANIZER-CONFIRMED'
    put(cleared, 'e3_receipt.json', receipt)
    result = policy.evaluate(cleared)
    assert not result['download_enabled']
    assert any('correctly classified submission artifact receipt' in reason for reason in result['reasons'])


@pytest.mark.parametrize('phase', ['surface', 'dots'])
def test_stale_phase_blocks(cleared, phase):
    put(cleared, f'e3_uniqueness_{phase}.json', {'phases': {phase: {'summary': dict(
        candidate_file_sha256='stale', stop_required=False, complete_accessible_scan=True)}}})
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('dot_overlap', [None, 0.0, 0.61, 0.70])
def test_stratified_gate_cannot_override_literal_failure(cleared, dot_overlap):
    # The written protocol applies to ANY registry raster. A diagnostic stratum
    # can explain a failure but cannot make a literal failure publishable.
    u = policy.read(cleared, 'e3_uniqueness.json')
    u['literal_gate']['overlap_ok'] = False
    u['stratified_gate'] = {'dotlike_overlap_ok': True}
    if dot_overlap is not None:
        u['worst_dot_overlap_dotlike'] = {'dot_overlap_3px': dot_overlap}
    put(cleared, 'e3_uniqueness.json', u)
    result = policy.evaluate(cleared)
    assert result['verdict'] == 'negative'
    assert not result['download_enabled']
    assert any('Literal registry dot-overlap gate' in reason for reason in result['reasons'])


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


def test_archived_transfer_runner_refuses_legacy_holdout_and_emission():
    from scripts import run_exp2b_transfer

    with pytest.raises(SystemExit, match='legacy chunked, unbuffered'):
        run_exp2b_transfer.cmd_gate()
    with pytest.raises(SystemExit, match='no protocol-qualified'):
        run_exp2b_transfer.cmd_emit()


def test_current_repo_fails_closed_on_literal_overlap():
    # A parallel branch rebound H69-J's holdout/source evidence, but its
    # literal all-registry overlap remains 1.0. A passing dotlike diagnostic
    # cannot turn that written duplicate-stop result into a promotion.
    result = policy.evaluate()
    assert result['verdict'] == 'negative'
    assert result['download_enabled'] is False
    assert any('Literal registry dot-overlap gate' in reason for reason in result['reasons'])


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


def test_write_card_refuses_to_overwrite_an_unbound_candidate(cleared):
    gate = policy.read(cleared, 'e2_gate.json')
    gate['artifact_sha256'] = 'another-candidate'
    put(cleared, 'e2_gate.json', gate)
    with pytest.raises(ValueError, match='holdout is not bound'):
        policy.write_card(cleared)
    assert not (cleared / 'evidence' / 'run_card.json').exists()


def test_write_card_refuses_cross_candidate_replacement_without_opt_in(cleared):
    put(cleared, 'run_card.json', {'raster': {'zeros': {'sha256': 'other-artifact'}}})
    with pytest.raises(ValueError, match='existing run card identifies a different artifact'):
        policy.write_card(cleared)
    card = policy.read(cleared, 'run_card.json')
    assert card['raster']['zeros']['sha256'] == 'other-artifact'
    replaced = policy.write_card(cleared, replace=True)
    assert replaced['raster']['zeros']['sha256'] != 'other-artifact'
