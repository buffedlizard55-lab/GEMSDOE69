#!/usr/bin/env python3
"""Build the public project site from current, hash-bound evidence (stdlib only)."""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence"

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "Executive Summary"),
    ("why-h33-scored.html", "Why H33"),
    ("hypotheses.html", "Hypotheses"),
    ("method.html", "Method"),
    ("results.html", "Results"),
    ("sources.html", "Sources"),
    ("irregularities.html", "Irregularities"),
    ("run-card.html", "Run Card"),
]


def esc(value: Any) -> str:
    return html.escape(str(value))


def load(name: str, default=None):
    path = EV / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return default


def page(title: str, active: str, body: str) -> str:
    nav = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">{label}</a>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · GEMSDOE69</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body>
<header><div class="wrap"><h1>GEMSDOE69 · Relay-ramp &amp; pull-apart corridor lane</h1>
<div class="sub">DOE GEMS Prize · catalogue-geometry fault proposal · submission status is evidence-gated</div></div></header>
<nav><div class="wrap">{nav}</div></nav>
<main class="wrap">{body}</main>
<footer>Negative results are deliverables · no organizer score is inferred from a local holdout.</footer>
</body></html>"""


def current_card() -> dict[str, Any]:
    return load("run_card.json", {}) or {}


def submission_banner():
    """Offer only the exact candidate cleared by the fail-closed release policy."""
    from release_gate import evaluate

    decision = evaluate(ROOT)
    downloads = DOCS / "downloads"
    # Remove any previously copied candidate before rendering the current decision.
    if downloads.exists():
        for artifact in downloads.iterdir():
            if artifact.is_file() and artifact.suffix.lower() in (".tif", ".tiff", ".zip"):
                artifact.unlink()
    if not decision["download_enabled"]:
        reasons = "".join(f"<li>{esc(reason)}</li>" for reason in decision["reasons"])
        banner = (
            '<div class="banner bad"><b>NOT OK TO SUBMIT — DO NOT SUBMIT.</b>'
            '<p>No TIFF download is offered. The archived candidate failed one or more literal, '
            'provenance, holdout, or validation gates. No competition slot was used.</p>'
            f'<ul>{reasons}</ul></div>'
        )
        return banner, None

    candidate = load("current_candidate.json", {}) or {}
    relative = candidate.get("artifact_path")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        return '<div class="banner bad"><b>NOT OK TO SUBMIT — DO NOT SUBMIT.</b><p>Unsafe candidate path.</p></div>', None
    artifact = (ROOT / relative).resolve()
    try:
        artifact.relative_to(ROOT.resolve())
    except ValueError:
        return '<div class="banner bad"><b>NOT OK TO SUBMIT — DO NOT SUBMIT.</b><p>Candidate path escapes the repository.</p></div>', None
    if not artifact.is_file():
        return '<div class="banner bad"><b>NOT OK TO SUBMIT — DO NOT SUBMIT.</b><p>Hash-cleared artifact is missing.</p></div>', None
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, downloads / artifact.name)
    banner = (
        '<div class="banner ok"><b>OK TO DOWNLOAD — SELECTOR AUTHORIZATION STILL REQUIRED.</b>'
        '<p>All automated release gates passed for this exact SHA-256. This is not an organizer score, '
        'and a separate selector must authorize any competition slot.</p></div>'
        f'<a class="btn big" href="downloads/{esc(artifact.name)}" download>Download the gated TIFF</a>'
    )
    return banner, artifact


def _float(value: Any, digits: int = 6) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "not recorded"


def _paired_row(label: str, item: dict[str, Any]) -> str:
    return (f"<tr><td>{esc(label)}</td><td>{_float(item.get('mean'))}</td>"
            f"<td>{esc(item.get('ci95', 'not recorded'))}</td><td>HOLDOUT-DTI paired delta</td></tr>")


def build_index() -> str:
    banner, _ = submission_banner()
    card = current_card()
    holdout = card.get("holdout", {})
    registry = card.get("correlation_overlap_vs_registry", {})
    raster = card.get("raster", {})
    validator = card.get("validator_output", {})
    surface = registry.get("surface_phase", {})
    dots = registry.get("dots_phase", {})
    best = holdout.get("current_best_comparison", "not established")
    if isinstance(best, dict):
        best_text = "paired HOLDOUT-DTI evidence is present"
    else:
        best_text = str(best)

    body = f"""{banner}
