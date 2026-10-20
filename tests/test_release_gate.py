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
        'all_finite_values_in_0_1', 'template_validator_passed',
        'no_positive_outside_footprint', 'zero_positive_on_mapped_catalogue', 'no_sentinel_values')}
    put(tmp_path, 'e2_gate.json', {'gate_passed': True, 'current_best_beaten': True,
        'artifact_sha256': sha, 'release_statistics': dict(aggregation='pooled_tp_fp_fn',
            evaluator_version='synthetic-test-only-not-a-real-score',
            withheld_positive_pixel_evaluations=100, candidate_dti=.31, candidate_ci95=[.29, .33],
            control_dti=.20, control_ci95=[.18, .22], current_best_dti=.28, current_best_ci95=[.26, .30],
            delta_vs_control_ci95=[.06, .15], delta_vs_current_best_ci95=[.01, .05],
            uncertainty_unit='spatial_block')})
    put(tmp_path, 'e3_uniqueness.json', dict(literal_gate=dict(rho_ok=True, overlap_ok=True),
        n_registry_blobs=1, n_compared=1, n_errors=0, my_sha256=sha,
        worst_abs_spearman=.20, worst_dot_overlap_all={'dot_overlap_3px': .40}))
    put(tmp_path, 'e3_receipt.json', dict(evidence_class='SUBMISSION-RECEIPT', submission_name='synthetic-unit-fixture',
        submission_note='Unit fixture, not a real submission', raster=dict(zeros=dict(path='candidate.tif', sha256=sha)),
        validator=dict(reports=[dict(sha256=sha, all_checks_passed=True, checks=checks)])))
    for phase in ('surface', 'dots'):
        put(tmp_path, f'e3_uniqueness_{phase}.json', {'phases': {phase: {'summary': dict(
            candidate_file_sha256=sha, stop_required=False, complete_accessible_scan=True, unique=True,
            registry_rasters_expected=1, registry_rasters_checked=1, missing_or_invalid=0,
            worst_spearman_full_footprint=.20, worst_dot_overlap=.40)},
            }, 'completed_before_placement': True})
    code = tmp_path / 'model.py'
    code.write_text('# reproducible fixture')
    holdout = tmp_path / 'holdout.py'
    holdout.write_text('# synthetic whole-segment buffered evaluator unit fixture')
    gate = policy.read(tmp_path, 'e2_gate.json')
    evaluator = gate['release_statistics']['evaluator_version']
    gate.update(evidence_class='HOLDOUT-DTI', evaluator=evaluator,
        withheld_positive_px_total=100, n_cells=8,
        paired_cell_bootstrap=dict(
            candidate_minus_control=dict(mean=.11, ci95=[.06, .15]),
            candidate_minus_current_best=dict(mean=.03, ci95=[.01, .05])))
    put(tmp_path, 'e2_gate.json', gate)
    put(tmp_path, 'e2_holdout_protocol_audit.json', dict(
        evidence_class='HOLDOUT-PROTOCOL-AUDIT', artifact_sha256=sha, evaluator=evaluator,
        compliant=True, whole_fault_segments_withheld=True, segment_chunking=False,
        withheld_context_buffer_px=3, catalogue_features_from_visible_faults_only=True,
        visible_fault_mask_pixel_exact=True, pooled_dti=True, alpha=.2, beta=.8,
        kernel='triangular', radius_m=300,
        source_sha256={'holdout.py': hashlib.sha256(holdout.read_bytes()).hexdigest()}))
    put(tmp_path, 'e3_method_manifest.json', dict(artifact_sha256=sha, feature_names=['hg'],
        source_sha256={'model.py': hashlib.sha256(code.read_bytes()).hexdigest()},
        catalogue_features_visible_only=True, geological_requirements=dict(
            source_polylines_used=True, same_dip_verified=True, releasing_slip_sense_verified=True)))
    put(tmp_path, 'e1_canaries.json', dict(artifact_sha256=sha, measurement_origin='computed_holdout', hg={'auc': .6}))
    return tmp_path


def test_complete_hash_bound_receipts_pass(cleared):
    decision = policy.evaluate(cleared)
    assert decision['download_enabled']
    assert decision['selector_authorization_required'] is True
    assert decision['holdout_protocol_compliant'] is True
    assert decision['paired_ci_control_passed'] and decision['paired_ci_current_best_passed']


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
    u['worst_dot_overlap_dotlike'] = {'dot_overlap_3px': .61}
    u['worst_dot_overlap_all'] = {'dot_overlap_3px': 1.0}
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


