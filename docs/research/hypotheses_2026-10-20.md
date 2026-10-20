# Historical hypothesis preregistration, session 2026-10-20

> Archived before the H69-E holdout look. It is not current status, and its proposal list must not be treated as untried after the later runs. See `untried-hypotheses-2026-10-20.md` and `../../evidence/run_card.json`.

Ranked before the H69-E holdout look. "Expected" is a prior, not a measurement. Every hypothesis stays inside the relay-ramp / pull-apart lane. Leaderboard numbers below are USER-REPORTED or an in-repo public snapshot, never organizer receipts.

## Why 0.2778 happened, and why 0.3195 is not a target we can claim

Measured on committed bytes (see `docs/research/why-0278.md`): `h33-h33-2-b2-zeros` is 37,654 unit dots, none on the mapped catalogue, median 1.97 km from it. The ladder that produced the user-reported 0.2778 deleted dots within ~200 m of mapped traces and dotted a wide lineament field at ~2.8 px spacing. At DTI 0.2778 a new dot pays only if its kernel credit exceeds 0.2 × 0.2778 ≈ 0.056. Known faults are masked from scoring (organizer forum thread 11516, cited in the family audit). So the score is near-minimal mass on a reasonably ranked *wide* field, not proof of the right geology.

The in-repo public leaderboard snapshot of 2026-10-12 (`registry/leaderboard_snapshot_2026-10-12.json`, source https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) shows rank 1 at 0.4275 and 0.3195 at rank 9 (participant DARD). The user now cites 0.3195 as the high score. This sandbox cannot reach drivendata.org, so that claim was not re-verified (IR-69-LB-01). A projection is not a score. This lane does not claim it can beat 0.3195 until a fresh holdout beats the current holdout best and a selector spends a slot.

## What this repo had already tried

- H69-A (2026-10-12): tip-graph corridors, all 1,200 slots filled at W = 2.8 km, grav/mag HG+tilt + lidar. HOLDOUT-DTI 0.0060 ± 0.0014 vs no-prior control 0.0021 ± 0.0006 (gems57 pooled hide, 8 cells, 22,641 withheld px). Gate vs that weak control passed. Absolute DTI is tiny.
- An earlier implementation (PR #5) lost to a distance-halo control (0.0749 vs 0.1096). Distance-to-catalogue predicts withheld *catalogue* segments and is the wrong live prior: the h33 ladder showed new faults rarely run within 100–200 m of published traces.
- A file named `h69-z-radiometric-halo-31994` was labelled H69-D, but committed `physics.py` at that commit had no radiometric transform, and `e2_gate.json` was the 2026-10-12 run. That file is not a validated radiometric result (IR-69-GATE-02).

## Ranked candidates

| Rank | Hypothesis | Layers | Signature | Why a catalogue-missing fault | Difference from this repo | Expected holdout gain / cost | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **H69-E width-stratified corridors + straight conductivity/basement steps + K depletion/ThK** | `cond_surf` (band 17), `depth_to_base_surf` (band 15), GeoDAWN K and Th/K (DOI 10.5066/P93LGLVQ), plus existing grav/mag/lidar | Structure-tensor coherence × gradient (straight boundary); K low vs a 2 km background; high Th/K | Linking faults in step-overs of any width, including under alluvium where no scarp exists. The 2.8 km-only cap missed the rest of the published 0.1–14.6 km range. | First use of structure-tensor straightness and of radiometrics *inside* a tip-graph corridor. Not a scarp-fusion blend (GEMSDOE46). | medium / low (data already pinned) | **Running this session** |
| 2 | **H69-B stream knickpoint / chi chains at step-over mouths** | `det_elev` (band 12), `det_elev_slope` (band 19) | Along-stream chi anomalies collinear with corridor strike | Blind faults offset bedrock and knick profiles with no scarp | No along-stream integral exists in this repo | low–medium / low | Queued. Not started (budget: one validated idea first). |
| 3 | **H69-F termination horsetails at free strike-slip tips** | same catalogue tip graph | Two splays rotated 20° and 40° into the extensional quadrant, as in the earlier `traces.py` design | Displacement-transfer zones at tips are drawn as terminations, not as the linking fault | Current raster tip graph emits step-over pairs only, not horsetails. Slip sense is unobserved (IR-69-DIP-01), so this needs the dextral prior stated as a prior. | unknown / low | Queued. Sense is a disclosed proxy, not a measurement. |
| 4 | **H69-G Poisson-disk 2.8 px thinning of a gated corridor field** | no new layer | Spacing matched to the 300 m kernel, the move that raised the h33 ladder | Does not find new faults; it stops paying for redundant dots on faults already proposed | Not implemented. Only worth running if H69-E passes the gate and is mass-heavy. | small / low | Queued behind the gate. |
| 5 | **H69-H instrumental seismicity nodal planes along corridor axes** | USGS ComCat / ANSS | Epicentre lineaments + focal nodal-plane strike | Active blind faults with no scarp | Family uses only pre-binned `ieq`/`deq` bands | unknown / blocked | **Not viable here.** Free official source: https://earthquake.usgs.gov/earthquakes/search/ — not reachable from this sandbox and not in the pinned mirrors. |

## Non-fault mimics (named before the look)

Lithologic contacts, felsic intrusions, soil moisture, and airborne survey-line artifacts can produce straight conductivity steps, K lows, and Th/K highs without a fault. Gamma rays sample the top ~0.5–1 m (GeoDAWN family receipt caveat). These layers are corroboration inside a geometry-proposed corridor, not a fault map.

## Validation rule

H69-E is offered for download only if, on the shared hide-and-recover instrument (alpha 0.2, beta 0.8, 300 m triangular kernel):

1. no single feature has holdout AUC > 0.90 (else leakage);
2. the corridor arm beats the same evidence composite with no corridor prior;
3. the corridor mean exceeds the prior holdout best 0.005975;
4. surface Spearman vs every registry raster ≤ 0.90 and ≤ 70% of dots lie within 3 px of any one dot-like registry raster or of an earlier GEMSDOE69 submission;
5. `validate_submission.py` passes, values in [0, 1], NaN only outside the footprint on the diagnostic twin. The file offered for the portal is the all-finite `-zeros` twin, because NaN has produced "Predicted values must be in range [0, 1]".
