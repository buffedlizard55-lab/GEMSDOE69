#!/usr/bin/env python3
"""Generate README.md: verdict block (from the run card) + the full standing brief + guide."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
SITE = "https://buffedlizard55-lab.github.io/GEMSDOE69/"


def f4(x):
    return "—" if x is None else f"{x:.4f}"


def main():
    card = json.loads((EVID / "run_card.json").read_text())
    e3 = json.loads((EVID / "e3_build.json").read_text())
    prompt = (ROOT / "PROMPT.md").read_text()
    g = card["holdout"]["gate"]
    sc = card["holdout"]["all_arms"]
    sub = card["raster"]
    u = card["registry_uniqueness"]
    comp = u.get("comparable_budget_reading") or {}
    promote = card["verdict"] == "promote"
    head = (
        "## ✅ OK TO DOWNLOAD AND SUBMIT — gate met, unique, validated"
        if promote
        else "## ⛔ NOT OK TO SUBMIT — negative result (do not spend a weekly slot)"
    )
    arms = "\n".join(f"| `{k}` | {f4(v['dti'])} | [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] |" for k, v in sc.items())
    text = f"""# GEMSDOE69 — relay-ramp & pull-apart corridor lane · DOE GEMS Prize (DrivenData #306)

**Site:** <{SITE}> · **How to submit:** <{SITE}docs/executive-summary.html> · **Run card:** [`evidence/run_card.json`](evidence/run_card.json)

{head}

**Lane in one line:** same-dip relay pairs between facing catalogue fault tips (W 0.1–15 km, along-strike separation ≤3.5W, up to 4 partners per tip) with oblique-connector, en échelon, wing-splay, and flank-relay breach traces, plus pull-aparts at strike-slip releasing steps and transfer zones at strike-slip terminations, scored by multi-scale gravity/magnetic edges, magnetic lows, lidar scarps and dilation tendency, calibrated by 3-level hierarchical empirical-Bayes shrinkage and placed by 300 m kernel-decimated greedy marginal-DTI allocation (`tile_px = 3`).

{('The lane artefact **passed its pre-registered holdout gate**, passed registry uniqueness across all 862 prior rasters (and all 584 comparable-budget `< 80,000`-dot rasters), and passed format validation on both GeoTIFF encodings. Promotion to one of the 3 weekly DrivenData submission slots is a separate selector step.' if promote else 'The lane artefact failed its pre-registered gate and is archived as a negative result.')}

| Gate (pre-registered) | Value |
|---|---|
| Lane arm `A_corridor` | HOLDOUT-DTI **{f4(sc['A_corridor']['dti'])}** [{sc['A_corridor']['ci95'][0]:.4f}, {sc['A_corridor']['ci95'][1]:.4f}] |
| Same pipeline without corridor priors `B1_halo` | HOLDOUT-DTI **{f4(sc['B1_halo']['dti'])}** [{sc['B1_halo']['ci95'][0]:.4f}, {sc['B1_halo']['ci95'][1]:.4f}] |
| Δ (paired 20 km block bootstrap) | **{g['delta']:+.4f}** [{g['ci95'][0]:+.4f}, {g['ci95'][1]:+.4f}] → **{'PASS' if g['passed'] else 'FAIL'}** (`per_draw_lower_bound_positive = {g['per_draw_lower_bound_positive']}`) |
| Evaluator / withheld positives | `{card['holdout']['evaluator_version']}` · {card['holdout']['withheld_positive_pixels_pooled']:,} pixels pooled over draws {card['holdout']['draws']} |
| Uniqueness vs {u['dots']['rasters_checked']} prior rasters | worst Spearman {f4(u['surface']['worst_spearman'])} (surface) / {f4(u['dots']['worst_spearman'])} (dots), limit 0.90; worst 3-px dot overlap vs {comp.get('comparable_rasters_checked', 584)} comparable-budget (`< 80k` dots) rasters **{f4(comp.get('worst_forward_overlap'))} ≤ 0.70** (`0` firings; `0` discriminating firings across all 862 rasters; 87 non-discriminating continuous-surface / `>= 80k`-dot blanket-halo firings audited in [`evidence/e3_uniqueness.json`](evidence/e3_uniqueness.json)) · bytes and decoded pixels unique among all checked rasters |
| Primary file (all-finite zeros) | [`{sub['zeros_tif']}`]({sub['zeros_tif']}) · sha256 `{sub['zeros_sha256']}` · {sub['dots']['n']:,} dots, 0 on the catalogue |
| ZIP / NaN-outside twin | [`{sub['zip']}`]({sub['zip']}) (`{sub['zip_sha256']}`) · [`{sub['nan_twin_tif']}`]({sub['nan_twin_tif']}) (`{sub['nan_twin_sha256']}`) |
| Validator | {'PASS' if all(v['all_checks_passed'] for v in card['validator_output'].values()) else 'FAIL'} (both encodings; `scripts/validate_submission.py`) |
| Name / note | `{card['submission_name']}` / `{card['submission_note']}` ({card['submission_note_chars']} chars) |

All arms (HOLDOUT-DTI, pooled over two draws; not leaderboard scores):

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
{arms}

`A_corridor` = the lane (dots inside corridors) · `AP_halo_corridor` = corridor prior as a boost · `B1_halo` = evidence × distance halo (gate comparator) ·
`B0_evidence` = evidence only · `C_distance` = distance only · `R_corridor_random` = random dispersed dots inside the same corridors.

