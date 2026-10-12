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
    promote = card["verdict"] == "promote"
    head = ("## ✅ OK TO SUBMIT — gate met, unique, validated" if promote else
            "## ⛔ NOT OK TO SUBMIT — negative result (do not spend a weekly slot)")
    arms = "\n".join(f"| `{k}` | {f4(v['dti'])} | [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] |" for k, v in sc.items())
    text = f"""# GEMSDOE69 — relay-ramp & pull-apart corridor lane · DOE GEMS Prize (DrivenData #306)

**Site:** <{SITE}> · **How to submit:** <{SITE}docs/executive-summary.html> · **Run card:** [`evidence/run_card.json`](evidence/run_card.json)

{head}

{('The lane artefact passed its pre-registered gate.' if promote else
  'A **unique, format-valid** TIF was generated for this lane, but it **failed the pre-registered gate**: the corridor-restricted dots '
  'did not beat the same pipeline without corridor priors on the hide-and-recover holdout. Per the protocol it is kept only as the '
  'negative-result deliverable (clearly labelled on the site) and is **not** offered as a submission.')}

| Gate (pre-registered) | Value |
|---|---|
| Lane arm `A_corridor` | HOLDOUT-DTI **{f4(sc['A_corridor']['dti'])}** [{sc['A_corridor']['ci95'][0]:.4f}, {sc['A_corridor']['ci95'][1]:.4f}] |
| Same pipeline without corridor priors `B1_halo` | HOLDOUT-DTI **{f4(sc['B1_halo']['dti'])}** [{sc['B1_halo']['ci95'][0]:.4f}, {sc['B1_halo']['ci95'][1]:.4f}] |
| Δ (paired 20 km block bootstrap) | **{g['delta']:+.4f}** [{g['ci95'][0]:+.4f}, {g['ci95'][1]:+.4f}] → **{'PASS' if g['passed'] else 'FAIL'}** |
| Evaluator / withheld positives | `{card['holdout']['evaluator_version']}` · {card['holdout']['withheld_positive_pixels_pooled']:,} pixels pooled over draws {card['holdout']['draws']} |
| Uniqueness (surface / dots) | worst Spearman {f4(u['surface']['worst_spearman'])} / {f4(u['dots']['worst_spearman'])}; worst 3-px overlap {f4(u['surface']['worst_forward_overlap_3px'])} / {f4(u['dots']['worst_forward_overlap_3px'])} against {u['dots']['rasters_checked']} prior rasters |
| File | [`{sub['zeros_tif']}`]({sub['zeros_tif']}) · sha256 `{sub['zeros_sha256']}` · {sub['dots']['n']:,} dots, 0 on the catalogue |
| Validator | {'PASS' if all(v['all_checks_passed'] for v in card['validator_output'].values()) else 'FAIL'} (both encodings; `scripts/validate_submission.py`) |
| Name / note | `{card['submission_name']}` / `{card['submission_note']}` ({card['submission_note_chars']} chars) |

All arms (HOLDOUT-DTI, pooled over two draws; not leaderboard scores):

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
{arms}

`A` = the lane (dots only inside corridors) · `AP` = corridor prior as a boost · `B1` = evidence × distance halo (gate comparator) ·
`B0` = evidence only · `C` = distance only · `R` = random dispersed dots inside the same corridors.

**What this means.** On the catalogue hide-and-recover instrument the withheld faults are best predicted by plain proximity to the
visible catalogue; neither the step-over geometry nor the geophysical evidence adds ranking power at this scale, and restricting dots to
corridors loses recall. See [docs/research/why-0278.md](docs/research/why-0278.md) for why the family's best file (owner-reported
0.2778) works — near-minimal mass on a wide field, with catalogue-adjacent dots removed — and what it would take to beat it.

---

{prompt}

---

## Repository guide

| Path | What it is |
|---|---|
| `src/gems69/` | lane code: `traces.py` (polylines, dip polarity, tips), `corridors.py` (relay / pull-apart / transfer corridors, scoring), `evidence.py` (multi-scale gravity & magnetic edges, magnetic lows, lidar scarps), `calibrate.py`, `pipeline.py` |
| `vendor/gems57/` | byte-for-byte copy of the shared template `60GEMSDOE/src/gems57` @ `32024716` (pins: `registry/template_pin.json`) — evaluator, writer, validator, allocator, uniqueness |
| `scripts/` | `restore_data.py`, `run_lane.py e1|e2`, `build_submission.py`, `check_uniqueness.py`, `validate_submission.py`, `make_run_card.py`, `build_site.py`, `build_readme.py`, `fetch_registry.py` |
| `evidence/` | every measurement: `e0_champion_ladder_measured.json`, `e1_first_test.json`, `e2_gate.json`, `e3_build.json`, `e3_uniqueness.json`, `e3_validation.json`, `e3_corridor_rationale.csv`, `run_card.json`, `irregularities.json` |
| `registry/` | `preregistration.json`, `template_pin.json`, `registry_index_69.json` (uniqueness corpus), `leaderboard_snapshot_2026-10-12.json` |
| `docs/` | GitHub Pages subpages and downloads; the landing page is `index.html` at the repository root |

### Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy rasterio scikit-image scikit-learn markdown pytest
.venv/bin/python scripts/restore_data.py          # pinned inputs -> $GEMS_DATA (default /tmp/gems_data)
.venv/bin/python -c "import sys; sys.path.insert(0,'src'); from gems69 import data, evidence; evidence.build_cache(data.load_grid())"
.venv/bin/python scripts/run_lane.py e1          # leakage canary + hard-link masking test
.venv/bin/python scripts/run_lane.py e2          # gate (two draws, six arms)
.venv/bin/python scripts/build_submission.py     # live artefact (verdict comes from e2)
.venv/bin/python scripts/fetch_registry.py && .venv/bin/python scripts/check_uniqueness.py
.venv/bin/python scripts/validate_submission.py docs/downloads/*.tif --json evidence/e3_validation.json
.venv/bin/python scripts/make_run_card.py && .venv/bin/python scripts/build_site.py && .venv/bin/python scripts/build_readme.py
.venv/bin/python -m pytest -q tests
```

## Limitations

* The holdout's truth is the **catalogue itself** (withheld components), whereas the prize's truth is **new** expert-mapped faults whose
  sources, types and coverage are undisclosed (organizer, forum thread 11527). A sibling measured ρ ≈ +0.14 between this kind of
  instrument and owner-reported live scores (IR-69-09). A negative here is strong evidence against the lane on catalogue-like faults,
  weaker evidence about new faults.
* Dip polarity is inferred from topography for ~59 % of records (90 % agreement where recorded); strike-slip sense comes from the
  catalogue's `sense` attribute only.
* The live greedy bar uses a modelled |G| = 12,226 px (IR-69-10); it changes the dot count, not the verdict.
* The uniqueness corpus is the owner's public repositories only (IR-12).

## Next steps (for a new session; each needs its own pre-registration)

1. **Placement, not geometry, was the larger loss inside corridors** — random dispersed dots in the same corridors beat the greedy
   placement there. Any future corridor work should cap density (Poisson-disk ≥ 2.8 px, as the 0.2778 ladder found) before testing priors.
2. **Measure on a population-matched instrument:** state-map faults absent from the catalogue (SGMC off-catalogue, used by 60GEMSDOE)
   are closer to "new faults" than withheld catalogue components.
3. **H69-4 accommodation zones** (opposite-dip tip pairs) and **H69-5 local stress orientation** from the INGENIOUS geodetic strain-rate
   tensors are untested; H69-5 needs the geodetics zip (SHA-256 `0dd65ccc…`), which is not in the mirrors reachable from this sandbox
   (GDR is not on the allow-list) — access need.
4. The selector (separate step) should keep the family's best file as the reference; nothing in this repository beats it on any
   instrument.
"""
    (ROOT / "README.md").write_text(text)
    print("README written", len(text), "chars")


if __name__ == "__main__":
    main()
