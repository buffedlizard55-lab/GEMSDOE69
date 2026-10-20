# H33 owner-source audit — 2026-10-20

## Scope and evidence class

This is a **provenance and byte-anatomy audit**, not an organizer evaluation.
It was conducted through GitHub's public API against the owner repository
[`buffedlizard55-lab/GEMSDOE32`](https://github.com/buffedlizard55-lab/GEMSDOE32)
at its then-current `main` commit
[`98901f3130e8704f4254f173784589e63f000673`](https://github.com/buffedlizard55-lab/GEMSDOE32/commit/98901f3130e8704f4254f173784589e63f000673),
whose commit metadata says `2026-10-20T10:13:42Z`.

No H33 TIFF was downloaded for model construction or used as a feature,
training label, target, threshold, or spatial mask. The only locally retained
H33 measurement is the pre-existing registry anatomy record
[`evidence/relayfix_champion_anatomy.json`](../evidence/relayfix_champion_anatomy.json).

## Finding: the current owner source contradicts the stated score premise

The user-associated file is:

- `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`
- owner-recorded SHA-256:
  `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`
- owner-recorded grid: one float32 band, EPSG:32611, 3730 × 3292, 100 m
  transform; 37,654 positive pixels.

The current owner [audit JSON](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json)
labels it as a catalogue-flank removal from a `0.2708 base`, explicitly says
`UNSCORED` in its submission note, records `predicted_leaderboard_dti` as
`0.27467315976932155`, and does **not** contain an organizer submission receipt.
The owner [site source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html)
says the 0.2708 anchor is the already-scored fallback and says no organizer
score exists for the primary. The owner
[submissions manifest](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/submissions_manifest.json)
contains `receipt: null` for the listed submission artifacts.

Therefore the prompt's `0.2778` association is
**USER-REPORTED-NOT-ORGANIZER-CONFIRMED**. It is not possible to establish
that 0.2778 is the organizer score of the cited H33-2-B2 TIFF from the source
currently available. The value `0.27467315976932155` is an owner projection,
not a score, and is not used as a benchmark or prediction in this repository.

## Measured byte anatomy (MEASURED-HERE)

The existing local anatomy record was computed from a fetched registry blob
with the SHA-256 above. It reports:

| Measurement | Result | Evidence class |
| --- | ---: | --- |
| Unit-valued dots | 37,654 | MEASURED-HERE |
| Dots on the mirrored catalogue | 0 | MEASURED-HERE |
| Minimum distance to mirrored catalogue | 2.236 pixels (223.6 m) | MEASURED-HERE |
| Median distance to mirrored catalogue | 19.647 pixels (1.965 km) | MEASURED-HERE |
| Dot fraction within 3 pixels | 0.05766 | MEASURED-HERE |

These values corroborate that the file is a sparse dot field rather than a
ribbon drawn directly on the mirrored catalogue. They do **not** reveal the
unpublished organizer truth, create a geological validation, or identify a
leaderboard score.

## What can, and cannot, be inferred scientifically

The owner description says the artifact deletes dots at catalogue distance
less than or equal to two pixels from a pre-existing anchor field. Under a
false-positive-penalizing, distance-kernel metric, such deletion could help
*if* the removed predictions add less unique hidden-fault coverage than their
false-positive contribution. This is a conditional metric-alignment
explanation, not a causal demonstration: adjacent predictions may also cover
true unmapped faults. Without the organizer truth and a submission-page
receipt, neither the alleged performance nor a geothermal interpretation is
identified.

The H33 method is not a valid model for the relay-ramp and pull-apart lane.
Using its dots, its output surface, its catalogue-flank threshold, or its
selection order would be copying a previous lane rather than proposing faults
from the current lane's catalogue tip graph. The current lane remains focused
on independently emitted relay, pull-apart, and transfer corridors.

## Action taken

1. The site and README no longer call H33-2-B2 a verified 0.2778 result.
2. The site states that the owner source says `UNSCORED`; the cited number is
   retained only as user-reported context.
3. No submission slot was used and no H33 artifact was copied or offered.
4. The discrepancy is logged as `IR-69-H33-01` in `FLAGGED.md`.

## Manual review links

- [GEMSDOE32 owner repository](https://github.com/buffedlizard55-lab/GEMSDOE32)
- [Owner H33 audit JSON](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json)
- [Owner page source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html)
- [Owner submissions manifest](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/submissions_manifest.json)
- [Organizer reference solution repository](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Official DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)

The last link is the place to establish an organizer score, but no authenticated
receipt was available in this environment.