<div class="card">
<h2>Current run — negative release decision</h2>
<p>The latest emitted candidate is <code>{esc(card.get('candidate_id', 'not recorded'))}</code>. Its local format validator passed, but that is not release clearance. The current policy is <strong>{esc(card.get('verdict', 'negative')).upper()}</strong>; there is no active download unless the red banner above changes after all gates pass.</p>
<table><tr><th>Evidence</th><th>Result</th><th>Interpretation</th></tr>
<tr><td>Primary pooled score</td><td>{_float(holdout.get('pooled_dti'))}</td><td>HOLDOUT-DTI; pooled from summed TP/FP/FN; no absolute pooled-DTI 95% CI is recorded</td></tr>
<tr><td>Evaluator and sample</td><td>{esc(holdout.get('evaluator_version', 'not recorded'))}</td><td>HOLDOUT-DTI; {esc(holdout.get('n_cells', 'unknown'))} cells, {esc(holdout.get('withheld_positive_pixels', 'unknown'))} withheld positives</td></tr>
<tr><td>Mean of cell DTI</td><td>{_float(holdout.get('mean_of_cell_dti'))}</td><td>HOLDOUT-DTI, normal-approximation interval {esc(holdout.get('mean_of_cell_dti_ci95_normal_approximation', 'not recorded'))}; not a pooled-DTI CI</td></tr>
{_paired_row('Transfer − corridor-v1 paired delta', holdout.get('paired_delta_vs_corridor_v1', {}))}
{_paired_row('Transfer − no-prior-control paired delta', holdout.get('paired_delta_vs_control', {}))}
<tr><td>Current holdout best</td><td>{esc(best_text)}</td><td>No hash-bound paired CI against a declared current-best artifact; no improvement claim</td></tr>
<tr><td>Literal registry scan</td><td>{esc(registry.get('registry_rasters_compared', 'not recorded'))}/{esc(registry.get('registry_rasters_expected', 'not recorded'))} accessible rasters; errors {esc(registry.get('registry_errors', 'not recorded'))}</td><td>REGISTRY-MEASUREMENT; public owner-repository index only, not organizer-complete</td></tr>
<tr><td>Worst final-dot overlap</td><td>{esc((registry.get('worst_dot_overlap_all') or {}).get('dot_overlap_3px', 'not recorded'))}</td><td>REGISTRY-MEASUREMENT; literal duplicate threshold is &gt;0.700 within 3 px</td></tr>
<tr><td>Surface phase</td><td>|rho| {_float(surface.get('worst_abs_spearman'))}; overlap {esc(surface.get('worst_dot_overlap', 'not recorded'))}</td><td>REGISTRY-MEASUREMENT; required before placement; current order: {esc(surface.get('phase_order', 'not certified'))}</td></tr>
<tr><td>Final dots phase</td><td>|rho| {_float(dots.get('worst_abs_spearman'))}; overlap {esc(dots.get('worst_dot_overlap', 'not recorded'))}</td><td>REGISTRY-MEASUREMENT; required after placement; current order: {esc(dots.get('phase_order', 'not certified'))}</td></tr>
<tr><td>Artifact bytes</td><td><code>{esc(raster.get('sha256', 'not recorded'))}</code></td><td>{esc(raster.get('positive_pixels', 'unknown'))} positives; archived at <code>{esc(raster.get('path', 'not recorded'))}</code></td></tr>
<tr><td>Local validator</td><td>{'PASS' if validator.get('all_checks_passed') else 'FAIL / not recorded'}</td><td>Format/range only; does not prove uniqueness, method provenance, or organizer acceptance</td></tr>
</table>
<p class="small"><b>Literal rule:</b> if any raster has |Spearman| &gt; 0.90 or &gt;70% of candidate dots within 3 px, record duplicate and stop. A stratified/dotlike diagnostic cannot override that failure.</p>
</div>
<div class="card">
<h2>H33 reported 0.2778 — cautious interpretation</h2>
<p><b>USER-REPORTED-NOT-ORGANIZER-CONFIRMED.</b> No organizer receipt in this repository binds the reported 0.2778 to H33 file bytes. An anatomy audit of an accessible family raster measures 37,654 unit dots, but that is not score authentication. Sparse fields can reduce redundant false-positive mass under a distance-weighted Tversky metric, yet this mechanism alone neither explains the reported score causally nor predicts that this lane will beat it. Holdout-DTI is a screening metric, not a leaderboard projection. See <a href="why-h33-scored.html">the full evidence note</a>.</p>
</div>
<div class="card">
<h2>What this project does</h2>
<p>The only active method lane is relay-ramp and pull-apart corridors proposed from catalogue tip geometry, using the shared template and cached features when available. Candidate corridors are scored with gravity/magnetic gradients and tilt, magnetic lows, LiDAR scarp evidence, and orientation priors; the current transfer-only candidate is not eligible. Strike is not dip, and dextral/releasing sense is not measured by a raster-only catalogue.</p>
<p><a href="hypotheses.html">Read the three untried, in-lane hypotheses</a> · <a href="results.html">Evidence and limitations</a> · <a href="run-card.html">Machine-readable run card</a>.</p>
</div>"""
    return page("Submission status", "index.html", body)


def build_executive_summary() -> str:
    banner, _ = submission_banner()
    card = current_card()
    raster = card.get("raster", {})
    name = card.get("submission_name", "not currently approved")
    note = card.get("submission_note", "")
    body = f"""{banner}
