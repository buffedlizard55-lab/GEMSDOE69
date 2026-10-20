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

## Latest session — 2026-10-20 relay-fix (Exp1 + Exp2b)

Read [session report](reports/relayfix-2026-10-20.md) before continuing, then
[prior three-pass audit](reports/review-2026-10-20.md).
Tip-graph repairs R1/R2 are implemented and the strict-xfail now passes. Fresh HOLDOUT-DTI
(pooled, 8 cells, 22,641 withheld positives): transfer-only candidate 0.00847 vs repaired
dilatational v1 0.00635 vs no-prior control 0.00215 — a screen, not an organizer score.
The candidate TIF in `submissions/` passes format validation on exact bytes but fails the
literal registry-overlap gate (worst overlap 1.0 vs whole-footprint registry surfaces;
Spearman ≤0.28 everywhere). Verdict stays **negative**: no download, no slot. Do not claim
a leaderboard improvement; only an organizer receipt could establish one.

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
GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py submissions/h69-transferonly-36325-20261020T204438Z-a114b6c4-zeros.tif
.venv/bin/pytest -q
```

Full science rerun (restores pinned mirrors first): `python scripts/restore_data.py`, link
`.cache/gems_data` to the restore target, then `scripts/run_relayfix_20261020.py gate` and
`scripts/run_exp2b_transfer.py gate`. Mirrors are integrity-pinned owner copies, not
organizer-authenticated sources. Registry corpus: 862 rasters per
`registry/registry_index_69.json` (fetch + sha256-verify into `/tmp/gems_registry_cache`).
CPU validation works; GPU training is not required for this geometry lane. A format validator cannot prove geothermal discovery or hidden-fault accuracy.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

'''
    (ROOT / 'README.md').write_text(head + (ROOT / 'PROMPT.md').read_text())

if __name__ == '__main__':
    main()
