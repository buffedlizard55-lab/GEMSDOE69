from gems import gate


def test_missing_receipt_is_blocked():
    d = gate.decide(None)
    assert d["status"] == "BLOCKED" and d["download_enabled"] is False


def test_incomplete_receipt_is_blocked():
    d = gate.decide({"candidate_dti": 0.5})
    assert d["status"] == "BLOCKED"


def test_pass_offers_download():
    r = dict(candidate_dti=0.31, baseline_dti=0.20, incumbent_dti=0.28, n_withheld_positives=400,
             ci95_low=0.25, ci95_high=0.37, evaluator_version="gems-dti-local-v1")
    assert gate.decide(r)["status"] == "OFFER_DOWNLOAD"


def test_fail_vs_incumbent_is_negative():
    r = dict(candidate_dti=0.27, baseline_dti=0.20, incumbent_dti=0.28, n_withheld_positives=400,
             ci95_low=0.2, ci95_high=0.3, evaluator_version="gems-dti-local-v1")
    assert gate.decide(r)["status"] == "NEGATIVE"


def test_note_limit():
    assert gate.note_ok("x" * 140)
    assert not gate.note_ok("x" * 141)
    assert not gate.note_ok("")
