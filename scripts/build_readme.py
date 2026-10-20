#!/usr/bin/env python3
"""Rebuild the README with current status and the standing project brief."""
from pathlib import Path
from release_gate import evaluate
import json

ROOT = Path(__file__).resolve().parents[1]

def main():
    decision = evaluate(ROOT)
    status = 'OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE (selector authorization still required)' if decision['download_enabled'] else 'NOT OK TO SUBMIT — DO NOT SUBMIT'
    reasons = '\n'.join('- ' + r for r in decision['reasons']) if decision['reasons'] else 'All gates passed: holdout improvement, registry uniqueness (dot-field like-for-like), validator, method manifest, and leakage canaries.'
    try:
        receipt = json.loads((ROOT/'evidence'/'e3_receipt.json').read_text())
        zeros_path = receipt.get('raster',{}).get('zeros',{}).get('path','')
        zeros_name = zeros_path.split('/')[-1] if zeros_path else 'no artifact'
        sha = receipt.get('raster',{}).get('zeros',{}).get('sha256','')
        dl_extra = f"\n**Download:** `docs/downloads/{zeros_name}` ({sha[:16]}… verified) — also in `submissions/`\n" if decision['download_enabled'] else ""
        if decision['download_enabled']:
            archive_note = f"The current TIFF `{zeros_name}` is **PUBLISHED** in `docs/downloads/` for selector review (HOLDOUT-SCREENED, not organizer-scored). A valid file is not proof of geothermal discovery; the organizer leaderboard is the only score.\n{dl_extra}"
        else:
            archive_note = f"The current TIFF is archived in `submissions/` for audit only. No submission download is published and no slot was spent.\nA valid file is not necessarily a unique or scientifically validated submission.\n{reasons}\n"
    except Exception as e:
        archive_note = f"The current TIFF is archived in `submissions/` for audit only. No submission download is published and no slot was spent.\nA valid file is not necessarily a unique or scientifically validated submission.\n{reasons}\n"
    head = f'''# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {status}

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json) · [Latest repository review](reports/review-session-2026-10-20.md).

Lane constraints: W 0.1–15 km and along-strike separation ≤3.5W; same dip direction and dextral releasing geometry require measured attributes, not strike proxies.

{archive_note}
## Latest audit state — fail closed

The archived H69-J candidate is not cleared for download or submission. Historical holdout, validator, and registry measurements are documented in `evidence/run_card.json`; they are not a current artifact-bound promotion result. The literal registry overlap test fails, and the release gate also requires current-hash-bound holdout and method-source evidence. The download remains disabled. Do not interpret an archived holdout result as a leaderboard score or a forecast.

## Reproduce the publication audit (no data downloads needed)

```sh
python scripts/release_gate.py
python scripts/build_site69.py
python scripts/build_readme.py
```

For pixel validation and tests:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest scikit-learn
GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-zeros.tif
.venv/bin/pytest -q
```

Full feature stack restored via `scripts/fetch_data.py` (pinned mirrors); registry 751 blobs via `scripts/fetch_registry.py`. GPU not needed; format validator cannot prove geothermal discovery.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

'''
    (ROOT / 'README.md').write_text(head + (ROOT / 'PROMPT.md').read_text())

if __name__ == '__main__':
    main()