<div class="card">
<h2>Executive summary — format and submission procedure</h2>
<p><strong>Current state: DO NOT SUBMIT.</strong> The archived candidate is <code>{esc(raster.get('path', 'not recorded'))}</code>; it is not offered as a download. Do not upload the archived file or spend a competition slot. The exact local format validator passed, but literal uniqueness and provenance gates did not.</p>
<p>If a future build changes the banner to <b>OK TO DOWNLOAD</b>, then, and only then:</p>
<ol>
<li>Download the exact <code>-zeros.tif</code> artifact linked below that green banner. Do not substitute the diagnostic <code>-nan</code> twin, labels, or feature rasters.</li>
<li>In DrivenData competition 306, choose New submission and upload the single GeoTIFF, or a ZIP containing exactly one GeoTIFF. It must be one float32 band, EPSG:32611, 3730×3292, with the official sample transform/bounds and values in [0,1].</li>
<li>Use the exact submission name and note from the then-current run card (the present candidate name <code>{esc(name)}</code> and note <code>{esc(note)}</code> are archived only and are not authorization).</li>
</ol>
<p>Format validator receipt for the archived bytes: {('PASS' if card.get('validator_output', {}).get('all_checks_passed') else 'not passed')}; SHA-256 <code>{esc(raster.get('sha256', 'not recorded'))}</code>. This proves only that the local file matches the locally available sample grid and numeric range; it does not prove organizer acceptance.</p>
</div>
<div class="card">
<h2>Portal range error: verified limits</h2>
<p>The repository does not retain an organizer submission-page receipt or a verified log tying a particular upload to the reported range error. Do not state a cause as confirmed. The local validator is the right first check on the exact upload bytes: no NaN in the footprint, all finite values in [0,1], correct CRS, shape and transform. The separate NaN diagnostic is never the upload variant. If the same error recurs after those checks, inspect the organizer's returned validation report rather than guessing.</p>
</div>
<div class="card">
<h2>Current constraints</h2>
<ul>
<li>Feature cache missing from this checkout (`.cache/gems_data`); only bridge submission inputs are present locally.</li>
<li>Competition/data mirrors are owner-supplied and hash-pinned, not organizer-authenticated.</li>
<li>The accessible registry census is not complete for private, external, or never-committed rasters.</li>
<li>HOLDOUT-DTI values are screening results; no organizer score or projection is claimed.</li>
<li>No slot selected or spent. See <a href="irregularities.html">irregularities</a> and the <a href="../reports/repo-review-2026-10-20.md">three-pass review</a>.</li>
</ul>
</div>"""
    return page("Executive summary", "executive-summary.html", body)


def build_why_h33() -> str:
    anatomy = load("relayfix_champion_anatomy.json", {}) or {}
    dots = anatomy.get("n_dots", "not measured")
    digest = anatomy.get("sha256", "not recorded")
    body = f"""<div class="card">
