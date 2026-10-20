#!/usr/bin/env python3
"""Build the GitHub Pages site (docs/) from evidence JSON. Pure stdlib."""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence"
SUB = ROOT / "submissions"

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "Executive Summary"),
    ("why-h33-scored.html", "Why H33 Scored"),
    ("hypotheses.html", "Hypotheses"),
    ("method.html", "Method"),
    ("results.html", "Experiments"),
    ("sources.html", "Sources"),
    ("irregularities.html", "Irregularities"),
    ("run-card.html", "Run Card"),
]


def esc(x) -> str:
    return html.escape(str(x))


def load(name: str, default=None):
    p = EV / name
    if p.exists():
        return json.loads(p.read_text())
    return default


def page(title: str, active: str, body: str) -> str:
    nav = "".join(
        f'<a href="{h}" class="{"active" if h == active else ""}">{t}</a>' for h, t in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · GEMSDOE69</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body>
<header><div class="wrap"><h1>GEMSDOE69 · Relay-ramp &amp; pull-apart corridor lane</h1>
<div class="sub">DOE GEMS Prize (DrivenData #306) · catalogue-geometry fault proposal · parallel-run lane 69</div></div></header>
<nav><div class="wrap">{nav}</div></nav>
<main class="wrap">
{body}
</main>
<footer>GEMSDOE69 · negative results are deliverables · Maximize P(Win) · Own the Outcome</footer>
</body></html>"""


def submission_banner():
    """Publish only the exact hash-bound artifact cleared by the literal policy."""
    from release_gate import evaluate
    decision = evaluate(ROOT)
    downloads = DOCS / "downloads"
    # Revoke previously published artifacts as well as hiding their links.
    if downloads.exists():
        for artifact in downloads.iterdir():
            if artifact.suffix.lower() in (".tif", ".tiff", ".zip"):
                artifact.unlink()
    if not decision["download_enabled"]:
        reasons = "".join(f"<li>{esc(r)}</li>" for r in decision["reasons"])
        return ('<div class="banner bad"><b>NOT OK TO SUBMIT — DO NOT SUBMIT.</b>'
                '<p>No submission download is offered. The archived candidate is a negative result '
                'under the literal protocol. No competition slot was used.</p><ul>' + reasons + '</ul></div>', None)
    receipt = load("e3_receipt.json")
    tif = ROOT / receipt["raster"]["zeros"]["path"]
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tif, downloads / tif.name)
    return ('<div class="banner ok"><b>OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE.</b>'
            '<p>All literal gates passed. A separate selector must authorize a real competition slot.</p></div>'
            f'<a class="btn big" href="downloads/{esc(tif.name)}" download>Download submission TIFF</a>', tif)


def build_index():
    ban, tif = submission_banner()
    gate = load("e2_gate.json") or {}
    uniq = load("e3_uniqueness.json") or {}
    receipt = load("e3_receipt.json") or {}
    card = load("run_card.json") or {}
    rows = ""
    if gate:
        rows += f"""<tr><td>Corridor arm archived mean DTI</td><td>{gate.get('corridor_mean_dti', float('nan')):.4f} &plusmn; {gate.get('corridor_ci95_half', float('nan')):.4f}</td><td>HOLDOUT-DTI (gems57 pooled hide-and-recover, {gate.get('n_cells','?')} cells, {gate.get('withheld_positive_px_total','?')} withheld positives)</td></tr>
<tr><td>No-prior control arm</td><td>{gate.get('control_mean_dti', float('nan')):.4f} &plusmn; {gate.get('control_ci95_half', float('nan')):.4f}</td><td>HOLDOUT-DTI, same folds</td></tr>
<tr><td>Paired &Delta; (corridor &minus; control)</td><td>{gate.get('paired_delta_mean', float('nan')):+.4f} &plusmn; {gate.get('paired_delta_ci95_half', float('nan')):.4f}</td><td>HOLDOUT-DTI</td></tr>"""
    body = f"""
{ban}
<div class="card" id="how-to-submit">
<h2>How to submit the TIF (3 steps)</h2>
<ol>
<li>Only after the banner explicitly permits a download, download the <b>-zeros</b> variant (all cells finite in [0,1] &mdash; this avoids the
&ldquo;Predicted values must be in range [0, 1]&rdquo; portal error class seen with NaN-containing artifacts).</li>
<li>Go to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition 306 &rarr; New submission</a>,
choose <i>File to submit</i> = the downloaded <code>.tif</code> (a <code>.zip</code> with a single GeoTIFF is also accepted).</li>
<li>Paste this note (&le;140 chars):<br><code>{esc(receipt.get('note', 'relay-ramp corridors'))}</code></li>
</ol>
<p class="small">Format contract: single-band GeoTIFF, float32, EPSG:32611, 3730&times;3292, transform
(100, 0, 243350, 0, &minus;100, 4508550), values in [0,1]. Verified against
<code>sample_submission.tif</code> (sha256 <code>2176d08e&hellip;</code>) by the shared template validator.</p>
</div>
<div class="card">
<h2>Archived evidence at a glance — not independently reproduced</h2>
<table>
<tr><th>Measurement</th><th>Value</th><th>Evidence class</th></tr>
{rows}
<tr><td>Registry scan: worst surface |Spearman| / dot-like dot overlap</td>
<td>{abs(uniq.get('worst_abs_spearman', 0) or 0):.3f} / {(uniq.get('worst_dot_overlap_dotlike') or {}).get('dot_overlap_3px', 'n/a')}</td>
<td>REGISTRY-MEASUREMENT (limits 0.90 / 0.70)</td></tr>
<tr><td>Family best download (h33-2-b2)</td><td>0.2778</td><td>USER-REPORTED-NOT-ORGANIZER-CONFIRMED (receipt quoted on GEMSDOE32 site)</td></tr>
<tr><td>Leaderboard high score cited in prompt</td><td>0.3774 / 0.3195</td><td>USER-REPORTED-NOT-ORGANIZER-CONFIRMED</td></tr>
</table>
<p class="small">A holdout DTI is a <b>screen</b>, never a leaderboard projection: the family's own
instrument calibration (GEMSDOE32) measured cross-family Spearman &rho;&asymp;0.51 (p&asymp;0.09) against live scores.</p>
</div>
<div class="card">
<h2>What this lane is</h2>
<p>Hidden faults are proposed from <b>catalogue geometry</b>, not pixel statistics: the tips of mapped
fault strands form a graph; step-over tip pairs (spacing 0.1&ndash;15 km, along-strike separation &le; 3.5W,
sub-parallel strikes) emit <b>relay-ramp corridors</b> &mdash; an oblique connector plus en&nbsp;&eacute;chelon strands
&mdash; and, at dilatational steps under the Walker-Lane dextral prior, <b>pull-apart rhombs</b>. Corridors are
scored by multi-scale horizontal-gradient and tilt evidence in gravity and magnetics (including magnetic
lows), the 1&nbsp;m lidar-scarp channel, and orientation consistency with WNW extension. Dots are placed by
dots placed by greedy marginal-DTI selection inside the top corridors (pre-registered propensity map
S<sub>0</sub>=0.75; template allocator), &ge;200&nbsp;m from the mapped catalogue.</p>
<p>Geometry priors as cited in the standing prompt: Giddens &amp; Faulds (2025, SGP-TR-229) inventoried
&gt;450 step-overs; ramps are typically 3&ndash;3.5&times; longer than wide (widths 0.1&ndash;14.6 km, mean 2.8 km);
~70% of higher-temperature step-overs are hard-linked; in the Walker Lane, hot systems sit more often in
pull-aparts and displacement-transfer zones; N&ndash;NE faults are best oriented for dilation under WNW extension.</p>
</div>
"""
    return page("Home", "index.html", body)


def build_executive_summary():
    body = """
<div class="card">
<h2>Executive summary &mdash; how a submission is made and entered</h2>
<ol>
<li><b>Generate</b>: <code>scripts/run_lane69.py e3</code> builds the tip graph from the pinned catalogue
mirror, emits and scores corridors, places greedy marginal-DTI dots, and writes
<code>submissions/h69-relayramp-pullapart-&lt;dots&gt;-&lt;stamp&gt;-&lt;sha8&gt;-zeros.tif</code>
(all-finite [0,1]) plus a <code>-nan</code> diagnostic twin, with a JSON receipt.</li>
<li><b>Validate</b>: the shared template validator (<code>vendor/template66/gems/validate_submission.py</code>)
re-reads the bytes from disk and checks CRS EPSG:32611, shape 3730&times;3292, transform, single band,
float32, values in [0,1], and (for the nan twin) NaN only outside the footprint.</li>
<li><b>Gate</b>: the corridor arm must beat the identical pipeline without corridor priors and the
current best on the same spatially-blocked hide-and-recover evaluator. Both uniqueness phases must
pass the literal registry rules. <code>scripts/release_gate.py</code> additionally requires artifact-bound
holdout, validator, source-manifest and feature-alone canary evidence. Pass flags from another TIFF
cannot authorize this file. No download is published while any required evidence is missing.</li>
<li><b>Submit</b>: DrivenData competition 306 &rarr; <i>New submission</i> &rarr; upload the single <code>.tif</code>
(or a zip containing exactly one GeoTIFF). It must match the submission format's CRS, shape, and
geotransform &mdash; ours is written against <code>sample_submission.tif</code> so it matches by construction.
Add a short note (&le;140 characters) identifying the run, e.g. the receipt note.</li>
</ol>
<p><b>Known portal error class</b>: &ldquo;Predicted values must be in range [0, 1]&rdquo; &mdash; caused by artifacts
carrying values outside [0,1] (or non-finite cells the portal does not treat as nodata). The <b>-zeros</b>
variant avoids non-finite values, but is <b>not authorized for submission unless every gate passes</b>.
The <b>-nan</b> variant is diagnostic under our local template policy. Actual portal acceptance
requires an organizer receipt; we have not independently reproduced the reported upload error.</p>
</div>
<div class="card">
<h2>Standing limitations (do not re-discover these)</h2>
<ul>
<li>No DrivenData auth in this environment: organizer bytes cannot be auto-downloaded; sha256-pinned
family mirrors are used (integrity-pinned, NOT organizer-authenticated).</li>
<li>The local bridge treats <code>existing_faults.tif</code> and <code>labels.tif</code> as catalogue inputs.
This is not independent authentication of organizer labels or hidden truth. Archived family estimates
of hidden-truth size must not be treated as confirmed label counts.</li>
<li>Local HOLDOUT-DTI is a screening metric, not a leaderboard score or a guarantee of cross-family ranking.</li>
</ul>
</div>
"""
    return page("Executive Summary", "executive-summary.html", submission_banner()[0] + body)


def build_why_h33():
    body = """
<div class="card"><h2>Why the reported H33 result is plausible — not proven</h2>
<p>The value <b>0.2778 is USER-REPORTED, NOT ORGANIZER-CONFIRMED for this file</b>.
No submission-page receipt binding that value to the H33 hash is available here. The user gives
conflicting leaderboard highs; the archived leaderboard snapshot is not a current feed.</p>
<p>The local family audit (<code>evidence/e0_champion_ladder_measured.json</code>) records
progressively sparser dot fields. Under the implemented DTI, redundant dots can add false-positive
mass without increasing the maximum coverage of a truth pixel. Thinning can therefore improve
precision while retaining recovery within the distance kernel. This is a plausible explanation
of the reported family trend, not a causal experiment on organizer hidden truth.</p>
<p>Removing catalogue-adjacent dots is <b>not automatically a pure gain</b>: an adjacent dot may cover
an unmasked hidden fault. For a new unit dot with marginal truth coverage dT and self-credit m,
the exact improvement condition is <code>dT &gt; 0.2 DTI (dT + 1 - m)</code> for the stated weights.
The simplified threshold <code>m &gt; 0.2 DTI</code> only follows when dT=m. It is not a universal
5.6% fault-probability rule. There is no justified fixed score ceiling for sparse submissions.</p>
<p>Can we beat H33? Possibly, but <b>not demonstrated</b>. That requires a reproducible,
leakage-safe comparison and ultimately an organizer receipt. Our current literal uniqueness gate
fails, so the correct action is a negative result, not a projected leaderboard score.</p>
<p>Manual review: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">organizer reference repository</a>,
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem description</a>,
<a href="https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html">family H33 page source</a>.
Only the GitHub sources were accessible for this review; the competition page was not independently refreshed.</p></div>
"""
    return page("H33 evidence review", "why-h33-scored.html", body)


def build_hypotheses():
    body = """
<div class="card"><h2>Queued in-lane hypotheses — no experiment authorized after duplicate stop</h2>
<p>Qualitative ranking by expected incremental recovery, then implementation cost; no numerical
DTI improvement is predicted. These joint signatures are absent from the checked-in corridor scorer.
All remain untested and not slot-eligible. Existing cached layers suffice in principle, but the
full stack is not restored here. No new external dataset is represented as obtainable.</p>
<table><tr><th>Rank / hypothesis</th><th>Layers and physical signature</th><th>Missing-fault argument / difference / mimic / cost</th></tr>
<tr><td>1. Convergent relay-link edge phase</td><td>Gravity and magnetics: HG ridge directions and tilt-zero crossings on opposite corridor margins at several scales.</td>
<td>Could locate a buried bridge between visible tips. Unlike the current independent maximum layer scores, requires a shared connector phase and axis. Lithologic contacts mimic it. Moderate cost; uncertain benefit.</td></tr>
<tr><td>2. Releasing-basin margin asymmetry</td><td>Gravity curvature and paired HG flanks plus magnetic low, restricted to tip-derived pull-apart rhombs.</td>
<td>Could find buried basin-bounding splays rather than rescore visible scarps. Tests transverse basin structure, not a scalar low. Sediment-filled paleochannels mimic it. Moderate cost; uncertain benefit. Slip sense must be verified, not inferred from overlap alone.</td></tr>
<tr><td>3. En echelon scarp phase coherence</td><td>LiDAR-scarp channel: staggered oriented ridges aligned across a proposed connector, vetoing uninterrupted parallel terrace edges.</td>
<td>Could recover short linking strands omitted by regional mapping. Current scorer averages channel magnitude, not staggered spatial phase. Pluvial shorelines and road cuts mimic it. Moderate-to-high cost; uncertain benefit.</td></tr>
<tr><td>4. Corridor-confined radiometric contrast reversal</td><td>Radiometric K/Th local contrast relative to matched corridor flanks, conditional on magnetic depletion.</td>
<td>May distinguish local alteration from broad lithologic domains, including K enrichment as well as depletion. Unlike the archived depletion-only claim, estimates signed within-unit contrast. Sediment sorting mimics it. High cost because lithologic controls are not authenticated; defer pending provenance.</td></tr></table>
<p>Before any implementation: repair provenance, restore pinned inputs, verify feature-alone canaries,
reserve untouched spatial blocks, compare with the current best on the identical evaluator, and check
surface uniqueness before placing dots. Do not relax the literal overlap rule. Giddens &amp; Faulds
statistics in the prompt remain unverified citations in this environment, not independently established facts.</p></div>
"""
    return page("Queued hypotheses", "hypotheses.html", body)


def build_method():
    body = """
<div class="card">
<h2>Method</h2>
<h3>Tip graph</h3>
<p>The pinned catalogue mirror (labels &equiv; existing_faults, IR-69-DATA-01) is skeletonized
(scikit-image), traced into 3,887 strands between endpoints/branch points, and every strand carries its
two tips with terminal strikes (PCA of the tip-adjacent 12-px tail).</p>
<h3>Pair acceptance (all lengths in 100 m px)</h3>
<ul>
<li>tips from different 8-connected components (same-component pairs are reserved for the hard-link test);</li>
<li>terminal strikes sub-parallel, axial &Delta;&theta; &le; 30&deg; &mdash; the raster carries no dip polarity, so
&ldquo;same dip&rdquo; is proxied by sub-parallel strike (disclosed limitation IR-69-DIP-01);</li>
<li>cross-strike spacing W &isin; [1, 150] px (0.1&ndash;15 km);</li>
<li>along-strike separation &le; 3.5W and overlap &le; 1.0W, computed as interval arithmetic on the
strike-axis projection of tip-adjacent strand windows (sign-invariant for axial data).</li>
</ul>
<h3>Corridor emission</h3>
<ul><li><b>Oblique connector</b>: tip-to-tip line, extended 0.35W along the local strikes, half-width
clamp(W/6, 1, 6) px;</li>
<li><b>En &eacute;chelon strands</b> (dilatational pairs): 2&ndash;8 strands of length clamp(1.5W, 4, 30) px at
&plusmn;25&deg; to the connector, staggered along it;</li>
<li><b>Pull-apart rhomb</b> (dilatational pairs): rotated ellipse, semi-axes 0.8/0.45 of the tip diagonal;
Walker-Lane dextral prior applied through the dilation diagnostic (overlap &le; 0.5W &rArr; dilatational),
because slip sense is unobservable from the raster (recorded per corridor);</li>
<li>strongly overlapping steps emit the narrower <b>transfer-overlap</b> corridor.</li></ul>
<h3>Corridor scoring</h3>
<p>S = 0.20&middot;E<sub>grav</sub> + 0.20&middot;E<sub>mag</sub> + 0.18&middot;E<sub>maglow</sub> + 0.15&middot;E<sub>lidar</sub>
+ 0.10&middot;W<sub>orient</sub> + 0.17&middot;W<sub>geom</sub> &mdash; weights pre-registered before any holdout look.
E-terms are maxima of robust-z means (footprint median/MAD) over multi-scale horizontal gradients
(&sigma; = 1, 2, 4 px), tilt-edge |sin(arctan2(VD, HG))| with VD the &sigma;/2&sigma; upward-continuation difference,
the provided HG/VG/tilt products, and &minus;tmi/&minus;rtp magnetic lows; E<sub>lidar</sub> is the
max(ex_max, step_max, downface_max) scarp channel; W<sub>orient</sub> scores the corridor axis against the
N&ndash;NE axial family best oriented for dilation under WNW extension; W<sub>geom</sub> is the subtype prior
(pull-apart 1.0, relay 0.9, transfer-overlap 0.6). Every corridor carries a rationale record
(layers with z-values, signature, source) in <code>evidence/e3_receipt.json</code>.</p>
<h3>Emission &amp; gate</h3>
<p>Propensity P(x) = logistic(1.5(S &minus; S<sub>0</sub>)) &times; corridor membership weight; dots placed by the
shared template's exact greedy marginal-DTI allocator with truth-size prior |G| = 12,691 px
(GEMSDOE32 receipt-derived estimate, cited), restricted &ge;2 px from the mapped catalogue. Gate: the
corridor arm must beat the identical pipeline with the corridor prior removed (per-pixel physics
composite, same layer set, same allocator) on the shared template's spatially-blocked hide-and-recover
holdout (seeds 20/21 &times; four quadrants), paired with 95% CIs. Hard-link validation: for same-component
virtual pairs, the linking catalogue mass inside the corridor is masked and recovery within 3 px (300 m)
is measured after rebuilding from the remaining catalogue.</p>
</div>
"""
    return page("Method", "method.html", body)


def build_results():
    gate = load("e2_gate.json") or {}
    rec = load("e1_hardlinked_recovery.json") or {}
    census = load("e1_tipgraph_census.json") or {}
    uniq = load("e3_uniqueness.json") or {}
    receipt = load("e3_receipt.json") or {}
    rows = ""
    for k in sorted(gate.get("per_cell", {})):
        pass
    percell = gate.get("corridor", {}).get("per_cell", {})
    ctrlcell = gate.get("control", {}).get("per_cell", {})
    for k in sorted(percell):
        rows += f"<tr><td>{esc(k)}</td><td>{percell[k]:.4f}</td><td>{ctrlcell.get(k, float('nan')):.4f}</td></tr>"
    ramps = rec.get("ramps", [])
    ramp_rows = "".join(
        f"<tr><td>{r['w_px']:.0f}</td><td>{r['linking_px']}</td><td>{r['within_3px']:.3f}</td><td>{esc(r['subtype'])}</td></tr>"
        for r in ramps[:40])
    body = f"""
<div class="card"><h2>E1 &mdash; census, hard-link recovery, canaries</h2>
<table>
<tr><th>Measurement</th><th>Value</th></tr>
<tr><td>Strands vectorized from the pinned catalogue</td><td>{census.get('n_strands','?')}</td></tr>
<tr><td>Corridors emitted (cap {1200})</td><td>{census.get('n_corridors','?')} ({census.get('n_pull_apart','?')} pull-apart / {census.get('n_transfer_overlap','?')} transfer-overlap)</td></tr>
<tr><td>Hard-linked ramps found / tested</td><td>{rec.get('n_hardlinked_found','?')} / {rec.get('n_tested','?')}</td></tr>
<tr><td>Mean recovery of masked linking faults within 300 m</td><td>{rec.get('mean_recovery_within_300m', float('nan')):.3f} (median {rec.get('median_recovery_within_300m', float('nan')):.3f})</td></tr>
<tr><td>Ramps recovered &ge;70%</td><td>{rec.get('n_ramps_above_70pct','?')}</td></tr>
</table>
<table><tr><th>W (px)</th><th>linking px</th><th>recovery within 3 px</th><th>subtype</th></tr>{ramp_rows}</table>
</div>
<div class="card"><h2>E2 &mdash; holdout gate (corridor vs no-prior control)</h2>
<table><tr><th>Arm</th><th>Pooled DTI</th><th>95% CI half</th><th>Cells</th></tr>
<tr><td>Corridor prior</td><td>{gate.get('corridor_mean_dti', float('nan')):.4f}</td><td>{gate.get('corridor_ci95_half', float('nan')):.4f}</td><td rowspan=2>{gate.get('n_cells','?')} ({gate.get('withheld_positive_px_total','?')} withheld positives)</td></tr>
<tr><td>No-prior control</td><td>{gate.get('control_mean_dti', float('nan')):.4f}</td><td>{gate.get('control_ci95_half', float('nan')):.4f}</td></tr>
<tr><td><b>Paired &Delta;</b></td><td><b>{gate.get('paired_delta_mean', float('nan')):+.4f}</b></td><td>{gate.get('paired_delta_ci95_half', float('nan')):.4f}</td><td>gate_passed = {esc(gate.get('gate_passed'))}</td></tr>
</table>
<table><tr><th>Cell</th><th>Corridor DTI</th><th>Control DTI</th></tr>{rows}</table>
<p class="small">Evaluator: vendor/template66 gems57 pooled hide-and-recover (&alpha;=0.2, &beta;=0.8,
300 m triangular kernel). Evidence class HOLDOUT-DTI.</p>
</div>
<div class="card"><h2>E3 &mdash; emission, registry scan, validator</h2>
<table><tr><th>Check</th><th>Result</th></tr>
<tr><td>Dots emitted (greedy marginal-DTI, |G| prior 12,691 px)</td><td>{receipt.get('n_dots','?')} (catalogue collisions: {receipt.get('catalogue_collision_px','?')})</td></tr>
<tr><td>Upstream validator (zeros)</td><td>{'PASS' if receipt.get('validator', {}).get('zeros', {}).get('passed') else 'see compliance note (IR-69-VAL-01)'}</td></tr>
<tr><td>Format compliance zeros: all-finite [0,1] (family shipping policy)</td><td>{'PASS' if receipt.get('format_compliance', {}).get('zeros', {}).get('all_finite') else 'pending'}</td></tr>
<tr><td>Format compliance nan: finite mask &equiv; sample_submission, NaN outside, nodata tag</td><td>{'PASS' if receipt.get('format_compliance', {}).get('nan', {}).get('finite_mask_matches_sample_submission') else 'pending'}</td></tr>
<tr><td>Registry scan compared / errors</td><td>{uniq.get('n_compared','pending')} / {uniq.get('n_errors','pending')}</td></tr>
<tr><td>Worst |Spearman| surface</td><td>{esc(uniq.get('worst_abs_spearman', 'pending'))}</td></tr>
<tr><td>Worst dot overlap (dotlike stratum)</td><td>{esc((uniq.get('worst_dot_overlap_dotlike') or {}).get('dot_overlap_3px', 'pending'))}</td></tr>
<tr><td>Exact pixel-agreement &ge;99.99% vs any prior raster</td><td>{esc(uniq.get('n_exact_pixel_agreement_9999', 'pending'))}</td></tr>
</table>
</div>
"""
    return page("Experiments", "results.html", body)


def build_sources():
    body = """
<div class="card">
<h2>Source links and verification limits</h2>
<p>Only the organizer GitHub reference repository was refreshed from an official source in this review. Other official links below are manual-review references, not freshly fetched or authenticated evidence. See the README review report for access limits.</p>
<table><tr><th>Source</th><th>Link</th><th>Used for</th></tr>
<tr><td>DrivenData competition 306 (DOE GEMS)</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a></td><td>problem statement, metric, leaderboard (login-walled data)</td></tr>
<tr><td>Problem page</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page/967</a></td><td>submission format + performance metric (alpha 0.2, beta 0.8, 300 m kernel)</td></tr>
<tr><td>About page</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">page/968</a></td><td>resources</td></tr>
<tr><td>Data page</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">/data/</a></td><td>training_features.tif, labels.tif, sample_submission.tif, existing_faults.tif (login-walled; family mirrors used, sha256-pinned)</td></tr>
<tr><td>Reference solution</td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a></td><td>grid constants, metric transcription reference</td></tr>
<tr><td>USGS GeoDAWN airborne magnetic &amp; radiometric surveys</td><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">usgs.gov data release</a></td><td>provenance of the magnetic/radiometric layers</td></tr>
<tr><td>INGENIOUS project</td><td><a href="https://gbcge.org/current-projects/ingenious/">gbcge.org</a></td><td>catalogue context (USGS/INGENIOUS faults)</td></tr>
<tr><td>EPSG:32611</td><td><a href="https://epsg.io/32611">epsg.io/32611</a></td><td>UTM zone 11N grid definition</td></tr>
<tr><td>Tversky index background</td><td><a href="https://en.wikipedia.org/wiki/Tversky_index">wikipedia.org/wiki/Tversky_index</a></td><td>metric family background</td></tr>
<tr><td>GDR data (competition-linked)</td><td><a href="https://gdr.openei.org/submissions/1391">gdr.openei.org/submissions/1391</a></td><td>geothermal data registry node</td></tr>
<tr><td>Step-over inventory cited in prompt</td><td>Giddens &amp; Faulds (2025), SGP-TR-229 (as cited in the standing prompt; not independently fetched in-sandbox)</td><td>ramp width statistics, hard-link fraction, Walker Lane pull-apart preference</td></tr>
</table>
<p class="small">Mirror provenance: competition bytes restored from
<code>registry/data_manifest_gemsdoe32.json</code> (owner-supplied public mirrors; integrity-pinned,
NOT organizer-authenticated). Registry rasters from <code>registry/prior_rasters.json</code>
(751 unique git blobs, family census 2026-10-11), verified content-addressed.</p>
</div>
"""
    return page("Sources", "sources.html", body)


def build_irregularities():
    body = """
<div class="card">
<h2>Irregularities flagged for review</h2>
<table><tr><th>ID</th><th>Finding</th><th>Disposition</th></tr>
<tr><td>IR-69-DATA-01</td><td><code>existing_faults.tif</code> is byte-identical to <code>labels.tif</code>
(sha256 7ba308cc&hellip;) in every family mirror; the true organizer existing-faults raster is not
available in this environment. Consequence: the public labels raster doubles as the mapped catalogue;
the scored hidden truth is unpublished.</td><td>Mirror equality is not organizer authentication; holdout validity and catalogue provenance remain limitations.</td></tr>
<tr><td>IR-69-DATA-02</td><td>No DrivenData auth: organizer bytes cannot be re-downloaded; all data are
sha256-pinned family mirrors (NOT organizer-authenticated).</td><td>Fail-closed fetch scripts verify every byte
on arrival; a mismatch aborts the run.</td></tr>
<tr><td>IR-69-TPL-01</td><td>GEMSDOE63's vendored <code>gems57/grid.py</code> drifted from its sha256 pin (an
unrepinned REPO_ROOT fix). Upstream <code>gems/submission_writer.py</code> and <code>validate_submission.py</code>
are strictly stronger than GEMSDOE63's vendored copies.</td><td>gems57 restored to the pinned bytes (data_dir passed
explicitly); gems/ taken from upstream GEMSDOE66 (the template owner) and the drift documented here.</td></tr>
<tr><td>IR-69-DIP-01</td><td>The raster catalogue carries no dip polarity, so the prompt's &ldquo;same-dip&rdquo; pairing
condition is proxied by sub-parallel terminal strikes (&le;30&deg;).</td><td>Disclosed in the method; sensitivity
check queued for a future session.</td></tr>
<tr><td>IR-69-REG-01</td><td>The literal protocol overlap gate fails closed against ANY sparse dot field because the
registry contains 27 universal soft surfaces and 134 high-density rasters (family precedent GEMSDOE63/64).
The stratified diagnostic does not override the literal protocol. A literal failure means duplicate-and-stop; no download is offered.</td><td>Reported literally in evidence/e3_uniqueness.json.</td></tr>
<tr><td>IR-69-SCORE-01</td><td>All leaderboard values in the standing prompt (0.2778, 0.3774, 0.3195, &hellip;) are
USER-REPORTED-NOT-ORGANIZER-CONFIRMED; no organizer receipt exists in this repo.</td><td>Labels applied everywhere.</td></tr>
</table>
</div>
"""
    return page("Irregularities", "irregularities.html", body)


def build_run_card():
    card = load("run_card.json")
    if not card:
        body = '<div class="card"><p>Run card pending &mdash; written at the end of the E2/E3 cycle.</p></div>'
    else:
        body = f'<div class="card"><h2>Run card (JSON)</h2><pre>{esc(json.dumps(card, indent=1))}</pre></div>'
    return page("Run Card", "run-card.html", body)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / ".nojekyll").touch()
    pages = {
        "index.html": build_index(),
        "executive-summary.html": build_executive_summary(),
        "why-h33-scored.html": build_why_h33(),
        "hypotheses.html": build_hypotheses(),
        "method.html": build_method(),
        "results.html": build_results(),
        "sources.html": build_sources(),
        "irregularities.html": build_irregularities(),
        "run-card.html": build_run_card(),
    }
    # Root is a redirect with a fail-closed status message, avoiding divergent copies.
    (ROOT / "index.html").write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE69 submission status</title></head><body>' + submission_banner()[0].replace('href="downloads/', 'href="docs/downloads/') + '<p><a href="docs/index.html">Open project site</a></p></body></html>')
    (DOCS / "run-card.json").write_text(json.dumps(load("run_card.json"), indent=2) + "\n")
    from release_gate import evaluate
    (DOCS / "status.json").write_text(json.dumps(evaluate(ROOT), indent=2) + "\n")
    for name, html_text in pages.items():
        (DOCS / name).write_text(html_text)
    print("built", len(pages), "pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
