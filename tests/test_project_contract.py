from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from scripts.audit_workspace import ROOT, build_report


class LocalLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


class BalancedTags(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}> with stack {self.stack[-3:]}")
            return
        self.stack.pop()


class ProjectContractTests(unittest.TestCase):
    def test_workspace_audit_fails_closed_on_missing_inputs_and_tools(self) -> None:
        report = build_report(ROOT)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["missing_prerequisites"])
        self.assertFalse(report["inputs"]["training_features"]["present"])
        self.assertFalse(report["inputs"]["labels"]["present"])
        self.assertFalse(report["inputs"]["existing_faults"]["present"])
        self.assertFalse(report["inputs"]["dem_links"]["present"])
        self.assertFalse(report["inputs"]["sample_submission"]["present"])
        # Since PR #5 the shared template is vendored byte-for-byte (vendor/gems57); competition inputs
        # are restored outside git by scripts/restore_data.py, so a fresh checkout still lacks them.
        self.assertTrue(report["shared_tools"]["holdout_evaluator"]["present"])
        self.assertTrue(report["shared_tools"]["submission_writer"]["present"])
        self.assertTrue(report["project_tools"]["dti_metric"]["present"])
        self.assertTrue(report["project_tools"]["format_validator"]["present"])
        self.assertTrue(report["project_tools"]["promotion_gate"]["present"])

    def test_run_card_is_valid_negative_and_has_short_note(self) -> None:
        card_path = ROOT / "reports/run-card-2026-10-12.json"
        card = json.loads(card_path.read_text(encoding="utf-8"))
        self.assertEqual(card["verdict"], "negative")
        self.assertIsNone(card["raster_sha256"])
        self.assertIsNone(card["submission"]["name"])
        self.assertLessEqual(len(card["submission"]["note"]), 140)
        self.assertEqual(card["holdout_DTI"]["evidence_class"], "HOLDOUT-DTI: NOT MEASURED")
        self.assertIsNone(card["organizer_confirmed_submission_receipt"])

    def test_site_makes_no_download_status_unambiguous(self) -> None:
        # Since PR #5 the site carries a data-backed NEGATIVE verdict: the lane TIF exists but is archived
        # as a negative result and must be labelled "do not submit" wherever it is linked.
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        guide = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8")
        card = json.loads((ROOT / "evidence/run_card.json").read_text(encoding="utf-8"))
        if card["verdict"] != "promote":
            self.assertIn("NOT OK TO SUBMIT", index)
            self.assertIn("DO NOT SUBMIT", index)
            self.assertIn("NOT OK TO SUBMIT", guide)
            self.assertIn("do not submit", index.lower())
        legacy = (ROOT / "docs/parallel/executive-summary.html").read_text(encoding="utf-8")
        self.assertIn("No submission file is available", legacy)

    def test_all_local_html_links_resolve(self) -> None:
        pages = sorted(ROOT.rglob("*.html"))
        self.assertGreaterEqual(len(pages), 5)
        missing: list[str] = []
        for page in pages:
            parser = LocalLinks()
            parser.feed(page.read_text(encoding="utf-8"))
            for href in parser.hrefs:
                parsed = urlparse(href)
                if parsed.scheme or parsed.netloc or href.startswith("#"):
                    continue
                local_path = (page.parent / parsed.path).resolve()
                if parsed.path and not local_path.exists():
                    missing.append(f"{page.name}: {href}")
        self.assertEqual(missing, [])

    def test_html_tags_are_balanced(self) -> None:
        unbalanced: list[str] = []
        for page in ROOT.rglob("*.html"):
            parser = BalancedTags()
            parser.feed(page.read_text(encoding="utf-8"))
            parser.close()
            if parser.errors or parser.stack:
                unbalanced.append(f"{page.name}: errors={parser.errors}, open={parser.stack}")
        self.assertEqual(unbalanced, [])

    def test_local_markdown_links_resolve(self) -> None:
        missing: list[str] = []
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for page in ROOT.rglob("*.md"):
            if ".git" in page.parts:
                continue
            for target in link_pattern.findall(page.read_text(encoding="utf-8")):
                parsed = urlparse(target)
                if parsed.scheme or parsed.netloc or target.startswith("#"):
                    continue
                if parsed.path and not (page.parent / parsed.path).resolve().exists():
                    missing.append(f"{page.relative_to(ROOT)}: {target}")
        self.assertEqual(missing, [])

    def test_geometry_lane_and_external_data_limits_are_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        hypotheses = (ROOT / "docs/parallel/hypotheses.html").read_text(encoding="utf-8")
        sources = (ROOT / "docs/parallel/sources.html").read_text(encoding="utf-8")
        self.assertIn("0.1–15 km", readme)
        self.assertIn("≤3.5W", readme)
        self.assertIn("same dip direction", hypotheses)
        self.assertIn("USGS National Map 3DEP one-meter DEM collection", sources)
        self.assertIn("Exact tile coverage over the competition AOI", sources)
        self.assertIn("not a ready-to-use independent predictor", sources)

    def test_exactly_five_ranked_hypotheses_are_present(self) -> None:
        page = (ROOT / "docs/parallel/hypotheses.html").read_text(encoding="utf-8")
        for marker in (
            "RANK 1 · TOP CANDIDATE",
            "RANK 2",
            "RANK 3",
            "RANK 4",
            "RANK 5",
        ):
            self.assertIn(marker, page)
        self.assertIn("not tested", page.lower())
        self.assertIn("not slot-eligible", page)


if __name__ == "__main__":
    unittest.main()
