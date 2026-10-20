#!/usr/bin/env python3
"""Build the static site from measured evidence, with one literal release policy."""
from __future__ import annotations

import html
import json
import shutil
import zipfile
from pathlib import Path

try:
    from .release_gate import evaluate, sha256_file, write_card
except ImportError:
    from release_gate import evaluate, sha256_file, write_card

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
NAV = [
    ('index.html', 'Overview'), ('executive-summary.html', 'Submission guide'),
    ('why-h33-scored.html', 'H33 analysis'), ('hypotheses.html', 'Research queue'),
    ('method.html', 'Method audit'), ('results.html', 'Evidence'),
    ('family-audit.html', 'Family results'), ('sources.html', 'Verified sources'),
    ('irregularities.html', 'Blockers'), ('run-card.html', 'Run card'),
]


def esc(value):
    return html.escape(str(value))


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {} if default is None else default


def load(name, default=None):
    return read_json(ROOT / 'evidence' / name, default)


def source_registry():
    return read_json(ROOT / 'registry/verified_sources_2026-10-20.json')


def source_link(key, text=None):
    source = next((r for r in source_registry().get('sources', []) if r['id'] == key), None)
    return f'<a href="{esc(source["url"])}">{esc(text or source["authority"])}</a>' if source else esc(text or key)


def page(title, active, body):
    cleared = evaluate(ROOT)['download_enabled']
    strip = ('PUBLICATION GATES PASSED · Selector authorization still required' if cleared
             else 'DO NOT SUBMIT · No eligible submission download')
    strip_class = 'ok' if cleared else 'bad'
    nav = ''.join(f'<a href="{href}"' + (' aria-current="page" class="active"' if href == active else '') + f'>{label}</a>' for href, label in NAV)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><title>{esc(title)} · GEMSDOE69</title>
<link rel="stylesheet" href="assets/site.css"></head><body>
<a class="skip" href="#content">Skip to content</a>
<div class="global-status {strip_class}" role="status"><div class="wrap"><strong>{strip}</strong> · <a href="executive-summary.html">Read submission instructions</a></div></div>
<header><div class="wrap"><p class="eyebrow">GEMS PRIZE · RESEARCH LANE 69</p><h1>Relay ramps. Pull-aparts. Evidence first.</h1>
<p class="sub">Catalogue-geometry fault discovery · reproducible checks · no unsupported score promises</p></div></header>
<nav aria-label="Main"><div class="wrap">{nav}</div></nav>
<main class="wrap" id="content">{body}</main>
<footer><div class="wrap">Maximize P(Win): protect scarce submission slots. Own the Outcome: publish negative results.<br>
<a href="https://github.com/buffedlizard55-lab/GEMSDOE69">Repository</a> · <a href="status.json">Release status JSON</a> · <a href="run-card.json">Run card JSON</a></div></footer>
</body></html>'''


def submission_banner():
    """Revoke stale files, then copy only the exact artifact cleared by policy."""
    decision = evaluate(ROOT)
    downloads = DOCS / 'downloads'
    # Retired routes must not retain a previously public raster or archive.
    # Limit revocation to the static site tree; keep private scientific history.
    for artifact in DOCS.rglob('*'):
        if artifact.is_file() and artifact.suffix.lower() in ('.tif', '.tiff', '.zip'):
            artifact.unlink()
    if not decision['download_enabled']:
        reasons = ''.join(f'<li>{esc(reason)}</li>' for reason in decision['reasons'])
        return (f'''<section class="banner bad" aria-label="Submission status"><div class="status-label">SUBMISSION STATUS · NEGATIVE</div>
<h2>NOT OK TO SUBMIT — DO NOT SUBMIT</h2>
<p>No TIFF or ZIP is published for submission. No submission download is offered. The literal registry gate fails and the current candidate's scientific evidence is not certified.
No new TIFF or competition upload was made in this review.</p>
<div class="actions"><span class="blocked">Download blocked by evidence gates</span><a href="executive-summary.html">What must pass?</a></div>
<details><summary>View all release blockers</summary><ul>{reasons}</ul></details></section>''', None)
    receipt = load('e3_receipt.json')
    tif = (ROOT / receipt['raster']['zeros']['path']).resolve()
    downloads.mkdir(parents=True, exist_ok=True)
    copied = downloads / tif.name
    shutil.copy2(tif, copied)
    if sha256_file(copied) != decision['artifact_sha256']:
        copied.unlink()
        raise RuntimeError('Copied publication bytes changed; download revoked')
    with zipfile.ZipFile(copied.with_suffix('.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(copied, copied.name)
    return (f'''<section class="banner ok" aria-label="Submission status"><div class="status-label">SUBMISSION STATUS · HOLDOUT-SCREENED</div>
