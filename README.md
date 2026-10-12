# GEMSDOE69 — relay-ramp & pull-apart corridor lane · DOE GEMS Prize (DrivenData #306)

**Site:** <https://buffedlizard55-lab.github.io/GEMSDOE69/> · **How to submit:** <https://buffedlizard55-lab.github.io/GEMSDOE69/docs/executive-summary.html> · **Run card:** [`evidence/run_card.json`](evidence/run_card.json)

## ⛔ NOT OK TO SUBMIT — negative result (do not spend a weekly slot)

A **byte- and pixel-unique, format-valid** TIF was generated for this lane (rank correlation with every one of 862 prior rasters ≤ 0.28), but (1) it **failed the pre-registered gate** and (2) its final dots are a **duplicate under the protocol’s 70 % / 3-px dot-overlap rule** (they sit inside denser near-catalogue emissions of other lanes more than random dots would). On the gate: the corridor-restricted dots did not beat the same pipeline without corridor priors on the hide-and-recover holdout. Per the protocol it is kept only as the negative-result deliverable (clearly labelled on the site) and is **not** offered as a submission.

| Gate (pre-registered) | Value |
|---|---|
| Lane arm `A_corridor` | HOLDOUT-DTI **0.0749** [0.0647, 0.0853] |
| Same pipeline without corridor priors `B1_halo` | HOLDOUT-DTI **0.1096** [0.0986, 0.1206] |
| Δ (paired 20 km block bootstrap) | **-0.0347** [-0.0410, -0.0278] → **FAIL** |
| Evaluator / withheld positives | `gems57-pooled-hide-v2` · 22,893 pixels pooled over draws [20, 21] |
| Uniqueness vs 862 prior rasters | worst Spearman 0.2844 (surface) / 0.0758 (dots), limit 0.90; worst 3-px dot overlap vs 809 dot-field rasters 0.9999, limit 0.70 → **DUPLICATE (dot-overlap rule): 96 firings, 22 of them discriminating (our dots overlap more than random dots in the same band; max excess +0.302)** · bytes and decoded pixels unique among checked rasters |
| File | [`docs/downloads/gems69-relay-pullapart-corridors-33680-20261012T015854Z-zeros.tif`](docs/downloads/gems69-relay-pullapart-corridors-33680-20261012T015854Z-zeros.tif) · sha256 `5ef7f9bdce16586544f819194bc3650156a78b66d36e03e6477e905a6b59a4df` · 33,680 dots, 0 on the catalogue |
| Validator | PASS (both encodings; `scripts/validate_submission.py`) |
| Name / note | `gems69-relay-pullapart-corridors-33680-20261012T015854Z` / `GEMSDOE69 relay-ramp/pull-apart corridor dots (33680); tip-graph corridors, gravity/mag/scarp scored; see repo run card` (119 chars) |

All arms (HOLDOUT-DTI, pooled over two draws; not leaderboard scores):

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
| `A_corridor` | 0.0749 | [0.0647, 0.0853] |
| `AP_halo_corridor` | 0.1061 | [0.0957, 0.1171] |
| `B1_halo` | 0.1096 | [0.0986, 0.1206] |
| `B0_evidence` | 0.0380 | [0.0308, 0.0451] |
| `C_distance` | 0.1259 | [0.1134, 0.1380] |
| `R_corridor_random` | 0.1106 | [0.0976, 0.1230] |

`A` = the lane (dots only inside corridors) · `AP` = corridor prior as a boost · `B1` = evidence × distance halo (gate comparator) ·
`B0` = evidence only · `C` = distance only · `R` = random dispersed dots inside the same corridors.

**What this means.** On the catalogue hide-and-recover instrument the withheld faults are best predicted by plain proximity to the
visible catalogue; neither the step-over geometry nor the geophysical evidence adds ranking power at this scale, and restricting dots to
corridors loses recall. Separately, the family's registry already holds dense near-catalogue emissions (80k–1.5M positive pixels) that
cover much of the corridor domain, so near-catalogue dots now trip the 70 % overlap rule unless they are much sparser or placed outside
those emissions' 300 m halos. See [docs/research/why-0278.md](docs/research/why-0278.md) for why the family's best file (owner-reported
0.2778) works — near-minimal mass on a wide field, with catalogue-adjacent dots removed — and what it would take to beat it.

