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
        f'<a href="{h}" class="{"active" if h == active else ""}">{t}</a>' for h, t in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · GEMSDOE69</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body>
<header><div class="wrap"><h1>GEMSDOE69 · Relay-ramp &amp; pull-apart corridor lane</h1>
<div class="sub">DOE GEMS Prize (DrivenData #306) · kinematics-resolved tip graph &amp; directional geophysics · parallel-run lane 69</div></div></header>
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
    if downloads.exists():
        for artifact in downloads.iterdir():
            if artifact.suffix.lower() in (".tif", ".tiff", ".zip"):
                artifact.unlink()
    if not decision["download_enabled"]:
        reasons = "".join(f"<li>{esc(r)}</li>" for r in decision["reasons"])
        return (
            '<div class="banner bad"><b>NOT OK TO SUBMIT — DO NOT SUBMIT.</b>'
            '<p>No public submission download is published and zero competition slots were used. '
            'Our new unique candidate GeoTIFF (<code>H69-K</code>, 54,471 unit dots) passes all science, '
            'leakage-canary, source-manifest, and pixel-format checks AND clears sparse dot-field overlap '
            '(<code>0.6860 &le; 0.70</code>), but the strict literal all-registry 3-px overlap rule fires '
            'at <code>1.0000</code> against whole-footprint soft probability surfaces in the family registry '
            '(<code>17GEMSDOE E-proba-multiscale</code> is &gt;0 on all 5,167,373 footprint pixels, leaving 0 '
            'uncovered cells). Per the mandatory duplicate-and-stop rule, the file is archived in '
            '<code>submissions/</code> for audit/selector review only.</p>'
            '<ul>' + reasons + '</ul></div>',
            None,
        )
    receipt = load("e3_receipt.json")
    tif = ROOT / receipt["raster"]["zeros"]["path"]
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tif, downloads / tif.name)
    return (
        '<div class="banner ok"><b>OK TO DOWNLOAD — HOLDOUT-SCREENED CANDIDATE.</b>'
        '<p>All literal gates passed. A separate selector must authorize a real competition slot.</p></div>'
        f'<a class="btn big" href="downloads/{esc(tif.name)}" download>Download submission TIFF</a>',
        tif,
    )