<h2>Why H33 was reported at 0.2778 — what is and is not supported</h2>
<p><b>0.2778 is USER-REPORTED-NOT-ORGANIZER-CONFIRMED.</b> The repository has no submission receipt binding that value to the exact H33 artifact. Do not present it as a verified score, current leaderboard rank, causal effect, or target this method can beat.</p>
<p><b>REGISTRY-MEASUREMENT:</b> a local anatomy audit of a family-repository H33 raster recorded {esc(dots)} unit dots and SHA-256 <code>{esc(digest)}</code>. This is a measurement of accessible file bytes, not authentication of the score. A sparse, distance-tolerant field can plausibly avoid paying for redundant false-positive mass while retaining some kernel coverage; the exact impact depends on the hidden faults, which are not available here.</p>
<p>The competition metric recorded in the source register is distance-weighted Tversky (alpha 0.2, beta 0.8, 300 m triangular kernel). A score on a private holdout is not calibrated to organizer leaderboard scores by any evidence in this candidate's run card. No unique lane result has demonstrated an organizer-score improvement. For a full source and uncertainty note, see <a href="research/0.2778-analysis.md">the repository analysis</a>.</p>
<p>Current limitation: no official receipt ties 0.2778 to the measured H33 bytes; historical leaderboard snapshots are not live. No leaderboard page was fetched during this review.</p>
</div>"""
    return page("H33 evidence review", "why-h33-scored.html", body)


def build_hypotheses() -> str:
    queue = load("hypothesis_queue_current.json", {}) or {}
    rows = []
    for item in queue.get("items", []):
        rows.append(
            "<section class=\"card\">"
            f"<h2>Rank {esc(item.get('rank'))}: {esc(item.get('name'))}</h2>"
            f"<p><b>Layers:</b> {esc(', '.join(item.get('layers', [])))}.</p>"
            f"<p><b>Signature:</b> {esc(item.get('signature'))}</p>"
            f"<p><b>Why a catalogue-missing fault:</b> {esc(item.get('why_catalogue_missing_fault'))}</p>"
            f"<p><b>Difference / untried audit:</b> {esc(item.get('difference_from_implemented_methods'))} {esc(item.get('closest_prior_and_untried_check'))}</p>"
            f"<p><b>Named mimics:</b> {esc(item.get('mimics'))}</p>"
            f"<p><b>Expected HOLDOUT-DTI improvement / cost:</b> {esc(item.get('expected_holdout_improvement'))}; {esc(item.get('implementation_cost'))}</p>"
            f"<p><b>Data / validation:</b> {esc(item.get('data_and_validation'))}</p>"
            f"<p class=\"small\"><b>Source limit:</b> {esc(item.get('source_note'))}</p>"
            "</section>"
        )
    body = (
        '<div class="card"><h2>Untried hypotheses — HYPOTHESIS-PRIOR only</h2>'
        f'<p>{esc(queue.get("lane", ""))}</p>'
        f'<p><b>Scope:</b> {esc(queue.get("untried_scope", ""))}</p>'
        '<p>Rank is a qualitative expected-improvement-per-cost prior; no score projection is made. '
        'Related earlier proposals and tests are explicitly reconciled in the register. None has been '
        'tested in this review or cleared for a submission slot.</p>'
        + "".join(rows)
        + '<p>Full register: <a href="research/untried-hypotheses-2026-10-20.md">Markdown</a> · '
        '<a href="../evidence/hypothesis_queue_current.json">JSON evidence</a>.</p></div>'
    )
    body += (
        '<div class="card"><h2>Test decision</h2>'
        f'<p><b>{esc(queue.get("selection", {}).get("decision", "NOT CLEARED"))}.</b> '
        f'{esc(queue.get("selection", {}).get("reason", ""))}</p>'
        '<p>Any future test must obey whole-fault-segment hide-and-recover, buffer, visible-only catalogue features, exact visible-fault masking, pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel), feature-alone leakage checks, paired comparison to the declared current best, and pre-placement surface uniqueness. No slot is used.</p></div>'
    )
    return page("Untried hypotheses", "hypotheses.html", body)


def build_method() -> str:
    card = current_card()
    body = f"""<div class="card">
