# Handoff — literal integrity review, 2026-10-20

## Read before every session

Read README.md, PROJECT_REQUEST.md (full current user request), and AGENTS.md. This checkout is tied to `arena/d7c9058c-gemsdoe69`; do not switch or rename the session branch. Historical reports are archival observations, not current clearance.

## Current state: NEGATIVE — DO NOT SUBMIT

No new model experiment, TIFF emission, competition slot selection, or upload was performed in this review. Validators, source research, synthetic unit tests, browser checks and archival raster comparisons are not model experiments.

- **Literal universal-prior failure freshly reproduced:** the pinned 17GEMSDOE raster is positive at all 5,167,373 mirrored footprint pixels. Archived H69-J's 38,669 dots have forward 3-pixel overlap **1.0**; full-footprint Spearman against that one raster is **0.10344425936824049**. This is a protocol/representation conflict, not proof of identical geology. No density exemption is authorized. One counterexample stops a candidate; it does not constitute exhaustive registry clearance.
- **Independent sparse-prior failure:** H69-J's forward overlap with a local sparse archived field is **0.8023481341643177**, also over 0.70. Excluding the universal prior would not rescue the archived candidate. Read the current `evidence/local-prior-audit.json` for the complete local comparison set; additional parallel-session archives must be included after integration.
- **Scientific evidence quarantined:** whole-catalogue flank masks and the older full-catalogue canary violate visible-only hide-and-recover; dip/slip/source-polyline requirements are not certified; mean-of-cell intervals and repeated-cell bootstrap do not establish the required pooled spatial-block comparison to the current best. Existing DTI numbers are archival, not newly certified HOLDOUT-DTI or organizer scores.
- **Format only:** both archived H69-J variants pass `scripts/validate_submission.py`; NaNs in the twin are outside the footprint only. This does not explain an unavailable portal rejection or prove portal acceptance.
- **Unsafe generator retired:** the old command could insert placeholder AUCs, borrow an earlier holdout and mark failed validators successful. Do not restore or rerun it. Generation, holdout and legacy evidence-finalization CLIs stop at preflight. No `--force` or dotlike-only override exists.

The shared template evaluator/writer bytes were not edited. No private scientific evaluator fork was created. `scripts/release_gate.py` is the publication policy; missing/malformed/contradictory measurements, stale source hashes and quarantine fail closed. Its CLI is audit-only. Card replacement requires matching E2/receipt bytes; crossing candidates needs explicit intent and archives the complete previous card before replacement. A new hash or rebinding old numbers is not new evidence.

## Reproduce safely

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python scripts/validate_submission.py \
  submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-zeros.tif \
  submissions/h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5-nan.tif
python scripts/release_gate.py
python scripts/build_site69.py
python scripts/build_readme.py
python scripts/check_site.py
```

The registry/H33 reproduction additionally needs the two pinned bytes in ignored `.cache/review20261020/`; fetch them using the URLs/blob/hash recorded in the audit JSONs before running `scripts/audit_registry_blocker.py`. Do not restore the full feature cache merely to work around the stop. Large files stay out of Git.

## Sources and research queue

- All **72 unique user-listed family page sources** were read through GitHub and git-blob verified; **91 user-supplied artifact-score claims** remain unconfirmed. A name/decimal mention or download link is not a verified pairing, raster clearance or organizer receipt. Exact chains are in `docs/data/family-feed.json`.
- H33's **0.2778 is user-reported, not organizer-confirmed for the pinned TIFF**. Fresh anatomy: 37,654 unit dots, zero on-catalogue positives. Official staff confirms known-fault pixels are masked in initial/final scoring, so zero on-catalogue dots alone does not explain an advantage. The official metric pools counts; it is not the mean of chunk scores.
- Official problem/rules/literature/USGS/GDR pages were read with the research fetch tool and recorded claim by claim. Shell `--official` smoke test recorded **14 explicit TLS errors** under Arena's host restrictions. Do not call those shell checks successful. A later research-tool leaderboard read returned only Loading; the earlier dated public snapshot is not a live guarantee or artifact-bound receipt.
- The qfault mirror has DIPDIRECT/SLIPSENSE and the trace CSV has record IDs/sense. Their pinned bytes were retrieved to ignored audit storage. Authentication of the official archive/joins and production integration remain missing; do not claim the attributes are absent or ready.
- Four ranked, unimplemented in-lane hypotheses are in `registry/hypotheses_review_2026-10-20.json`: P1 nuisance-matched signed connector profiles; P2 dip/slip-aware releasing-vs-restraining counterfactual; P3 W-scaled localized magnetic-low neck; P4 scarp-relief taper (deferred until exact tiles verified). No numeric gain forecasts. No GPU is required.

## Site, automation and review status

The generated site has a negative status strip on every active page, a clear top-level NOT OK TO SUBMIT banner, no approved download, claim-level source/family tables, H33 metric explanation, methods audit, ranked queue, blockers and a single current audit card. Negative builds revoke TIFF/ZIP files anywhere under docs while preserving private scientific history. The Pages artifact is scoped to static files, not the repository's submission archive.

Daily Actions source refresh is defined for best-effort 08:17 UTC. It retains a previous-observation cache, records byte changes only when two readable hashes exist, and exposes failures without changing science gates. It never trains, selects or submits. Publishing requires the repository Pages workflow setting and a verified Actions deployment; do not claim deployment from a local build alone.

Three additive passes: (1) baseline audit/source and raster verification; (2) fail-closed policy/orchestration and malformed-input regression tests; (3) end-to-end static/browser/CI/deployment review. Latest pre-integration local result: **184 passed, 24 existing rasterio deprecation warnings**; static links/policy **18 pages passed**; Chromium 153 browser smoke **20 active-page/viewport visits passed** at desktop 1440×1000 and mobile 390×844, root redirect works, no public raster links or horizontal body overflow. Screenshots/tool dependencies remain ignored.

### Integration still to finish at this checkpoint

Remote main advanced from the session base to `5ce061a` while other sessions merged. Integrate it on this branch, preserve the H69-H2 card as an explicitly archived original before selecting the H69-J negative audit card, recheck newly inherited local TIFFs, rerun all checks, then open/review/merge this branch's PR. PR16 and other concurrent PRs are not authorized by this review; do not merge their score/promotion claims on assumption. Update this checkpoint with actual merge/deployment outcomes.

## Only legitimate path to another experiment

Resolve the protocol conflict through an explicit written owner/selector decision; keep the literal stop until then. Authenticate input bytes, source polylines and record joins. Repair all hidden-target use in the lane caller, reserve untouched blocks, preregister one queued hypothesis, compute feature-alone canaries and pooled spatial-block contrasts against both control and current best. Only after a truly new candidate passes both correctly ordered exhaustive uniqueness phases and exact-byte format validation may the site offer a download. Slot selection/upload remains a separate selector step under the authenticated allowance.

**Maximize P(Win):** preserve slots and falsify confounded hypotheses. **Own the Outcome:** publish defects, uncertainty and negative results without cosmetic promotion.
