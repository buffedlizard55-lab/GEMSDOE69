# Leaderboard check — 2026-10-12

**Label for every number on this page:** `OFFICIAL-LEADERBOARD` = copied from the organizer's public DrivenData
leaderboard page (team/user level, *public-test* DW-Tversky, not a submission receipt).
Nothing here is a holdout score for this project. No submission from this repository has been scored.

**Source (verified this session):** https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
— read with `fetch_page` on 2026-10-12; the page lists the top 50 rows only (`hasMore: false` at rank 50).
The board shows **participant usernames only, not submission names**, so no leaderboard row can be linked to a
submission file from the owner's list.

## Claims in the brief, checked against that page

| Claim in the brief | What the official page shows (2026-10-12) | Verdict |
|---|---|---|
| "0.3195 is the highest score right now" | #1 is `xiaofanhu` at **0.4275**. `DARD` at **0.3195** is rank **#9**. | **FALSE** (IR-01) |
| "0.3774 — top score" | No row shows 0.3774 in the top 50. | **NOT FOUND** (IR-02) |
| "h33-h33-2-b2-…-zeros: 0.2778" | Rank **#24** `extradr19` shows **0.2778**. No file name is shown, so the attribution is unverifiable. | **UNATTRIBUTABLE** (IR-03) |
| "0.2600 — GEMSDOE25/30/…" | Rank **#47** `SDCF9` shows 0.2600. Not attributable to a file. | UNATTRIBUTABLE |
| "0.2708 / 0.2710 / 0.2707 (owner files)" | Rows #36 `smrtdoog5` 0.2708, #37 `bot_account` 0.2707, #35 `smashi34` 0.2710. Not attributable. | UNATTRIBUTABLE |

Board volatility (irregularity IR-01b): the GEMSDOE32 repo's own ledger records a 2026-10-04 snapshot with
#1 `nchuzhoy` 0.3262 and #2 `DARD` 0.3195 (`registry/leaderboard_history.jsonl`, read from the sibling repo).
On 2026-10-12, `nchuzhoy` is #7 at 0.3262 and `DARD` is #9 at 0.3195. The ranking has moved; the
public board is not a stable target.

Gap arithmetic (verified from the rows below): #1 − #24 = 0.4275 − 0.2778 = **0.1497**. The 5th-place
public score is 0.3333 (#5 `joeyfezster`). Prize Phase 1 is decided on the **private** test set, so public
rank is not prize rank (rules §3.6.1–3.6.2).

## Top 50 (verbatim from the page)

| Rank | Participant | Public DW-Tversky |
|---:|---|---:|
| 1 | xiaofanhu | 0.4275 |
| 2 | cfld__ | 0.3585 |
| 3 | JerryDataWorks | 0.3418 |
| 4 | alexoktaba | 0.3361 |
| 5 | joeyfezster | 0.3333 |
| 6 | Batik Shirt Brothers | 0.3300 |
| 7 | nchuzhoy | 0.3262 |
| 8 | kinghorton42 | 0.3261 |
| 9 | DARD | 0.3195 |
| 10 | ohyeah | 0.3147 |
| 11 | mzoorob | 0.3129 |
| 12 | ruping | 0.3104 |
| 13 | newway | 0.3080 |
| 14 | BrandenKMurray | 0.3050 |
| 15 | giles | 0.3025 |
| 16 | notmyfault | 0.2981 |
| 17 | baobao | 0.2974 |
| 18 | GrigorSargsyan | 0.2892 |
| 19 | ndavis7 | 0.2888 |
| 20 | HardcoreTechGod | 0.2854 |
| 21 | nsabaj | 0.2843 |
| 22 | jgaines | 0.2820 |
| 23 | op01 | 0.2797 |
| 24 | extradr19 | 0.2778 |
| 25 | arnofault | 0.2764 |
| 26 | faultsofthy | 0.2764 |
| 27 | wonderfulbig12 | 0.2761 |
| 28 | No Fault of Our Own | 0.2761 |
| 29 | doublebigmac | 0.2758 |
| 30 | wbg1 | 0.2750 |
| 31 | raboush2 | 0.2747 |
| 32 | Mekhi12 | 0.2747 |
| 33 | 1stop | 0.2747 |
| 34 | li002666 | 0.2726 |
| 35 | smashi34 | 0.2710 |
| 36 | smrtdoog5 | 0.2708 |
| 37 | bot_account | 0.2707 |
| 38 | kpomazi | 0.2706 |
| 39 | NoahNault | 0.2702 |
| 40 | shixing | 0.2664 |
| 41 | roison | 0.2655 |
| 42 | yifanxu | 0.2650 |
| 43 | ad3002 | 0.2643 |
| 44 | moongrega | 0.2640 |
| 45 | regan_towin | 0.2632 |
| 46 | jfper21 | 0.2607 |
| 47 | SDCF9 | 0.2600 |
| 48 | haiderz | 0.2584 |
| 49 | tchu | 0.2511 |
| 50 | MSU-Laskowski-GEMS | 0.2448 |

(`bot_account` at #37 is listed as shown. Its meaning is not explained on the page; flagged for review, IR-19.)
