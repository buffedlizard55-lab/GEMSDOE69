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


def _candidate_receipt(decision):
    cand = decision.get("candidate") or {}
    if cand.get("hypothesis") and cand.get("receipt"):
        return load(cand["receipt"]) or {}
    return {}


def submission_banner():
    """Publish only the exact hash-bound artifact cleared by scripts/release_gate.py."""
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
                '<p>No submission download is offered. This session\'s preregistered experiments are negative '
                'results (see the table below). No competition slot was used.</p><ul>' + reasons + '</ul></div>', None)
    receipt = _candidate_receipt(decision) or load("e3_receipt.json")
    tif = ROOT / receipt["raster"]["zeros"]["path"]
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tif, downloads / tif.name)
    return ('<div class="banner ok"><b>OK TO DOWNLOAD — HOLDOUT-SCREENED, UNIQUE, VALIDATED CANDIDATE.</b>'
            '<p>Every gate passed and is bound to this file\'s SHA-256. Choosing to spend a weekly slot is a '
            'separate decision (not made here).</p>'
            f'<p class="small">sha256 <code>{esc(decision["artifact_sha256"])}</code> · note: '
            f'<code>{esc(receipt.get("submission_note", ""))}</code></p></div>'
            f'<a class="btn big" href="downloads/{esc(tif.name)}" download>Download submission TIFF</a>', tif)


def _session():
    return (load("session_experiments.json") or {}).get("experiments", [])


def _fmt_d(d):
    return f"{d['mean']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]"


def _session_table():
    exps = _session()
    if not exps:
        return "<p>No session experiment summary (evidence/session_experiments.json) yet.</p>"
    rows = ""
    for e in exps:
        for ep, label in (("primary_detached", "detached (primary)"), ("secondary_all", "all (secondary)")):
            r = e["results"][ep]; pd = r["pooled_dti"]
            rows += (f"<tr><td>{esc(e['id'])}</td><td>{label}</td><td>{r['withheld_positive_px']}</td>"
                     f"<td><b>{pd[e['candidate_arm']]:.4f}</b></td><td>{pd['control_noprior']:.4f}</td>"
                     f"<td>{pd['transfer_ref']:.4f}</td><td>{_fmt_d(r['candidate_minus_control'])}</td>"
                     f"<td>{_fmt_d(r['candidate_minus_transfer_ref'])}</td>"
                     f"<td>{'<b>' + esc(e['verdict']) + '</b>' if ep == 'primary_detached' else ''}</td></tr>")
    return ("<table><tr><th>Experiment</th><th>Endpoint</th><th>Withheld px</th><th>Candidate</th><th>No-prior control</th>"
            "<th>transfer_ref (current best)</th><th>&Delta; vs control [95% CI]</th><th>&Delta; vs transfer_ref [95% CI]</th>"
            "<th>Verdict</th></tr>" + rows + "</table>"
            "<p class=\"small\">All values HOLDOUT-DTI: vendor/template66 <code>gems57.holdout</code> build_holdout + score_cell "
            "(&alpha; 0.2, &beta; 0.8, 300 m triangular kernel), seeds 20/21, pooled TP/FP/FN over 8 cells per endpoint, paired "
            "cell bootstrap (2,000, seed 20261021). Not comparable with live leaderboard values: the truth here is withheld "
            "mapped segments, not the expert-labelled new faults.</p>")


def _status_paragraph(tif):
    exps = _session()
    parts = ["This lane proposes hidden faults inside relay ramps and pull-aparts found in the mapped-fault tip graph. "
             "This session fixed a bias in the holdout instrument (IR-69-HOLD-01) and ran "
             f"{len(exps)} preregistered experiment(s)."]
    for e in exps:
        parts.append(f"{e['id']}: beats the no-corridor control (prompt gate) = {e['prompt_gate_passed']}; "
                     f"beats the current holdout best (transfer-only selector) = {e['current_best_beaten']}; "
                     f"verdict {e['verdict']}.")
    parts.append("The transfer-only selector itself is a dot-overlap duplicate of another family raster (IR-69-REG-03). " +
                 ("A candidate cleared every gate; the download above is bound to its SHA-256." if tif else
                  "No unique candidate cleared every gate, so no TIFF is offered."))
    return esc(" ".join(parts))


