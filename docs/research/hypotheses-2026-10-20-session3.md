# Untried in-lane hypotheses — 2026-10-20 (session 3), ranked before testing

Lane (unchanged): relay-ramp and pull-apart corridor generator from the catalogue tip graph.
Every number below is labelled. No projection is written as a score.

## What this repo has already tried (excluded from this list)

| Tried | Where | Outcome (as archived) |
|---|---|---|
| Vector tip graph with measured USGS dip (`DIPDIRECT`) + DEM hanging-wall inference | `traces.py`, E2 | negative vs halo baseline (`docs/research/hypotheses.md`) |
| OR-logic grav/mag HG + tilt scoring (v1) | `scoring.py` | relayfix v1, negative/duplicate |
| AND-logic joint grav+mag edge phase (H69-J) | `scoring_joint.py` | archived "gate pass" is biased by IR-69-HOLD-01 |
| Radiometric K/Th alteration halo (H69-D) | `scoring_rad.py` | not validated (IR-69-GATE-02) |
| Transfer-only selector (Exp2b) | `run_exp2b_transfer.py` | literal-overlap duplicate of GEMSDOE53 (IR-69-REG-03) |
| Evidence-first global top-1,200 (H69-M) | `evidence_first.py` | this session, experiment 1 |
| Evidence-first with spatial tile quota (H69-N) | `evidence_quota.py` | this session, experiment 2 |
| Pull-apart asymmetry, en échelon coherence, strain orientation | `hypotheses_ranked_20261020.md` | proposed, not run |

## Ranked candidates (expected HOLDOUT-DTI gain ÷ cost; all use data already sha-pinned in `.cache/gems_data`)

### 1. Domain-conditioned ramp geometry (Walker Lane vs central Nevada seismic belt)
- **Layers:** catalogue tip graph (W, along-strike length, overlap); provided geodetic *shear* strain rate (band 7) and *dilatation* rate (band 8) of `training_features.tif` as the domain classifier (Walker Lane = shear-dominated).
- **Signature:** per step-over likelihood under the domain's measured population: Walker Lane ramps are the narrowest (mean 1.9 km), central Nevada seismic belt the widest (mean 3.5 km), study-wide 2.8 km; ramps are "typically 3 to 3.5 times longer than the width" ([Giddens & Faulds 2025, §3 and §6.2](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf)). Score `−|log(W/W_domain)| − |log((L/W)/3.25)|`.
- **Why off-catalogue:** linking faults inside ramps that *look like* the regional population are the ones a mapper would expect to exist but that the scarp-based catalogue misses.
- **Difference from repo:** every selector so far used a single global 2.8 km target (IR-69-CAP-01) and no aspect test; H69-M/N selected median W ≈ 4.1 km (above every domain mean).
- **Mimic:** en échelon *folds* or range-front embayments with ramp-like geometry but no linkage.
- **Cost:** low (selection reweighting only). **Expected gain:** low–medium.

### 2. Buried basement step under the connector (depth-to-basement + conductive base)
- **Layers:** `basement_depth` (band 15) and `cond_surf` (band 17): their HG/tilt transforms (`base_hg_s2`, `base_tilt_s2`, `cond_hg_s2`, `cond_tilt_s2`) are already computed in `physics.py`, but **never enter corridor scoring** (`evidence_first.JOINT_LAYERS` excludes them).
- **Signature:** a basement-depth gradient ridge parallel to the connector (a buried offset), coinciding with a conductive-base step (fluid-bearing damage zone).
- **Why off-catalogue:** buried beneath basin fill with no scarp; the catalogue is dominated by scarp-mapped faults ([Giddens & Faulds §4](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf): ~25 % of the area mapped at 1:24k, the rest from Qfault database/lidar/NAIP).
- **Difference:** new evidence channels, not a reweighting of grav/mag/lidar.
- **Mimic:** depositional basin geometry; clay-rich playa sediments are conductive without faulting.
- **Cost:** low. **Expected gain:** medium-uncertain (100 m resolution of those products is coarse relative to the 300 m kernel).

### 3. Self-supervised linkage style from the catalogue's own hard-linked ramps
- **Layers:** visible catalogue only (tip graph + existing linking segments).
- **Signature:** ~51 % of all identified step-overs and ~70 % of >120 °C ones are hard-linked (Giddens & Faulds, abstract and §6.1). Learn *where inside a ramp* links run (oblique connector vs en échelon strand, position along the ramp) from visible hard-linked ramps; emit the learned template in soft-linked ones.
- **Why off-catalogue:** soft-linked ramps in the catalogue are where an unmapped breaching fault is most probable.
- **Difference:** the hard-link recovery test exists only as *validation* (IR-69-HL-01, mean recovery 0.846); it has never been used to *shape* emission.
- **Mimic:** catalogue mapping convention (mappers join segments that aren't physically linked).
- **Leakage guard:** fit only on the visible catalogue in each cell.
- **Cost:** medium. **Expected gain:** medium.

### 4. Seismicity-aligned linkage
- **Layers:** earthquake density (`deq` band 10, `ieq` band 16), unused in corridor scoring.
- **Signature:** connector-line seismicity density above flank density.
- **Why off-catalogue:** blind active linkage produces seismicity without a scarp.
- **Mimic:** geothermal/magmatic swarms; epicentre error of km scale ≫ 300 m kernel.
- **Cost:** low. **Expected gain:** low.

### 5. 1 m lidar scarp confirmation inside top corridors only (needs external data)
- **Layers:** 1 m DEM tiles listed in the organizer's `1m_DEM_links.csv` ([problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)); USGS 3DEP 1 m DEM.
- **Signature:** sub-100 m scarp-curvature lineaments parallel to the connector.
- **Obtainability check (this sandbox):** **not obtainable**: outbound access is limited to GitHub/PyPI/npm hosts; the link list sits behind the DrivenData login and the tiles are hosted by USGS. Not viable here; listed so a session with USGS access can run it.
- **Cost:** high. **Expected gain:** unknown.

## Validation rule (unchanged, binding)
Template hide-and-recover holdout (seeds 20/21; modes all + detached; pooled DTI, α 0.2, β 0.8, 300 m kernel), paired cell bootstrap CI, beat both the no-corridor control and the current holdout best, single-feature canary AUC ≤ 0.90, uniqueness on surface and dots, validator, release gate. No submission slot is touched by this lane.
