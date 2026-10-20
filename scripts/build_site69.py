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
    ("why-h33-scored.html", "H33 Source Audit"),
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
                '<p><b>No TIFF or ZIP is published for submission.</b> Do not upload an audit artifact '
                'from <code>submissions/</code>. The literal duplicate-and-stop policy is controlling, '
                'and no competition slot was used.</p><ul>' + reasons + '</ul></div>', None)
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
        rows += f"""<tr><td>Archived corridor mean DTI</td><td>{gate.get('corridor_mean_dti', float('nan')):.4f} &plusmn; {gate.get('corridor_ci95_half', float('nan')):.4f}</td><td>ARCHIVED HOLDOUT-DTI (gems57 pooled hide-and-recover, {gate.get('n_cells','?')} cells, {gate.get('withheld_positive_px_total','?')} withheld positives; not bound to the current artifact)</td></tr>
<tr><td>Archived no-prior control arm</td><td>{gate.get('control_mean_dti', float('nan')):.4f} &plusmn; {gate.get('control_ci95_half', float('nan')):.4f}</td><td>ARCHIVED HOLDOUT-DTI, same historical folds</td></tr>
<tr><td>Archived paired &Delta; (corridor &minus; control)</td><td>{gate.get('paired_delta_mean', float('nan')):+.4f} &plusmn; {gate.get('paired_delta_ci95_half', float('nan')):.4f}</td><td>ARCHIVED HOLDOUT-DTI</td></tr>"""
    if tif is None:
        workflow = """
<div class="card" id="how-to-submit">
<h2>Submission workflow is locked</h2>
<p><b>There is no file to download or submit from this page.</b> The prominent red banner is the release decision. Do not substitute any file from <code>submissions/</code>, rename an archived TIFF, or upload a diagnostic twin.</p>
<p>When and only when a future banner says <b>OK TO DOWNLOAD</b>, it will publish the exact hash-bound artifact and its note. The [Executive Summary](executive-summary.html) explains the required checks and the portal workflow without authorizing the current artifacts.</p>
</div>
"""
    else:
        workflow = f"""
<div class="card" id="how-to-submit">
<h2>How to submit the cleared TIF</h2>
<ol>
<li>Download only the artifact linked by the green banner above. Its exact bytes, grid, and value range were checked by the release gate.</li>
<li>Go to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition 306 &rarr; New submission</a> and choose <i>File to submit</i> = that <code>.tif</code> (or a <code>.zip</code> containing exactly one GeoTIFF).</li>
<li>Paste this receipt note (&le;140 chars):<br><code>{esc(receipt.get('note', 'relay-ramp corridors'))}</code></li>
</ol>
<p class="small">Format contract: single-band GeoTIFF, float32, EPSG:32611, 3730&times;3292, transform (100, 0, 243350, 0, &minus;100, 4508550), values in [0,1]. A release banner is still not an organizer score or submission authorization.</p>
</div>
"""
    body = f"""
{ban}
{workflow}
<div class="card">
<h2>Evidence at a glance — archived measurements, not release clearance</h2>
<table>
<tr><th>Measurement</th><th>Value</th><th>Evidence class</th></tr>
{rows}
<tr><td>Archived registry scan: worst surface |Spearman| / dot-like dot overlap</td>
<td>{abs(uniq.get('worst_abs_spearman', 0) or 0):.3f} / {(uniq.get('worst_dot_overlap_dotlike') or {}).get('dot_overlap_3px', 'n/a')}</td>
<td>REGISTRY-MEASUREMENT; the literal all-registry overlap check is false and controls publication</td></tr>
<tr><td>H33-2-B2 owner audit</td><td>UNSCORED; owner projection 0.2747</td><td>OWNER-REPORTED, NOT ORGANIZER-CONFIRMED; current owner audit contains no organizer receipt for these bytes. The user-supplied 0.2778 is not attributed to this file here.</td></tr>
<tr><td>User-cited leaderboard figures</td><td>not refreshed in this review</td><td>USER-REPORTED-NOT-ORGANIZER-CONFIRMED unless copied from an organizer receipt</td></tr>
<tr><td>Transfer-only candidate</td><td>no organizer score &mdash; no slot spent</td><td>ARCHIVED HOLDOUT-DTI pooled 0.008470 vs control 0.002154; literal registry gate failed, so it is not downloadable</td></tr>
</table>
<p class="small">A holdout DTI is a <b>screen</b>, never a leaderboard projection. Read the H33 source audit before treating owner-reported values as competition results.</p>
</div>
<div class="card">
<h2>What this lane is</h2>
<p>Hidden faults are proposed from <b>catalogue geometry</b>, not pixel statistics: the tips of mapped
fault strands form a graph; step-over tip pairs (spacing 0.1&ndash;15 km, along-strike separation &le; 3.5W,
sub-parallel strikes) emit <b>relay-ramp corridors</b> &mdash; an oblique connector plus en&nbsp;&eacute;chelon strands
&mdash; and, at dilatational steps under the Walker-Lane dextral prior, <b>pull-apart rhombs</b>. Corridors are
scored by multi-scale horizontal-gradient and tilt evidence in gravity and magnetics (including magnetic
lows), the 1&nbsp;m lidar-scarp channel, and orientation consistency with WNW extension. Dots are placed by
greedy marginal-DTI selection inside the top corridors (pre-registered propensity map
S<sub>0</sub>=0.75; template allocator), &ge;200&nbsp;m from the mapped catalogue.</p>
<p>Geometry priors as cited in the standing prompt: Giddens &amp; Faulds (2025, SGP-TR-229) inventoried
&gt;450 step-overs; ramps are typically 3&ndash;3.5&times; longer than wide (widths 0.1&ndash;14.6 km, mean 2.8 km);
~70% of higher-temperature step-overs are hard-linked; in the Walker Lane, hot systems sit more often in
pull-aparts and displacement-transfer zones; N&ndash;NE faults are best oriented for dilation under WNW extension.</p>
</div>
"""
    return page("Home", "index.html", body)