def test_current_repo_is_quarantined_and_literal_failure_is_binding():
    # Rebinding archived evidence cannot clear a literal failure or an
    # unresolved integrity review. A changed hash is not a new experiment.
    result = policy.evaluate()
    assert result['verdict'] == 'negative'
    assert result['download_enabled'] is False
    assert any('quarantined' in reason for reason in result['reasons'])
    assert any('Literal registry' in reason for reason in result['reasons'])


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


@pytest.mark.parametrize('field,value', [
    ('worst_abs_spearman', .91), ('worst_abs_spearman', float('nan')),
    ('worst_abs_spearman', True), ('worst_abs_spearman', None),
])
def test_numeric_registry_evidence_overrides_pass_flags(cleared, field, value):
    u = policy.read(cleared, 'e3_uniqueness.json')
    u[field] = value
    put(cleared, 'e3_uniqueness.json', u)
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('overlap', [.70001, float('inf'), float('nan'), None, True])
def test_numeric_overlap_cannot_be_hidden_by_a_pass_flag(cleared, overlap):
    u = policy.read(cleared, 'e3_uniqueness.json')
    u['worst_dot_overlap_all'] = {'dot_overlap_3px': overlap}
    put(cleared, 'e3_uniqueness.json', u)
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('phase', ['surface', 'dots'])
def test_literal_phase_contradiction_blocks_even_when_summary_says_unique(cleared, phase):
    doc = policy.read(cleared, f'e3_uniqueness_{phase}.json')
    doc['phases'][phase]['two_phase'] = {
        'literal_reading': {'duplicate': True, 'worst_forward_overlap': 1.0},
        'like_for_like_reading': {'duplicate': False, 'worst_forward_overlap_dot_fields': .61}}
    put(cleared, f'e3_uniqueness_{phase}.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('key,value', [
    ('candidate_dti', .27), ('candidate_dti', float('nan')),
    ('aggregation', 'mean_of_cells'), ('uncertainty_unit', 'repeated_cell'),
    ('delta_vs_current_best_ci95', [-.001, .02]),
    ('delta_vs_control_ci95', [0, .02]), ('candidate_ci95', [.4, .2]),
    ('withheld_positive_pixel_evaluations', True),
])
def test_holdout_booleans_are_not_enough(cleared, key, value):
    doc = policy.read(cleared, 'e2_gate.json')
    doc['release_statistics'][key] = value
    put(cleared, 'e2_gate.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


def test_surface_after_placement_is_not_clearance(cleared):
    doc = policy.read(cleared, 'e3_uniqueness_surface.json')
    doc['completed_before_placement'] = False
    put(cleared, 'e3_uniqueness_surface.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


def test_computed_canary_origin_required(cleared):
    doc = policy.read(cleared, 'e1_canaries.json')
    doc.pop('measurement_origin')
    put(cleared, 'e1_canaries.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('field', ['source_polylines_used', 'same_dip_verified', 'releasing_slip_sense_verified'])
def test_geological_proxy_is_not_verified_attribute(cleared, field):
    doc = policy.read(cleared, 'e3_method_manifest.json')
    doc['geological_requirements'][field] = False
    put(cleared, 'e3_method_manifest.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


def test_full_catalogue_holdout_feature_is_not_eligible(cleared):
    doc = policy.read(cleared, 'e3_method_manifest.json')
    doc['catalogue_features_visible_only'] = False
    put(cleared, 'e3_method_manifest.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


def test_quarantine_is_not_cleared_by_rebinding_old_evidence(cleared):
    sha = policy.evaluate(cleared)['artifact_sha256']
    put(cleared, 'integrity_review.json', {'status': 'quarantined', 'artifact_sha256': [sha]})
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('name,key', [
    ('e3_receipt.json', 'raster'), ('e3_receipt.json', 'validator'),
    ('e3_uniqueness.json', 'literal_gate'), ('e3_uniqueness.json', 'worst_dot_overlap_all'),
    ('e3_uniqueness_surface.json', 'phases'), ('e3_method_manifest.json', 'source_sha256'),
    ('e3_method_manifest.json', 'geological_requirements'), ('e2_gate.json', 'release_statistics'),
])
def test_malformed_nested_receipt_fails_closed(cleared, name, key):
    doc = policy.read(cleared, name)
    doc[key] = ['malformed', 'not an object']
    put(cleared, name, doc)
    assert policy.evaluate(cleared)['download_enabled'] is False


@pytest.mark.parametrize('bad', ['not json', '[]', 'null'])
def test_malformed_top_level_evidence_fails_closed(cleared, bad):
    (cleared / 'evidence/e3_receipt.json').write_text(bad)
    assert not policy.evaluate(cleared)['download_enabled']


def test_external_artifact_path_is_rejected(cleared, tmp_path):
    doc = policy.read(cleared, 'e3_receipt.json')
    doc['raster']['zeros']['path'] = '../outside.tif'
    put(cleared, 'e3_receipt.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


def test_threshold_boundaries_are_inclusive(cleared):
    u = policy.read(cleared, 'e3_uniqueness.json')
    u['worst_abs_spearman'] = .90
    u['worst_dot_overlap_all']['dot_overlap_3px'] = .70
    put(cleared, 'e3_uniqueness.json', u)
    assert policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('field', ['submission_name', 'submission_note'])
def test_name_and_note_cannot_be_silently_truncated(cleared, field):
    doc = policy.read(cleared, 'e3_receipt.json')
    doc[field] = 'x' * 141
    put(cleared, 'e3_receipt.json', doc)
    assert not policy.evaluate(cleared)['download_enabled']


def test_fresh_sparse_prior_failure_overrides_all_old_pass_flags(cleared):
    sha = policy.evaluate(cleared)['artifact_sha256']
    put(cleared, 'local-prior-audit.json', dict(candidate_sha256=sha,
        rows=[dict(exact_bytes_equal=False, exact_footprint_pixels_equal=False, dots_within_3px=.81)]))
    result = policy.evaluate(cleared)
    assert not result['download_enabled']
    assert any('sparse fields' in reason for reason in result['reasons'])


def test_fresh_universal_stop_overrides_rebinding(cleared):
    put(cleared, 'registry-blocker.json', dict(candidate_sha256='old bytes', stop_required=True,
                                             registry_covers_entire_footprint=True))
    assert not policy.evaluate(cleared)['download_enabled']


def test_write_card_preserves_unbound_evidence_instead_of_attributing_it(cleared):
    gate = policy.read(cleared, 'e2_gate.json')
    gate['artifact_sha256'] = 'other artifact'
    put(cleared, 'e2_gate.json', gate)
    with pytest.raises(ValueError, match='holdout is not bound'):
        policy.write_card(cleared)
    assert not (cleared / 'evidence/run_card.json').exists()


def test_cross_candidate_card_needs_intent_and_preserves_full_history(cleared):
    old = {'raster': {'zeros': {'sha256': 'another artifact'}}, 'hypothesis': 'keep me'}
    put(cleared, 'run_card.json', old)
    with pytest.raises(ValueError, match='existing run card identifies a different artifact'):
        policy.write_card(cleared)
    assert policy.read(cleared, 'run_card.json') == old
    new = policy.write_card(cleared, replace=True)
    assert new['raster']['zeros']['sha256'] != 'another artifact'
    archives = list((cleared / 'evidence').glob('run_card_archived_*.json'))
    assert len(archives) == 1
    assert json.loads(archives[0].read_text()) == old
    # Explicit intent changes the record's identity, never loosens a gate.
    assert new['release_policy'] == policy.evaluate(cleared)


def test_out_of_range_huge_integer_cannot_crash_the_policy(cleared):
    gate = policy.read(cleared, 'e2_gate.json')
    gate['release_statistics']['candidate_dti'] = 10 ** 1000
    put(cleared, 'e2_gate.json', gate)
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('value', ['\0', 123, None])
def test_invalid_local_path_fails_closed(cleared, value):
    receipt = policy.read(cleared, 'e3_receipt.json')
    receipt['raster']['zeros']['path'] = value
    put(cleared, 'e3_receipt.json', receipt)
    assert not policy.evaluate(cleared)['download_enabled']


@pytest.mark.parametrize('field', ['registry_rasters_expected', 'registry_rasters_checked', 'missing_or_invalid'])
def test_phase_counts_are_integers_not_boolean_passes(cleared, field):
    document = policy.read(cleared, 'e3_uniqueness_surface.json')
    document['phases']['surface']['summary'][field] = True if field != 'missing_or_invalid' else False
    put(cleared, 'e3_uniqueness_surface.json', document)
    assert not policy.evaluate(cleared)['download_enabled']


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