def build_index():
    ban, _tif = submission_banner()
    gate = load("e2_gate.json") or {}
    uniq = load("e3_uniqueness.json") or {}
    receipt = load("e3_receipt.json") or {}
    zeros_meta = receipt.get("raster", {}).get("zeros", {})
    nan_meta = receipt.get("raster", {}).get("nan", {})
    sub_name = receipt.get("submission_name", "h69k-kinematic-directional")
    sub_note = receipt.get("submission_note") or receipt.get("note") or "relay-ramp corridors"
    bn = gate.get("benchmark_20_21", {})
    c4 = gate.get("combined_4draw_summary", {})
    dotlike_ov = (uniq.get("worst_dot_overlap_dotlike") or {}).get("dot_overlap_3px", "n/a")
    loc_ov = ((uniq.get("local_prior_overlap") or {}).get("worst") or {}).get("dot_overlap_3px", "n/a")
    h33_ov = (uniq.get("vs_h33_champion") or {}).get("dot_overlap_3px", "n/a")

    body = f"""
{ban}
<div class="card" id="candidate-summary">
<h2>Archived Unique Candidate GeoTIFF (Audit &amp; Upstream Selector Review)</h2>
<table>
<tr><th>Field</th><th>Verified Value</th></tr>
<tr><td>Portal-ready file (all-finite float32 in [0, 1])</td><td><code>{esc(zeros_meta.get('path', 'n/a'))}</code> ({zeros_meta.get('bytes', 0):,} bytes; SHA-256 <code>{esc(zeros_meta.get('sha256', '')[:24])}&hellip;</code>)</td></tr>
<tr><td>Spec-literal diagnostic twin (NaN outside footprint ONLY &mdash; DO NOT UPLOAD)</td><td><code>{esc(nan_meta.get('path', 'n/a'))}</code> (SHA-256 <code>{esc(nan_meta.get('sha256', '')[:24])}&hellip;</code>)</td></tr>
<tr><td>Unique submission name</td><td><code>{esc(sub_name)}</code></td></tr>
<tr><td>Submission note ({len(sub_note)}/140 chars)</td><td><code>{esc(sub_note)}</code></td></tr>
<tr><td>Emitted unit dots / mapped-catalogue collisions</td><td><b>{receipt.get('n_dots', 0):,}</b> dots at <code>1.0</code> / <b>{receipt.get('catalogue_collision_px', 0)}</b> catalogue collisions (100% pixel-validated)</td></tr>
</table>
</div>
<div class="card" id="how-to-submit">
<h2>How to submit a cleared TIF to DrivenData (Executive Quick-Start)</h2>
<ol>
<li><b>Wait for green clearance or explicit upstream selector authorization:</b> only upload when the top banner states <code>OK TO DOWNLOAD</code> or the portfolio selector authorizes <code>{esc(sub_name)}</code> within the weekly submission cap.</li>
<li><b>Use ONLY the <code>-zeros.tif</code> file:</b> single-band <code>float32</code> GeoTIFF, <code>EPSG:32611</code>, <code>3730&times;3292</code>, 100&nbsp;m geotransform <code>(100, 0, 243350, 0, -100, 4508550)</code>, all 12,279,160 pixels finite in <code>[0.0, 1.0]</code>. This prevents the DrivenData portal error <i>&ldquo;Predicted values must be in range [0, 1]&rdquo;</i> triggered by NaN or negative sentinel cells.</li>
<li>On <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData Competition #306 &rarr; New submission</a>, choose <i>File to submit</i> = the <code>-zeros.tif</code> (or a <code>.zip</code> containing only that GeoTIFF) and paste the note (&le;140 chars):<br><code>{esc(sub_note)}</code></li>
</ol>
<p class="small">Full step-by-step walkthrough and byte-level diagnosis of the portal range error: see <a href="executive-summary.html">Executive Summary</a>.</p>
</div>
<div class="card">
<h2>Evidence at a glance — 2026-10-20 H69-K session</h2>
<table>
<tr><th>Measurement</th><th>Value</th><th>Evidence class &amp; provenance</th></tr>
<tr><td>Primary untouched holdout (<code>A_corridor</code> vs <code>B1_halo</code>, seeds 22 &amp; 23)</td>
<td><b>{gate.get('corridor_mean_dti', float('nan')):.4f}</b> vs {gate.get('control_mean_dti', float('nan')):.4f} (&Delta; {gate.get('paired_delta_mean', float('nan')):+.4f}; <b>7/8 folds won</b>, paired fold CI <code>[+0.0007, +0.0076]</code>)</td>
<td>HOLDOUT-DTI (<code>vendor/template66 gems57-pooled-hide-v2</code>, 8 untouched folds, {gate.get('withheld_positive_px_total', '?')} withheld positive px; intra-seed sub-block bootstrap <code>[-0.0007, +0.0072]</code>)</td></tr>
<tr><td>Historical same-fold benchmark (<code>A_corridor</code> vs <code>B1_halo</code>, seeds 20 &amp; 21)</td>
<td><b>{bn.get('pooled', {}).get('scores', {}).get('A_corridor', {}).get('dti', float('nan')):.4f}</b> vs {bn.get('pooled', {}).get('scores', {}).get('B1_halo', {}).get('dti', float('nan')):.4f} (&Delta; <b>{bn.get('paired_delta_vs_B1_halo', {}).get('delta', float('nan')):+.4f}</b>, CI <code>[{bn.get('paired_delta_vs_B1_halo', {}).get('ci95', [float('nan'), float('nan')])[0]:+.4f}, {bn.get('paired_delta_vs_B1_halo', {}).get('ci95', [float('nan'), float('nan')])[1]:+.4f}]</code>; <b>8/8 folds won</b>)</td>
<td>HOLDOUT-DTI (same evaluator &amp; seeds as prior family runs; beats checked-in prior best 0.0085 after fixing <code>IR-69-17</code> self-masking bug)</td></tr>
<tr><td>Combined 16-fold evaluation (seeds 22, 23, 20, 21)</td>
<td><b>{c4.get('corridor_pooled_dti', float('nan')):.4f}</b> vs {c4.get('control_pooled_dti', float('nan')):.4f} (<b>15/16 folds won</b>, sign-test <i>p</i>&nbsp;=&nbsp;0.00052, CI <code>[{c4.get('fold_delta_ci95', [float('nan'), float('nan')])[0]:+.4f}, {c4.get('fold_delta_ci95', [float('nan'), float('nan')])[1]:+.4f}]</code>)</td>
<td>HOLDOUT-DTI ({c4.get('withheld_positive_px_total', '?')} total withheld positive pixels)</td></tr>
<tr><td>Hard-linked ramp 300 m masking recovery / Dip validation</td>
<td><b>1.0000</b> (69 ramps) / <b>90.27%</b> (1,984 normal strands)</td>
<td>HOLDOUT-GEOMETRY (measured <code>qfault_attributes.csv</code> + 100 m DEM polarity)</td></tr>
<tr><td>Feature-alone leakage canaries (14 features on untouched draws)</td>
<td>max AUC = <b>{gate.get('worst_canary', {}).get('auc', float('nan')):.4f}</b> (&le; 0.90 limit; 0 flags)</td>
<td>LEAKAGE-CANARY (<code>evidence/e1_canaries.json</code>, SHA-256 bound)</td></tr>
<tr><td>Registry uniqueness across <b>{uniq.get('n_compared', '?')}</b> family rasters (862 pinned + 62 live refresh, 0 errors)</td>
<td>Surface |&rho;|&nbsp;=&nbsp;<b>{uniq.get('worst_abs_spearman_surface', 0):.4f}</b>; Dots |&rho;|&nbsp;=&nbsp;<b>{uniq.get('worst_abs_spearman', 0):.4f}</b>; Sparse &le;150k overlap&nbsp;=&nbsp;<b>{esc(dotlike_ov)}</b>; vs H33&nbsp;=&nbsp;<b>{esc(h33_ov)}</b>; vs prior GEMSDOE69&nbsp;=&nbsp;<b>{esc(loc_ov)}</b>; Literal all-registry overlap&nbsp;=&nbsp;<b>1.0000</b> (STOP)</td>
<td>REGISTRY-MEASUREMENT (0 byte/pixel matches; literal 1.0 certified due to 5,167,373-cell continuous surface <code>17GEMSDOE E-proba-multiscale</code>)</td></tr>
<tr><td>Family H33 score / User-cited leaderboard highs</td>
<td>H33: <b>0.2778</b>; User-cited highs: <b>0.3195</b>, <b>0.3774</b>, <b>0.4413</b>; Local 2026-10-12 snapshot #1: <b>0.4275</b></td>
<td>USER-REPORTED-NOT-ORGANIZER-CONFIRMED (prompt figures conflict; <code>drivendata.org</code> is outside sandbox outbound access so live board not re-fetched here)</td></tr>
</table>
</div>
<div class="card">
<h2>What this lane does</h2>
<p>Rather than classifying individual pixels directly, Lane 69 builds a <b>kinematics-resolved fault-tip graph</b> from mapped USGS/INGENIOUS Quaternary fault polylines (<code>trace_segments_utm11.csv</code> joined 1:1 with <code>qfault_attributes.csv</code> for recorded dip direction <code>DIPDIRECT</code> and slip sense <code>RL</code>/<code>LL</code>/<code>N</code>, plus validated DEM hanging-wall polarity). Across every geometrically admissible same-dip step-over (spacing <code>W &isin; [0.1, 15]</code>&nbsp;km, <code>|L| &le; 3.5W</code>), overlapping flank relay, and free-tip dextral/sinistral termination, the generator proposes structural corridors (oblique connectors, pull-apart rhomb sidewalls, cross-ramp breaches, en&nbsp;&eacute;chelon strands, and tensile horsetail splays), scores each corridor along its strike normal using upward-continued gravity and reduced-to-pole magnetic horizontal gradients (<code>|&nabla;F &middot; n&#770;|</code>), 3&nbsp;km magnetic alteration lows, and 1&nbsp;m 3DEP lidar scarps, calibrates out-of-fold empirical-Bayes truth probabilities, and selects nodes inside the top corridors via the shared template's greedy marginal-DTI allocator.</p>
</div>
"""
    return page("Home", "index.html", body)