---

# Standing brief for GEMSDOE69 — read this first, every session

> **Provenance of this text (irregularity IR-69-01).** The paragraphs marked *verbatim* are the
> family prompt's shared text, identical to the copy preserved in the sibling repository
> [`GEMSDOE63/README.md`](https://github.com/buffedlizard55-lab/GEMSDOE63/blob/main/README.md)
> ("The prompt this project answers to (verbatim)"). The **lane paragraph** and the **family-brief
> bullets** are reproduced from this session's own record of the owner's message; every
> requirement is preserved, but the wording may differ slightly from the original message.

## Core Values — focal to every decision

* **Maximize P(Win).** Weigh trade-offs, assess risk, and choose the path that maximizes the
  probability of winning. Set emotions aside.
* **Own the Outcome.** Own results end to end. Act when problems arise without waiting for
  permission. Treat failure and success as signals. Stay accountable for the final outcome.

## Highest urgency (verbatim)

```
THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF
SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED
TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.
Read the entire prompt.
```

## This session's lane (single method paragraph; reconstructed wording)

```
Relay-ramp and pull-apart corridor generator: propose faults from catalogue geometry.
Giddens & Faulds (2025, SGP-TR-229) mapped more than 450 step-overs in the Great Basin:
ramps are typically 3-3.5x longer than wide, widths range 0.1-14.6 km (mean 2.8 km), and
about 70% of higher-temperature step-overs are hard-linked; Walker Lane hot systems favour
pull-aparts and displacement-transfer zones, and N-NE faults are best oriented for dilation
under WNW extension. Build a tip graph from catalogue polylines. Pair same-dip tips that
overlap or underlap with widths W of 0.1-15 km and along-strike separation <= 3.5 W; emit
candidate corridors as an oblique connector plus en echelon strands. Add pull-apart and
transfer-zone corridors at dextral releasing steps and terminations. Score corridors by
multi-scale horizontal-gradient and tilt evidence in gravity and magnetics (including
magnetic lows), the lidar-scarp channel, and orientation consistency with the stress field.
Place nodes inside the top corridors by calibrated greedy marginal-DTI selection. Validate
by masking known linking faults in hard-linked ramps and testing recovery within 300 m.
Gate: beat the same pipeline without corridor priors. Record per-corridor rationale
(layers, signature, source). Normalise to [0,1]; write a float32 EPSG:32611 100 m GeoTIFF
with NaN only outside the footprint; pass validate_submission.py; run a hash/pixel-agreement
check against all prior rasters; offer the download if the gate is met, otherwise log the
negative result.
```

## Parallel-run protocol (verbatim)

```
PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this
same prompt.

1. LANE. Your lane is the single method paragraph above. Stay inside it. If your
   raster's rank-correlation with any registry raster exceeds [0.90], or more than
   [70%] of your dots fall within 3 px of one registry raster's dots, you have
   drifted into another lane: log it as a duplicate and stop. Check this on the
   surface before placement AND on the final dots.
2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout
   and submission_writer. Holdout = hide-and-recover: withhold whole fault segments
   with a buffer, derive every catalogue-based feature only from the visible faults,
   mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m
   triangular kernel). If a shared tool is wrong, fix it once in the template and
   report it; never keep a private fork.
3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld
   positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page
   receipt). A projection is never written as a score.
4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any
   result. AUC above [0.90] means leakage until proven otherwise.
5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault
   process that could mimic it; holdout DTI + CI; correlation/overlap vs registry;
   raster sha256; validator output (no NaN inside the footprint, values in [0,1],
   CRS/shape/transform match); submission name + note of at most 140 characters;
   verdict promote / negative. Negative results are deliverables.
6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions:
   promotion to a real slot is a separate selector step, within the weekly cap
   shown on the submission page.
```

## Family brief (requirements carried in the owner's message; reconstructed wording)

1. **Review the repo** and study why GEMSDOE32
   `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored **0.2778** (best of the group) and whether
   it can be beaten — a PhD-level answer.
2. **Before implementing new ideas**, rank 3–5 candidate geological hypotheses not yet tried, each
   naming the specific layers, the physical signature targeted, why it could catch a fault the
   USGS/INGENIOUS catalogue misses rather than one already in it, and how it differs from everything
   already in the repository; rank by expected DTI improvement and implementation cost; validate
   the top candidate on the spatially-blocked holdout **before touching a weekly submission slot**;
   do not spend a slot on an idea that has not beaten the current holdout best; if a candidate needs
   new external data, name the specific free official source and check that it is obtainable.
3. **Put this prompt in the README** and read it every session; keep the Core Values central.
4. **GitHub Pages site**: clean UI; the TIF download must be obvious at the very top (executive
   summary / first screen); an executive-summary subpage explaining exactly how to submit
   (upload the `.tif` or a `.zip`, a unique submission name, a short note); official, verified links.
5. **Fix / prevent the portal error** "Predicted values must be in range [0, 1]".
6. **Deep research** from official sources; contrarian but grounded hypotheses; aim above the
   public board (the message cites 0.3195 and 0.3774 as the high marks — see IR-69-02 for the
   live board on 2026-10-12).
7. Work **line by line**, verify from official trusted sources, give links for manual review, flag
   irregularities, no hallucinations, no manual steps for the owner.
8. **Multiple passes** (implement and verify → review and fix → re-check against the request),
   then **open a PR and merge it to main**; list limitations, access needs and next work.


---

## Repository guide

| Path | What it is |
|---|---|
| `src/gems69/` | lane code: `traces.py` (polylines, dip polarity, tips), `corridors.py` (relay / pull-apart / transfer corridors, scoring), `evidence.py` (multi-scale gravity & magnetic edges, magnetic lows, lidar scarps), `calibrate.py`, `pipeline.py` |
| `vendor/gems57/` | byte-for-byte copy of the shared template `60GEMSDOE/src/gems57` @ `32024716` (pins: `registry/template_pin.json`) — evaluator, writer, validator, allocator, uniqueness |
| `scripts/` | `restore_data.py`, `run_lane.py e1` / `e2`, `build_submission.py`, `check_uniqueness.py`, `validate_submission.py`, `make_run_card.py`, `build_site.py`, `build_readme.py`, `fetch_registry.py` |
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
* The uniqueness corpus is the owner's public repositories only (IR-69-12).

## Compliance note (official rules, verified)

The official rules (§3.2, <https://www.nlr.gov/docs/fy26osti/96647.pdf>) allow generative-AI use but require finalists to
**disclose in the narrative** the extent to which it was used, and to deliver complete, reproducible code and documentation. This
repository was produced with an AI agent; its code, pins and evidence files are kept reproducible for that purpose.

## Next steps (for a new session; each needs its own pre-registration)

1. **Two separate losses.** Inside the corridors, dense greedy placement cost DTI (random dispersed dots in the same corridors:
   0.1106 vs 0.0749); and even dispersed corridor dots do not beat a plain
   distance halo (0.1259). Future corridor work should cap density (Poisson-disk ≥ 2.8 px, as the 0.2778
   ladder found) *and* be judged against the distance-only control, not only against the evidence halo.
2. **Measure on a population-matched instrument:** state-map faults absent from the catalogue (SGMC off-catalogue, used by 60GEMSDOE)
   are closer to "new faults" than withheld catalogue components.
3. **H69-4 accommodation zones** (opposite-dip tip pairs) and **H69-5 local stress orientation** from the INGENIOUS geodetic strain-rate
   tensors are untested; H69-5 needs the geodetics zip (SHA-256 `0dd65ccc…`), which is not in the mirrors reachable from this sandbox
   (GDR is not on the allow-list) — access need.
4. **Uniqueness headroom is now the binding constraint near the catalogue.** 22 dense prior emissions overlap this lane's dots
   more than random dots would; a future corridor emission must be far sparser or restricted to corridor cells outside those
   emissions' 300 m halos — check that *before* placement with the per-firing random-dot baseline in `scripts/check_uniqueness.py`.
5. The selector (separate step) should keep the family's best file as the reference; nothing in this repository beats it on any
   instrument.
