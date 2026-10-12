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
