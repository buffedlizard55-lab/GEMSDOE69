#!/usr/bin/env python3
"""Render the same literal release status and full retained request into README."""
from pathlib import Path

try:
    from .release_gate import evaluate
except ImportError:
    from release_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


def main():
    decision = evaluate(ROOT)
    title = 'OK TO DOWNLOAD — SELECTOR AUTHORIZATION STILL REQUIRED' if decision['download_enabled'] else 'NOT OK TO SUBMIT — DO NOT SUBMIT'
    reasons = '\n'.join('- ' + reason for reason in decision['reasons'])
    head = f'''# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {title}

**[Open the project site](https://buffedlizard55-lab.github.io/GEMSDOE69/)** · [Executive summary / submission guide](docs/executive-summary.html) · [Run card](evidence/run_card.json) · [Integrity review](evidence/integrity_review.json)

No new unique, gate-qualified TIFF was produced in this review. No competition slot was selected or used. The archived candidate is format-valid but **not cleared to download or submit**. Negative results are deliverables; a new name or byte hash cannot rescue a failed protocol gate.

### Start here every session

Read this README, the full current request below ([separate copy](PROJECT_REQUEST.md)), [AGENTS.md](AGENTS.md), and [HANDOFF.md](HANDOFF.md) before model work. Historical results in PROMPT.md and archived reports are not current clearance.

Lane: source-polyline tip graph; same dip direction; W **0.1–15 km**; along-strike separation **≤3.5W**. Oblique/en échelon connectors plus kinematically verified dextral releasing pull-aparts and transfer zones. No borrowing another lane's pixel candidates.

### What this review found and fixed

- Freshly reproduced a literal registry failure using the pinned shared comparator: a hash-verified prior has positive values in the whole mirrored footprint, so every nonempty in-footprint proposal has forward overlap 1.0 under the specified support definition. This is a protocol/representation conflict, not identical geology. No private density exemption is allowed.
- Independently found **0.8023481341643177** forward overlap against a sparse local archived field. The candidate therefore still fails even if the universal-support conflict were resolved.
- Removed the release-policy stratification bypass, checked numeric measurements against flags, and blocked model/generation CLIs after the recorded stop.
- Retired an unsafe legacy generator that could synthesize missing canaries, reuse a previous holdout, and mark failed validators successful. Archived artifacts and evidence are preserved, not rewritten to manufacture a pass.
- Flagged hidden-target-dependent flank masks and the older full-catalogue canary. Current HOLDOUT-DTI claims are **archived, not certified**; no numerical improvement is promised.
- Re-read official competition/rules/USGS/geothermal-literature sources; audited all requested family page sources; documented four ranked, untested in-lane hypotheses and data-readiness limits.
- Revalidated both archived TIFF variants locally: float32, EPSG:32611, matching 3730×3292/100 m grid, no NaN inside the footprint, finite values in [0,1]. This is not organizer acceptance or uniqueness clearance.

The H33 reported result **0.2778 is USER-REPORTED-NOT-ORGANIZER-CONFIRMED for its exact file**. Official staff confirms known USGS/INGENIOUS pixels are masked in initial/final scoring, so zero on-catalogue dots alone is not a scoring advantage. Sparse emission plausibly reduces redundant false-positive mass while retaining distance-weighted coverage; hidden-truth causality and a better candidate are not established. [Fresh raster anatomy](evidence/h33-audit-2026-10-20.json) · [Scientific explanation](docs/why-h33-scored.html).

### Current release blockers

{reasons if reasons else 'All literal publication gates passed; a separate selector must still authorize a real slot.'}

### Reproduce without training or external data

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python scripts/validate_submission.py \\
  submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-zeros.tif \\
  submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-nan.tif
python scripts/release_gate.py
python scripts/build_site69.py
python scripts/build_readme.py
```

`generate_unique_submission.py` is intentionally retired; generation/holdout entry points stop before model work while the protocol stop persists. Missing measurements are never filled in.

### Autonomous source feed and site

- `python scripts/refresh_sources.py --family`: reads all user-listed family page sources through GitHub, verifies blob identity and records page/download-link observations separately from user-reported scores. Not an all-raster registry scan or an organizer receipt audit.
- `python scripts/refresh_sources.py --all`: also performs official-source health checks and a dated public leaderboard-table read; errors/login redirects stay explicit. Direct shell downloads are host-allowlisted in Arena, while the research fetch tool could read the official public pages.
- The GitHub Actions workflow refreshes source feeds daily and retains an audited static-site artifact. Direct workflow publishing requires Pages Source = GitHub Actions; while the repository remains on legacy Pages, deployment is explicitly skipped and the committed site is a dated snapshot. The site was verified live after PR29. The workflow never trains, submits, changes thresholds or selects a slot. See Actions for current daily artifacts and any source errors.
- [Claim-level official sources](registry/verified_sources_2026-10-20.json) · [Full family audit](docs/data/family-feed.json) · [Ranked hypotheses](registry/hypotheses_review_2026-10-20.json).

Actual limits: literal registry stop, uncertified holdout/provenance, missing verified attribute joins, non-restored full feature cache, no authenticated organizer data/receipts/remaining weekly allowance. **No GPU is required for this geometry lane.** Source metadata and hash-pinned owner mirrors are useful but do not authenticate official competition input bytes.

Core values: **Maximize P(Win)** by protecting slots and testing falsifiable hypotheses; **Own the Outcome** by exposing defects and negative results.

## Full current project request — read every session

User-reported numbers and earlier pipeline claims below are retained instructions/context, not endorsed measurements. Current status is the gate above.

<details>
<summary>Expand the full 2026-10-20 request (also retained in PROJECT_REQUEST.md)</summary>

'''
    request = (ROOT / 'PROJECT_REQUEST.md').read_text()
    (ROOT / 'README.md').write_text(head + request + '\n</details>\n')


if __name__ == '__main__':
    main()
