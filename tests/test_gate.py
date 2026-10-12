from gems import gate


def valid_receipt():
    return {
        "evidence_class": "HOLDOUT-DTI",
        "candidate_dti": 0.31,
        "baseline_dti": 0.20,
        "incumbent_dti": 0.28,
        "ci95_low": 0.29,
        "ci95_high": 0.33,
        "delta_vs_baseline_ci95_low": 0.05,
        "delta_vs_baseline_ci95_high": 0.15,
        "delta_vs_incumbent_ci95_low": 0.02,
        "delta_vs_incumbent_ci95_high": 0.06,
        "n_withheld_positives": 400,
        "evaluator_version": "gems-dti-local-v1",
        "leakage_canaries_clean": True,
        "registry_raster_count": 3,
        "max_registry_rank_correlation": 0.82,
        "max_dots_within_3px_fraction": 0.58,
        "exact_pixel_match_found": False,
        "raster_sha256": "a" * 64,
        "format_validation_passed": True,
        "format_validation_reference_type": "official_sample_submission",
        "format_validation_reference": "data/sample_submission.tif",
        "format_validation_reference_sha256": "b" * 64,
        "submission_name": "gemsdoe69-relay-20261012-a1b2c3d4",
        "submission_name_unique": True,
        "note": "Corridor-gated relay hypotheses; paired spatial holdout passed.",
    }


def test_missing_receipt_is_blocked():
    decision = gate.decide(None)
    assert decision["status"] == "BLOCKED" and decision["download_enabled"] is False


def test_incomplete_receipt_is_blocked():
    decision = gate.decide({"candidate_dti": 0.5})
    assert decision["status"] == "BLOCKED"


def test_full_receipt_passes_all_gates():
    assert gate.decide(valid_receipt())["status"] == "OFFER_DOWNLOAD"


def test_fail_vs_incumbent_is_negative():
    receipt = valid_receipt()
    receipt["candidate_dti"] = 0.27
    assert gate.decide(receipt)["status"] == "NEGATIVE"


def test_paired_ci_must_establish_positive_improvement():
    receipt = valid_receipt()
    receipt["delta_vs_baseline_ci95_low"] = -0.01
    assert gate.decide(receipt)["status"] == "NEGATIVE"


def test_nonfinite_or_out_of_range_scores_are_blocked():
    for value in (float("nan"), float("inf"), -0.1, 1.1):
        receipt = valid_receipt()
        receipt["candidate_dti"] = value
        assert gate.decide(receipt)["status"] == "BLOCKED"


def test_registry_duplicate_stops_download():
    receipt = valid_receipt()
    receipt["max_registry_rank_correlation"] = 0.91
    assert gate.decide(receipt)["status"] == "NEGATIVE"
    receipt = valid_receipt()
    receipt["max_dots_within_3px_fraction"] = 0.71
    assert gate.decide(receipt)["status"] == "NEGATIVE"


def test_failed_validator_stops_download():
    receipt = valid_receipt()
    receipt["format_validation_passed"] = False
    assert gate.decide(receipt)["status"] == "NEGATIVE"


def test_only_official_sample_grid_can_validate_release():
    receipt = valid_receipt()
    receipt["format_validation_reference_type"] = "training_features"
    assert gate.decide(receipt)["status"] == "BLOCKED"


def test_hash_and_name_must_be_verified():
    receipt = valid_receipt()
    receipt["raster_sha256"] = "bad"
    assert gate.decide(receipt)["status"] == "BLOCKED"
    receipt = valid_receipt()
    receipt["submission_name_unique"] = False
    assert gate.decide(receipt)["status"] == "BLOCKED"


def test_note_limit():
    assert gate.note_ok("x" * 140)
    assert not gate.note_ok("x" * 141)
    assert not gate.note_ok("")
    assert not gate.note_ok(None)