def build_executive_summary():
    banner, tif = submission_banner()
    current = (
        "A file is currently cleared and linked above; use only that exact linked artifact."
        if tif is not None
        else "<b>No file is currently cleared.</b> Do not upload a TIFF from <code>submissions/</code>; those files are retained only for audit."
    )
    body = f"""
<div class="card">
<h2>Executive summary &mdash; release decision first</h2>
<p>{current} The home-page banner is generated by <code>scripts/release_gate.py</code>; it is the sole publication policy.</p>
<h3>Required sequence before a future submission</h3>
<ol>
<li><b>Preregister and generate:</b> restore the exact integrity-pinned inputs and use the shared template's cached feature stack, holdout evaluator, and submission writer. A TIFF written during development is not automatically publishable.</li>
<li><b>Validate exact bytes:</b> re-read the artifact with the shared validator. It must be a single-band float32 GeoTIFF in EPSG:32611, 3730&times;3292, with transform (100, 0, 243350, 0, &minus;100, 4508550), finite footprint values in [0,1], and the required outside-footprint behavior.</li>
<li><b>Science gate:</b> on untouched spatially blocked hide-and-recover data, beat the identical no-corridor-prior pipeline; bind the holdout receipt to the artifact SHA-256; run a feature-alone leakage canary for every named feature.</li>
<li><b>Literal registry gate:</b> compare the pre-placement surface and final dots against every available registry raster. Any rank correlation above 0.90 or any &gt;70% 3-pixel dot overlap is duplicate-and-stop. Dense-support strata are diagnostics, not exemptions.</li>
<li><b>Publish and submit:</b> only if the banner becomes green, download the exact linked <code>.tif</code>, open DrivenData competition 306 &rarr; <i>New submission</i>, select it (or a ZIP with exactly one GeoTIFF), and paste the receipt note of at most 140 characters. A selector still decides whether to spend a weekly slot.</li>
</ol>
<h3>About the portal range error</h3>
<p>The reported &ldquo;Predicted values must be in range [0, 1]&rdquo; error is consistent with uploading a wrong file, a nodata/sentinel field, or NaNs that the portal treats as invalid. Do not infer that a filename suffix alone makes a file safe. Re-run <code>scripts/validate_submission.py &lt;file&gt;</code> on the exact bytes and upload only the artifact explicitly linked by an <b>OK TO DOWNLOAD</b> banner.</p>
</div>
<div class="card">
<h2>Standing limitations</h2>
<ul>
<li>No DrivenData authentication is available in this environment. Competition mirrors are integrity-pinned owner mirrors, not organizer-authenticated downloads; no organizer receipt is available here.</li>
<li>The local bridge data support format auditing, not a fresh full-feature scientific rerun. The hidden competition truth remains unavailable.</li>
<li>Holdout DTI is a screening measurement, not a leaderboard projection. Only an organizer submission-page receipt can establish an organizer score.</li>
<li>The current literal all-registry overlap policy is intentionally fail-closed and may make sparse-dot publication impossible while universal-support registry surfaces remain in scope. It must be resolved by the protocol owner, not relaxed locally.</li>
</ul>
</div>
"""
    return page("Executive Summary", "executive-summary.html", banner + body)


