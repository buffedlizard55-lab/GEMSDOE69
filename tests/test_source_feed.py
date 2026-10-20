"""Source auditing is not model scoring and cannot invent a receipt."""
from pathlib import Path
import hashlib
import json

import pytest

from scripts import refresh_sources as feed


def test_request_parser_excludes_standalone_leaderboard_numbers():
    text = '''https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
h33-zeros: 0.2778
Current competition leaderboard GEMSDOE high score:

0.4413
https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
h33-zeros: 0.2778
https://buffedlizard55-lab.github.io/GEMSDOE69/
:
'''
    rows = feed.requested_sites(text)
    assert len(rows) == 2
    assert rows[0]['claims'] == [dict(submission_name='h33-zeros', value=.2778,
        evidence_class='USER-REPORTED-NOT-ORGANIZER-CONFIRMED', organizer_submission_receipt=None)]
    assert rows[1]['source_path'] == 'index.html'
    assert not rows[1]['claims']


def test_directory_redirect_is_followed_to_index(monkeypatch):
    files = {
        'index.html': b'<html><head><meta http-equiv="refresh" content="0; url=docs/"></head><body></body></html>',
        'docs/index.html': b'<html><body><a href="downloads/a.tif">TIFF</a><p>h33-zeros 0.2778</p></body></html>',
    }
    def fake(repo, path):
        raw = files[path]
        return raw, hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    monkeypatch.setattr(feed, 'github_file', fake)
    row = dict(repo='GEMSDOE32', requested_url='https://buffedlizard55-lab.github.io/GEMSDOE32/',
               source_path='index.html', claims=[dict(submission_name='h33-zeros', value=.2778)])
    doc = feed.inspect_family(row)
    assert doc['status'] == 'read_owner_page_source'
    assert [r['path'] for r in doc['source_chain']] == ['index.html', 'docs/index.html']
    assert doc['download_links_observed'] == ['https://buffedlizard55-lab.github.io/GEMSDOE32/docs/downloads/a.tif']
    assert doc['organizer_confirmed_submission_receipt'] is None
    assert doc['claim_checks'][0]['value_mentioned']


def test_page_source_failure_is_explicit(monkeypatch):
    def fail(*args):
        raise RuntimeError('network unavailable')
    monkeypatch.setattr(feed, 'github_file', fail)
    doc = feed.inspect_family(dict(repo='GEMSDOE69', requested_url='https://example.invalid/', source_path='index.html', claims=[]))
    assert doc['status'] == 'error'
    assert 'network unavailable' in doc['error']
    assert doc['organizer_confirmed_submission_receipt'] is None


def test_external_redirect_is_not_followed(monkeypatch):
    monkeypatch.setattr(feed, 'github_file', lambda *args: (b'<meta http-equiv="refresh" content="0;url=https://example.invalid/">', 'blob'))
    doc = feed.inspect_family(dict(repo='GEMSDOE69', requested_url='https://example.invalid/', source_path='index.html', claims=[]))
    assert doc['status'] == 'error'
    assert 'External redirect' in doc['error']


def test_leaderboard_table_parser_does_not_parse_arbitrary_decimals():
    html = '''<p>Random old score 0.9999</p><table><tr><th>Rank</th><th>Members</th><th>Participant</th><th>Score</th></tr>
<tr><td>#1</td><td></td><td><a>xiaofanhu</a><span>19h ago</span></td><td>0.4413</td></tr></table>'''
    parsed = feed.parse_leaderboard(html)
    assert len(parsed) == 1 and parsed[0]['public_dw_tversky'] == .4413
    assert parsed[0]['rank'] == 1
    with pytest.raises(ValueError, match='not recognized'):
        feed.parse_leaderboard('<p>Leader: 0.4413</p>')


def test_requested_site_and_claim_census_is_complete():
    root = Path(__file__).resolve().parents[1]
    rows = feed.requested_sites((root / 'PROJECT_REQUEST.md').read_text())
    assert len(rows) == 72
    assert len({r['repo'] for r in rows}) == 72
    assert sum(len(r['claims']) for r in rows) == 91
    assert all(c['organizer_submission_receipt'] is None for r in rows for c in r['claims'])


def test_feed_preserves_errors_and_never_confirms_an_owner_score():
    root = Path(__file__).resolve().parents[1]
    doc = json.loads((root / 'docs/data/family-feed.json').read_text())
    assert doc['requested_sites'] == 72
    assert doc['read_sites'] + doc['errors'] == 72
    assert all(r['organizer_confirmed_submission_receipt'] is None for r in doc['rows'])


def test_changed_content_needs_two_successful_observations():
    baseline = dict(generated_utc='2026-10-19', rows=[dict(repo='A', status='read_owner_page_source',
                                                       source_chain=[dict(sha256='before')])])
    rows = [dict(repo='A', status='read_owner_page_source', source_chain=[dict(sha256='after')])]
    feed.compare_to_baseline(rows, baseline, 'repo', family=True)
    assert rows[0]['content_changed_since_baseline'] is True
    assert rows[0]['baseline_generated_utc'] == '2026-10-19'
    failed = [dict(repo='A', status='error', source_chain=[])]
    feed.compare_to_baseline(failed, baseline, 'repo', family=True)
    assert failed[0]['content_changed_since_baseline'] is None


def test_unchanged_official_bytes_and_first_observation():
    baseline = dict(generated_utc='2026-10-19', rows=[dict(id='A', status='read', raw_sha256='same')])
    rows = [dict(id='A', status='read', raw_sha256='same'), dict(id='B', status='read', raw_sha256='new')]
    feed.compare_to_baseline(rows, baseline, 'id')
    assert rows[0]['content_changed_since_baseline'] is False
    assert rows[1]['content_changed_since_baseline'] is None