<h2>Method lane and its limits</h2>
<p>Candidate corridors are proposed from the mapped catalogue tip graph. Geometry restrictions include spacing W of 0.1–15 km and along-strike separation no greater than 3.5W. The raster catalogue does not encode dip polarity or slip sense; parallel strike is not a measurement of same dip, and dextral/releasing classification remains a stated regional prior.</p>
<p>The shared project implementation renders oblique connectors and en-échelon/pull-apart geometries; the current candidate restricts its scored proposals to transfer-overlap pairs. Physics scores use gravity/magnetic horizontal gradients and tilt-derived fields, magnetic lows, a LiDAR scarp magnitude composite, and a fixed orientation prior. Dots are selected by the pinned shared template allocator. No private template fork was created for this review.</p>
<h3>What the joint scorer actually computes</h3>
<p><code>src/gems69/scoring_joint.py</code> takes maxima across gravity and magnetic feature groups, combines them with <code>min(E_grav, E_mag)</code>, and adds scalar magnetic-low, LiDAR, orientation, and geometry terms. It does not compute signed edge polarity, spatial co-location, phase alignment, or cross-height persistence. This distinction is why the new hypothesis register does not call the earlier H69-J run a spatial phase test.</p>
<h3>Current experiment</h3>
<p>{esc(card.get('hypothesis', 'No current hypothesis recorded.'))}</p>
<p><b>Mechanism:</b> {esc(card.get('mechanism', 'not recorded'))}</p>
<p><b>Named non-fault mimic:</b> {esc(card.get('non_fault_mimic', 'not recorded'))}</p>
<p>For exact thresholds and evidence, see the <a href="results.html">Results page</a> and <a href="../evidence/run_card.json">JSON run card</a>.</p>
</div>"""
    return page("Method", "method.html", body)


def build_results() -> str:
    card = current_card()
    holdout = card.get("holdout", {})
    registry = card.get("correlation_overlap_vs_registry", {})
    report = card.get("validator_output", {})
    policy = card.get("release_policy", {})
    delta_v1 = holdout.get("paired_delta_vs_corridor_v1", {})
    delta_control = holdout.get("paired_delta_vs_control", {})
    reasons = "".join(f"<li>{esc(reason)}</li>" for reason in policy.get("reasons", []))
    body = f"""<div class="card">
