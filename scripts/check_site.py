#!/usr/bin/env python3
"""Check generated HTML resources and publication consistency without a browser."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from .release_gate import evaluate
except ImportError:
    from release_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


class InspectHTML(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__()
        self.links, self.stack, self.errors = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for attr in ('href', 'src'):
            if attrs.get(attr):
                self.links.append(attrs[attr])
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'Unbalanced end tag {tag}')
        else:
            self.stack.pop()


def check(root=ROOT):
    root = Path(root).resolve()
    errors = []
    pages = [root / 'index.html', *sorted((root / 'docs').rglob('*.html'))]
    for page in pages:
        parsed = InspectHTML()
        parsed.feed(page.read_text())
        if parsed.errors or parsed.stack:
            errors.append(f'{page.relative_to(root)}: {parsed.errors}; open={parsed.stack}')
        for href in parsed.links:
            url = urlparse(href)
            if url.scheme or url.netloc or not url.path:
                continue
            local = (page.parent / unquote(url.path)).resolve()
            if (not local.is_relative_to(root) or not local.exists()
                    or (page.is_relative_to(root / 'docs') and not local.is_relative_to(root / 'docs'))):
                errors.append(f'{page.relative_to(root)}: missing/escaping resource {href}')
    policy = evaluate(root)
    status_path = root / 'docs/status.json'
    try:
        status = json.loads(status_path.read_text())
    except (OSError, ValueError):
        status = {}
    if status != policy:
        errors.append('Generated status JSON differs from the live literal release policy')
    card_path = root / 'docs/run-card.json'
    try:
        card = json.loads(card_path.read_text())
    except (OSError, ValueError):
        card = {}
    if card.get('verdict') != policy['verdict'] or card.get('release_policy') != policy:
        errors.append('Generated run card differs from the live literal release policy')
    downloads = [p for p in (root / 'docs').rglob('*') if p.suffix.lower() in ('.tif', '.tiff', '.zip')]
    if not policy['download_enabled']:
        if downloads:
            errors.append('A public TIFF/ZIP remains despite a negative verdict')
        for path in (root / 'index.html', root / 'docs/index.html', root / 'docs/executive-summary.html'):
            if 'NOT OK TO SUBMIT' not in path.read_text():
                errors.append(f'{path.relative_to(root)} has no clear negative banner')
    return dict(pages_checked=len(pages), verdict=policy['verdict'], errors=errors, passed=not errors,
                scope='Static HTML/resource and policy-consistency checks; not a visual-browser or organizer acceptance test')


def main():
    report = check()
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