def build_why_h33():
    body = """
<div class="card"><h2>H33 source audit: the reported 0.2778 cannot be verified for these bytes</h2>
<p>The user's premise associates <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> with 0.2778. A direct GitHub API audit of the current owner repository on 2026-10-20 found a conflict: the owner&apos;s audit JSON and page label this exact file <b>UNSCORED</b>, call 0.2747 a <b>projection</b>, and identify a 0.2708 anchor as an already-scored fallback. Its submissions manifest contains no organizer receipt for H33-2-B2. Therefore 0.2778 is <b>USER-REPORTED-NOT-ORGANIZER-CONFIRMED</b> and cannot be called a score of these bytes here.</p>
<p>Measured locally from the fetched registry blob (evidence/relayfix_champion_anatomy.json): SHA-256 <code>c55bafc4&hellip;</code>, 37,654 unit-valued dots, zero dots on the mirrored catalogue, minimum catalogue distance 2.24 pixels, median distance 1.96 km, and 5.8% within 300 m. The owner describes the construction as removal of dots at catalogue distance &le;2 pixels from a pre-existing field. This is a removal/thinning operation, not evidence that a new H33 geology surface was responsible for an organizer result.</p>
<p><b>What could make that operation look good in a distance-weighted Tversky metric?</b> If removed dots supplied little unique distance-kernel coverage of hidden faults, removal reduces false-positive mass while retaining coverage from other dots. That is a metric-alignment mechanism, not proof: removal can also discard useful hidden-fault coverage, and the organizer truth is unavailable. It does not establish geothermal vent discovery.</p>
<p><b>Can this lane beat any cited H33 value?</b> Not established. Reusing H33 dots or its catalogue-flank thinning rule would violate this lane&apos;s novelty and duplicate checks. The current relay/pull-apart artifacts are negative under the literal registry gate, and no organizer slot was spent.</p>
<p>Manual review: <a href="https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json">owner H33 audit JSON</a>, <a href="https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html">owner H33 page source</a>, <a href="https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/submissions_manifest.json">owner submissions manifest</a>, and <a href="https://github.com/drivendataorg/gems-prize-reference-solution">organizer reference repository</a>. These owner materials are useful for provenance and learning, not organizer receipts.</p></div>
"""
    return page("H33 evidence review", "why-h33-scored.html", body)