<h2>HOLDOUT-DTI — screening result, not a leaderboard score</h2>
<p>Evaluator: <code>{esc(holdout.get('evaluator_version', 'not recorded'))}</code>; {esc(holdout.get('n_cells', 'unknown'))} holdout cells; {esc(holdout.get('withheld_positive_pixels', 'unknown'))} withheld positive pixels. Primary statistic: {esc(holdout.get('primary_statistic', 'not recorded'))}.</p>
<table><tr><th>Quantity</th><th>HOLDOUT-DTI</th><th>95% interval</th><th>Meaning</th></tr>
<tr><td>Transfer-only candidate, primary pooled</td><td>{_float(holdout.get('pooled_dti'))}</td><td>not available for absolute pooled DTI</td><td>Summed TP/FP/FN; not directly comparable to leaderboard scores</td></tr>
<tr><td>Mean of cell DTI</td><td>{_float(holdout.get('mean_of_cell_dti'))}</td><td>{esc(holdout.get('mean_of_cell_dti_ci95_normal_approximation', 'not recorded'))}</td><td>Normal approximation over cells; different estimand from pooled DTI</td></tr>
{_paired_row('Candidate − corridor-v1', delta_v1)}
{_paired_row('Candidate − no-prior control', delta_control)}
</table>
<p><b>Current-best comparison:</b> {esc(holdout.get('current_best_comparison', 'not established'))} The stored <code>beats_current_best</code> boolean in older evidence is not accepted without artifact-bound same-evaluator paired evidence.</p>
<p class="small">Method/evaluator and withheld counts are shown with each number as required. Paired-delta intervals are not absolute candidate-score intervals.</p>
</div>
<div class="card">
<h2>REGISTRY-MEASUREMENT — literal uniqueness</h2>
<p>Accessible indexed rasters: {esc(registry.get('registry_rasters_compared', 'unknown'))}/{esc(registry.get('registry_rasters_expected', 'unknown'))}; scan errors: {esc(registry.get('registry_errors', 'unknown'))}. Scope: {esc(registry.get('registry_scope', 'not recorded'))}</p>
<table><tr><th>Phase</th><th>Worst absolute Spearman</th><th>Worst literal 3-px overlap</th><th>Required order / outcome</th></tr>
<tr><td>Pre-placement surface</td><td>{_float(registry.get('surface_phase', {}).get('worst_abs_spearman'))}</td><td>{esc(registry.get('surface_phase', {}).get('worst_dot_overlap', 'not recorded'))}</td><td>{esc(registry.get('surface_phase', {}).get('phase_order', 'not certified'))}; stop required = {esc(registry.get('surface_phase', {}).get('stop_required', 'not recorded'))}</td></tr>
<tr><td>Final dots</td><td>{_float(registry.get('dots_phase', {}).get('worst_abs_spearman'))}</td><td>{esc(registry.get('dots_phase', {}).get('worst_dot_overlap', 'not recorded'))}</td><td>{esc(registry.get('dots_phase', {}).get('phase_order', 'not certified'))}; stop required = {esc(registry.get('dots_phase', {}).get('stop_required', 'not recorded'))}</td></tr>
<tr><td>Aggregate literal gate</td><td>{esc(registry.get('literal_gate', {}).get('rho_ok', 'not recorded'))}</td><td>{esc(registry.get('literal_gate', {}).get('overlap_ok', 'not recorded'))}</td><td>Any |rho| &gt; 0.90 or overlap &gt; 0.700 means duplicate-and-stop</td></tr>
</table>
<p>The saved per-raster scan has a literal dot overlap of 1.0 against at least one accessible raster. A smaller-raster/dotlike diagnostic is not a waiver. The 862-raster public owner-repository index explicitly omits private, external, and never-committed files, so it is not an exhaustive organizer registry.</p>
</div>
<div class="card">
<h2>Artifact, validator, and provenance</h2>
<p>Archived path: <code>{esc(card.get('raster', {}).get('path', 'not recorded'))}</code><br>SHA-256: <code>{esc(card.get('raster', {}).get('sha256', 'not recorded'))}</code></p>
<p>Exact-byte local validator: <b>{'PASS' if report.get('all_checks_passed') else 'FAIL / not recorded'}</b>; values min/max {esc(report.get('min', 'not recorded'))}/{esc(report.get('max', 'not recorded'))}; NaNs inside footprint {esc(report.get('n_nan_inside_footprint', 'not recorded'))}; grid {esc((report.get('meta') or {}).get('crs', 'unknown'))}, {esc((report.get('meta') or {}).get('shape', 'unknown'))}, transform {esc((report.get('meta') or {}).get('transform', 'unknown'))}. This is a format check only.</p>
<p>Method manifest: stale source hashes were detected for the transfer candidate (<code>holdout69.py</code>) and for H69-J (four source files). Those hashes were not silently rewritten.</p>
<h3>Why publication is blocked</h3><ul>{reasons}</ul>
</div>"""
    return page("Results and evidence", "results.html", body)


def build_sources() -> str:
    body = """<div class="card">