def build_index():
    ban, tif = submission_banner()
    body = f"""
{ban}
<div class="card"><h2>Status in one paragraph</h2><p>{_status_paragraph(tif)}</p></div>
<div class="card"><h2>Session experiments (2026-10-20, session 3)</h2>{_session_table()}</div>
<div class="card" id="how-to-submit"><h2>How to submit (applies only when the banner above is green)</h2>
<ol><li>Download the <b>-zeros</b> file from the green button (all cells finite in [0,1]: avoids the portal error
&ldquo;Predicted values must be in range [0, 1]&rdquo;).</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition 306</a> &rarr; Submissions &rarr;
upload the single <code>.tif</code> (or a <code>.zip</code> containing exactly one GeoTIFF).</li>
<li>Paste the note shown in the banner (&le;140 characters).</li></ol>
<p class="small">Full checklist: <a href="executive-summary.html">Executive summary</a>.</p></div>
<div class="card"><h2>Context numbers and their evidence class</h2><table>
<tr><th>Item</th><th>Value</th><th>Evidence class</th></tr>
<tr><td>Family best download h33-h33-2-b2 (GEMSDOE32)</td><td>0.2778</td><td>USER-REPORTED-NOT-ORGANIZER-CONFIRMED (bytes re-measured: 37,654 unit dots, sha256 c55bafc4&hellip;)</td></tr>
<tr><td>Leaderboard highs cited by the user</td><td>0.4413 / 0.3774 / 0.3195</td><td>USER-REPORTED (live leaderboard is JavaScript-rendered and could not be re-read this session)</td></tr>
<tr><td>Any lane raster</td><td>no organizer score</td><td>no slot spent</td></tr></table></div>
<div class="card"><h2>What this lane is</h2>
<p>Hidden faults proposed from <b>catalogue geometry</b>: mapped strands &rarr; tip graph (3,887 strands, 383,827 tip pairs,
117,006 de-duplicated step-overs); each step-over (spacing 0.1&ndash;15 km, along-strike separation &le;3.5W) emits an oblique
connector plus en&nbsp;&eacute;chelon strands, or a pull-apart at dilatational steps. Corridors are scored by multi-scale
horizontal-gradient and tilt evidence in gravity and magnetics (incl. magnetic lows), the lidar-scarp channel and N&ndash;NE
orientation; dots are placed by the template's greedy marginal-DTI allocator, &ge;200 m from mapped faults.</p>
<p>Verified this session in <a href="https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf">Giddens &amp; Faulds
(2025, SGP-TR-229)</a>: &gt;450 step-overs; widths 0.1&ndash;14.6 km (mean 2.8 km); ramps typically 3&ndash;3.5&times; longer than wide;
~70% of &gt;120&nbsp;&deg;C step-overs hard-linked; Walker Lane is the only domain where step-overs are <i>not</i> the most common
favorable setting, hosts no step-over power plants, and has the narrowest ramps (mean 1.9 km). The prompt's wording that Walker
Lane hot systems sit &ldquo;more often in pull-aparts and displacement-transfer zones&rdquo; is an inference, not a statement in the
paper (IR-69-SRC-01).</p></div>
"""
    return page("Home", "index.html", body)