def build_executive_summary():
    receipt = load("e3_receipt.json") or {}
    sub_name = receipt.get("submission_name", "h69k-kinematic-directional")
    sub_note = receipt.get("submission_note", "relay-ramp corridors")
    zeros_path = receipt.get("raster", {}).get("zeros", {}).get("path", "")
    zeros_sha = receipt.get("raster", {}).get("zeros", {}).get("sha256", "")
    body = f"""
<div class="card">
<h2>Executive Summary &mdash; Exactly How Submissions Are Built, Verified, and Entered</h2>
<ol>
<li><b>Step 1 &mdash; Check Gate Banner First:</b> Check the banner at the top of this page. Under the parallel-run protocol, a competition slot is precious (subject to DrivenData weekly submission caps). Right now the banner reads <b>NOT OK TO SUBMIT &mdash; DO NOT SUBMIT</b> solely because whole-footprint soft probability rasters in the historical family registry force the literal 3-px dot-overlap check to <code>1.0000</code> on every nonempty prediction. If the upstream selector formally authorizes sparse dot-field clearance (<code>0.6860 &le; 0.70</code>), proceed to Step 2 using the exact file below.</li>
<li><b>Step 2 &mdash; Verify the Exact GeoTIFF File Locally Before Upload:</b>
<ul>
<li><b>File to submit:</b> <code>{esc(zeros_path)}</code> (single-band <code>float32</code> GeoTIFF, <code>EPSG:32611</code>, <code>3730&times;3292</code>, <code>156,596</code> bytes)</li>
<li><b>Expected SHA-256:</b> <code>{esc(zeros_sha)}</code></li>
<li><b>Run local validator check:</b> <code>GEMS_DATA="$PWD/data/bridge" .venv/bin/python scripts/validate_submission.py {esc(zeros_path)}</code> (must print <code>PASS</code> with <code>nan=0</code>, <code>positives=54471</code>).</li>
</ul></li>
<li><b>Step 3 &mdash; Enter on DrivenData Competition #306:</b>
<ul>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS Prize &rarr; Submissions &rarr; New submission</a>.</li>
<li>Under <b>File to submit</b>, select <code>{esc(Path(zeros_path).name if zeros_path else sub_name + '.tif')}</code> (you may also zip that single GeoTIFF into a <code>.zip</code> archive).</li>
<li>Under <b>Note (optional)</b>, paste this exact identifier (&le;140 chars):<br><code>{esc(sub_note)}</code></li>
</ul></li>
</ol>
</div>
<div class="card">
<h2>Why You Saw &ldquo;Predicted values must be in range [0, 1]&rdquo; (Byte-Verified Root Causes)</h2>
<p>Inspecting every raster in the workspace byte-by-byte identifies three exact traps that trigger DrivenData's <code>Predicted values must be in range [0, 1]</code> portal rejection:</p>
<ol>
<li><b><code>-nan.tif</code> diagnostic twins contain <code>7,111,787</code> <code>NaN</code> pixels outside the GeoDAWN footprint:</b> any strict portal check evaluating <code>(arr &gt;= 0.0) &amp; (arr &lt;= 1.0)</code> returns <code>False</code> on IEEE-754 <code>NaN</code>!</li>
<li><b><code>labels.tif</code> and <code>existing_faults.tif</code> store <code>-1</code> outside the footprint</b> (signed integer nodata value <code>-1 &lt; 0</code>).</li>
<li><b><code>training_features.tif</code> stores <code>-3.4028235e+38</code></b> as float32 nodata sentinel.</li>
</ol>
<p><b>Permanent solution enforced here:</b> always submit ONLY the <b><code>-zeros.tif</code></b> output written by <code>vendor/template66/gems57/submission_writer.py</code>, which guarantees <code>0</code> NaNs, <code>0</code> Infs, <code>min = 0.0</code>, <code>max = 1.0</code> across all <code>12,279,160</code> cells ( confirmed by <code>h33-h33-2-b2-...-zeros.tif</code> acceptance on the portal).</p>
</div>
<div class="card">
<h2>Current Environment Limitations &amp; Required Upstream Actions</h2>
<ul>
<li><b>No DrivenData authentication in sandbox:</b> login-walled competition files cannot be pulled directly from <code>drivendata.org</code>; SHA-256-pinned public repository mirrors are restored and verified via <code>scripts/restore_data.py</code> and <code>scripts/fetch_data.py</code>.</li>
<li><b>Outbound host allowlist:</b> only GitHub, PyPI, and npm registries are reachable directly from this sandbox; external agency URLs (DrivenData, USGS, OpenEI GDR, Stanford Geothermal Workshop PDFs, NREL OSTI) are linked for manual verification without fabricating fresh live fetches.</li>
<li><b>Upstream selector ruling needed:</b> exclude continuous surfaces (<code>support_fraction &gt; 0.20</code>) from the 3-px sparse dot-overlap check in the shared template before any sparse lane can automatically flip <code>release_gate.py</code> to green.</li>
</ul>
</div>
"""
    return page("Executive Summary", "executive-summary.html", submission_banner()[0] + body)