<h2>OK TO DOWNLOAD — SELECTOR AUTHORIZATION STILL REQUIRED</h2><p>All literal publication gates passed. No organizer score or geothermal discovery is claimed.
A separate selector must authorize an actual weekly slot.</p>
<a class="btn" href="downloads/{esc(tif.name)}" download>Download submission TIFF</a>
<a class="btn alt" href="downloads/{esc(tif.with_suffix('.zip').name)}" download>ZIP · one TIFF</a></section>''', tif)


def build_index():
    banner, _ = submission_banner()
    blocker = load('registry-blocker.json')
    validation = load('validator-audit-2026-10-20.json')
    local = load('local-prior-audit.json')
    anatomy = load('h33-audit-2026-10-20.json')
    family = read_json(DOCS / 'data/family-feed.json')
    body = banner + f'''
<div class="grid stats">
<section class="card"><p class="eyebrow">FRESH REGISTRY COUNTEREXAMPLE</p><p class="stat">{blocker.get('candidate_dots_within_3px', '—')}</p>
<p>Dot overlap within the 3-pixel radius. The literal limit is 0.70. Different bytes do not mean protocol-unique.</p><a href="results.html">Inspect the measured stop →</a></section>
<section class="card"><p class="eyebrow">LOCAL GEOTIFF FORMAT CHECK</p><p class="stat">{'PASS' if validation.get('all_files_passed') else 'NOT CHECKED'}</p>
<p>The archived variants satisfy the local range/grid tests. Format validity is not scientific or submission clearance.</p><a href="executive-summary.html">Understand the format →</a></section>
<section class="card"><p class="eyebrow">FAMILY SOURCE REVIEW</p><p class="stat">{family.get('read_sites', '—')}/{family.get('requested_sites', '—')}</p>
<p>User-listed page sources read through GitHub. Owner claims are never treated as organizer receipts.</p><a href="family-audit.html">Explore the full source table →</a></section>
</div>
<section class="card"><h2>What was actually achieved</h2>
<ul><li>Independently measured forward overlap {esc(local.get("max_dot_overlap_3px", "not measured"))} against a sparse local archived field, above the 0.70 limit. Resolving the universal-support conflict alone would not clear this candidate.</li><li>Reproduced a decisive literal duplicate failure from hash-verified registry bytes using the pinned shared comparator. No new model experiment was justified after that stop.</li>
<li>Removed a release-policy density exemption and retired a legacy generator that could fill in missing validation evidence.</li>
<li>Re-read official competition, rules, USGS and geothermal literature sources; saved claim-level evidence and four ranked, untested in-lane hypotheses.</li>
<li>Revalidated the archived TIFFs and measured H33's raster anatomy: {anatomy.get('dots', 0):,} unit dots, with no on-catalogue prediction pixels in the pinned mirror.</li></ul>
<p><b>Not achieved:</b> a new unique, gate-qualified submission or a demonstrated leaderboard improvement. Negative results are deliverables; a changed filename is not a new scientific result.</p></section>
<section class="card"><h2>Why H33's reported advantage is plausible</h2>
<p>The reported <b>0.2778 is USER-REPORTED-NOT-ORGANIZER-CONFIRMED for H33's exact file</b>. A sparse layout can remove redundant false-positive mass while retaining distance-tolerant coverage.
That explains a plausible metric mechanism, not the hidden-label outcome. No file-bound organizer receipt is available.</p>
<a href="why-h33-scored.html">Read the metric and geological analysis →</a></section>
<section class="card"><h2>Start here when a new candidate is possible</h2>
<p>The lane is a tip graph from catalogue polylines: same dip direction, W 0.1–15 km, along-strike separation ≤3.5W; oblique connectors, en échelon strands, and kinematically verified releasing/transfer zones.
Gravity/magnetics and lidar score those corridors; they do not generate unrelated pixel candidates.</p>
<p>After the literal stop and provenance blockers are resolved, test the top hypothesis on repaired, untouched spatial blocks before placement or any weekly slot.
The <a href="executive-summary.html">submission guide</a> explains generation, gates, format, name, short note and eventual upload. This is a static evidence site, not browser-based training.</p></section>'''
    return page('Submission status', 'index.html', body)


def build_executive_summary():
    receipt = load('e3_receipt.json')
    name = receipt.get('submission_name', 'No cleared artifact')
    note = receipt.get('submission_note', 'No cleared artifact')
    body = submission_banner()[0] + f'''