<h2>Official and primary references — access status</h2>
<p>No external web page was fetched during this review. These links are supplied for manual verification; the local source register records prior access dates and limitations. Do not treat the historic leaderboard snapshot as current.</p>
<table><tr><th>Source</th><th>Link</th><th>Use / status</th></tr>
<tr><td>DrivenData DOE GEMS competition 306</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition</a></td><td>Official competition page; not refreshed in this review</td></tr>
<tr><td>DrivenData problem description</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem page 967</a></td><td>Metric, task, data and format reference; login/access limitations recorded in sources.md</td></tr>
<tr><td>DrivenData about page</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">About page 968</a></td><td>Competition context; not refreshed in this review</td></tr>
<tr><td>DrivenData data page</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Data page</a></td><td>Login-walled organizer inputs; local copies are owner-supplied mirrors, not organizer-authenticated</td></tr>
<tr><td>Organizer reference solution</td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">GitHub repository</a></td><td>Code-format reference, cloned/inspected in an earlier documented review</td></tr>
<tr><td>USGS GeoDAWN release</td><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS data release</a></td><td>Official source link for geophysical input provenance; not fetched this review</td></tr>
<tr><td>INGENIOUS project</td><td><a href="https://gbcge.org/current-projects/ingenious/">Project page</a></td><td>Catalogue context; not fetched this review</td></tr>
<tr><td>Giddens &amp; Faulds (2025), SGP-TR-229</td><td><a href="https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf">Stanford Geothermal Workshop PDF</a></td><td>Relay-ramp/step-over prior; the local source register reports prior verification (2026-10-12), not re-fetched now</td></tr>
<tr><td>EPSG:32611</td><td><a href="https://epsg.io/32611">EPSG reference</a></td><td>Grid CRS manual reference; not refreshed in this review</td></tr>
<tr><td>Potential theory reference</td><td>Blakely (1995), <i>Potential Theory in Gravity and Magnetic Applications</i>, Cambridge University Press</td><td>Suggested background for the depth-persistence hypothesis; not fetched/verified in this review</td></tr>
</table>
<p class="small">See <a href="research/sources.md">source register</a> and <a href="../evidence/official-reference-readme-2026-10-20.md">official-reference access note</a>. Current feature cache is absent; data manifests pin owner mirrors but do not prove organizer provenance.</p>
</div>"""
    return page("Sources and verification", "sources.html", body)


def build_irregularities() -> str:
    card = current_card()
    registry = card.get("correlation_overlap_vs_registry", {})
    body = f"""<div class="card">
