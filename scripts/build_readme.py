#!/usr/bin/env python3
"""Rebuild the README with current status and the standing project brief."""
from pathlib import Path
from release_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]

def main():
    decision = evaluate(ROOT)
    status = 'OK TO DOWNLOAD — selector authorization still required' if decision['download_enabled'] else 'NOT OK TO SUBMIT — DO NOT SUBMIT'
    reasons = '\n'.join('- ' + r for r in decision['reasons'])
    head = f'''# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {status}

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json).

Lane constraints: W 0.1–15 km and along-strike separation ≤3.5W; same dip direction and dextral releasing geometry require measured attributes, not strike proxies.

The current TIFF is archived in `submissions/` for audit only. No submission download is published and no slot was spent.
A valid file is not necessarily a unique or scientifically validated submission. The literal overlap gate cannot be replaced by a stratified diagnostic.

{reasons}

## Latest review — 2026-10-20

Read [three-pass audit and next steps](reports/review-2026-10-20.md) and the
[follow-up audit](reports/followup-2026-10-20.md), plus the concurrent
[checkout review](reports/checkout-audit-2026-10-20.md), before continuing.
The archived HOLDOUT-DTI result is not an organizer score and was not rerun in this review.
Both current TIFF variants were revalidated on the pinned bridge grid; see [fresh validator output](evidence/review_validator_2026-10-20.json).
The latest radiometric method is not reproducible from the checked-in scoring code. Do not claim a leaderboard improvement.

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
GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py submissions/h69-z-radiometric-halo-31994-20261020T182654Z-31913c0c-zeros.tif
.venv/bin/pytest -q
```

The full feature stack and registry corpus are not restored in this checkout. Existing fetch scripts use integrity-pinned owner mirrors, not organizer-authenticated sources.
CPU validation works; GPU training is not required for this geometry lane. A format validator cannot prove geothermal discovery or hidden-fault accuracy.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

'''
    (ROOT / 'README.md').write_text(head + (ROOT / 'PROMPT.md').read_text())

if __name__ == '__main__':
    main()