def build_why_h33():
    body = """
<div class="card"><h2>PhD Forensic Analysis: Why H33 Achieved 0.2778 (User-Reported) &amp; How Unique Submissions Can Beat 0.2778 / 0.3195</h2>
<p><b>Evidence classification upfront:</b> <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> = <code>0.2778</code> is <b>USER-REPORTED-NOT-ORGANIZER-CONFIRMED</b> (no signed organizer submission receipt exists in git). Similarly, user-cited competition highs (<code>0.3195</code>, <code>0.3774</code>, <code>0.4413</code>) conflict across messages; our checked-in public snapshot (<code>registry/leaderboard_snapshot_2026-10-12.json</code>) recorded rank&nbsp;1 at <code>0.4275</code> and rank&nbsp;9 at <code>0.3195</code> on 2026-10-12. No figure below is a projected leaderboard score.</p>

<h3>1. Byte-level anatomy of the family progression (measured directly on registry rasters)</h3>
<table>
<tr><th>Submission Rung</th><th>Dots (<code>=1.0</code>)</th><th>Min dist to catalogue</th><th>Median dist</th><th>% within 300 m</th><th>User-reported score</th></tr>
<tr><td><code>h19-5</code> solid multiline</td><td>121,131</td><td>1.00 px (100 m)</td><td>1.46 km</td><td>19.95%</td><td>0.1922</td></tr>
<tr><td><code>h25-1</code> dotted <code>d=1.5</code></td><td>60,069</td><td>1.00 px (100 m)</td><td>1.49 km</td><td>19.87%</td><td>0.2477</td></tr>
<tr><td><code>d28</code> dotted <code>d=2.8</code></td><td>44,090</td><td>1.00 px (100 m)</td><td>1.50 km</td><td>19.52%</td><td>0.2600</td></tr>
<tr><td><code>h27-4-r1-solo</code></td><td>40,199</td><td>1.41 px (141 m)</td><td>1.77 km</td><td>11.73%</td><td>0.2708</td></tr>
<tr><td><b><code>h33-2-b2-zeros</code></b></td><td><b>37,654</b></td><td><b>2.24 px (224 m)</b></td><td><b>1.97 km</b></td><td><b>5.77%</b></td><td><b>0.2778</b></td></tr>
</table>

<h3>2. Exact Tversky kernel mathematics explaining the +0.0856 jump (0.1922 &rarr; 0.2778)</h3>
<ul>
<li><b>Mechanism A &mdash; Kernel non-redundancy (<code>121,131 &rarr; 44,090</code> dots, <code>+0.0678</code>):</b> under Distance-Weighted Tversky (<code>&alpha;=0.2, &beta;=0.8, R=300 m</code> triangular kernel), truth coverage takes the <i>pointwise maximum</i> <code>max_{p} k(d(g,p))</code>, NOT a sum, whereas false positives sum <code>0.2 &Sigma;(1 - m(p))</code> across every emitted pixel. A solid 1-px ribbon along a 10&nbsp;km lineament emits 300&ndash;500 pixels to cover truth pixels that 35 isolated dots spaced at <code>2.8 px</code> (<code>280 m</code>) already cover to &gt;80% peak weight &mdash; cutting false-positive mass by nearly 3&times; at minimal recall loss.</li>
<li><b>Mechanism B &mdash; Exact marginal acceptance bar &amp; 200 m flank pruning (<code>44,090 &rarr; 37,654</code> dots, <code>+0.0178</code>):</b> adding one dot with marginal uncovered truth credit <code>dT</code> and self-credit <code>m</code> improves DTI if and only if:<br>
<code>dT &gt; [&alpha; &middot; DTI / (1 - &alpha; &middot; DTI)] &middot; (1 - m)</code>.<br>
At <code>DTI = 0.2778</code>, <code>c = 0.0588</code>. Because mapped catalogue faults are masked out of evaluation and compilation digitization offsets rarely place genuinely unmapped independent structures at <code>100&ndash;200 m</code> parallel to already-mapped scarps, pruning the <code>6,436</code> flank dots at <code>1.0&ndash;2.0 px</code> removed pure false-positive denominator penalty.</li>
<li><b>Mechanism C &mdash; What blocked prior Lane-69 runs (<code>0.0059&ndash;0.0085</code> HOLDOUT-DTI):</b> we discovered two compounding bugs in prior GEMSDOE69 code: (1) uncalibrated <code>sigmoid(1.5*(S - 0.75))</code> yielded <code>p(x) &asymp; 0.5</code>, making kernel convolution <code>E[k] &asymp; 5.0 &ge; 1.0</code> so <code>1 - k_self == 0</code> and <code>greedy_allocate</code>'s marginal bar collapsed identically to <code>0.0</code>; and (2) <code>holdout69.py</code> computed <code>offcat</code> from <code>ctx.grid.catalogue</code> (including withheld truth!), gouging 200&nbsp;m holes directly around target faults (<code>IR-69-17</code>). Fixing both lifted our same-evaluator pooled HOLDOUT-DTI from <code>0.0085</code> to <b><code>0.1492</code></b>.</li>
</ul>

<h3>3. Can a genuinely unique submission surpass 0.2778 / 0.3195?</h3>
<p><b>Mathematically possible, not yet organizer-confirmed.</b> Thinning H33 alone has reached diminishing returns (and would violate our lane uniqueness rule). Raising DTI from <code>0.28</code> to <code>0.35+</code> at <code>~40k&ndash;55k</code> dots requires ~30% higher mean truth credit per dot on unmapped basin/step-over faults &mdash; i.e., combining structural-kinematic priors (where strain transfer <i>must</i> localize between fault tips, where H69-K has only <code>25.4%</code> 3-px overlap with H33!) with crisp multi-sensor physical localization. Only an authorized live submission receipt can test live leaderboard gain.</p>
</div>
"""
    return page("Why H33 Scored", "why-h33-scored.html", body)


