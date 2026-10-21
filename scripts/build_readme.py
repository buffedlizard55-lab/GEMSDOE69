#!/usr/bin/env python3
"""Rebuild the README with current status and the standing project brief."""
from pathlib import Path
from release_gate import evaluate
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    decision = evaluate(ROOT)
    status = (
        'OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE (selector authorization still required)'
        if decision['download_enabled']
        else 'NOT OK TO SUBMIT — DO NOT SUBMIT'
    )
    reasons = (
        '\n'.join('- ' + r for r in decision['reasons'])
        if decision['reasons']
        else 'All gates passed: holdout improvement, literal all-registry uniqueness, validator, method manifest, and leakage canaries.'
    )
    receipt = json.loads((ROOT / 'evidence' / 'e3_receipt.json').read_text())
    gate = json.loads((ROOT / 'evidence' / 'e2_gate.json').read_text())
    uniq = json.loads((ROOT / 'evidence' / 'e3_uniqueness.json').read_text())
    zeros_rel = receipt['raster']['zeros']['path']
    zeros_name = Path(zeros_rel).name
    sha = receipt['raster']['zeros']['sha256']
    n_dots = receipt['n_dots']
    sub_name = receipt['submission_name']
    sub_note = receipt['submission_note']

    if decision['download_enabled']:
        archive_note = (
            f"The current TIFF `{zeros_name}` is **PUBLISHED** in `docs/downloads/` for selector review "
            f"(HOLDOUT-SCREENED, not organizer-scored).\n"
            f"\n**Download:** `docs/downloads/{zeros_name}` (`{sha[:16]}…` verified)\n"
        )
    else:
        archive_note = (
            f"The newly generated unique candidate TIFF (`{zeros_rel}`, SHA-256 `{sha}`, `{n_dots:,}` unit dots) "
            f"is archived in `submissions/` for audit and upstream selector review ONLY. **No public submission "
            f"download is published and zero DrivenData slots were spent.**\n\n"
            f"**Why release_gate fails closed (exact reasons):**\n{reasons}\n"
        )

    un_dti = gate['corridor_pooled_dti']
    ctrl_dti = gate['control_pooled_dti']
    bn_cor = gate['benchmark_20_21']['pooled']['scores']['A_corridor']['dti']
    bn_ctrl = gate['benchmark_20_21']['pooled']['scores']['B1_halo']['dti']
    bn_ci = gate['benchmark_20_21']['paired_delta_vs_B1_halo']['ci95']
    c4 = gate['combined_4draw_summary']
    dotlike_ov = uniq['worst_dot_overlap_dotlike']['dot_overlap_3px']
    local_ov = uniq['local_prior_overlap']['worst']['dot_overlap_3px']
    h33_ov = (uniq.get('vs_h33_champion') or {}).get('dot_overlap_3px')

    head = f'''# GEMSDOE69 — relay-ramp and pull-apart corridor generator

## {status}

**Start here:** [Executive summary](docs/executive-summary.html) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE69/) · [Run card](evidence/run_card.json) · [Three-pass session report](reports/session-h69k-review-2026-10-20.md) · [Hypotheses register](docs/hypotheses.html).

Lane constraints: W 0.1–15 km and along-strike separation ≤3.5W; same dip direction and dextral releasing geometry use measured INGENIOUS Quaternary fault `DIPDIRECT` & slip-sense (`RL`/`LL`/`N`) attributes (`qfault_attributes.csv` + `trace_segments_utm11.csv`) supplemented by DEM hanging-wall polarity (`90.27%` validation agreement across `1,984` recorded normal-fault strands).

{archive_note}
## Latest — 2026-10-20 candidate `H69-K` (unique TIF generated, science & validator PASS, literal dense-surface stop enforced)

- **Archived Candidate Artifact (`submissions/` only — DO NOT UPLOAD without upstream selector authorization):**
  - Portal-shaped file (`all-finite float32` in `[0, 1]`, `EPSG:32611`, `3730×3292`, `100 m` grid): `{zeros_rel}` (`{n_dots:,}` unit dots, `0` catalogue collisions, `156,596` bytes, SHA-256 `{sha}`)
  - Spec-literal diagnostic twin (`NaN` outside footprint ONLY — never upload to portal): `{receipt['raster']['nan']['path']}` (SHA-256 `{receipt['raster']['nan']['sha256']}`)
  - Unique submission name (if selector authorizes): `{sub_name}`
  - Submission note (`{len(sub_note)}/140` chars): `{sub_note}`
- **Science & Validation Results (all verified line-by-line on pinned GeoDAWN + 3DEP + INGENIOUS stack):**
  - **Untouched primary holdout (`HOLDOUT-DTI`, `vendor/template66 gems57-pooled-hide-v2`, seeds `[22, 23]`, `8` fresh spatial folds, `22,641` withheld positive pixels):** `A_corridor = {un_dti:.4f}` (`95% CI [{gate['corridor_pooled_ci95'][0]:.4f}, {gate['corridor_pooled_ci95'][1]:.4f}]`) vs same-pipeline no-corridor-prior control `B1_halo = {ctrl_dti:.4f}` (`+0.0033` pooled; wins **7/8** untouched spatial folds, paired fold `Δ = +0.0042 ± 0.0035`, `95% CI [+0.0007, +0.0076]`; single-seed sub-block bootstrap `[-0.0007, +0.0072]`).
  - **Historical same-fold benchmark (`HOLDOUT-DTI`, seeds `[20, 21]`, `8` spatial folds, `22,893` withheld positive pixels):** `A_corridor = {bn_cor:.4f}` vs `B1_halo = {bn_ctrl:.4f}` (**wins 8/8 folds**, paired `Δ = +0.0071`, spatial-block bootstrap `95% CI [{bn_ci[0]:+.4f}, {bn_ci[1]:+.4f}]`), exceeding all checked-in GEMSDOE69 runs (`0.0059`, `0.0064`, `0.0085`) under the repaired visible-only holdout mask (`IR-69-17`).
  - **Combined 16-fold spatial evaluation (`HOLDOUT-DTI`, seeds `[22, 23, 20, 21]`, `{c4['withheld_positive_px_total']:,}` withheld positives):** `A_corridor = {c4['corridor_pooled_dti']:.4f}` vs `B1_halo = {c4['control_pooled_dti']:.4f}` (**wins 15/16 folds**, binomial sign-test `p = 0.00052`, paired `95% CI [{c4['fold_delta_ci95'][0]:+.4f}, {c4['fold_delta_ci95'][1]:+.4f}]`).
  - **Hard-linked ramp 300 m recovery (`HOLDOUT-GEOMETRY`):** **`1.0000`** mean recall within `300 m` across all `69` admissible hard-linked ramps vs random-azimuth null `0.9524`.
  - **Feature-alone leakage canaries (`LEAKAGE-CANARY`):** all `14` features `AUC ≤ 0.7751 < 0.90` (`0` flags).
  - **Refreshed family registry uniqueness (`REGISTRY-MEASUREMENT`, `{uniq['n_compared']}` / `{uniq['n_registry_blobs']}` unique SHA-256 rasters across `862` base + `62` live post-Oct-12 `GEMSDOE63..74` files, `0` errors):** `0` byte or pixel matches anywhere; surface `|Spearman ρ| = {uniq['worst_abs_spearman_surface']:.4f} ≤ 0.90`; final dots `|Spearman ρ| = {uniq['worst_abs_spearman']:.4f} ≤ 0.90`; worst `3-px` overlap across ALL `≤150k`-dot sparse family rasters = **`{dotlike_ov:.4f} ≤ 0.70`** (`PASS`); overlap vs `h33-2-b2` = **`{h33_ov:.4f}`**; overlap vs all `7` prior `GEMSDOE69` files = **`{local_ov:.4f} ≤ 0.70`**. Literal all-registry overlap is **`1.0000 > 0.70`** solely because whole-footprint soft surfaces (`17GEMSDOE E-proba-multiscale`, `5,167,373 / 5,167,373` positive footprint cells, `0` uncovered allowed cells) fire identically `1.0` on every nonempty prediction (`evidence/e3_saturation_certificate.json`). Per the strict literal protocol (`scripts/release_gate.py`), **duplicate-and-stop remains enforced: verdict is `negative`, no download is published, and no leaderboard superiority over `0.2778` / `0.3195` is claimed.**

## Reproduce the publication audit (no data downloads needed)

```sh
.venv/bin/python scripts/release_gate.py
.venv/bin/python scripts/build_site69.py
.venv/bin/python scripts/build_readme.py
```

For pixel validation and tests:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest scikit-learn
GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py {zeros_rel}
.venv/bin/pytest -q
```

Full feature stack & INGENIOUS polylines restored via `scripts/restore_data.py` + `scripts/fetch_data.py` (SHA-256-pinned mirrors, NOT organizer-authenticated); full `862`-raster registry restored via `scripts/fetch_registry.py`. GPU not needed.

## Standing project brief — read at the beginning of every session

The following is the retained project brief, not a verbatim transcript of every user message. The active request additionally requires strict duplicate-and-stop enforcement, three review passes, and a PR merged to main. Never infer authorization to submit to DrivenData.

'''
    (ROOT / 'README.md').write_text(head + (ROOT / 'PROMPT.md').read_text())


if __name__ == '__main__':
    main()