<section class="card"><h2>Executive summary: exactly how to make a submission</h2>
<p><b>Today: stop. Do not upload an archived file.</b> The file name and note below identify an audit artifact only, not a recommended submission.</p>
<dl><dt>Archived name</dt><dd><code>{esc(name)}</code></dd><dt>Archived note ({len(note)} characters; project limit ≤140)</dt><dd><code>{esc(note)}</code></dd></dl>
<h3>1 · Prepare a scientifically admissible experiment</h3>
<p>Resolve the literal registry conflict without a private exemption. Restore pinned caches outside Git, authenticate available source polylines/attributes, and remove withheld segments plus buffers before all catalogue-derived features, canaries and masks.
The current mirror table contains dip/slip attributes, but the production candidate did not use a verified record-level join. No GPU is needed for this geometry lane.</p>
<h3>2 · Validate before selecting a weekly slot</h3>
<p>Preregister a new hypothesis, reserve untouched spatial blocks, run every feature alone for leakage, and compare pooled HOLDOUT-DTI with both the same no-prior pipeline and the current best. Record evaluator/source/input hashes, withheld-positive counts and paired spatial-block confidence intervals.
Seeds repeating one block do not create independent blocks. Do not call overlapping uncertainty a win.</p>
<h3>3 · Stop duplicates before placement</h3>
<p>Use the pinned template comparator on the normalized surface <b>before</b> greedy marginal-DTI dot placement. A literal correlation &gt;0.90 or forward overlap &gt;0.70 means stop; a dotlike-only diagnostic cannot override it.
After placement, repeat the complete registry/local-prior hash, decoded-pixel and dot scan. A filename or byte hash difference alone is not sufficient.</p>
<h3>4 · Write, re-open and validate the exact TIFF</h3>
<p>Use the shared writer. {source_link('problem', 'The official format')} is one float32 band, EPSG:32611, 100 m, matching the authoritative sample's shape/bounds/geotransform, with confidence values in [0,1] and null/NaN outside bounds.
Our mirrored sample is 3730 rows ×3292 columns with transform <code>(100,0,243350,0,-100,4508550)</code>. Its SHA is pinned, not organizer-authenticated.</p>
<pre>python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/validate_submission.py PATH_TO_ACTUAL_CANDIDATE.tif
python scripts/release_gate.py
python scripts/build_site69.py</pre>
<p>The release policy requires hash-bound science statistics, method sources, visible-only provenance, geological attributes, computed canaries, two literal uniqueness phases in the correct order, and a passing validator receipt. No single Boolean can clear it.
Current model-generation CLIs are blocked by the recorded stop; the unsafe legacy generator is retired.</p>
<h3>5 · Only after an OK banner and separate selector authorization</h3>
<ol><li>Use the one-click TIFF or single-TIFF ZIP download shown at the top of the site <em>only when every gate permits it</em>.</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → New submission</a>, choose that exact file and paste its unique name/short note from the receipt.</li>
<li>Check the actual current weekly allowance on the authenticated portal, submit only if authorized, and preserve the organizer receipt with the exact artifact SHA. The {source_link('rules', 'September 2026 rules, §3.4')} describe up to three submissions per week; the current portal allowance was not accessible here.</li></ol></section>
<section class="card"><h2>About “Predicted values must be in range [0, 1]”</h2>
<p>The rejected user file and portal implementation were not provided. We cannot identify its cause. Negative sentinels, infinities, NaN inside the footprint and finite values outside [0,1] fail our local tests.
An outside-footprint NaN is allowed by the stated layout; do not assert that NaN necessarily caused the portal rejection or that a zeros variant guarantees acceptance.</p>
<p>Re-open and test the actual candidate bytes, not a screenshot, feature stack, labels file or old report. Both current archived variants pass local checks; neither is cleared to submit.</p></section>'''
    return page('Submission guide', 'executive-summary.html', body)


def build_why_h33():
    anatomy = load('h33-audit-2026-10-20.json')
    body = f'''<section class="card"><p class="eyebrow">EVIDENCE, NOT A SCORE PROJECTION</p><h2>Why might the reported H33 file perform well?</h2>
