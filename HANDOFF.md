# Handoff — 2026-10-20 session 3

Read README.md (status + standing brief), PROMPT.md, AGENTS.md (session-3 rules), then
`reports/session3-2026-10-20.md`.

## State: NEGATIVE — DO NOT SUBMIT (fail-closed, bound via `evidence/current_candidate.json` = none)

* Two preregistered experiments ran on the corrected holdout instrument (IR-69-HOLD-01 fix):
  H69-M (evidence-first, global top 1,200) and H69-N (evidence-first + 20 km tile quota).
  Both beat the no-corridor control; neither beats the current holdout best (transfer-only
  selector, recomputed in-run). Numbers: `evidence/session_experiments.json`, per-cell detail
  in `evidence/h69m_gate.json`, `evidence/h69n_gate.json`.
* Experiment 3 was not started (budget: 2 h window).
* No TIFF was emitted this session (the preregistered rule emits only after
  prompt_gate AND current_best AND canary). Older TIFFs in `submissions/` are audit-only.

## Decisions for the user (cannot be made by an agent)

1. **What is "the current holdout best"?** The preregistrations define it as the transfer-only
   arm, which is itself a dot-overlap duplicate of a GEMSDOE53 raster (IR-69-REG-03) and so can
   never be submitted. If the bar is instead "best *unique* arm", H69-M/H69-N/joint_priority would
   be compared with each other (joint_priority ≈ H69-M on the primary endpoint; CI spans 0).
2. **Overlap policy** (AGENTS.md, session 3): literal vs like-for-like + rank-matched top-K.
   Only matters once a candidate clears every other gate.

## Next session — start here (ranked)

1. **H69-T, transfer population with evidence and spatial quota.** The transfer/overlap corridors
   carry the most hidden-fault signal on the corrected instrument (Δ vs control +0.034, CI > 0).
   Preregister: transfer population only (non-dilatational), evidence ranks within 20 km tiles.
   **Run the surface uniqueness check vs GEMSDOE53 before the gate**, because the archived
   transfer emission overlapped it at 0.85.
2. Hypotheses 1–2 in `docs/research/hypotheses-2026-10-20-session3.md` (domain-conditioned
   ramp geometry; basement-depth + conductivity connector evidence, already in the z-stack).
3. Re-run the hard-link recovery test under the session-3 runner (archived 0.882, n=17).

## Operational notes

* Restore: `python scripts/restore_data.py`, then fetch `external/geodawn_rad_u8.tif` (sha256
  c22420f7…ba682) from GEMSDOE24@07345ea0 via `gh api` (restore_data.py does not fetch it).
* Registry: `scripts/refresh_registry_v2.py` → `/tmp/gems_registry_cache` (942 rasters).
* ONE z-stack process at a time (3.9 GB RAM; OOM on 2026-10-20, IR-69-OOM-01).
* Gate ≈ 40 min (16 cells × ~145 s); surface ≈ 3 min; surface uniqueness ≈ 10 min.
* `scripts/generate_unique_submission.py` is disabled (IR-69-INTEG-01).
