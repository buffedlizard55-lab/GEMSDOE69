# Sources (verified links for manual review)

"Verified" = fetched and read in this session (2026-10-12); the quoted fact is what was read.

## Competition (official)

| Source | What it establishes | Status |
|---|---|---|
| [Problem description (page 967)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Test set = faults identified by experts that are **not** in the USGS database; Initial round ($50k, top 5 × $10k) on a fixed private set; Final round ($250k: $100k/$70k/$40k/$25k/$15k) re-scores the **single** selected submission against an expanded label set; metric = distance-weighted Tversky, α = 0.2, β = 0.8, triangular kernel R = 300 m, worked example TP 3.00 / FP 1.89 / FN 2.00 → 0.60; format = single float32 layer, EPSG:32611, 100 m, same bounds, "data outside the bounds is null or nan", values between 0 and 1; external data allowed if licensed | Verified |
| [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | #1 xiaofanhu 0.4275, #2 cfld__ 0.3585, #9 DARD 0.3195; 0.2778 appears under `extradr19` (no file attribution) — snapshot `registry/leaderboard_snapshot_2026-10-12.json` | Verified |
| [Forum 11516 — masking of known faults](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) | DrivenData staff: "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation"; re-evaluation will also mask them | Verified |
| [Forum 11527 — how test faults were identified](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527) | DrivenData staff (2026-09-23): data sources, fault types and coverage of the test faults are **not disclosed**; Phase 2 test set is updated by expert review of all Phase 1 submissions | Verified |
| [Rules page](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/) → [HeroX resource 2274](https://www.herox.com/GEMSPrize/resource/2274) → [official rules PDF](https://www.nlr.gov/docs/fy26osti/96647.pdf) | §1.1 "Participants will submit a single entry, which will be evaluated in two prize phases"; Phase 1 $50,000 split among the top five, Phase 2 $100k/$70k/$40k/$25k/$15k; §3.2 "You can make multiple submissions, subject to the limits specified on the competition website (three submissions per week)"; generative-AI use allowed but must be disclosed in the narrative; finalists submit complete code and documentation able to reproduce the results; new-fault labels by experts at NLR and USGS | Verified |
| [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | Commit `aebe92f7` (2026-06-16), notebook cell 19 writes the prediction with `rasterio.open(..., "w", driver="GTiff", count=1, dtype=..., crs=..., transform=...)` and **no nodata tag** | Verified (cloned) |
| [GeoDAWN data release (USGS)](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) and [INGENIOUS project](https://gbcge.org/current-projects/ingenious/) | Origin of the feature stack and labels (linked from the problem description) | Links verified on the problem page |

## Geology used by the lane

| Source | Fact used | Status |
|---|---|---|
| Giddens, M.H. & Faulds, J.E. (2025) *Analysis of step-overs (or relay ramps) in normal fault systems in the Great Basin region*, 50th Stanford Geothermal Workshop, SGP-TR-229 — [PDF](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf) | > 450 step-overs; relay widths 0.1–14.6 km, mean 2.8 km; step-overs at > 120 °C systems ~70 % hard-linked, ~56 % overlapping, ~74 % between N–NNE strands; relays "typically 3 to 3.5 times longer than the width"; step-over = transfer to an adjacent parallel fault "with the same direction of dip"; breaching minor faults range from oblique connectors to en échelon strands | Verified |
| Faulds, J. et al. (2026) *Favorable structural settings for geothermal systems in the Great Basin region*, 51st Stanford Geothermal Workshop — [PDF](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2026/Faulds.pdf) | Displacement-transfer zones and pull-aparts are more prominent in the transtensional western Great Basin within and near the Walker Lane; step-overs ~40 % of favorable settings | Read from the search-engine excerpt of the PDF (not fully fetched) |
| Peacock & Sanderson (1994), AAPG Bulletin 78(2) — relay-ramp evolution stages (cited inside Giddens & Faulds 2025, Fig. 4) | Stage 3: upper ramp breached → hard-linked | Cited via the verified Giddens & Faulds text |
| Miller & Singh (1994), J. Applied Geophysics 32 — tilt angle `atan(VDR/THDR)` | Edge detector used for gravity / magnetics | Standard method; not fetched |

## Data mirrors (integrity-pinned, not organizer-authenticated)

* Feature stack: `buffedlizard55-lab/GEMSDOE` @ `c0c06ac8…` (five parts, SHA-256 `4371c82e…`); the mirror manifest records the organizer Dropbox links it was copied from.
* Catalogue raster, sample submission and external layers: `buffedlizard55-lab/60GEMSDOE` @ `32024716…` (`data/`), every file re-hashed against the pins in `src/gems69/data.py`.
* INGENIOUS Quaternary-fault polylines: `trace_segments_utm11.csv` (SHA-256 `c5edf9df…`) + `qfault_attributes.csv` (`3b8745f0…`); the join `record_id` = attribute row was verified on slip rate and slip sense for 1,126 / 1,126 records, and 99.98 % of catalogue pixels lie within 100 m of the rasterised traces.