<p><b>0.2778 remains USER-REPORTED-NOT-ORGANIZER-CONFIRMED for the file.</b> We read the owner page and re-fetched the TIFF. Those checks verify the file's properties, not a submitted score. A public leaderboard number cannot bind itself to an arbitrary TIFF.</p>
<p>Fresh RASTER-MEASUREMENTS from pinned mirror bytes: {anatomy.get('dots', 0):,} unit dots; zero on-catalogue pixels; nearest catalogue distance {anatomy.get('nearest_catalogue_m', 0):.1f} m; median {anatomy.get('median_catalogue_distance_m', 0):.1f} m.
The SHA-256 is <code>{esc(anatomy.get('sha256', 'not measured'))}</code>. {source_link('problem', 'Official metric and sample format')}.</p>
<p><b>Official masking caveat:</b> known USGS/INGENIOUS fault pixels are excluded from initial and final scoring. Zero on-catalogue dots is a layout measurement, not by itself a score advantage. The marginal-DTI argument below concerns scored pixels only. {source_link('masking_clarification', 'DrivenData Staff clarification')}.</p>
<p>The owner source labels the exact H33 variant <b>UNSCORED</b> and provides no artifact-bound organizer receipt. A projection elsewhere is not a measured hidden-truth score.</p>
<h3>Metric mechanism</h3>
<p>Let T be weighted true-positive coverage, S total predicted mass, M the prediction-weighted nearest-truth kernel credit, and N the number of true pixels. With α=0.2 and β=0.8,</p>
<pre>DTI = T / [0.2(T + S − M) + 0.8N + ε].
A new unit dot improves DTI iff:
ΔT &gt; 0.2 · DTI · (ΔT + 1 − m).</pre>
<p>Here m is that dot's nearest-truth kernel credit and ΔT its <em>new</em> coverage after existing predictions. They need not be equal. Redundant nearby dots can add mass without much new coverage; thinning can therefore help, but it can also lose recall.
The simplified m &gt;0.2·DTI condition is only a special case, not a universal fault-probability threshold.</p>
<h3>Geological interpretation and what would improve it</h3>
<p>Sparse off-catalogue coverage is compatible with a good detector plus economical emission; it does not prove relay geology or geothermal permeability.
Intrusive contacts, basin edges and shorelines are important confounders. A corridor prior must add independent, kinematically and physically coherent evidence rather than copy H33's dots or inherit its hidden-truth model as measured ground truth.</p>
<p>Can we exceed the reported H33 result? <b>Possible in principle, not demonstrated in this repo review.</b> The organizer public leaderboard was read separately and is shown as a dated snapshot on the sources page. No current candidate has a qualifying HOLDOUT-DTI certificate or an organizer receipt.
The top queued hypothesis uses nuisance-matched connector profiles, not the old scorer's scalar min/max aggregation. No score is projected.</p>
<p>Audit files: <a href="data/h33-audit.json">fresh H33 measurements</a> · <a href="family-audit.html">all requested family-page source checks</a> · <a href="hypotheses.html">ranked research queue</a>.</p></section>'''
    return page('H33 analysis', 'why-h33-scored.html', body)


def build_hypotheses():
    register = read_json(ROOT / 'registry/hypotheses_review_2026-10-20.json')
    rows = []
    for h in register.get('hypotheses', []):
        sources = ' · '.join(source_link(key, key) for key in h['source_ids'])
        layers = ''.join(f'<li>{esc(layer)}</li>' for layer in h['layers'])
        rows.append(f'''<section class="card hypothesis"><p class="eyebrow">RANK {h['rank']} · {esc(h['id'])} · NOT TESTED</p>
<h2>{esc(h['name'])}</h2><ul>{layers}</ul>
<dl><dt>Physical signature</dt><dd>{esc(h['signature'])}</dd><dt>Why an unmapped fault?</dt><dd>{esc(h['missing_fault_mechanism'])}</dd>
<dt>What differs from existing code?</dt><dd>{esc(h['difference_from_repo'])}</dd><dt>Named non-fault mimic</dt><dd>{esc(h['non_fault_mimic'])}</dd>
<dt>Expected improvement / cost</dt><dd>{esc(h['expected_dti_improvement'])} {esc(h['implementation_cost'])}</dd>
<dt>Data readiness</dt><dd>{esc(h['data_readiness'])}</dd></dl><p class="small">Sources: {sources}</p></section>''')
    steps = ''.join(f'<li>{esc(step)}</li>' for step in register.get('validation_plan_after_blockers', []))
    body = f'''<section class="banner review"><h2>Research queue — not slot-eligible</h2><p>{esc(register.get('ranking_basis'))}</p>
<p>No new scientific experiment was run after the duplicate stop. These hypotheses are not discoveries or numerical improvement promises.</p></section>''' + ''.join(rows) + f'<section class="card"><h2>Validation plan after blockers</h2><ol>{steps}</ol></section>'
    return page('Research queue', 'hypotheses.html', body)


def build_method():
    body = '''<section class="card"><h2>Implemented method versus required method</h2>
