# Repository review — 2026-10-20

> **Historical-state note:** this session predates a later H69-J local-evidence
> rebinding. That rebinding does not affect its literal 1.0 overlap failure;
> for the reconciled current state, read
> [`final-audit-2026-10-20.md`](final-audit-2026-10-20.md). No TIFF is currently
> publishable.

## Decision

**NEGATIVE — NOT OK TO DOWNLOAD OR SUBMIT.** No new TIFF, experiment, or competition upload was created. This is deliberate: the recorded literal registry overlap check fails, and the lane protocol requires duplicate-and-stop. Format validation of an archived file does not override the uniqueness or scientific-release gates.

The newest source-of-truth publication status is `docs/status.json`; the site banner and README are regenerated from `scripts/release_gate.py`. No organizer receipt or fresh leaderboard score was obtained during this review.

## Pass 1 — inspect and verify

- Read `PROMPT.md`, `README.md`, `AGENTS.md`, `HANDOFF.md`, current reports, evidence/run card, hypotheses, release policy, generator, validator, and tests.
- Found a policy mismatch: the release-gate comments and implementation allowed a favorable stratified/dotlike overlap diagnostic to override a failed literal overlap gate. That contradicted the standing duplicate-and-stop rule, regardless of the current candidate's other blockers.
- Corrected `scripts/release_gate.py` so *both* literal registry checks must pass. A stratified result remains diagnostic only. Added a regression test where the dotlike diagnostic is favorable but literal overlap fails; release must remain blocked.
- Removed contradictory README copy claiming that an archived candidate's gates had passed and presenting stratified uniqueness as sufficient. Rebuilt README and site from the corrected policy. The top-level banner now explicitly says **NOT OK TO SUBMIT — DO NOT SUBMIT**, explains the literal overlap stop, and offers no raster link.
- Revalidated the archived H69-J all-finite TIFF using the local bridge data and `scripts/validate_submission.py`: PASS. Its byte hash begins `981beb5707bb9933`; this confirms format only, not scientific validity, uniqueness, organizer acceptance, or submission readiness.

## Pass 2 — adversarial review and edge cases

- Ran `.venv/bin/pytest -q`: **100 passed**, with 18 upstream rasterio pending-deprecation warnings. `git diff --check` passed.
- Ran `scripts/release_gate.py`: verdict `negative`, `download_enabled=false`. The literal dot-overlap condition is now reported as a blocker in addition to stale/missing artifact-bound holdout and method-source evidence.
- Checked generated pages for obvious download links and status. No `.tif` is published under `docs/downloads/`; the website shows a prominent negative banner.
- The release gate checks exact file hashes and evidence bindings; the test fixture is intentionally non-geospatial and tests policy behavior only. The real archive was separately checked by the submission validator.
- No new scientific experiment was run. Re-running a candidate to get a different hash would evade, not satisfy, the protocol. Archived holdout values are not relabeled as current results.

## Pass 3 — original request reconciliation

### Candidate ideas already registered (qualitative, not validated in this review)

See [`docs/hypotheses.html`](../docs/hypotheses.html) and [`docs/research/hypotheses-2026-10-20.md`](../docs/research/hypotheses-2026-10-20.md). The existing ranked queue is:

1. **Convergent relay-link edge phase** — gravity and magnetic horizontal-gradient ridges plus tilt zero-crossings on opposite corridor margins; seeks a buried bridge between visible tips; differs by requiring joint phase/axis coherence rather than independent layer maxima. Named mimic: lithologic contacts. Cost: moderate.
2. **Releasing-basin margin asymmetry** — gravity curvature, paired gradient flanks, and magnetic low within tip-derived rhombs; seeks buried basin-bounding splays; differs from scalar low ranking. Named mimic: sediment-filled paleochannels. Cost: moderate; requires measured slip sense.
3. **En-échelon scarp phase coherence** — oriented LiDAR scarp ridges staggered across a corridor; seeks short unmapped links; differs from average scarp magnitude. Named mimics: pluvial shorelines and road cuts. Cost: moderate-high.
4. **Corridor-confined radiometric contrast reversal** — local K/Th contrast relative to matched flanks, conditional on magnetic depletion; seeks local alteration hidden by broad lithology and allows signed contrast rather than depletion-only ranking. Named mimic: sediment sorting. Cost: high; source and lithologic controls require verification.

These are hypotheses only, not claimed discoveries or score improvements. The full feature stack, valid holdout run, and duplicate-stop clearance would be prerequisites; the literal stop currently prevents proceeding to a new surface or dot placement. If an upstream selector changes the rule, that change must be explicit and applied consistently, not locally improvised.

### H33 and score context

The claimed H33 **0.2778** is **USER-REPORTED-NOT-ORGANIZER-CONFIRMED** in the supplied prompt. Sparse dot emission and catalogue-flank pruning plausibly improve precision under the distance-weighted metric by reducing false-positive mass while retaining credit near hidden faults. This is a mechanism hypothesis, not a causal explanation proven against organizer truth. The cited competition highs are conflicting user reports; the public board was not independently refreshed in this review. A higher score is possible in principle but not demonstrated by this repository review.

### Source / data status

No source outside the permitted host set was fetched in this review. Manual-review links already tracked in the project:

- [DrivenData competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — login-gated per prior repository attempts; this review did not authenticate.
- [Official reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [Giddens & Faulds report cited in the prompt](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf) — statistics are not independently verified here.
- [Submission format PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

Official organizer input bytes and submission receipts are still unavailable in this environment. Hash-pinned family mirrors prove byte consistency, not organizer authentication. No claim is made that this project directly validates geothermal vents; its submission target is hidden fault locations used as a proxy.

## Verification commands

```sh
PYTHONPATH=vendor/template66:src .venv/bin/pytest -q
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/release_gate.py
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/build_readme.py
PYTHONPATH=vendor/template66:src .venv/bin/python scripts/build_site69.py
GEMS_DATA="$PWD/data/bridge" PYTHONPATH=vendor/template66:src .venv/bin/python scripts/validate_submission.py submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-zeros.tif
```

## Next work — blocked until protocol/inputs are resolved

1. Keep the public download disabled. Obtain an explicit upstream ruling on the literal registry-overlap policy; do not override it in this repo.
2. Obtain authenticated competition data/receipts or document the exact constraints preventing them. Confirm the official sample grid and catalogue identity.
3. Recover and pin all source code and feature inputs for the exact candidate; re-verify the repaired tip-graph invariants and resolve measured dip/slip attribute limitations in the shared template only.
4. Only after the stop is formally resolved: pre-register untouched spatial blocks; use the shared holdout/evaluator and writer; run feature-alone leakage checks; compare pooled HOLDOUT-DTI and a spatial-block CI against both control and declared current best; perform complete surface uniqueness before placement and dot uniqueness afterward.
5. Rebuild and revalidate exact artifact bytes, bind all reports to the raster and source hashes, and require every release gate to pass before any download can be offered. Submission-slot selection remains separate.

No submission slot was used. No promotion is recommended.
