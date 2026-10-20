#!/usr/bin/env python3
"""Refresh a public, auditable source feed; never train, submit or change gates.

--family reads *every* family site named in PROJECT_REQUEST.md through the
GitHub contents API, follows in-repository index redirects, verifies git blob
identity, and records download links and USER-REPORTED claims separately.
--official checks the fixed official source URLs and a dated public leaderboard
snapshot. Login redirects and errors stay explicit. No account cookies are used.

Shell downloads in Arena are allowlisted. --family is usable here; --all is also
scheduled on GitHub Actions, where official HTTPS hosts can be checked directly.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import posixpath
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'buffedlizard55-lab'
SITE = re.compile(r'https://buffedlizard55-lab\.github\.io/([A-Za-z0-9_-]+)(/[^\s<>]*)?')
CLAIM = re.compile(r'^([A-Za-z0-9_.-]+):[ \t]*(0\.\d{4})[ \t]*$', re.MULTILINE)


def now():
    return datetime.now(timezone.utc).isoformat()


def requested_sites(text):
    matches = list(SITE.finditer(text))
    result = {}
    for i, match in enumerate(matches):
        repo = match.group(1)
        path = match.group(2) or '/'
        path = unquote(path).rstrip(').,')
        url = f'https://{OWNER}.github.io/{repo}{path}'
        source_path = path.lstrip('/')
        if not source_path or source_path.endswith('/'):
            source_path += 'index.html'
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Restrict the final site block to the results section, not the rest of
        # the request. Only artifact: decimal lines count as supplied claims.
        block = text[match.end():end].split('The following is the leaderboard')[0]
        claims = [dict(submission_name=name.strip(), value=float(score),
                       evidence_class='USER-REPORTED-NOT-ORGANIZER-CONFIRMED',
                       organizer_submission_receipt=None) for name, score in CLAIM.findall(block)]
        row = result.setdefault(repo, dict(repo=repo, requested_url=url, source_path=source_path, claims=[]))
        for claim in claims:
            if claim not in row['claims']:
                row['claims'].append(claim)
    return list(result.values())


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.redirect, self.text = [], None, []
        self.rows, self.row, self.cell = [], None, None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag == 'meta' and a.get('http-equiv', '').lower() == 'refresh':
            m = re.search(r'url\s*=\s*[\'\"]?([^\'\"]+)', a.get('content', ''), re.I)
            if m:
                self.redirect = m.group(1).strip()
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(self.cell).strip())
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.text.append(data.strip())
            if self.cell is not None:
                self.cell.append(data.strip())


def github_file(repo, path):
    api = f'repos/{OWNER}/{repo}/contents/{path}?ref=main'
    call = subprocess.run(['gh', 'api', api], capture_output=True, text=True, timeout=45)
    if call.returncode:
        raise RuntimeError(f'GitHub content request failed ({call.returncode}): {call.stderr.strip()[:160]}')
    doc = json.loads(call.stdout)
    if not isinstance(doc, dict) or doc.get('type') != 'file':
        raise ValueError('Expected a GitHub file')
    if doc.get('encoding') == 'base64':
        raw = base64.b64decode(doc['content'])
    else:
        raw_call = subprocess.run(['gh', 'api', f"repos/{OWNER}/{repo}/git/blobs/{doc['sha']}",
                                   '-H', 'Accept: application/vnd.github.raw'], capture_output=True, timeout=45)
        if raw_call.returncode:
            raise RuntimeError('GitHub raw blob request failed')
        raw = raw_call.stdout
    got = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if got != doc['sha']:
        raise ValueError('Git blob content-address check failed')
    return raw, got


def inspect_family(row):
    out = dict(row, checked_utc=now(), status='error', organizer_confirmed_submission_receipt=None)
    chain = []
    try:
        path = row['source_path']
        visited = set()
        for _ in range(4):
            if path in visited:
                raise ValueError('In-repository redirect loop')
            visited.add(path)
            try:
                raw, blob = github_file(row['repo'], path)
            except RuntimeError as exc:
                if path != 'index.html' or 'Not Found' not in str(exc):
                    raise
                # Several family sites deploy /docs, not the repository root.
                # Inspect the known docs index without pretending to have
                # rendered the requested Pages URL or verified its deployment.
                out['path_resolution_note'] = 'Repository root index absent; inspected docs/index.html. Live Pages source mapping not verified by this source audit.'
                path = 'docs/index.html'
                raw, blob = github_file(row['repo'], path)
            chain.append(dict(path=path, blob_sha1=blob, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
            parsed = Page()
            parsed.feed(raw.decode('utf-8', errors='replace'))
            next_path = parsed.redirect
            if not next_path and path == 'index.html' and 'docs/index.html' in parsed.links:
                next_path = 'docs/index.html'
            if not next_path:
                break
            u = urlparse(next_path)
            if u.scheme or u.netloc:
                # A site redirect is not permission to fetch an arbitrary host.
                raise ValueError('External redirect not followed in GitHub source audit')
            path = posixpath.normpath(posixpath.join(posixpath.dirname(path), u.path))
            if path.startswith('../') or path.startswith('/'):
                raise ValueError('Redirect escapes repository')
            if u.path.endswith('/') or path in ('.', 'docs'):
                path = posixpath.join(path, 'index.html')
        else:
            raise ValueError('Too many index redirects')
        text = ' '.join(parsed.text)
        out['status'] = 'read_owner_page_source'
        out['source_chain'] = chain
        out['source_api_url'] = f"https://api.github.com/repos/{OWNER}/{row['repo']}/git/blobs/{chain[-1]['blob_sha1']}"
        out['source_github_url'] = f"https://github.com/{OWNER}/{row['repo']}/blob/main/{path}"
        base = f"https://{OWNER}.github.io/{row['repo']}/{path}"
        out['download_links_observed'] = sorted({urljoin(base, link) for link in parsed.links
            if urlparse(link).path.lower().endswith(('.tif', '.tiff', '.zip'))})
        out['claim_checks'] = [dict(claim,
            name_mentioned=claim['submission_name'] in text or claim['submission_name'] in raw.decode('utf-8', errors='replace'),
            value_mentioned=f"{claim['value']:.4f}" in text,
            interpretation='Independent name/value mentions are not a verified pairing or organizer score.') for claim in row['claims']]
        out['limits'] = 'Owner-authored page source only; no organizer receipt, download safety, raster identity, or score is inferred.'
    except Exception as exc:
        out['error'] = str(exc)[:240]
        out['source_chain'] = chain
    return out


def parse_leaderboard(html):
    parsed = Page()
    parsed.feed(html)
    rows = []
    for cells in parsed.rows:
        if len(cells) < 4 or not re.fullmatch(r'#?\s*\d+', cells[0]):
            continue
        score = next((x for x in cells[3:] if re.fullmatch(r'0\.\d{4}', x)), None)
        if score is not None:
            rows.append(dict(rank=int(cells[0].replace('#', '').strip()),
                             participant_page_text=cells[2][:240], public_dw_tversky=float(score)))
    if not rows or rows[0]['rank'] != 1:
        raise ValueError('Public leaderboard table format not recognized; do not invent a score')
    return rows


def inspect_official(source):
    out = dict(id=source['id'], url=source['url'], checked_utc=now())
    try:
        req = Request(source['url'], headers={'User-Agent': 'GEMSDOE69-source-audit/1.0'})
        with urlopen(req, timeout=25) as response:
            raw = response.read(12_000_001)
            if len(raw) > 12_000_000:
                raise ValueError('Source exceeds 12 MB audit limit')
            final, kind = response.geturl(), response.headers.get_content_type()
        out.update(final_url=final, status='login_redirect' if '/accounts/login' in final else 'read',
                   content_type=kind, bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest())
        if source['id'] == 'leaderboard' and out['status'] == 'read':
            out['snapshot'] = parse_leaderboard(raw.decode('utf-8', errors='replace'))
            out['evidence_class'] = 'OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT; NOT a submission-page receipt'
    except Exception as exc:
        out.update(status='error', error=str(exc)[:240])
    return out



def compare_to_baseline(rows, baseline, key, *, family=False):
    """Record byte changes only when both observations contain content hashes."""
    previous = {row[key]: row for row in baseline.get('rows', []) if key in row}
    for row in rows:
        old = previous.get(row[key], {})
        current_hash, previous_hash = row.get('raw_sha256'), old.get('raw_sha256')
        if family:
            current_hash = row.get('source_chain', [{}])[-1].get('sha256') if row.get('source_chain') else None
            previous_hash = old.get('source_chain', [{}])[-1].get('sha256') if old.get('source_chain') else None
        readable = row.get('status') in ('read', 'read_owner_page_source')
        old_readable = old.get('status') in ('read', 'read_owner_page_source')
        row['baseline_generated_utc'] = baseline.get('generated_utc')
        row['previous_observed_status'] = old.get('status')
        row['previous_content_sha256'] = previous_hash
        row['content_changed_since_baseline'] = (current_hash != previous_hash
            if readable and old_readable and current_hash and previous_hash else None)
    return rows


def prior_feed(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (ValueError, OSError):
        return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', action='store_true')
    parser.add_argument('--official', action='store_true')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args(argv)
    if not (args.family or args.official or args.all):
        parser.error('Choose --family, --official, or --all')
    target = ROOT / 'docs/data'
    target.mkdir(parents=True, exist_ok=True)
    errors = 0
    if args.family or args.all:
        baseline = prior_feed(target / 'family-feed.json')
        sites = requested_sites((ROOT / 'PROJECT_REQUEST.md').read_text())
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(inspect_family, sites))
        compare_to_baseline(rows, baseline, 'repo', family=True)
        errors += sum(r['status'] == 'error' for r in rows)
        feed = dict(generated_utc=now(), evidence_class='OWNER-PAGE-SOURCE-AUDIT',
            scope='All unique family sites explicitly named in PROJECT_REQUEST.md, current GitHub main page sources. Not the raster registry and not organizer receipts.',
            requested_sites=len(sites), read_sites=sum(r['status'] != 'error' for r in rows),
            errors=sum(r['status'] == 'error' for r in rows), rows=rows)
        (target / 'family-feed.json').write_text(json.dumps(feed, indent=2, allow_nan=False) + '\n')
        print(f"Family source audit: {feed['read_sites']}/{len(sites)} read, {feed['errors']} errors")
    if args.official or args.all:
        baseline = prior_feed(target / 'source-health.json')
        sources = json.loads((ROOT / 'registry/verified_sources_2026-10-20.json').read_text())['sources']
        sources = [s for s in sources if s['id'] != 'reference']
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(inspect_official, sources))
        compare_to_baseline(rows, baseline, 'id')
        errors += sum(r['status'] == 'error' for r in rows)
        (target / 'source-health.json').write_text(json.dumps(dict(generated_utc=now(),
            scope='Unauthenticated official-source health checks; no successful fetch authenticates model inputs or promotes an artifact.', rows=rows), indent=2, allow_nan=False) + '\n')
        print(f"Official source audit: {len(rows)} checked, {sum(r['status'] == 'error' for r in rows)} errors")
    # Feed failures are visible and fail CI, rather than retaining a false fresh
    # timestamp or interpreting absent source content as a scientific pass.
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