<p>This audit describes archived code, not a newly validated model. Shared evaluator/writer bytes remain pinned and unchanged.</p>
<div class="table-scroll"><table><thead><tr><th>Requirement</th><th>What the archived production path does</th><th>Status</th></tr></thead><tbody>
<tr><td>Catalogue-polyline tip graph</td><td>Skeletonizes the raster mirror and traces terminal windows; separate vector compatibility APIs exist but do not prove the candidate used source polylines.</td><td>Not certified</td></tr>
<tr><td>Same dip; dextral releasing geometry</td><td>Uses subparallel terminal strike and an unsigned-overlap dilation proxy. Downloadable mirror attributes exist but are not integrated into this artifact.</td><td>Not satisfied by the proxy</td></tr>
<tr><td>W 0.1–15 km; separation ≤3.5W</td><td>Repaired interval origin and search radius are covered by unit tests. Those source repairs make older manifests stale.</td><td>Geometry tests are not a rerun certificate</td></tr>
<tr><td>Multi-scale HG/tilt evidence</td><td>HG of Gaussian-smoothed fields; an unsigned Gaussian-difference/gradient proxy; scalar corridor means and group maxima/minima. Not signed tilt-zero profile coincidence or physical upward continuation.</td><td>Description corrected; science not re-fit after stop</td></tr>
<tr><td>Visible-only hide-and-recover</td><td>Corridor geometry is rebuilt from visible faults, but an allowed-pixel flank mask still uses the full catalogue. The older canary propensity also uses the full catalogue.</td><td>Blocking label-dependent input</td></tr>
<tr><td>Whole-segment withholding with a buffer</td><td>The archived shared build_holdout caller chunks branches at MAX_SEG_PX=12 and leaves visible context unbuffered. Quadrant-boundary erosion is not a withheld-segment buffer.</td><td>Missing compliant, hash-bound protocol audit; legacy transfer functions also stop when imported</td></tr>
<tr><td>Pooled HOLDOUT-DTI; spatial-block CI</td><td>Some archives contain mean-of-cell results; others pool counts but bootstrap repeated cells as independent. Repeated seeds share blocks.</td><td>Not a release certificate</td></tr>
<tr><td>Surface uniqueness before placement</td><td>Some archived comparisons were made only after emission; some phase summaries contradict their literal readings.</td><td>Blocking; no post-hoc clearance</td></tr>
<tr><td>Source/layer rationale</td><td>Archived rationale tables exist, but entries lack authenticated dip/slip provenance and are not proof of a geological link.</td><td>Geologist review still required</td></tr>
</tbody></table></div></section>
<section class="card"><h2>The intended scientific pipeline remains in-lane</h2>
<p>Compatible visible source-polyline tips → legal relay/pull-apart/termination corridors → multi-layer, stress-consistent evidence → calibrated greedy marginal-DTI placement inside corridors → independent hide-and-recover and hard-link recovery → both literal uniqueness phases → exact-byte format validation → selector review.</p>
<p>The current synthetic tests verify code behavior, not geothermal vents. Fixing bookkeeping does not validate a geological hypothesis. Read the research queue for a falsifiable next experiment once the stop is legitimately resolved.</p></section>'''
    return page('Method audit', 'method.html', body)


def build_results():
    blocker = load('registry-blocker.json')
    report = load('validator-audit-2026-10-20.json')
    gate = load('e2_gate.json')
    local = load('local-prior-audit.json')
    maximum = max((r['dots_within_3px'] for r in local.get('rows', []) if isinstance(r.get('dots_within_3px'), (int, float))), default=None)
    mean, half = gate.get('corridor_mean_dti'), gate.get('corridor_ci95_half')
    archived = f'{mean:.7f}, archived 95% interval [{mean-half:.7f}, {mean+half:.7f}]' if isinstance(mean, (int, float)) and isinstance(half, (int, float)) else 'not available'
    vrows = ''
    for v in report.get('reports', []):
        vrows += f'<tr><td><code>{esc(Path(v["file"]).name)}</code></td><td>{esc(v["all_checks_passed"])}</td><td>{v["n_nan_inside_footprint"]}</td><td>[{v["min"]}, {v["max"]}]</td><td><code>{esc(v["sha256"])}</code></td></tr>'
    body = f'''<section class="card"><h2>Fresh registry measurement — STOP</h2>
