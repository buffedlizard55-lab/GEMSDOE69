# Instructions for every session in this repository

1. Read `PROMPT.md` (the standing brief, embedded in full in `README.md`) before doing anything.
2. Core values are focal: **Maximize P(Win)** and **Own the Outcome**.
3. Parallel-run protocol: stay in the relay-ramp / pull-apart corridor lane; reuse `vendor/gems57`
   (byte-identical to `60GEMSDOE/src/gems57`, see `registry/template_pin.json`) — never edit it locally;
   label every number (HOLDOUT-DTI with evaluator version, withheld positives and 95% CI, or
   ORGANIZER-CONFIRMED); run the leakage canary; end with `evidence/run_card.json`; stop after
   3 experiments or 2 hours; never pick a submission slot.
4. Large inputs live outside git (`scripts/restore_data.py` -> `$GEMS_DATA`); every number on the site
   is generated from `evidence/*.json` by `scripts/build_site.py` / `scripts/build_readme.py`.