def build_hypotheses():
    body = """
<div class="card"><h2>Five Ranked Lane-69 Geological Hypotheses (Pre-Registered &amp; Obtainability-Checked)</h2>
<p>All five hypotheses stay strictly inside the GEMSDOE69 catalogue-geometry lane (proposing faults from the fault-tip graph rather than raw pixel classification) and use <b>100% free, public-domain USGS / DOE GDR datasets already restored and SHA-256 verified on disk</b> (zero unobtainable external data dependencies). Only top-ranked <b>H69-K</b> consumed session experiments (3 total runs within the 3-experiment budget).</p>
<table>
<tr><th>Rank &amp; ID</th><th>Specific Verified Layers</th><th>Physical Signature Targeted</th><th>Why Hidden vs Mapped Catalogue &amp; Non-Fault Mimic</th><th>Status &amp; Expected Gain / Cost</th></tr>
<tr><td><b>Rank 1 &cdot; H69-K</b><br>(Implemented &amp; Validated)</td>
<td><code>trace_segments_utm11.csv</code>, <code>qfault_attributes.csv</code>, <code>geodawn_dem_a2_100m.tif</code>; <code>iso_grav_anom</code> (b13), <code>rtp</code> (b2), upward-continued THDR/tilt; <code>lidar_scarp_features_u8.tif</code> (<code>ex_max</code>, <code>step_max</code>, <code>downface_max</code>)</td>
<td>Measured <code>DIPDIRECT</code> + <code>RL</code>/<code>LL</code> releasing kinematics; pull-apart rhomb sidewalls + oblique breaches + flank relays + tensile horsetail splays; strike-normal gradient projection <code>|&nabla;F &middot; n&#770;|</code> + convergent <code>min(grav_perp, mag_perp)</code>; 3-level empirical-Bayes calibration.</td>
<td>Catches sub-alluvial relay connectors, unbreached sidewall extensions, and horsetail splays missed by 1:100k surface mapping while rejecting range-front gradients perpendicular to corridors. <i>Mimic:</i> strike-aligned pluton walls or pluvial shorelines.</td>
<td><b>TESTED:</b> Pooled HOLDOUT-DTI <b>0.1439</b> vs 0.1406 untouched (7/8 folds); <b>0.1492</b> vs 0.1421 benchmark (8/8 folds); 15/16 total folds won (<i>p</i>=0.00052). Low cost.</td></tr>
<tr><td><b>Rank 2 &cdot; H69-L</b><br>(Queued)</td>
<td><code>rtp</code> (b2), <code>iso_grav_anom</code> (b13), <code>TMI_up150</code> (<code>geodawn_extensions_u8.tif</code> b4), <code>depth_to_base_surf</code> (b15)</td>
<td>Upward-continuation depth-persistence ratio <code>THDR_1800m / (THDR_200m + &tau;)</code> along step-over connectors normalized by basin fill thickness.</td>
<td>Separates deep basement-cutting geothermal conduits (&gt;1.5 km throw) from noisy shallow Quaternary lava lobe edges that mask faults at surface. <i>Mimic:</i> steep non-faulted Mesozoic pluton contacts under alluvium.</td>
<td>Untested (not slot-eligible). Medium expected lift / Low cost.</td></tr>
<tr><td><b>Rank 3 &cdot; H69-M</b><br>(Queued)</td>
<td><code>geodawn_rad_u8.tif</code> (<code>K</code> b1, <code>Th</code> b2, <code>U</code> b3), <code>geodawn_extensions_u8.tif</code> (<code>ThK</code> b1), <code>rtp</code> (b2)</td>
<td>Paired bilateral contrast <code>&Delta;<sub>core - wallrock</sub></code> comparing corridor core (<code>d &le; 2 px</code>) directly against its immediate host flanks (<code>4 &le; d &le; 10 px</code>) in RTP demagnetization and <code>Th/K</code> ratio.</td>
<td>Removes regional felsic-vs-mafic lithologic variance that confounded prior global z-score radiometric tests (H69-D/G), isolating local hydrothermal clay/silica alteration along blind fault cores. <i>Mimic:</i> axial fluvial channel sorting.</td>
<td>Untested (not slot-eligible). Medium expected lift / Low-medium cost.</td></tr>
<tr><td><b>Rank 4 &cdot; H69-N</b><br>(Queued)</td>
<td><code>det_elev</code> (b12), <code>det_elev_slope</code> (b19), <code>lidar_scarp_features_u8.tif</code> (<code>lapneg_max</code> b4, <code>lappos_max</code> b5)</td>
<td>Longitudinal ramp tilt gradient along synthetic normal overlap paired with transverse Laplacian inflection maxima marking incipient ramp-breaching scarps.</td>
<td>Detects distributed flexural warps and sub-metre breaching scarps in soft-to-hard transition ramps overlooked by regional compilers. <i>Mimic:</i> coalescing alluvial fan bajadas.</td>
<td>Untested (not slot-eligible). Low-medium expected lift / Medium cost.</td></tr>
<tr><td><b>Rank 5 &cdot; H69-O</b><br>(Queued)</td>
<td><code>geod_shearrate</code> (b7), <code>geod_dilaterate</code> (b8), <code>geod_2ndinv</code> (b4), <code>deq_n100a15</code> (b10), <code>ieq_n100a15</code> (b16)</td>
<td>Couples corridor slip-dilation tendency to local GPS/InSAR strain-rate tensor magnitude and microseismic proximity inside active Walker Lane shear belts.</td>
<td>Highlights aseismically creeping or microseismically active blind transfer zones lacking large Holocene surface ruptures. <i>Mimic:</i> coarse GPS station interpolation lobes.</td>
<td>Untested (not slot-eligible). Low expected lift / Low cost.</td></tr>
</table>
</div>
"""
    return page("Hypotheses", "hypotheses.html", body)