<h2>Irregularities and limitations</h2>
<table><tr><th>ID</th><th>Finding</th><th>Disposition</th></tr>
<tr><td>IR-69-REG-01</td><td>Current transfer candidate has literal dot-overlap {esc((registry.get('worst_dot_overlap_all') or {}).get('dot_overlap_3px', 'not recorded'))} in the accessible registry scan, above the 0.700 stop threshold. Surface and final-dot phases both require stop.</td><td>Duplicate-and-stop. No stratified/dotlike diagnostic can override it; no TIFF offered.</td></tr>
<tr><td>IR-69-REG-02</td><td>862-raster registry index is an accessible public owner-repository inventory, not an organizer-complete census; private, external, and never-committed rasters are excluded.</td><td>State scope explicitly; do not claim global uniqueness.</td></tr>
<tr><td>IR-69-ORDER-01</td><td>The recorded surface comparison occurred after emission; it is not certified as a pre-placement check. The final-dots comparison is not independently certified as an after-placement phase in its manifest.</td><td>Release policy fails closed on phase-order evidence.</td></tr>
<tr><td>IR-69-SOURCE-01</td><td>The transfer method manifest has a stale <code>holdout69.py</code> hash. The H69-J manifest has four source mismatches. These manifests do not prove that the current checkout reproduces the artifacts.</td><td>Do not rewrite the hashes without an artifact-reproducing run; no experiment was rerun.</td></tr>
<tr><td>IR-69-BEST-01</td><td>Archived HOLDOUT-DTI evidence compares transfer with corridor-v1 and a no-prior control, but has no hash-bound paired interval against a declared current holdout-best artifact.</td><td>Do not treat an old <code>current_best_beaten</code> boolean as sufficient; no current-best claim.</td></tr>
<tr><td>IR-69-PROTOCOL-01</td><td>The preregistration records <code>frozen_utc=2026-10-20T20:50:00Z</code>, later than the HOLDOUT-DTI record's <code>generated_utc=20261020T204429Z</code>. These UTC fields conflict with the text claiming it was frozen before the look.</td><td>Pin both records, mark preregistration order unverified, and do not treat this holdout as protocol-certified until the timestamp discrepancy is resolved.</td></tr>
<tr><td>IR-69-DATA-01</td><td>Competition inputs in the manifests are owner-supplied, hash-pinned mirrors, not organizer-authenticated. The feature cache is absent from this checkout.</td><td>No current local feature restoration or experiment was performed.</td></tr>
<tr><td>IR-69-SCORE-01</td><td>H33's reported 0.2778 has no organizer receipt binding the score to file bytes; historical leaderboard snapshots are stale.</td><td>Label USER-REPORTED-NOT-ORGANIZER-CONFIRMED; no projection.</td></tr>
<tr><td>IR-69-DIP-01</td><td>The catalogue raster does not encode dip polarity or fault slip sense.</td><td>Strike similarity and regional dextral assumptions remain proxies, not observations.</td></tr>
</table>
</div>"""
    return page("Irregularities", "irregularities.html", body)


def build_run_card() -> str:
    card = current_card()
    body = '<div class="card"><h2>Current JSON run card</h2><p>Negative result; status and uncertainty are artifact-bound as far as archived evidence permits. See the release policy field.</p><pre>' + esc(json.dumps(card, indent=2)) + '</pre></div>'
    return page("Run card", "run-card.html", body)


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

    from release_gate import evaluate
    status = evaluate(ROOT)
    (DOCS / "run-card.json").write_text(json.dumps(current_card(), indent=2) + "\n", encoding="utf-8")
    (DOCS / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    for name, markup in pages.items():
        (DOCS / name).write_text(markup, encoding="utf-8")

    banner, _ = submission_banner()
    root_page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                 '<meta http-equiv="refresh" content="0;url=docs/index.html">'
                 '<meta name="viewport" content="width=device-width, initial-scale=1">'
                 '<title>GEMSDOE69 submission status</title></head><body>'
                 + banner.replace('href="downloads/', 'href="docs/downloads/')
                 + '<p><a href="docs/index.html">Open project site</a></p></body></html>')
    (ROOT / "index.html").write_text(root_page, encoding="utf-8")
    print(f"built {len(pages)} pages; verdict={status['verdict']}; download_enabled={status['download_enabled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