**What this means.** With multi-partner relay connectors (`max_partners = 4`), normal-fault tip continuations, wing splays, and flank-relay breaches (`include_splays = True`, capturing 84.1 %–95.8 % of withheld truth inside `dline ≤ 8 px`), 3-level hierarchical empirical-Bayes calibration (`src/gems69/calibrate.py`), and 300 m kernel-radius decimation (`tile_px = 3`, `src/gems69/pipeline.py`), `A_corridor` (**0.1347**) beats `B1_halo` (**0.1264**, Δ = **+0.0083 [+0.0039, +0.0123]**) as well as `AP_halo_corridor` (0.1334), `C_distance` (0.1218), `R_corridor_random` (0.1112), and `B0_evidence` (0.0823). On the live 43,056-dot build, 61.98 % of the `h33-2-b2` champion's dots sit inside our corridor band while only 25.67 % of our dots lie within 3 px of a champion dot. See [docs/research/why-0278.md](docs/research/why-0278.md) for why the family's best file (owner-reported 0.2778) works and [docs/research/hypotheses.md](docs/research/hypotheses.md) for the 5 ranked geological hypotheses.

---

{prompt}

---

## Repository guide

| Path | What it is |
|---|---|
| `src/gems69/` | lane code: `traces.py` (polylines, dip polarity, tips), `corridors.py` (relay / pull-apart / transfer + tip-splay / flank-breach corridors, scoring), `evidence.py` (multi-scale gravity & magnetic edges, magnetic lows, lidar scarps), `calibrate.py` (3-level hierarchical empirical-Bayes calibration), `pipeline.py` (`tile_px = 3` kernel-decimated greedy allocation), `holdout69.py` |
| `vendor/template66/gems57/` | byte-for-byte copy of the shared template `60GEMSDOE/src/gems57` @ `32024716` (pins: `TEMPLATE_SHA256.txt`) — evaluator, writer, validator, allocator, uniqueness |
| `scripts/` | `restore_data.py`, `run_lane.py e1` / `e2`, `build_submission.py`, `check_uniqueness.py`, `validate_submission.py`, `make_run_card.py`, `build_site.py`, `build_readme.py`, `fetch_registry.py` |
| `evidence/` | every measurement: `e0_champion_ladder_measured.json`, `e1_first_test.json`, `e2_gate.json`, `e3_build.json`, `e3_uniqueness.json`, `e3_validation.json`, `e3_corridor_rationale.csv`, `run_card.json`, `irregularities.json` |
| `registry/` | `preregistration.json`, `template_pin.json`, `registry_index_69.json` (uniqueness corpus), `leaderboard_snapshot_2026-10-12.json` |
| `docs/` | GitHub Pages subpages and downloads; both `index.html` at the repository root and `docs/index.html` render the full landing page |
| `docs/parallel/`, `src/gems/`, `reports/`, `scripts/status.py`, `scripts/audit_workspace.py` | preserved work of the parallel data-less workbench sessions on this repository (PRs #1–#4): their site pages, local DTI metric / validator / gate and tests |

### Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy rasterio scikit-image scikit-learn markdown pytest
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/restore_data.py          # pinned inputs -> $GEMS_DATA (default /tmp/gems_data)
PYTHONPATH=src:vendor/template66 .venv/bin/python -c "from gems69 import data, evidence; evidence.build_cache(data.load_grid())"
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/run_lane.py e1           # leakage canary + hard-link masking test
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/run_lane.py e2 --draws 2 # gate (two draws, six arms)
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/build_submission.py      # live artefact (43,056 dots)
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/check_uniqueness.py      # 862-raster uniqueness audit (surface + dots)
PYTHONPATH=src:vendor/template66 .venv/bin/python scripts/validate_submission.py docs/downloads/*.tif --json evidence/e3_validation.json
.venv/bin/python scripts/make_run_card.py && .venv/bin/python scripts/build_site.py && .venv/bin/python scripts/build_readme.py
PYTHONPATH=src:vendor/template66 .venv/bin/python -m pytest -q tests
```

## Limitations

* The holdout's truth is the **catalogue itself** (withheld components), whereas the prize's truth is **new** expert-mapped faults whose
  sources, types and coverage are undisclosed (organizer, forum thread 11527). Passing the holdout gate is necessary, not sufficient, for a live leaderboard gain; promotion to one of the 3 weekly slots is a separate selector step.
* Dip polarity is inferred from topography for ~59 % of records (90.3 % agreement where recorded); strike-slip sense comes from the
  catalogue's `sense` attribute only.
* The live greedy bar uses a modelled |G| = 12,226 px (IR-69-10); it sets the live dot count (43,056), not the holdout gate verdict.
* The uniqueness corpus is the owner's public repositories only (IR-69-12).

## Compliance note (official rules, verified)

The official rules (§3.2, <https://www.nlr.gov/docs/fy26osti/96647.pdf>) allow generative-AI use but require finalists to
**disclose in the narrative** the extent to which it was used, and to deliver complete, reproducible code and documentation. This
repository was produced with an AI agent; its code, pins and evidence files are kept reproducible for that purpose.
"""
    (ROOT / "README.md").write_text(text)
    print("README written", len(text), "chars")


if __name__ == "__main__":
    main()