<p>Evidence class: <b>REGISTRY-MEASUREMENT</b>. Checked {esc(blocker.get('checked_utc'))}. Shared pinned <code>gems57.uniqueness</code> comparator, exact full-footprint correlation, positive finite support, Euclidean radius 3 pixels.</p>
<dl><dt>Pinned comparator</dt><dd>{esc(blocker.get('registry_source'))}</dd><dt>Candidate dots within 3 pixels</dt><dd>{esc(blocker.get('candidate_dots_within_3px'))} (literal maximum permitted: 0.70)</dd>
<dt>Full-footprint Spearman, this one comparator</dt><dd>{esc(blocker.get('full_footprint_spearman'))} (not a fresh full-registry maximum)</dd>
<dt>Positive footprint cells in comparator</dt><dd>{blocker.get('registry_positive_footprint_pixels', '—')} / {blocker.get('footprint_pixels', '—')}</dd>
<dt>Byte/pixel identity</dt><dd>Different bytes; footprint exact-value agreement {blocker.get('footprint_pixel_agreement', '—')}. Neither fact overrides the literal overlap rule.</dd></dl>
<p>A universal positive surface overlaps every nonempty in-footprint proposal under the inherited support definition. This is a measurable protocol/representation conflict, not evidence that all geology is identical. The rule cannot be relaxed here.</p>
<p><b>Independent sparse-prior failure:</b> among the {len(local.get('rows', []))} other local archived TIFFs, the largest forward 3-pixel overlap is {maximum}. It also exceeds 0.70. Excluding a universal-support prior would not make this archived candidate unique.</p>
<p><b>Scope:</b> one decisive counterexample freshly reproduced, plus all other local archived files. No fresh exhaustive registry clearance is claimed. No surface was generated or dots placed after the stop.</p>
<a href="data/registry-blocker.json">Counterexample JSON</a> · <a href="data/local-prior-audit.json">Local hash/pixel/overlap audit</a></section>
<section class="card"><h2>HOLDOUT-DTI: archived claim, not certified</h2>
<p>Joint arm mean of cells: <b>{archived}</b>; no-prior control mean {gate.get('control_mean_dti', '—')}.
Evaluator label in the archive: <code>{esc(gate.get('evaluator'))}</code>. The archive reports {gate.get('withheld_positive_px_total', '—')} withheld-positive <em>pixel evaluations</em> over {gate.get('n_cells', '—')} repeated cells, not that many unique independent positives.</p>
<p>The organizer explicitly confirms a single pooled index, not the mean of per-chunk scores ({source_link('pooled_aggregation_clarification', 'DrivenData Staff')}). The interval here is a normal approximation over repeated cells, not an independent spatial-block CI; a field named “pooled” does not change its arithmetic. Hidden-target-dependent flank exclusion, the older full-catalogue canary and method lineage prevent certification.
There is <b>no new HOLDOUT-DTI result or demonstrated current-best improvement</b> from this review.</p>
<p>The transfer-only archive contains a larger pooled claim, but shares the full-catalogue flank-mask problem and fails literal uniqueness. It is not silently substituted for the joint candidate.</p></section>
<section class="card"><h2>Fresh exact-byte format validation</h2><p>Evidence class: FORMAT-CHECK, not organizer acceptance or a score. Both variants are float32, EPSG:32611, 3730×3292, 100 m, with the pinned sample transform. No NaN inside the footprint; finite values in [0,1].</p>
<div class="table-scroll"><table><thead><tr><th>Archived file</th><th>Local pass</th><th>NaN inside</th><th>Range</th><th>SHA-256</th></tr></thead><tbody>{vrows}</tbody></table></div>
<a href="data/validator-audit.json">Full validator output</a></section>'''
    return page('Evidence', 'results.html', body)


def build_family():
    feed = read_json(DOCS / 'data/family-feed.json')
    rows = []
    for row in feed.get('rows', []):
        claims = '<br>'.join(f'<code>{esc(c["submission_name"])}</code>: {c["value"]:.4f}' for c in row.get('claims', [])) or 'No result supplied'
        checks = row.get('claim_checks', [])
        mentions = sum(c['name_mentioned'] and c['value_mentioned'] for c in checks)
        source = f'<a href="{esc(row.get("source_github_url", row["requested_url"]))}">Read source</a>'
        rows.append(f'<tr><td><a href="{esc(row["requested_url"])}">{esc(row["repo"])}</a><br>{source}</td><td>{claims}</td><td>{esc(row["status"])}<br>{mentions}/{len(checks)} supplied pairs have both strings present (not verified pairing).<br>{len(row.get("download_links_observed", []))} TIFF/ZIP links observed.<br>{esc(row.get("path_resolution_note", row.get("error", "")))}</td></tr>')
    body = f'''<section class="card"><h2>All user-listed family sites — source audit</h2>