def build_method():
    body = """
<div class="card">
<h2>H69-K Method Architecture (Verified Line-by-Line in <code>src/gems69/</code>)</h2>
<h3>1. Polyline Tip Graph &amp; Measured Kinematic Polarity (<code>traces.py</code>, <code>corridors.py</code>)</h3>
<ul>
<li>Loads 84,331 UTM Zone 11N segments from <code>external/trace_segments_utm11.csv</code> grouped into 13,953 continuous fault parts and joined 1:1 to <code>external/qfault_attributes.csv</code> (recorded <code>DIPDIRECT</code> and slip sense <code>RL</code>, <code>LL</code>, <code>N</code>).</li>
<li>Where <code>DIPDIRECT</code> is unrecorded, infers hanging-wall polarity as the topographically lower side across 600&nbsp;m and 1.2&nbsp;km normal offsets on <code>geodawn_dem_a2_100m.tif</code> &mdash; validated against 1,984 recorded normal-fault strands at <b>90.27% agreement</b>.</li>
<li>In every holdout fold, polylines are split strictly against the buffered visible mask (300&nbsp;m collar around withheld components) so zero hidden-fault geometry or attribute leaks into tip detection.</li>
<li>Admissible step-overs enforce: sub-parallel terminal strikes (&le;35&deg;), compatible dip polarity (<code>dip_a &middot; dip_b &ge; 0</code>), spacing <code>W &isin; [0.1, 15.0]</code>&nbsp;km, <code>|L| &le; 3.5W</code>, and releasing strike-slip step sense (<code>RL</code> right step, <code>LL</code> left step).</li>
<li>Emits: <code>relay_connector</code>, <code>relay_sidewall</code> (soft-linked rhomb margins), <code>relay_breach</code>, staggered <code>relay_enechelon</code> strands, overlapping <code>flank_relay</code> + <code>flank_breach</code> strands, and free-tip tensile horsetail <code>termination_splay</code> / <code>wing_splay</code> / <code>transfer_link</code> structures.</li>
</ul>
<h3>2. Strike-Normal Potential-Field &amp; Scarp Scoring (<code>evidence.py</code>, <code>corridors.py</code>)</h3>
<p>Pre-registered weights summing to 1.00 (<code>registry/preregistration-2026-10-20-h69k.json</code>):<br>
<code>S = 0.22&middot;grav_perp + 0.20&middot;mag_perp + 0.16&middot;min(grav_perp, mag_perp) + 0.14&middot;mag_low + 0.14&middot;scarp + 0.08&middot;cos&sup2;(&theta; - 22.5&deg;) + 0.06&middot;W_kinematic</code>,<br>
where <code>grav_perp</code> and <code>mag_perp</code> combine upward-continued (200/600/1800&nbsp;m) THDR&times;tilt zero-crossing edges with <code>|&nabla;F<sub>300m</sub> &middot; n&#770;<sub>corridor</sub>|</code> normal projection.</p>
<h3>3. Out-of-Fold Empirical-Bayes Calibration &amp; Greedy Marginal-DTI Selection (<code>calibrate.py</code>, <code>pipeline.py</code>)</h3>
<p>Three-level hierarchical shrinkage estimates <code>P(truth | d_vis, d_line, d_tip, s_band)</code> strictly on training quadrants, preventing the uncalibrated <code>k_self = 1</code> saturation failure. Live emission selects top corridors (<code>score &ge; p72</code>, 34,518 corridors covering 15.34% of footprint) and allocates <b>54,471 unit dots</b> via <code>gems57.emit.emit_decimated(tile_px=3)</code> + <code>gems57.emit.greedy_allocate</code>. All per-corridor geologist rationales are archived in <code>evidence/e3_corridor_rationale.csv</code>.</p>
</div>
"""
    return page("Method", "method.html", body)


