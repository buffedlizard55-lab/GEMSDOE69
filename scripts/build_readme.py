#!/usr/bin/env python3
"""Rebuild the README with current status and the standing project brief."""
from pathlib import Path
from release_gate import evaluate
import json

ROOT = Path(__file__).resolve().parents[1]


def latest_section():
    p = ROOT / 'evidence' / 'session_experiments.json'
    if not p.exists():
        return '## Latest\n\nNo session experiment summary found (evidence/session_experiments.json).\n'
    doc = json.loads(p.read_text())
    lines = ['## Latest — 2026-10-20 session 3 (preregistered experiments; HOLDOUT-DTI, not organizer scores)', '',
             '| Experiment | Detached pooled DTI (candidate / control / transfer_ref) | Δ vs control [95% CI] | Δ vs transfer_ref [95% CI] | Verdict |',
             '|---|---|---|---|---|']
    for e in doc['experiments']:
        r = e['results']['primary_detached']; pd = r['pooled_dti']
        c = pd[e['candidate_arm']]
        dc, dt = r['candidate_minus_control'], r['candidate_minus_transfer_ref']
        f = lambda d: f"{d['mean']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]"
        lines.append(f"| {e['id']} | {c:.4f} / {pd['control_noprior']:.4f} / {pd['transfer_ref']:.4f} | {f(dc)} | {f(dt)} | **{e['verdict']}** |")
    lines += ['', 'Evaluator: vendor/template66 `gems57.holdout` (α 0.2, β 0.8, 300 m triangular), seeds 20/21, 8 detached cells, '
              f"{doc['experiments'][0]['results']['primary_detached']['withheld_positive_px'] if doc['experiments'] else 0} withheld positive px; paired cell bootstrap (2,000). "
              'Instrument fix IR-69-HOLD-01: archived lane numbers are not comparable. Details: `reports/session3-2026-10-20.md`.', '']
    return '\n'.join(lines)


def main():
    decision = evaluate(ROOT)
    status = 'OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE (selector authorization still required)' if decision['download_enabled'] else 'NOT OK TO SUBMIT — DO NOT SUBMIT'
    reasons = '\n'.join('- ' + r for r in decision['reasons']) if decision['reasons'] else 'All gates passed: holdout improvement, registry uniqueness (dot-field like-for-like), validator, method manifest, and leakage canaries.'
    try:
        cand = decision.get('candidate') or {}
        receipt = json.loads((ROOT/'evidence'/(cand.get('receipt') or 'e3_receipt.json')).read_text())
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
    latest = latest_section()
    head = f'''# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {status}

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json).

Lane constraints: W 0.1–15 km and along-strike separation ≤3.5W; same dip direction and dextral releasing geometry require measured attributes, not strike proxies.

{archive_note}
{latest}
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
GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py submissions/<candidate>-zeros.tif
.venv/bin/pytest -q
```

Full feature stack restored via `scripts/fetch_data.py` (pinned mirrors); registry index v2 (942 grid rasters) via `scripts/refresh_registry_v2.py`. GPU not needed; format validator cannot prove geothermal discovery.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

'''
    (ROOT / 'README.md').write_text(head + (ROOT / 'PROMPT.md').read_text())

if __name__ == '__main__':
    main()
