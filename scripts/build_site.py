#!/usr/bin/env python3
"""Build the GitHub Pages site from evidence JSON (no hand-copied numbers).

Pages (Pages serves the repository root of ``main``):
  index.html                       first screen: verdict banner + download block + key numbers
  docs/index.html                  redirect to ../index.html
  docs/executive-summary.html      exactly how to submit (file, name, note, steps), verdict
  docs/method.html                 lane method, experiments, all arms with CIs
  docs/why-0278.html               research note (docs/research/why-0278.md)
  docs/hypotheses.html             ranked hypotheses (docs/research/hypotheses.md)
  docs/sources.html                verified official links
  docs/irregularities.html         irregularity register (evidence/irregularities.json)
  docs/run-card.json               copy of evidence/run_card.json
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
DOCS = ROOT / "docs"
REPO = "https://github.com/buffedlizard55-lab/GEMSDOE69"
SITE = "https://buffedlizard55-lab.github.io/GEMSDOE69/"

CSS = """
:root{--ink:#1d2433;--muted:#5b6577;--line:#e3e7ee;--bg:#f7f8fb;--ok:#0f7b3f;--okbg:#e8f6ee;--bad:#b42318;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fff6e0;--acc:#1f5fbf}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line)}.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
header .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-top:14px;padding-bottom:14px;flex-wrap:wrap}
header b{font-size:17px}nav a{color:var(--muted);text-decoration:none;margin-left:14px;font-size:14px}nav a:hover{color:var(--acc)}
main .wrap{padding-top:22px;padding-bottom:40px}h1{font-size:26px;margin:.2em 0 .4em}h2{font-size:20px;margin:1.6em 0 .5em}h3{font-size:17px}
.banner{border-radius:12px;padding:18px 20px;margin:0 0 18px;border:1px solid}.banner h2{margin:0 0 6px;font-size:21px}
.ok{background:var(--okbg);border-color:#b7e2c8;color:var(--ok)}.bad{background:var(--badbg);border-color:#f5c2bd;color:var(--bad)}.warn{background:var(--warnbg);border-color:#f0d58c;color:var(--warn)}
.banner p{color:var(--ink);margin:.35em 0}.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:14px 0}
.btn{display:inline-block;padding:10px 16px;border-radius:9px;text-decoration:none;font-weight:600;margin:6px 8px 6px 0;border:1px solid var(--line);color:var(--ink);background:#fff}
.btn.primary{background:var(--ok);border-color:var(--ok);color:#fff}.btn.danger{background:#fff;border-color:var(--bad);color:var(--bad)}
table{border-collapse:collapse;width:100%;background:#fff;font-size:14px}th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}th{background:#f1f3f8}
code{background:#eef1f6;padding:1px 5px;border-radius:5px;font-size:13px;word-break:break-all}pre{background:#0f1729;color:#e6edf7;padding:12px;border-radius:9px;overflow:auto;font-size:13px}
pre code{background:none;color:inherit}.muted{color:var(--muted);font-size:14px}.kv td:first-child{width:34%;color:var(--muted)}footer{color:var(--muted);font-size:13px;padding:24px 0}
.tag{display:inline-block;font-size:12px;font-weight:700;padding:2px 7px;border-radius:6px;background:#eef1f6;color:var(--muted);margin-right:6px}
"""

NAV = [("Home", "index.html"), ("How to submit", "docs/executive-summary.html"), ("Method & results", "docs/method.html"),
       ("Why 0.2778", "docs/why-0278.html"), ("Hypotheses", "docs/hypotheses.html"), ("Sources", "docs/sources.html"),
       ("Irregularities", "docs/irregularities.html"), ("Run card", "docs/run-card.json"), ("Repo", REPO)]


def page(title: str, body: str, depth: int) -> str:
    pre = "../" * depth
    nav = "".join(f'<a href="{(u if u.startswith("http") else pre + u)}">{html.escape(t)}</a>' for t, u in NAV)
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)} · GEMSDOE69</title><style>{CSS}</style></head><body>"
            f"<header><div class=wrap><b>GEMSDOE69 · relay-ramp &amp; pull-apart corridor lane</b><nav>{nav}</nav></div></header>"
            f"<main><div class=wrap>{body}</div></main><footer><div class=wrap>DOE GEMS Prize (DrivenData competition 306). "
            f"Every number on this site is labelled HOLDOUT-DTI (this repository's hide-and-recover instrument), OFFICIAL "
            f"(public competition page) or OWNER-REPORTED. Nothing here is an organizer-confirmed score of this repository's file. "
            f"Source: <a href='{REPO}'>{REPO}</a></div></footer></body></html>")


def firing_html(u) -> str:
    d = (u.get("dots") or {}).get("dot_overlap_firings_diagnostic") or {}
    if not d.get("firings"):
        return ""
    show = sorted([f for f in d["firings"] if not f["non_discriminating"]], key=lambda f: -f["excess_over_random"]) or d["firings"][:10]
    rows = "".join(f"<tr><td><code>{html.escape(str(f['submission']))}</code></td><td>{f['support_fraction']:.1%}</td>"
                   f"<td>{f['forward_overlap']:.3f}</td><td>{f['halo_coverage_of_allowed_domain']:.1%}</td>"
                   f"<td>{', '.join(f'{x:.3f}' for x in f['random_dots_in_our_band_overlap'])}</td><td>{f['excess_over_random']:+.3f}</td>"
                   f"<td>{'non-discriminating (random dots also exceed 0.70)' if f['non_discriminating'] else 'DISCRIMINATING'}</td></tr>" for f in show)
    return (f"<div class='banner bad'><h2>Dot-overlap rule: DUPLICATE — {d['n_firings']} firings, {d['n_discriminating_firings']} discriminating</h2>"
            f"<p>More than 70% of this file's dots lie within 3 px of the dots of {d['n_firings']} prior rasters. {d['n_non_discriminating']} of those "
            f"firings carry no information (random dots placed in the same corridor band also exceed 70% — space-filling lattices and dense "
            f"surfaces), but <b>{d['n_discriminating_firings']} are genuine</b>: our dots sit inside these denser near-catalogue emissions more "
            f"than random dots would (excess up to {d['max_excess_over_random']:+.3f}). Under the protocol this is a duplicate: logged and stopped. "
            f"The template gap for the non-discriminating cases is reported in the run card (<code>template_gap_reported</code>). "
            f"Discriminating firings:</p>"
            f"<table><tr><th>Registry raster</th><th>Support</th><th>Our dots within 3 px</th><th>Halo covers allowed domain</th>"
            f"<th>Random dots in our band</th><th>Excess over random</th><th>Reading</th></tr>{rows}</table></div>")


def fmt(x, n=4):
    return "—" if x is None else f"{x:.{n}f}"


def ci(c):
    return f"[{c[0]:.4f}, {c[1]:.4f}]"


def results_md(card, e2, e3) -> str:
    """Generated results section (numbers straight from the evidence JSON)."""
    L = ["## 5. Results (generated from `evidence/*.json`)", ""]
    e1 = json.loads((EVID / "e1_first_test.json").read_text())
    can = e1["leakage_canary"]["seed20"]
    L += ["### E1 — leakage canary (draw seed 20, pooled over quadrants)", "",
          "| Feature | AUC (withheld truth vs other pixels) |", "|---|---|"]
    L += [f"| `{k}` | {v:.3f} |" for k, v in can["pooled_auc"].items()]
    L += ["", f"Leakage flags (AUC > 0.90): **{can['leakage_flags'] or 'none'}**.", ""]
    hl = e1["hardlink_test"]["summary"]
    L += ["### E1 — hard-linked-ramp masking test", "",
          f"{hl['links_found']} catalogue links joining two traces were found; {hl['relay_admissible']} satisfy the relay rules "
          f"after masking. Mean recovery within 300 m: **{hl['mean_recall_300m']:.3f}** (kernel-weighted {hl['mean_kernel_recall']:.3f}) "
          f"versus **{hl['mean_null_recall_300m']:.3f}** for random-azimuth traces from the same tips "
          f"(links beating the null's 95th percentile: {hl['frac_links_beating_null_p95']:.1%}). Rejections: {hl['reject_reasons']}.", ""]
    pdg = e1["hardlink_test"].get("paired_diagnostic")
    if pdg:
        L += [f"Post-hoc paired view of the same rows (no new experiment): corridor traces beat the null mean on "
              f"{pdg['frac_links_recall_gt_null_mean']:.1%} of the {pdg['n']} admissible links (mean gain {pdg['mean_paired_gain']:+.3f}, "
              f"one-sided Wilcoxon p = {pdg['wilcoxon_one_sided_p']:.1e}); the 95th-percentile criterion is saturated "
              f"({pdg['frac_null_p95_saturated_at_1']:.0%} of null p95 values equal 1.0). Admissible links are short "
              f"(median {pdg['link_len_km_median']:.2f} km), so this geometric agreement is real but small in metric terms.", ""]
    L += ["### E2 — gate (HOLDOUT-DTI, pooled over two draws)", "",
          f"Evaluator `{e2['evaluator_version']}`; withheld positive pixels pooled: {card['holdout']['withheld_positive_pixels_pooled']:,}.", "",
          "| Arm | HOLDOUT-DTI | 95% CI |", "|---|---|---|"]
    for k, v in card["holdout"]["all_arms"].items():
        L.append(f"| `{k}` | {v['dti']:.4f} | [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] |")
    g = card["holdout"]["gate"]
    L += ["", f"**Gate (A_corridor − B1_halo): Δ = {g['delta']:+.4f}, 95% CI [{g['ci95'][0]:+.4f}, {g['ci95'][1]:+.4f}] → "
          f"{'PASS' if g['passed'] else 'FAIL'}.**", ""]
    ap = card["holdout"]["corridor_boost_sensitivity_AP_vs_B1"]
    L += [f"Sensitivity (corridor prior as a boost, AP − B1): Δ = {ap['delta']:+.4f}, 95% CI [{ap['ci95'][0]:+.4f}, {ap['ci95'][1]:+.4f}].", ""]
    L += ["#### Per draw and quadrant (HOLDOUT-DTI / dots)", "", "| Draw | Arm | NW | NE | SW | SE |", "|---|---|---|---|---|---|"]
    for dk, dv in e2["draws"].items():
        for arm, av in dv["arms"].items():
            cells = " | ".join(f"{r['dti']:.4f} / {r['n_dots']:,}" for r in av["folds"])
            L.append(f"| {dk} | `{arm}` | {cells} |")
    nA = sum(r["n_dots"] for dv in e2["draws"].values() for r in dv["arms"]["A_corridor"]["folds"])
    nR = sum(r["n_dots"] for dv in e2["draws"].values() for r in dv["arms"]["R_corridor_random"]["folds"])
    L += ["", f"Note on `R_corridor_random`: it was asked for as many dots as `A_corridor` in every quadrant, but 2-px Poisson-disk "
          f"spacing fits only {nR:,} of {nA:,} ({nR / nA:.0%}) inside the corridor band, so it is a density-limited random control, "
          f"not a count-matched one. Its higher DTI with fewer dots is itself the evidence that the greedy over-emits inside corridors."]
    L += ["", "### E3 — live build of the lane artefact", ""]
    d = e3["dots"]
    L += [f"* {d['n']:,} dots, {d['on_catalogue']} on the catalogue, min / median / p95 distance to the catalogue "
          f"{d['min_dist_to_catalogue_px']/10:.2f} / {d['median_dist_to_catalogue_px']/10:.2f} / {d['p95_dist_to_catalogue_px']/10:.2f} km.",
          f"* Corridors that received dots: {e3['corridors_with_dots']:,} — by setting: {e3['corridors_by_setting']}. "
          f"Per-corridor rationale: [`evidence/e3_corridor_rationale.csv`](https://github.com/buffedlizard55-lab/GEMSDOE69/blob/main/evidence/e3_corridor_rationale.csv).",
          f"* Live tip graph: {e3['live_geometry']['tip_receipt']['free_tips']:,} free tips; corridor counts {e3['live_geometry']['corridor_counts']['relay_pairs']:,} relays, "
          f"{e3['live_geometry']['corridor_counts']['pullapart_pairs']:,} pull-aparts, {e3['live_geometry']['corridor_counts']['termination_tips']:,} terminations."]
    ch = e3.get("champion_vs_corridors")
    if ch:
        L.append(f"* The owner-reported 0.2778 champion has {ch['in_corridor_band_frac']:.1%} of its dots inside our corridor band "
                 f"(the band is {ch['corridor_band_frac_of_allowed']:.1%} of the allowed area); {ch['our_dots_within_3px_of_champion']:.1%} of our dots lie within 3 px of a champion dot.")
    u = card["registry_uniqueness"]
    L += ["", "### Uniqueness (862-raster corpus, `registry/registry_index_69.json`)", "",
          "| Phase | Worst Spearman (limit 0.90) | Literal 3-px overlap | Overlap vs dot fields (template like-for-like) | Discriminating firings | Decision |",
          "|---|---|---|---|---|---|"]
    for ph in ("surface", "dots"):
        x = u[ph]
        dd = x.get("dot_overlap_firings_diagnostic") or {}
        L.append(f"| {ph} | {fmt(x['worst_spearman'],3)} ({x['worst_spearman_raster']}) | {fmt(x['worst_forward_overlap_3px'],3)} "
                 f"({x['literal_overlap_firings']} firings) | {fmt(x['worst_forward_overlap_dot_fields'],3)} "
                 f"({x['worst_forward_overlap_dot_field_raster']}) | {dd.get('n_discriminating_firings', 'n/a') if ph == 'dots' else 'n/a'} | "
                 f"{'DUPLICATE' if x['duplicate'] else 'unique'} |")
    L += ["", f"Decision rule: {u['decision_rule']}"]
    return "\n".join(L) + "\n"


def main():
    card = json.loads((EVID / "run_card.json").read_text())
    e2 = json.loads((EVID / "e2_gate.json").read_text())
    e3 = json.loads((EVID / "e3_build.json").read_text())
    DOCS.mkdir(exist_ok=True)
    shutil.copy(EVID / "run_card.json", DOCS / "run-card.json")
    promote = card["verdict"] == "promote"
    sub = card["raster"]
    zeros = sub["zeros_tif"]
    zipf = sub["zip"]
    nan = sub["nan_twin_tif"]
    g = card["holdout"]["gate"]
    sc = card["holdout"]["all_arms"]
    npos = card["holdout"]["withheld_positive_pixels_pooled"]
    ev = card["holdout"]["evaluator_version"]
    u = card["registry_uniqueness"]

    if promote:
        banner = (f"<div class='banner ok'><h2>OK TO SUBMIT — gate met, unique, validated</h2>"
                  f"<p>The lane's TIF beat the same pipeline without corridor priors on the pre-registered holdout "
                  f"(Δ HOLDOUT-DTI {g['delta']:+.4f}, 95% CI {ci(g['ci95'])}).</p>"
                  f"<a class='btn primary' href='{zeros}' download>Download submission TIF</a>"
                  f"<a class='btn' href='{zipf}' download>Download ZIP</a></div>")
    else:
        nd = (u['dots'].get('dot_overlap_firings_diagnostic') or {})
        banner = (f"<div class='banner bad'><h2>NOT OK TO SUBMIT — negative result (do not spend a weekly slot)</h2>"
                  f"<p>This session generated a <b>byte- and pixel-unique, format-valid</b> TIF for the relay-ramp / pull-apart corridor "
                  f"lane (rank correlation ≤ {max(u['surface']['worst_spearman'], u['dots']['worst_spearman']):.2f} with all "
                  f"{u['dots']['rasters_checked']} prior rasters). It is <b>not cleared</b>, for two independent reasons:</p>"
                  f"<p><b>1. Gate failed.</b> On the hide-and-recover holdout the corridor-restricted dots scored HOLDOUT-DTI "
                  f"<b>{fmt(sc['A_corridor']['dti'])}</b> {ci(sc['A_corridor']['ci95'])} versus <b>{fmt(sc['B1_halo']['dti'])}</b> "
                  f"{ci(sc['B1_halo']['ci95'])} for the same pipeline without corridor priors (Δ {g['delta']:+.4f}, paired 95% CI "
                  f"{ci(g['ci95'])}; {ev}; {npos:,} withheld positive pixels pooled over two draws).</p>"
                  f"<p><b>2. Duplicate by the dot-overlap rule.</b> More than 70% of its dots lie within 3 px of the dots of "
                  f"{nd.get('n_firings', 0)} prior rasters; {nd.get('n_discriminating_firings', 0)} of these firings are genuine (our dots "
                  f"overlap more than random dots in the same corridor band would).</p>"
                  f"<p>Per the protocol, the file is <b>not offered as a submission</b>. It is kept below, clearly labelled, as the "
                  f"negative-result deliverable so the result can be audited.</p></div>")
    neg_block = "" if promote else (
        f"<div class='card'><span class=tag>NEGATIVE-RESULT ARCHIVE · DO NOT SUBMIT</span>"
        f"<p class=muted>Valid GeoTIFF (float32, EPSG:32611, 100 m, values in [0,1], zero NaN inside the footprint) kept only "
        f"for audit and for future selector comparisons.</p>"
        f"<a class='btn danger' href='{zeros}' download>Archive TIF (do not submit)</a>"
        f"<a class='btn' href='{nan}' download>NaN-outside twin (do not submit)</a>"
        f"<a class='btn' href='{zipf}' download>Archive ZIP</a></div>")
    rows = "".join(f"<tr><td><code>{k}</code></td><td>{fmt(v['dti'])}</td><td>{ci(v['ci95'])}</td></tr>" for k, v in sc.items())
    uq = (f"<tr><td>Pre-placement surface</td><td>{u['surface']['rasters_checked']}</td><td>{fmt(u['surface']['worst_spearman'],3)}</td>"
          f"<td>n/a (surface phase judged by rank correlation)</td><td>{fmt(u['surface']['worst_forward_overlap_3px'],3)} "
          f"({u['surface']['literal_overlap_firings']} firings)</td><td>{'DUPLICATE' if u['surface']['duplicate'] else 'unique'}</td></tr>"
          f"<tr><td>Final dots</td><td>{u['dots']['rasters_checked']}</td><td>{fmt(u['dots']['worst_spearman'],3)}</td>"
          f"<td>{fmt(u['dots']['worst_forward_overlap_dot_fields'],3)} vs {u['dots']['dot_field_rasters']} dot-field rasters</td>"
          f"<td>{fmt(u['dots']['worst_forward_overlap_3px'],3)} ({u['dots']['literal_overlap_firings']} firings, "
          f"{'all continuous surfaces' if u['dots']['literal_firings_all_continuous_surfaces'] else 'incl. dot fields'})</td>"
          f"<td>{'DUPLICATE' if u['dots']['duplicate'] else 'unique'}</td></tr>")
    body = (f"{banner}<h1>Relay-ramp and pull-apart corridor generator</h1>"
            f"<p>Candidate faults proposed from the <b>geometry of the mapped catalogue</b>: same-dip relay ramps between facing fault "
            f"tips (W 0.1–15 km, |L| ≤ 3.5 W), pull-aparts at strike-slip releasing steps and transfer zones at strike-slip "
            f"terminations; scored by multi-scale gravity / magnetic edges, magnetic lows, lidar scarps and dilation tendency; dots placed "
            f"by the shared template's calibrated greedy marginal-DTI allocator.</p>"
            f"{neg_block}"
            f"<div class=card><img src='docs/img/overview.png' alt='Corridor band and lane dots over the mapped catalogue' style='width:100%;border-radius:8px'>"
            f"<p class=muted>Grey: mapped catalogue (USGS/INGENIOUS). Blue: corridor band (relay, pull-apart and transfer traces). "
            f"Red: the lane's dots. Downsampled 4x for display.</p></div>"
            f"<h2>Holdout results (pooled over two draws)</h2><p class=muted>HOLDOUT-DTI · evaluator <code>{ev}</code> · {npos:,} withheld "
            f"positive pixels · 95% CI = paired 20 km spatial-block bootstrap (1,000 draws). Not leaderboard scores.</p>"
            f"<table><tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>{rows}</table>"
            f"<p class=muted><code>A_corridor</code> = the lane · <code>B1_halo</code> = the same pipeline without corridor priors (gate "
            f"comparator) · <code>AP_halo_corridor</code> = corridor prior used as a boost (sensitivity) · <code>B0</code> evidence only · "
            f"<code>C</code> distance only · <code>R</code> random dots inside the corridors.</p>"
            f"<h2>Uniqueness against every prior raster</h2><table><tr><th>Phase</th><th>Rasters checked</th><th>Worst Spearman (limit 0.90)</th>"
            f"<th>Worst 3-px overlap vs dot fields (limit 0.70)</th><th>Literal 3-px overlap incl. continuous surfaces (degenerate)</th><th>Result</th></tr>{uq}</table>"
            f"<p class=muted>A registry raster that is positive on (almost) the whole footprint lies within 3 px of every possible dot, so the "
            f"literal overlap test cannot discriminate against it; the template's like-for-like reading applies the 70% rule to dot-field rasters "
            f"(support ≤ 20% of the footprint) and the 0.90 rank-correlation rule to every raster. Both readings are in "
            f"<a href='evidence/e3_uniqueness.json'>evidence/e3_uniqueness.json</a>.</p>"
            f"{firing_html(u)}"
            f"<h2>File facts</h2><table class=kv>"
            f"<tr><td>Submission name</td><td><code>{html.escape(card['submission_name'])}</code></td></tr>"
            f"<tr><td>Note ({card['submission_note_chars']} chars)</td><td><code>{html.escape(card['submission_note'])}</code></td></tr>"
            f"<tr><td>Primary file (zeros outside footprint)</td><td><code>{zeros}</code><br>sha256 <code>{sub['zeros_sha256']}</code></td></tr>"
            f"<tr><td>NaN-outside twin</td><td><code>{nan}</code><br>sha256 <code>{sub['nan_twin_sha256']}</code></td></tr>"
            f"<tr><td>Dots</td><td>{sub['dots']['n']:,} (0 on the catalogue; median {fmt(sub['dots']['median_dist_to_catalogue_px']/10,2)} km from it)</td></tr>"
            f"<tr><td>Verdict</td><td><b>{card['verdict'].upper()}</b> — {html.escape(card['verdict_reason'])}</td></tr></table>"
            f"<h2>Read next</h2><p><a href='docs/executive-summary.html'>How to submit (exact steps)</a> · "
            f"<a href='docs/method.html'>Method &amp; results</a> · <a href='docs/why-0278.html'>Why 0.2778 scored best</a> · "
            f"<a href='docs/run-card.json'>Run card (JSON)</a></p>")
    (ROOT / "index.html").write_text(page("Home", body, 0))
    (DOCS / "index.html").write_text("<!doctype html><meta charset=utf-8><meta http-equiv=refresh content='0; url=../index.html'>"
                                     "<a href='../index.html'>GEMSDOE69 home</a>")

    # executive summary / how to submit
    status = ("<div class='banner ok'><h2>This file is cleared: OK to submit</h2></div>" if promote else
              "<div class='banner bad'><h2>Current status: NOT OK TO SUBMIT</h2><p>The only file this session produced failed its "
              "pre-registered gate. Submitting it would spend one of the 3 weekly slots on an idea that did not beat the holdout "
              "baseline. The steps below are the exact procedure for any cleared file (and for this one, if the selector ever "
              "overrides the verdict).</p></div>")
    es = (f"{status}<h1>Executive summary — how to make a submission</h1>"
          f"<div class=card><ol>"
          f"<li>Sign in at <a href='https://www.drivendata.org/competitions/306/competition-doe-gems/'>drivendata.org/competitions/306</a> "
          f"with the account registered for the competition and open the <a href='https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/'>Submissions</a> tab.</li>"
          f"<li>Download the file: <a href='../{zeros}' download><code>{zeros.split('/')[-1]}</code></a> (or the one-file ZIP "
          f"<a href='../{zipf}' download><code>{zipf.split('/')[-1]}</code></a>). Do not open and re-save it in GIS software.</li>"
          f"<li>Upload the <code>.tif</code> (or the <code>.zip</code>) in the submission form.</li>"
          f"<li>Submission name (unique): <code>{html.escape(card['submission_name'])}</code></li>"
          f"<li>Note (≤ 140 characters, {card['submission_note_chars']} used): <code>{html.escape(card['submission_note'])}</code></li>"
          f"<li>Submit, then copy the returned score into the repo ledger as ORGANIZER-CONFIRMED with the file's sha256 "
          f"<code>{sub['zeros_sha256']}</code>.</li></ol></div>"
          f"<h2>Why the “Predicted values must be in range [0, 1]” error cannot occur with this file</h2>"
          f"<div class=card><p>The family's root-cause analysis (GEMSDOE32 <code>docs/research/range-error-root-cause-2026-10-03.md</code>; "
          f"not organizer-confirmed) traced that rejection to values outside [0, 1] where the portal reads the raster: the feature "
          f"stack's sentinel <code>-3.4e38</code> leaking into a file, or NaN cells inside the scored footprint. The "
          f"primary file is written by the shared fail-closed writer: <b>every cell is finite</b>, the footprint holds only 0.0 and "
          f"1.0, cells outside the footprint are 0.0, and there is <b>no nodata tag</b> — the same encoding as the organizer's "
          f"reference solution (<a href='https://github.com/drivendataorg/gems-prize-reference-solution'>drivendataorg/gems-prize-reference-solution</a>) "
          f"and as the family's best-scored file. Validator: {'PASS' if all(v['all_checks_passed'] for v in card['validator_output'].values()) else 'FAIL'} "
          f"on both encodings (<a href='../evidence/e3_validation.json'>evidence/e3_validation.json</a>).</p></div>"
          f"<h2>Rules that matter</h2><div class=card><ul><li>Format: single-band float32 GeoTIFF, EPSG:32611, 100 m, same grid as "
          f"<code>sample_submission.tif</code>, values in [0, 1] (<a href='https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/'>problem description</a>).</li>"
          f"<li>Metric: distance-weighted Tversky index, α = 0.2, β = 0.8, 300 m triangular kernel; known USGS/INGENIOUS fault pixels are "
          f"masked from scoring (<a href='https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516'>organizer forum answer</a>).</li>"
          f"<li>Three submissions per week; a single selected entry is scored in both prize phases; generative-AI use is allowed but "
          f"must be disclosed in the finalist narrative; finalists deliver reproducible code and documentation "
          f"(<a href='https://www.nlr.gov/docs/fy26osti/96647.pdf'>official rules</a>, §1.1 and §3.2, linked from "
          f"<a href='https://www.herox.com/GEMSPrize/resource/2274'>HeroX</a>).</li></ul></div>"
          f"<h2>Bottom line</h2><div class=card><p><b>{card['verdict'].upper()}.</b> {html.escape(card['verdict_reason'])} "
          f"Live context: public #1 is 0.4275 (2026-10-12); the family's best owner-reported score is 0.2778.</p></div>")
    (DOCS / "executive-summary.html").write_text(page("How to submit", es, 1))

    # markdown pages
    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    (ROOT / "docs/research/method.md").write_text((ROOT / "docs/research/method_narrative.md").read_text() + "\n" + results_md(card, e2, e3))
    for src, out, title in ((ROOT / "docs/research/why-0278.md", DOCS / "why-0278.html", "Why 0.2778"),
                            (ROOT / "docs/research/hypotheses.md", DOCS / "hypotheses.html", "Hypotheses"),
                            (ROOT / "docs/research/method.md", DOCS / "method.html", "Method & results"),
                            (ROOT / "docs/research/sources.md", DOCS / "sources.html", "Sources")):
        if src.exists():
            out.write_text(page(title, md.reset().convert(src.read_text()), 1))
    irr = json.loads((EVID / "irregularities.json").read_text())
    rows = "".join(f"<tr><td><code>{html.escape(r['id'])}</code></td><td>{html.escape(r['severity'])}</td><td>{html.escape(r['finding'])}</td>"
                   f"<td>{html.escape(r['handling'])}</td></tr>" for r in irr["items"])
    (DOCS / "irregularities.html").write_text(page("Irregularities", f"<h1>Irregularity register</h1><table><tr><th>ID</th><th>Severity</th>"
                                                    f"<th>Finding</th><th>Handling</th></tr>{rows}</table>", 1))
    (ROOT / ".nojekyll").write_text("")
    print("site built:", SITE)


if __name__ == "__main__":
    main()