def build_results():
    gate = load("e2_gate.json") or {}
    rec = load("e1_hardlinked_recovery.json") or {}
    uniq = load("e3_uniqueness.json") or {}
    receipt = load("e3_receipt.json") or {}

    fold_rows = ""
    for group_label, detail in (
        ("Untouched primary", gate.get("untouched_draws_detail", {})),
        ("Historical benchmark", gate.get("benchmark_20_21", {}).get("draws_detail", {})),
    ):
        for skey in sorted(detail):
            a_f = detail[skey]["arms"]["A_corridor"]["folds"]
            b_f = detail[skey]["arms"]["B1_halo"]["folds"]
            r_f = detail[skey]["arms"]["R_corridor_random"]["folds"]
            for ra, rb, rr in zip(a_f, b_f, r_f):
                delta = ra["dti"] - rb["dti"]
                fold_rows += (
                    f"<tr><td>{esc(group_label)}</td><td>{esc(skey)}_{esc(ra['fold'])}</td>"
                    f"<td><b>{ra['dti']:.4f}</b> ({ra['n_dots']:,})</td>"
                    f"<td>{rb['dti']:.4f} ({rb['n_dots']:,})</td>"
                    f"<td>{rr['dti']:.4f}</td>"
                    f"<td><b>{delta:+.4f}</b></td></tr>"
                )

    top_rows = ""
    for r in (receipt.get("top_corridors") or [])[:15]:
        top_rows += (
            f"<tr><td>{r.get('corridor_id')}</td><td>{esc(r.get('setting'))}/{esc(r.get('kind'))}</td>"
            f"<td>{r.get('n_dots')}</td><td>{r.get('score_S'):.4f}</td>"
            f"<td>{esc(r.get('sense'))} ({esc(r.get('dip_source'))})</td>"
            f"<td>{esc(r.get('signature'))}</td></tr>"
        )

    body = f"""
<div class="card"><h2>E1 &mdash; Dip Validation, Hard-Link Masking Recovery, and Leakage Canaries</h2>
<table>
<tr><th>Check</th><th>Measured Result</th></tr>
<tr><td>INGENIOUS polylines loaded / recorded dip / DEM-inferred dip</td><td>13,953 parts / 3,552 recorded / 3,287 inferred (<b>90.27%</b> agreement on 1,984 recorded normal strands)</td></tr>
<tr><td>Hard-linked ramps tested (known linking fault masked)</td><td><b>{rec.get('n_tested', '?')}</b> admissible ramps; mean 300 m recall = <b>{rec.get('mean_recovery_within_300m', float('nan')):.4f}</b> vs random-azimuth null {rec.get('mean_null_recall_300m', float('nan')):.4f}</td></tr>
<tr><td>Single-feature &amp; OOF-posterior leakage canaries (14 features)</td><td>Worst AUC = <b>{gate.get('worst_canary', {}).get('auc', float('nan')):.4f}</b> (<code>{esc(gate.get('worst_canary', {}).get('feature'))}</code>) &le; 0.90 &mdash; <b>PASS (0 flags)</b></td></tr>
</table>
</div>
<div class="card"><h2>E2 &mdash; Controlled Holdout Gate Across All 16 Spatial Folds (<code>HOLDOUT-DTI</code>)</h2>
<table>
<tr><th>Split Group</th><th>Cell</th><th><code>A_corridor</code> DTI (dots)</th><th><code>B1_halo</code> No-Prior Control (dots)</th><th><code>R_corridor_random</code></th><th>Paired &Delta;</th></tr>
{fold_rows}
</table>
<p class="small">Evaluator: byte-pinned <code>vendor/template66 gems57-pooled-hide-v2</code> (&alpha;=0.2, &beta;=0.8, 300&nbsp;m triangular kernel). <code>A_corridor</code> wins <b>7/8</b> untouched folds and <b>8/8</b> benchmark folds (<b>15/16 total, sign-test p=0.00052</b>).</p>
</div>
<div class="card"><h2>E3 &mdash; Live Candidate Emission, 924-Raster Uniqueness Scan &amp; Top Geologist Rationales</h2>
<table>
<tr><th>Audit Metric</th><th>Measured Value</th></tr>
<tr><td>Candidate file &amp; SHA-256</td><td><code>{esc(receipt.get('raster', {}).get('zeros', {}).get('path'))}</code> (<code>{esc(receipt.get('raster', {}).get('zeros', {}).get('sha256'))}</code>)</td></tr>
<tr><td>Emitted unit dots / corridors with dots</td><td><b>{receipt.get('n_dots', 0):,}</b> dots across <b>{receipt.get('n_corridors_with_dots', 0):,}</b> corridors (min catalogue dist {receipt.get('distance_to_catalogue_px', {}).get('min', 0):.2f} px, median {receipt.get('distance_to_catalogue_px', {}).get('median', 0):.2f} px)</td></tr>
<tr><td>Format &amp; template validator (both variants)</td><td><b>PASS</b> (<code>all_files_passed = {esc(receipt.get('validator', {}).get('all_files_passed'))}</code>)</td></tr>
<tr><td>Registry scan scope &amp; errors</td><td><b>{uniq.get('n_compared', '?')} / {uniq.get('n_registry_blobs', '?')}</b> unique grid rasters (<b>0 errors</b>; 0 byte/pixel matches)</td></tr>
<tr><td>Pre-placement surface |Spearman| / Final dots |Spearman|</td><td><b>{uniq.get('worst_abs_spearman_surface', 0):.4f}</b> / <b>{uniq.get('worst_abs_spearman', 0):.4f}</b> (limit &le; 0.90 &mdash; PASS)</td></tr>
<tr><td>Sparse dot-field 3-px overlap (&le;150k &amp; &le;80k) / Local prior overlap</td><td><b>{esc((uniq.get('worst_dot_overlap_dotlike') or {}).get('dot_overlap_3px'))}</b> / <b>{esc(((uniq.get('local_prior_overlap') or {}).get('worst') or {}).get('dot_overlap_3px'))}</b> (limit &le; 0.70 &mdash; PASS)</td></tr>
<tr><td>Literal all-registry 3-px overlap</td><td><b>1.0000</b> against <code>17GEMSDOE E-proba-multiscale</code> (5,167,373 positive cells) &rarr; <b>FAIL-CLOSED STOP</b></td></tr>
</table>
<h3>Top 15 Emitted Corridors (Full Table in <code>evidence/e3_corridor_rationale.csv</code>)</h3>
<table>
<tr><th>ID</th><th>Type</th><th>Dots</th><th>Score S</th><th>Kinematics</th><th>Geophysical Signature</th></tr>
{top_rows}
</table>
</div>
"""
    return page("Experiments", "results.html", body)


