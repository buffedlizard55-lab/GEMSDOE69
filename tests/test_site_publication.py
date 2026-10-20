"""No orphaned public files or placeholders can survive a negative build."""
from pathlib import Path
import json

from scripts import build_site69 as site
from scripts.check_site import check
from scripts.release_gate import write_card

ROOT = Path(__file__).resolve().parents[1]


def test_negative_build_revokes_nested_legacy_rasters_but_keeps_history(tmp_path, monkeypatch):
    public = tmp_path / 'docs'
    (public / 'downloads').mkdir(parents=True)
    (public / 'parallel/downloads').mkdir(parents=True)
    (tmp_path / 'submissions').mkdir()
    stale = [public / 'downloads/old.tif', public / 'downloads/old.zip', public / 'parallel/downloads/old.TIFF']
    for path in stale:
        path.write_bytes(b'fixture')
    archive = tmp_path / 'submissions/scientific-history.tif'
    archive.write_bytes(b'preserve negative evidence')
    data = public / 'downloads/receipt.json'
    data.write_text('{}')
    monkeypatch.setattr(site, 'ROOT', tmp_path)
    monkeypatch.setattr(site, 'DOCS', public)
    banner, tif = site.submission_banner()
    assert 'NOT OK TO SUBMIT' in banner and 'DO NOT SUBMIT' in banner
    assert tif is None and 'download>Download' not in banner
    assert not any(path.exists() for path in stale)
    assert archive.is_file() and data.is_file()


def test_current_built_site_matches_policy_and_has_no_broken_resources():
    result = check(ROOT)
    assert result['pages_checked'] >= 18
    assert result['passed'], result['errors']


def test_readme_retains_the_complete_current_request():
    request = (ROOT / 'PROJECT_REQUEST.md').read_text()
    assert request in (ROOT / 'README.md').read_text()


def test_current_card_discloses_uncertified_statistics_and_no_new_experiments():
    card = json.loads((ROOT / 'evidence/run_card.json').read_text())
    assert card['verdict'] == 'negative'
    assert card['holdout']['dti'] is None and card['holdout']['ci95'] is None
    assert card['scientific_experiments_this_review'] == 0
    assert card['submission_slots_used'] == 0
    assert len(card['submission_note']) <= 140
    assert card['correlation_overlap_vs_registry']['fresh_counterexample']['exhaustive_scan'] is False