def build_executive_summary():
    body = """
<div class="card"><h2>Executive summary &mdash; exactly how to submit</h2>
<ol>
<li><b>Only if the banner is green.</b> The banner is computed by <code>scripts/release_gate.py</code> from hash-bound evidence:
holdout gate, current-best comparison, leakage canary, uniqueness (surface and dots), validator and method manifest.</li>
<li><b>File.</b> Single-band GeoTIFF <code>.tif</code>, or a <code>.zip</code> containing exactly one GeoTIFF. Use the <b>-zeros</b>
variant: float32, EPSG:32611, 3730&times;3292, transform (100, 0, 243350, 0, &minus;100, 4508550), every value finite in [0,1].</li>
<li><b>Upload.</b> <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition 306</a> &rarr; Submissions &rarr;
choose the file &rarr; add a unique note of at most 140 characters (e.g. <code>relay-ramp corridors, k=12k dots</code>).</li>
<li><b>One final choice.</b> Per the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>,
competitors pick a <i>single</i> submission for both prize rounds; the Final round rescores against labels revised after expert review of
all submissions.</li></ol>
<h3>Portal error &ldquo;Predicted values must be in range [0, 1]&rdquo;</h3>
<p>Byte-verified causes in this family: <code>labels.tif</code>/<code>existing_faults.tif</code> carry &minus;1 in 7,111,787 outside-footprint
cells; <code>-nan</code> twins carry 7,111,787 NaN cells; <code>training_features.tif</code> carries the &minus;3.4&times;10<sup>38</sup> sentinel.
Upload only a <code>-zeros.tif</code> and run <code>scripts/validate_submission.py &lt;file&gt;</code> on the exact bytes first. (The official
format text says data outside the bounds is null or NaN; the all-finite variant is the family's portal-safe choice, IR-69-VAL-01.)</p>
<h3>Official rules verified this session (2026-10-20)</h3>
<ul>
<li>Metric: distance-weighted Tversky, &alpha; 0.2, &beta; 0.8, triangular kernel R = 300 m;
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>.</li>
<li>Known USGS/INGENIOUS fault pixels are masked from evaluation in both rounds;
<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum 11516 (staff)</a>.</li>
<li>Leaderboard is one pooled index over all public-subset pixels; final re-evaluation covers the entire GeoDAWN area;
<a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">forum 11550 (staff)</a>.</li>
<li>Phase 2 labels may be added, removed or changed; no extra fault weighting; same exclusion mask;
<a href="https://community.drivendata.org/t/questions-about-the-final-round-rules/11556">forum 11556 (staff)</a>.</li>
<li>Organizers do not disclose label data sources; Phase 2 test set updated by expert review of all Phase 1 submissions;
<a href="https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527">forum 11527 (staff)</a>.</li>
</ul>
<h3>Reproduce this session</h3>
<pre>python scripts/restore_data.py            # pinned mirrors (+ external/geodawn_rad_u8.tif, see HANDOFF)
PYTHONPATH=src:vendor/template66:vendor .venv/bin/python scripts/run_h69m.py gate      # experiment 1
PYTHONPATH=src:vendor/template66:vendor .venv/bin/python scripts/run_h69n.py gate      # experiment 2
.venv/bin/python scripts/summarize_session.py && .venv/bin/python scripts/release_gate.py
.venv/bin/python scripts/build_site69.py && .venv/bin/python scripts/build_readme.py</pre>
</div>
<div class="card"><h2>Standing limitations</h2><ul>
<li>No DrivenData login here: organizer bytes are sha256-pinned family mirrors, not organizer-authenticated (IR-69-DATA-02).</li>
<li><code>existing_faults.tif</code> &equiv; <code>labels.tif</code> in every mirror (IR-69-DATA-01).</li>
<li>HOLDOUT-DTI screens methods; it is not a leaderboard projection.</li></ul></div>
"""
    return page("Executive Summary", "executive-summary.html", submission_banner()[0] + body)


def build_why_h33():
    body = """
<div class="card"><h2>Why h33-h33-2-b2 scored 0.2778 (USER-REPORTED) &mdash; and can a unique lane raster beat it?</h2>
<p><b>The file</b> (GEMSDOE32, sha256 c55bafc4&hellip;, re-measured from bytes): 37,654 pixels equal to 1.0, zeros elsewhere; none on
the catalogue (nearest 2.24 px), median 1.97 km from it, only 5.77% within 300 m of a mapped fault &mdash; a wide, sparse dot field.</p>
<p><b>How it got there</b> (owner-reported ladder): h19-5 solid 121,131 px 0.1922 &rarr; d1.5 dotted 60,069 0.2477 &rarr; d2.8 44,090 0.2600
&rarr; h27-4-r1-solo 40,199 0.2708 &rarr; h33-2-b2 37,654 0.2778. Each step removed mass from one ranked field.</p>
<p><b>Why that works</b> (official metric, model arithmetic): for a binary dot field, adding a dot with kernel credit k raises DTI only if
k &gt; 0.2&middot;DTI (&asymp;0.056 at 0.2778). Dotting keeps most coverage of a 1-D trace at a third of the mass; dots 100&ndash;200 m from
mapped faults rarely earn credit because known faults are masked (forum 11516). So 0.2778 is near-minimal mass on a reasonably
ranked wide field &mdash; not proof of correct geology.</p>
<p><b>Can this lane beat it?</b> Not demonstrated. On the corrected holdout every corridor arm beats the no-prior control, but the
best arm (transfer-only) duplicates a GEMSDOE53 raster, and this session's unique candidates (H69-M, H69-N) do not beat it. Holdout
values (~0.03&ndash;0.05) are not comparable with 0.2778. Copying H33's dots would violate the uniqueness rule. Full write-up:
<code>docs/research/why-0278.md</code>.</p></div>
"""
    return page("Why H33 scored", "why-h33-scored.html", body)