def build_sources():
    body = """
<div class="card">
<h2>Auditable Data &amp; Literature Verification Table</h2>
<p>Outbound access in this sandbox is restricted to GitHub, PyPI, and npm hosts. Every local dataset SHA-256 below was verified directly on disk in this session; non-GitHub agency URLs are provided for manual review without claiming fresh live HTTP retrieval.</p>
<table>
<tr><th>Resource / Dataset</th><th>Official Source Link</th><th>Session Verification &amp; SHA-256</th></tr>
<tr><td>DOE GEMS Competition Overview &amp; Problem Spec</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">drivendata.org/.../page/967/</a></td><td>Manual-review URL (metric &alpha;=0.2, &beta;=0.8, R=300 m matches byte-pinned reference code)</td></tr>
<tr><td>DOE GEMS About &amp; Data Tabs</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">page/968</a> &middot; <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data/</a></td><td>Login-walled; unauthenticated here; owner mirrors pinned below</td></tr>
<tr><td>DOE GEMS Public Leaderboard</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">drivendata.org/.../leaderboard/</a></td><td>Archived snapshot <code>registry/leaderboard_snapshot_2026-10-12.json</code>; user-cited values labelled unconfirmed</td></tr>
<tr><td>Official Reference Solution Repository</td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a></td><td>Verified via GitHub API (commit <code>aebe92f7...</code>)</td></tr>
<tr><td>Competition Submission Specification PDF</td><td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov/docs/fy26osti/96647.pdf</a></td><td>Manual-review URL</td></tr>
<tr><td>USGS GeoDAWN Airborne Magnetic &amp; Radiometric Survey</td><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">usgs.gov GeoDAWN release</a></td><td>19-band stack verified: <code>training_features.tif</code> SHA-256 <code>4371c82e3b8339b8...</code>; <code>geodawn_rad_u8.tif</code> <code>c22420f75999030d...</code></td></tr>
<tr><td>GBCGE INGENIOUS Great Basin Geothermal Dataset</td><td><a href="https://gbcge.org/current-projects/ingenious/">gbcge.org/current-projects/ingenious/</a> &middot; <a href="https://gdr.openei.org/submissions/1391">GDR #1391</a></td><td>Polylines &amp; fault attributes verified: <code>trace_segments_utm11.csv</code> <code>c5edf9df3e0e1413...</code>; <code>qfault_attributes.csv</code> <code>3b8745f0086a57b8...</code></td></tr>
<tr><td>USGS 3DEP 1 m LiDAR Scarp Composite</td><td><a href="https://www.usgs.gov/3d-elevation-program">usgs.gov/3d-elevation-program</a></td><td>12-band derived scarp raster verified: <code>lidar_scarp_features_u8.tif</code> SHA-256 <code>d580bb8bdcdb941e...</code></td></tr>
<tr><td>Coordinate Reference System &amp; Metric Theory</td><td><a href="https://epsg.io/32611">epsg.io/32611</a> &middot; <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></td><td>Verified against <code>sample_submission.tif</code> SHA-256 <code>2176d08e485aa2cd...</code></td></tr>
<tr><td>Step-Over Structural Priors</td><td>Giddens &amp; Faulds (2025, SGP-TR-229)</td><td>Used strictly as cited in standing prompt (widths 0.1&ndash;14.6 km, aspect 3&ndash;3.5&times;, ~70% hard-linked)</td></tr>
</table>
</div>
"""
    return page("Sources", "sources.html", body)


def build_irregularities():
    body = """
<div class="card">
<h2>Irregularities Flagged &amp; Resolved for Review</h2>
<table><tr><th>ID</th><th>Finding</th><th>Disposition</th></tr>
<tr><td>IR-69-17 (RESOLVED)</td><td><code>src/gems69/holdout69.py</code> previously computed <code>offcat = edt(~ctx.grid.catalogue) &gt; 2</code> and ran <code>leakage_canary</code> on <code>ctx.grid.catalogue</code> (containing hidden target faults), carving 200&nbsp;m holes around withheld target faults and depressing HOLDOUT-DTI ~15&times;.</td><td>Fixed in <code>src/gems69/holdout69.py</code> to use strictly per-cell <code>ctx.visible(key)</code> and covered by regression tests in <code>tests/test_h69k_pipeline.py</code>.</td></tr>
<tr><td>IR-69-CALIB-01 (RESOLVED)</td><td>Uncalibrated <code>sigmoid(1.5*(S - 0.75))</code> gave <code>p &asymp; 0.5</code>, saturating kernel sum <code>E[k] &ge; 1.0</code> so <code>1 - k_self = 0</code> collapsed <code>greedy_allocate</code>'s marginal threshold to zero.</td><td>Resolved via 3-level out-of-fold empirical-Bayes posterior calibration in <code>calibrate.py</code> + <code>pipeline.py</code>.</td></tr>
<tr><td>IR-69-DATA-01</td><td><code>existing_faults.tif</code> is byte-identical to <code>labels.tif</code> (SHA-256 <code>7ba308cc...</code>) in all family mirrors; scored hidden organizer truth is unpublished.</td><td>Whole-component buffered LOQO hide-and-recover holdout used exclusively for model screening.</td></tr>
<tr><td>IR-69-DATA-02</td><td>No DrivenData auth in sandbox: files come from SHA-256-pinned owner mirrors rather than live organizer downloads.</td><td>Every file hash verified fail-closed before execution.</td></tr>
<tr><td>IR-69-REG-01</td><td>Whole-footprint continuous probability surfaces in the family registry (<code>17GEMSDOE E-proba-multiscale</code>: 5,167,373/5,167,373 footprint pixels &gt;0) cause literal 3-px dot overlap to equal <code>1.0000</code> for every nonempty prediction.</td><td>Reported literally in <code>evidence/e3_uniqueness.json</code> with mathematical saturation certificate (<code>evidence/e3_saturation_certificate.json</code>); <code>release_gate.py</code> kept fail-closed (<code>negative</code>).</td></tr>
<tr><td>IR-69-SCORE-01</td><td>Prompt leaderboard highs (<code>0.3195</code>, <code>0.3774</code>, <code>0.4413</code>) conflict and <code>0.2778</code> has no organizer file receipt in git.</td><td>Explicitly labelled <code>USER-REPORTED-NOT-ORGANIZER-CONFIRMED</code> throughout all reports and pages.</td></tr>
</table>
</div>
"""
    return page("Irregularities", "irregularities.html", body)


def build_run_card():
    card = load("run_card.json")
    if not card:
        body = '<div class="card"><p>Run card pending.</p></div>'
    else:
        body = f'<div class="card"><h2>Run card (JSON)</h2><pre>{esc(json.dumps(card, indent=2))}</pre></div>'
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
    (ROOT / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0;url=docs/index.html">'
        '<title>GEMSDOE69 submission status</title></head><body>'
        + submission_banner()[0].replace('href="downloads/', 'href="docs/downloads/')
        + '<p><a href="docs/index.html">Open project site</a></p></body></html>'
    )
    (DOCS / "run-card.json").write_text(json.dumps(load("run_card.json"), indent=2) + "\n")
    from release_gate import evaluate
    (DOCS / "status.json").write_text(json.dumps(evaluate(ROOT), indent=2) + "\n")
    for name, html_text in pages.items():
        (DOCS / name).write_text(html_text)
    print("built", len(pages), "pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
