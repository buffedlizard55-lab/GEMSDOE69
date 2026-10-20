# GEMSDOE69 current-session review — 2026-10-20

## Decision

**NEGATIVE — do not download or submit any TIFF from this repository.** No new raster was generated, no submission slot was touched, and the historical TIFFs remain audit artifacts only. This follows the lane's duplicate-and-stop rule: the available current-artifact registry receipt fails its literal overlap test, is incomplete, and the two-phase receipts do not bind to the current artifact. Producing a newly named raster would not cure those failures and would evade the prescribed stop condition.

This is not an organizer rejection or a leaderboard score. No organizer receipt was available in this review.

## Three review passes

### Pass 1 — implementation and local verification

- Read `PROMPT.md`, `README.md`, `AGENTS.md`, `HANDOFF.md`, the existing run card, release gate, candidate hypotheses, validator, and tests.
- Installed the declared Python requirements and pytest in the ignored local `.venv`; no project dependency files were changed.
- Ran `PYTHONPATH=vendor/template66:src .venv/bin/pytest -q`: **89 passed, 1 xfailed**. The expected failure documents the known tip-interval gap defect; it is not a passing geometry validation. Rasterio emitted 18 upstream pending-deprecation warnings.
- Revalidated the archived all-finite raster with the local bridge grid:
  `GEMS_DATA="$PWD/data/bridge" PYTHONPATH=vendor/template66:src .venv/bin/python scripts/validate_submission.py submissions/h69-z-radiometric-halo-31994-20261020T182654Z-31913c0c-zeros.tif`
  Result: `PASS`, SHA-256 `be84d6fa9efc3ec85f9532d5574e98a4e77c587db7be3d50a9392924917c78c7`; the prior receipt records single-band float32, EPSG:32611, shape 3730×3292, transform (100, 0, 243350, 0, -100, 4508550), finite footprint, and values in [0,1]. This establishes local format compliance only.
- Ran `scripts/release_gate.py`: `verdict=negative`, `download_enabled=false`.
- Ran `git diff --check`: clean at review time.

### Pass 2 — bugs, stale evidence, and assumptions

1. **No current scientific run is reproducible from this checkout.** The latest E3 receipt describes K/Th radiometric depletion, but the checkout does not contain the claimed production scorer implementation or an artifact-bound method-source manifest. The checked-in `src/gems69/physics.py` and `src/gems69/scoring.py` do not establish the latest radiometric scoring mechanism. Do not attribute the old output to code that cannot be audited here.
2. **Registry novelty is not cleared.** The aggregate current-artifact scan records rank correlation below the threshold but a literal dot-overlap firing of 1.0 against a universal/dense surface, with the literal overlap gate false. The dot-like-only diagnostic is below the limit, but it does not supersede the specified literal test. That scan reports 750/751 comparisons and one shape error, so is incomplete. Separate surface/dot phase artifacts concern a prior 33,680-dot candidate and a different 862-entry corpus, not this 31,994-dot raster; they cannot be reused as clearance.
3. **Sequence requirement is unmet.** The separate uniqueness records say phases were computed after placement (the surface data itself is pre-placement). The protocol requires the surface gate before placement and the final-dot gate after. The current build therefore has no qualifying pre-placement stop clearance even apart from the overlap firing.
4. **Holdout numbers are historical screen measurements, not promotion evidence.** The archived `e2_gate.json` reports HOLDOUT-DTI 0.005975 (reported CI half-width 0.001441) for the corridor arm versus HOLDOUT-DTI 0.002148 (half-width 0.000578) for its no-prior comparator, across 8 repeated cells and 22,641 withheld positive pixels. The interval is a normal approximation over repeated cells, not an independent spatial-block bootstrap. There is no explicit same-evaluator comparison against a declared current holdout best for the novel method, and no evidence here that it predicts a leaderboard gain.
5. **The feature canary is not sufficient to validate the latest hypothesis.** The archived canary file predates the latest artifact and lacks an artifact SHA binding; its named feature set does not demonstrate an isolated K/Th radiometric-depletion canary for the current scorer. A low AUC for other features cannot be substituted.
6. **Known geometry issue remains.** The strict expected-failure test documents that interval-window logic can accept an excessive tip gap relative to 3.5W. Same dip and dextral releasing sense also require measured attributes; strike subparallelism or geometric overlap alone is not proof of either.
7. **Inputs are limited.** `data/bridge/` contains only existing-faults, labels, and sample-submission TIFFs. The full feature stack/cache is absent; no DrivenData login is available. The checked-in sources state that these bridge files are owner mirrors, not organizer-authenticated downloads. The local workspace audit therefore reports the project as blocked for a fresh full-stack run.