def build_hypotheses():
    body = """
<div class="card"><h2>Untried in-lane hypotheses, ranked (full text: docs/research/hypotheses-2026-10-20-session3.md)</h2>
<table><tr><th>#</th><th>Hypothesis</th><th>Layers &rarr; signature</th><th>Why off-catalogue / difference / mimic</th><th>Cost &middot; expected gain</th></tr>
<tr><td>1</td><td>Domain-conditioned ramp geometry</td><td>tip graph + geodetic shear/dilatation (bands 7, 8) &rarr; likelihood of W and
length/width under the domain's measured population (Walker Lane mean 1.9 km, CNSB 3.5 km; aspect 3&ndash;3.5&times;)</td><td>linking faults in
ramps that match the regional population; every selector so far used one global 2.8 km target; mimic: en &eacute;chelon folds</td><td>low &middot; low&ndash;medium</td></tr>
<tr><td>2</td><td>Buried basement step under the connector</td><td>basement depth (band 15) + conductive surface (band 17) HG/tilt, computed but
never used in corridor scoring</td><td>buried beneath basin fill, no scarp; mimic: depositional basin shape, conductive playa clays</td><td>low &middot; medium (uncertain)</td></tr>
<tr><td>3</td><td>Self-supervised linkage style</td><td>visible hard-linked ramps &rarr; learned link position/style emitted in soft-linked ramps</td><td>recovery test
exists only as validation; mimic: mapping convention; fit on visible catalogue only</td><td>medium &middot; medium</td></tr>
<tr><td>4</td><td>Seismicity-aligned linkage</td><td>earthquake density (bands 10, 16) along connector vs flanks</td><td>blind active linkage; mimic: swarms;
km-scale epicentre error</td><td>low &middot; low</td></tr>
<tr><td>5</td><td>1 m lidar scarp confirmation in top corridors</td><td>organizer 1 m DEM links / USGS 3DEP</td><td><b>not obtainable in this sandbox</b>
(no USGS/DrivenData egress); listed for a session with access</td><td>high &middot; unknown</td></tr></table>
<p>Tested this session: H69-M (evidence-first, global top-1,200) and H69-N (evidence-first with 20 km tile quota) &mdash; see Experiments.</p></div>
"""
    return page("Hypotheses", "hypotheses.html", body)