<p>Updated {esc(feed.get('generated_utc', 'not available'))}: <b>{feed.get('read_sites', 0)}/{feed.get('requested_sites', 0)} page sources read</b>, {feed.get('errors', 'unknown')} errors.
Each response is git-blob-verified and SHA-256 recorded. Redirects inside each repository are followed. A docs fallback is disclosed where root index is absent. This checks current GitHub sources, not browser rendering or every raster link.</p>
<p><b>Every number in the result column is USER-REPORTED-NOT-ORGANIZER-CONFIRMED.</b> A matching name and decimal on an owner page is not a submission-page receipt or a verified score pairing. No reported family score is promoted to organizer-confirmed evidence.</p>
<p>The H33 page names the target TIFF, but the source audit did not find the supplied 0.2778 decimal on that page. Its source says no organizer score exists there. That is an irregularity to preserve, not resolve by assumption.</p>
<a href="data/family-feed.json">Download full audit JSON with source hashes, all observed download links and claim checks</a>
<div class="table-scroll"><table><thead><tr><th>Site / source</th><th>User-reported result(s)</th><th>Source observation</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''
    return page('Family source audit', 'family-audit.html', body)


def build_sources():
    registry = source_registry()
    rows = []
    for source in registry.get('sources', []):
        claims = '<ul>' + ''.join(f'<li>{esc(claim)}</li>' for claim in source.get('claims', [])) + '</ul>'
        rows.append(f'<tr><td>{source_link(source["id"])}<br><code>{esc(source["id"])}</code></td><td>{esc(source["status"])}<br>{esc(source.get("license_observed", ""))}</td><td>{claims}{esc(source.get("limits", ""))}</td></tr>')
    board = next((s for s in registry.get('sources', []) if s['id'] == 'leaderboard'), {})
    top = board.get('snapshot', [{}])[0]
    health = read_json(DOCS / 'data/source-health.json')
    live = next((s for s in health.get('rows', []) if s['id'] == 'leaderboard' and s.get('status') == 'read' and s.get('snapshot')), None)
    board_text = f'{esc(top.get("participant", "unknown"))}: {top.get("public_dw_tversky", "unknown")}, rank {top.get("rank", "unknown")}; research-tool snapshot {registry.get("review_date_utc")}'
    if live:
        top = live['snapshot'][0]
        board_text = f'{esc(top["participant_page_text"])}: {top["public_dw_tversky"]}, rank {top["rank"]}; fetched {esc(live["checked_utc"])}'
    body = f'''<section class="card"><h2>Official sources, checked claim by claim</h2>
<p>The research fetch tool could read official pages even though direct shell downloads are host-allowlisted. Competition data and submission pages redirect to login. No account credentials were requested, and no authenticated competition input or submission receipt was obtained.</p>
<p><b>Public leaderboard observation:</b> {board_text}. Evidence class: OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT, <b>not an ORGANIZER-CONFIRMED submission-page receipt</b>. It assigns no score to our TIFF or H33. Older conflicting highs in the retained request are user reports, not current facts. A later research-tool request returned only “Loading…”; the earlier dated snapshot is not a live guarantee.</p>
<p>Review date: {esc(registry.get('review_date_utc'))}. <a href="data/verified-sources.json">Claim-level registry JSON</a>. The daily GitHub Actions feed separately records source health, changes and parse failures and retains an audited site artifact; it never changes scientific gates or submits files. Direct automated publishing requires the repository Pages source to be GitHub Actions. While it remains on legacy Pages, that deployment is explicitly skipped; the committed site is a dated snapshot. <a href="https://github.com/buffedlizard55-lab/GEMSDOE69/actions/workflows/pages.yml">Inspect latest daily artifacts and deployment state</a>.</p>
<div class="table-scroll"><table><thead><tr><th>Official source</th><th>Observation</th><th>Verified scope / limitations</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''
    if health:
        body += f'<section class="card"><h2>Source observation feed</h2><p>Last shell attempt: {esc(health.get("generated_utc"))}; {sum(r.get("status") == "error" for r in health.get("rows", []))}/{len(health.get("rows", []))} errors. Shell host restrictions and research-tool reads are separate observations. An error remains an error; it never becomes a fresh verified claim.</p><a href="data/source-health.json">Inspect full health feed</a></section>'
    return page('Verified sources', 'sources.html', body)


def build_irregularities():
    findings = load('integrity_review.json').get('findings', [])
    rows = ''.join(f'<tr><td>{esc(f["id"])}<br>{esc(f["severity"])}</td><td>{esc(f["finding"])}<br><code>{esc(f["source"])}</code></td><td>{esc(f["disposition"])}</td></tr>' for f in findings)
    body = f'''<section class="card"><h2>Blocking irregularities — no silent exceptions</h2><p>The current candidate and its receipts are quarantined. Archived evidence was not edited to manufacture a pass. This review fixes publication/orchestration, not the scientific evaluator or a new model run.</p>