def build_hypotheses():
    body = """
<div class="card"><h2>Ranked in-lane hypotheses &mdash; queued, not slot-eligible</h2>
<p>The four candidates below were registered before any future implementation. They remain <b>untested in this review</b> because the literal duplicate-and-stop condition already fired. Historical experiments are documented in the relay-fix report, but no historical holdout is treated as a current promotion. For every future experiment, report HOLDOUT-DTI with evaluator version, withheld-positive count, and 95% CI; do not project a leaderboard score.</p>
<table><tr><th>Rank / hypothesis</th><th>Layers and physical signature</th><th>Missing-fault rationale, novelty, mimic, cost, and viability</th></tr>
<tr><td>1. Opposing-margin relay-link profile phase</td><td>Cached gravity and magnetic horizontal-gradient vectors plus tilt zero-crossings, sampled at several stations on opposing margins of a tip-graph connector.</td>
<td>A buried connector can produce paired, phase-consistent edges between mapped tips without having a mapped surface trace. Unlike H69-J&apos;s corridor-wide maxima and min(E<sub>grav</sub>,E<sub>mag</sub>), require stationwise co-location on a common connector axis and opposite margins. <b>Mimic:</b> lithologic contact. <b>Expected HOLDOUT-DTI effect:</b> medium (qualitative). <b>Cost:</b> moderate. Uses existing layers only, but blocked until the cached stack is restored and every source hash is checked.</td></tr>
<tr><td>2. Releasing-basin margin asymmetry</td><td>Gravity curvature, paired horizontal-gradient flanks, and a magnetic low inside a tip-derived pull-apart rhomb.</td>
<td>Buried basin-bounding splays can be absent from a surface catalogue; paired margin geometry is more specific than a scalar gravity or magnetic low. <b>Mimic:</b> sediment-filled paleochannel. <b>Expected HOLDOUT-DTI effect:</b> medium-low (qualitative). <b>Cost:</b> moderate. Requires auditable slip-sense attributes; do not infer dextral release from overlap alone.</td></tr>
<tr><td>3. En-echelon scarp phase coherence</td><td>LiDAR-scarp orientation, stagger, and phase continuity across a proposed relay connector; veto uninterrupted terrace-parallel edges.</td>
<td>A set of short aligned scarps may identify a linking strand individually below regional mapping threshold. This differs from average scarp magnitude by testing arrangement. <b>Mimics:</b> pluvial shorelines, roads, terrace edges. <b>Expected HOLDOUT-DTI effect:</b> low-medium (qualitative). <b>Cost:</b> moderate-high. Existing LiDAR channel is sufficient once the full stack is restored.</td></tr>
<tr><td>4. Matched-flank radiometric contrast reversal</td><td>GeoDAWN K/Th/total-count contrast inside versus matched corridor flanks, conditioned on magnetic response.</td>
<td>Could distinguish local alteration or structural contrast under cover from broad background domains, unlike H69-G&apos;s simple depletion score. <b>Mimic:</b> sediment sorting or lithologic variation. <b>Expected HOLDOUT-DTI effect:</b> uncertain (qualitative). <b>Cost:</b> high. It is <b>not viable yet</b>: a verified lithologic control source and coverage check are missing, so it will not be implemented or promoted as an external-data hypothesis.</td></tr></table>
<p>Before any implementation: restore the pinned feature stack, verify each feature-alone leakage canary, reserve untouched spatial blocks, compare against the current best with the identical evaluator, and run a literal surface registry scan before placing dots and a literal dot scan after. Do not relax the literal overlap rule. Giddens &amp; Faulds statistics in the prompt remain cited, not independently verified in this environment.</p></div>
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
<div class="card"><h2>E2 &mdash; archived holdout screen (not bound to the current artifact)</h2>
<table><tr><th>Arm</th><th>Pooled DTI</th><th>95% CI half</th><th>Cells</th></tr>
<tr><td>Corridor prior</td><td>{gate.get('corridor_mean_dti', float('nan')):.4f}</td><td>{gate.get('corridor_ci95_half', float('nan')):.4f}</td><td rowspan=2>{gate.get('n_cells','?')} ({gate.get('withheld_positive_px_total','?')} withheld positives)</td></tr>
<tr><td>No-prior control</td><td>{gate.get('control_mean_dti', float('nan')):.4f}</td><td>{gate.get('control_ci95_half', float('nan')):.4f}</td></tr>
<tr><td><b>Paired &Delta;</b></td><td><b>{gate.get('paired_delta_mean', float('nan')):+.4f}</b></td><td>{gate.get('paired_delta_ci95_half', float('nan')):.4f}</td><td>gate_passed = {esc(gate.get('gate_passed'))}</td></tr>
</table>
<table><tr><th>Cell</th><th>Corridor DTI</th><th>Control DTI</th></tr>{rows}</table>
<p class="small">Evaluator: vendor/template66 gems57 pooled hide-and-recover (&alpha;=0.2, &beta;=0.8,
300 m triangular kernel). Evidence class HOLDOUT-DTI.</p>
</div>
<div class="card"><h2>E3 &mdash; archived emission, registry scan, and validator</h2>
<table><tr><th>Check</th><th>Result</th></tr>
<tr><td>Dots emitted (greedy marginal-DTI, |G| prior 12,691 px)</td><td>{receipt.get('n_dots','?')} (catalogue collisions: {receipt.get('catalogue_collision_px','?')})</td></tr>
<tr><td>Validator on exact bytes (scripts/validate_submission.py, both variants)</td><td>{'PASS' if receipt.get('validator', {}).get('all_files_passed') else 'FAIL/pending — see evidence/relayfix_transfer_validator.json'}</td></tr>
<tr><td>Portal file (-zeros): all-finite float32 in [0,1], EPSG:32611, 3730&times;3292</td><td>{'PASS' if receipt.get('validator', {}).get('all_files_passed') else 'pending'}</td></tr>
<tr><td>Diagnostic twin (-nan): NaN only outside footprint &mdash; DO NOT UPLOAD</td><td>archived for audit</td></tr>
<tr><td>Registry scan compared / errors</td><td>{uniq.get('n_compared','pending')} / {uniq.get('n_errors','pending')}</td></tr>
<tr><td>Worst |Spearman| surface</td><td>{esc(uniq.get('worst_abs_spearman', 'pending'))}</td></tr>
<tr><td>Worst dot overlap (dotlike stratum; diagnostic only)</td><td>{esc((uniq.get('worst_dot_overlap_dotlike') or {}).get('dot_overlap_3px', 'pending'))}</td></tr>
<tr><td>Literal registry overlap gate (publication controlling)</td><td>{esc((uniq.get('literal_gate') or {}).get('overlap_ok', 'pending'))} &mdash; false means duplicate-and-stop</td></tr>
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
<tr><td>IR-69-REG-01</td><td>The literal protocol overlap gate fails closed against any sparse dot field because the registry contains universal/support-dense surfaces. Dotlike strata are diagnostic only; a literal failure is duplicate-and-stop.</td><td>Publication remains blocked until the protocol owner resolves registry-support semantics. No local exception is allowed.</td></tr>
<tr><td>IR-69-SCORE-01</td><td>Leaderboard values supplied in the standing prompt are USER-REPORTED-NOT-ORGANIZER-CONFIRMED unless a submission-page receipt binds a value to exact bytes.</td><td>Labels applied everywhere; projections are never reported as scores.</td></tr>
<tr><td>IR-69-H33-01</td><td>The current public owner source for H33-2-B2 says UNSCORED, labels 0.2747 a projection, and provides no organizer receipt. This conflicts with the user-supplied 0.2778 association.</td><td>Logged in <code>reports/h33-owner-source-audit-2026-10-20.md</code>; H33 artifacts are learning-only and are not reused in this lane.</td></tr>
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