### Pass 3 — request reconciliation and next actions

- The request for a new downloadable TIF conflicts with the explicit parallel-run rule to stop after a literal duplicate firing. The fail-closed outcome takes precedence: no new candidate, renamed file, or download link is offered.
- Existing TIFs are not advertised as submission-ready. A format-valid raster can still be scientifically unvalidated or a lane duplicate.
- No experiment was run in this review; historical artifacts are not relabelled as a new experiment. The prior three-experiment/two-hour cap and stop conditions remain binding.
- Before a next experiment, recover the exact method implementation and inputs that produced the radiometric artifact, complete the registry scan and fix its shape/error entry, obtain decision on how to handle dense-surface overlap without changing the user's threshold, repair tip interval search, and bind the current candidate surface to a complete pre-placement comparison. If the literal gate still fires, stop again.

## Candidate hypotheses for a later, preregistered run

These are qualitative research proposals, not measured improvements. Rank reflects mechanism-specific plausibility for recovering missing structures, discounted by the current data/provenance blockers; no score projection is made.

| Rank | Candidate | Existing layers / targeted signature | Why it may find faults absent from catalogue | Difference from audited scorer | Cost / blocker |
|---|---|---|---|---|---|
| 1 | **Convergent relay-link edge phase** | Gravity and magnetic horizontal-gradient ridges plus tilt zero-crossings on opposing corridor margins, evaluated at multiple scales and conditioned on connector azimuth | A paired, spatially phase-consistent bridge between mapped tips could expose a buried linking structure without simply rewarding mapped scarps | Joint connector-phase constraint rather than independent per-layer corridor maxima | Moderate; cached feature stack must be restored and every input source hash verified |
| 2 | **Releasing-basin margin asymmetry** | Gravity curvature and paired horizontal-gradient flanks with a magnetic low inside independently verified releasing-step rhombs | Asymmetric basin margins may indicate buried splays under basin fill where catalogue surface traces are absent | Tests paired basin geometry rather than scalar geophysical lows; requires actual slip-sense evidence | Moderate; current catalogue attributes and releasing-sense inference need audit |
| 3 | **En-echelon scarp phase coherence** | LiDAR-scarp channel orientation and stagger/phase continuity across a proposed connector | Short, aligned scarps that are individually below mapping threshold may collectively reveal an omitted link | Spatial arrangement/coherence, not average scarp magnitude | Moderate-high; distinguish pluvial shorelines, roads, and terrace edges; full lidar stack required |
| 4 | **Matched lithology radiometric contrast reversal** | GeoDAWN K/Th/total-count contrasts between corridor interior and matched flanks, conditioned on magnetic response | Local contrast could identify alteration or structural boundaries concealed by weak morphology, while controlling broad lithologic background | Signed within-unit contrast rather than a simple absolute K/Th depletion score | High; cannot use until radiometric method provenance and lithologic controls are verified |

**No candidate is promoted as validated.** Since the literal uniqueness stop already fired and the cached full feature stack is not present, validating one now would violate the stop and reuse requirements. Do not spend a competition slot.

## H33 0.2778 interpretation and leaderboard context