def build_results():
    blocks = ""
    for cid, arm in (("h69m", "h69m_evidence_first"), ("h69n", "h69n_evidence_quota")):
        g = load(f"{cid}_gate.json")
        if not g:
            continue
        arms = list(next(iter(g["per_cell"].values())).keys())
        head = "".join(f"<th>{esc(a)}</th>" for a in arms)
        rows = ""
        for k in sorted(g["per_cell"]):
            c = g["per_cell"][k]
            rows += (f"<tr><td>{esc(k)}</td><td>{c[arms[0]]['n_truth']}</td>" +
                     "".join(f"<td>{c[a]['dti']:.4f} <span class=\"small\">({c[a]['n_dots']})</span></td>" for a in arms) + "</tr>")
        u = load(f"{cid}_uniqueness_surface.json") or {}
        blocks += (f"<div class=\"card\"><h2>{esc(g['hypothesis'])}</h2>"
                   f"<p>Preregistration <code>{esc(g['preregistration'])}</code>. prompt_gate_passed = <b>{g['prompt_gate_passed']}</b>, "
                   f"current_best_beaten = <b>{g['current_best_beaten']}</b>, canary_ok = <b>{g['canary_ok']}</b> "
                   f"(worst AUC {max(g['canary_worst_auc'].values()):.3f}).</p>"
                   f"<table><tr><th>Cell</th><th>Withheld px</th>{head}</tr>{rows}</table>"
                   "<p class=\"small\">HOLDOUT-DTI per cell (dots placed in parentheses).</p>"
                   + (f"<p>Surface uniqueness (pre-placement): worst Spearman {u.get('worst_spearman'):.3f} vs "
                      f"{u.get('corpus', {}).get('compared')} rasters (registry v2 + own submissions); stop_required = "
                      f"{u.get('stop_required')}.</p>" if u else "") + "</div>")
    body = (f"<div class=\"card\"><h2>Session 3 summary</h2>{_session_table()}</div>" + blocks +
            "<div class=\"card\"><h2>Archived lane numbers</h2><p>Every holdout number archived before this session (e.g. transfer-only "
            "0.00847, control 0.00215, H69-J 0.0059) was produced with an allowed mask that excluded pixels near the <i>withheld</i> truth "
            "(IR-69-HOLD-01). They are biased low and are not comparable with the table above.</p></div>")
    return page("Experiments", "results.html", body)


def build_sources():
    body = """
<div class="card"><h2>Sources (fetched and checked 2026-10-20 unless marked)</h2>
<table><tr><th>Source</th><th>What was verified</th></tr>
<tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description</a></td><td>metric formula, &alpha;/&beta;, 300 m kernel; submission format; single selected submission for both rounds; Final round rescoring on expanded labels</td></tr>
<tr><td><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Forum 11516</a></td><td>known faults masked in both rounds (staff)</td></tr>
<tr><td><a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">Forum 11550</a></td><td>pooled leaderboard index; final on whole GeoDAWN area (staff)</td></tr>
<tr><td><a href="https://community.drivendata.org/t/questions-about-the-final-round-rules/11556">Forum 11556</a></td><td>Phase 2 labels can be added/removed/changed; no extra weighting (staff)</td></tr>
<tr><td><a href="https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527">Forum 11527</a></td><td>label sources not disclosed (staff)</td></tr>
<tr><td><a href="https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf">Giddens &amp; Faulds 2025, SGP-TR-229</a></td><td>abstract, &sect;3, &sect;6.1, &sect;6.2 statistics quoted on Home / Hypotheses</td></tr>
<tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></td><td><b>not verifiable</b>: page renders by JavaScript; values on this site are USER-REPORTED</td></tr>
<tr><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution</a></td><td>grid constants (earlier sessions)</td></tr>
<tr><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a>, <a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS</a>, <a href="https://epsg.io/32611">EPSG:32611</a></td><td>manual-review references (not re-fetched)</td></tr>
</table>
<p class="small">Data: sha256-pinned family mirrors (<code>registry/data_manifest_gemsdoe32.json</code>), not organizer-authenticated.
Registry: <code>registry/registry_index_69_v2.json</code> (942 grid rasters, complete scan 2026-10-20).</p></div>
"""
    return page("Sources", "sources.html", body)


def build_irregularities():
    rows = ""
    for line in (ROOT / "FLAGGED.md").read_text().splitlines():
        if line.startswith("| IR-"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:
                rows += (f"<tr><td>{esc(cells[0])}</td><td>{esc(cells[1])}</td><td>{esc(cells[2])}</td>"
                         f"<td>{esc(cells[3])}</td></tr>")
    body = ("<div class=\"card\"><h2>Irregularities flagged for review (rendered from FLAGGED.md)</h2>"
            "<table><tr><th>ID</th><th>Finding</th><th>Severity</th><th>Resolution</th></tr>" + rows +
            "</table><p class=\"small\">Long-form entries (IR-69-REG-02, DUP-01, GATE-02, LB-01, CAP-01, HIST-01) are in "
            "FLAGGED.md.</p></div>")
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