<div class="table-scroll"><table><thead><tr><th>ID</th><th>Finding and source</th><th>Disposition</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="card"><h2>Additional limits and next-session order</h2>
<ol><li>Resolve the universal-positive registry conflict at the protocol/selector level. Keep the literal stop until then; do not rename, jitter or reweight an old submission to force uniqueness.</li>
<li>Authenticate source polylines, record IDs, dip/slip metadata and the sample grid. Pinned owner mirrors prove integrity, not organizer origin. Known labels equal existing_faults in this mirror; equality itself is not proof of a data defect.</li>
<li>Repair hidden-target use in the lane caller's flank mask and canary; use the one pinned shared evaluator/writer. Re-derive all catalogue features from visible faults only, then reserve untouched blocks.</li>
<li>Preregister one ranked hypothesis, compute feature-alone canaries and pooled HOLDOUT-DTI with block CIs against both comparators. Full source/input/measurement provenance is required; do not rebind old claims.</li>
<li>Run the complete two-phase registry/local-prior scan in the correct order. Re-open exact output bytes, validate, and offer a download only after every policy condition passes.</li></ol>
<p>The full feature cache is not restored in this fresh checkout. CPU suffices for this lane; a GPU is not the blocking resource. The old download_competition_data.sh/prepare_data.py instructions in the user brief do not correspond to files in this checkout.</p></section>'''
    return page('Blockers and limitations', 'irregularities.html', body)


def build_run_card():
    card = load('run_card.json')
    return page('Run card', 'run-card.html', '<section class="card"><h2>One authoritative run card</h2><p>Negative result, no new candidate or slot. Null certified holdout fields mean not measured/certified, not zero performance.</p><a href="run-card.json">Download JSON</a><pre>' + esc(json.dumps(card, indent=2, allow_nan=False)) + '</pre></section>')


def main():
    DOCS.mkdir(exist_ok=True)
    (DOCS / '.nojekyll').touch()
    card = write_card(ROOT)
    pages = {
        'index.html': build_index(), 'executive-summary.html': build_executive_summary(),
        'why-h33-scored.html': build_why_h33(), 'hypotheses.html': build_hypotheses(),
        'method.html': build_method(), 'results.html': build_results(),
        'family-audit.html': build_family(), 'sources.html': build_sources(),
        'irregularities.html': build_irregularities(), 'run-card.html': build_run_card(),
    }
    for alias in ('why-0278.html', 'why-h33-scored.html'):
        pages[alias] = pages['why-h33-scored.html']
    for name, content in pages.items():
        (DOCS / name).write_text(content)
    data = DOCS / 'data'
    data.mkdir(exist_ok=True)
    for source, name in (
        (ROOT / 'registry/verified_sources_2026-10-20.json', 'verified-sources.json'),
        (ROOT / 'evidence/registry-blocker.json', 'registry-blocker.json'),
        (ROOT / 'evidence/local-prior-audit.json', 'local-prior-audit.json'),
        (ROOT / 'evidence/h33-audit-2026-10-20.json', 'h33-audit.json'),
        (ROOT / 'evidence/validator-audit-2026-10-20.json', 'validator-audit.json'),
    ):
        if source.exists():
            shutil.copyfile(source, data / name)
    (DOCS / 'run-card.json').write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    (DOCS / 'status.json').write_text(json.dumps(evaluate(ROOT), indent=2, allow_nan=False) + '\n')
    # Pages currently serves main:/; this redirect retains a visible status for
    # clients that do not follow it. Never create a competing root policy.
    banner = submission_banner()[0].replace('href="downloads/', 'href="docs/downloads/').replace('href="executive-summary.html"', 'href="docs/executive-summary.html"')
    (ROOT / 'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE69 submission status</title><link rel="stylesheet" href="docs/assets/site.css"></head><body><main class="wrap">' + banner + '<p><a href="docs/index.html">Open project site</a></p></main></body></html>')
    print(f'Built {len(pages)} pages; downloads {"enabled" if evaluate(ROOT)["download_enabled"] else "blocked"}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