The supplied GEMSDOE32 site associates `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` with **0.2778**, but this repository has no organizer submission-page receipt binding that score to those TIFF bytes. Therefore **0.2778 is USER-REPORTED-NOT-ORGANIZER-CONFIRMED**. The committed family-raster analysis describes H33 as a sparse binary-dot selection from a broader lineament surface, with successive mass-removal/thinning and a catalogue-flank exclusion. The plausible metric mechanism is improved precision: the competition evaluates distance-weighted fault recovery, while mapped catalogue traces are excluded from scoring; removing predictions too near already-mapped faults can reduce false-positive cost, and sparse dots distribute limited prediction mass rather than assigning broad high-valued areas. Retaining dots near lineaments that happen to lie within the 300 m credit neighborhood of withheld faults can still recover positive credit. This interpretation is consistent with the metric and inspected family artifacts, but cannot establish the causal organizer score without the score-to-file receipt and exact organizer evaluation. It also does not prove geothermal vent discovery: the target is hidden faults as a proxy, not direct vent labels. H33 may have performed well because of metric alignment and useful spatial ranking, not necessarily because every predicted structure is geologically correct. This is a plausible mechanism, not proof of why the organizer assigned the stated score. It is not evidence that the current corridor candidate can beat it.

Could a new candidate beat 0.2778 (or a user-reported higher leaderboard value)? **In principle yes; on available evidence, not established.** A stronger geologic prior only helps if it increases the fraction of predictions receiving distance-weighted credit at comparable false-positive cost. The archived corridor holdout is a weak screening result and does not compare the newest radiometric method to a declared current best. The current method's source/provenance gap and duplicate-stop make a new TIFF unjustified here. No forecast score should be stated.

The prompt's leaderboard values are not reconciled here against a current organizer page. Do not present 0.3195, 0.3774, or any other user-provided value as a current verified high score. Consult the official links below before relying on current competition status.

## Official/manual-review sources

These URLs are provided for review; this session did not independently refresh pages on hosts outside the sandbox's allowed outbound hosts.

- [DrivenData competition overview and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — login-gated in the repository's prior documented attempts
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution repository](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [Giddens & Faulds (2025), SGP-TR-229 PDF](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf) — geological statistics were supplied in the project prompt and remain unverified in this review.
- [Submission-format PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

## Required run card

```json
{
  "hypothesis": "No new hypothesis tested; queued: convergent relay-link edge phase",
  "mechanism": "Proposed joint gravity/magnetic HG and tilt phase on tip-graph corridors; no current artifact generated",
  "named_non_fault_mimic": "Lithologic contacts and sediment-filled paleochannels can mimic geophysical gradients and basin margins",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI (archived; not rerun)",
    "evaluator_version": "vendor/template66 gems57 pooled hide-and-recover, alpha=0.2, beta=0.8, 300 m triangular kernel; archived 8-cell run",
    "withheld_positive_pixels": 22641,
    "dti": 0.0059751979,
    "ci95": [0.0045338401, 0.0074165556],
    "note": "normal-approximation interval across repeated cells, not independent block bootstrap; not a candidate-vs-current-best test"
  },
  "correlation_overlap_vs_registry": {
    "evidence_class": "REGISTRY-MEASUREMENT (archived; incomplete)",
    "worst_abs_spearman": 0.1544272276,
    "worst_literal_dot_overlap": 1.0,
    "compared": 750,
    "expected": 751,
    "errors": 1,
    "verdict": "duplicate-and-stop; phase files are stale for this artifact"
  },
  "raster_sha256": "be84d6fa9efc3ec85f9532d5574e98a4e77c587db7be3d50a9392924917c78c7",
  "validator": "Archived zeros TIFF locally passes: float32, EPSG:32611, 3730x3292, expected transform, no NaN in footprint, values [0,1]; this is not uniqueness or scientific clearance",
  "submission_name": "h69-z-radiometric-halo-31994-20261020T182654Z-31913c0c-zeros (archived; not offered)",
  "submission_note": "Archived radiometric halo candidate; do not submit",
  "verdict": "negative"
}
```
