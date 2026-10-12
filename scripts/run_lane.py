#!/usr/bin/env python3
"""GEMSDOE69 lane runner.  Three experiments, no more (parallel-run protocol budget).

  e1  first test   : leakage canary (each feature alone, AUC) + hard-linked-ramp
                     masking test (recover the masked linking fault within 300 m)
  e2  gate         : pooled HOLDOUT-DTI of every arm on the shared hide-and-recover
                     instrument (template evaluator, paired spatial-block CIs)
  e3  build        : live emission on the full catalogue (only the artefact; the
                     verdict comes from e2), written by the template writer

Every number written by e1/e2 is HOLDOUT-DTI or a diagnostic; nothing here is a
leaderboard score.  Outputs go to ``evidence/``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems69 import calibrate, corridors, pipeline, traces  # noqa: E402
from gems57 import emit, evaluate_holdout, holdout  # noqa: E402

EVID = ROOT / "evidence"
SEEDS = (20, 21)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def dump(name, obj):
    EVID.mkdir(exist_ok=True)
    (EVID / name).write_text(json.dumps(obj, indent=1, default=float))


def removed_mask(fold0):
    hidden = fold0["hidden_all"]
    return ndi.distance_transform_edt(~hidden) <= 3


# ----------------------------------------------------------------------------------------- E1
def hardlink_test(ctx, n_null: int = 50, seed: int = 7) -> dict:
    """Mask catalogue linking faults of hard-linked ramps; test 300 m recovery."""
    polys = traces.visible_polys(ctx.parts, None)
    idx = corridors.PolyIndex(polys)
    rng = np.random.default_rng(seed)
    H, W = ctx.fp.shape
    rows = []
    for ci, qc in enumerate(polys):
        Lc = traces.poly_length(qc.verts)
        if not (2.0 <= Lc <= 50.0):
            continue
        ends = (qc.verts[0], qc.verts[-1])
        attach = []
        for e in ends:
            near = idx.tree.query_ball_point(e, 2.5)
            owners = sorted({int(idx.owner[k]) for k in near} - {ci})
            attach.append(owners)
        if not attach[0] or not attach[1]:
            continue
        pairs = [(a, b) for a in attach[0] for b in attach[1] if a != b]
        if not pairs:
            continue
        a, b = pairs[0]
        # tips that appear on A and B once C is masked (no other polyline within 2.5 px)
        tip_objs = []
        for owner, e in ((a, ends[0]), (b, ends[1])):
            qa = polys[owner]
            d0 = np.hypot(*(qa.verts[0] - e))
            d1 = np.hypot(*(qa.verts[-1] - e))
            at_end = d1 < d0
            pos = qa.verts[-1] if at_end else qa.verts[0]
            if min(d0, d1) > 3.0 or traces.poly_length(qa.verts) < 3.0:
                tip_objs = None
                break
            near = idx.tree.query_ball_point(pos, 2.5)
            if any(int(idx.owner[k]) not in (owner, ci) for k in near):
                tip_objs = None
                break
            out = traces._outward(qa.verts, at_end)
            dvec = None
            if qa.part.dip_side != 0:
                d = out if at_end else -out
                dvec = qa.part.dip_side * np.array([d[1], -d[0]])
            tip_objs.append(traces.Tip(len(tip_objs), owner, pos.copy(), out, qa.part.sense, dvec,
                                       qa.part.dip_source, qa.part.length, False, qa.part.record))
        if not tip_objs:
            continue
        ok, why = corridors._pair_ok(tip_objs[0], tip_objs[1])
        # link pixels (truth for this test)
        s = traces.sample_polyline(qc.verts, 0.25)
        r, c = traces.rc_of(s)
        inside = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        r, c = r[inside], c[inside]
        if r.size == 0 or not ctx.fp[r, c].all():
            continue
        link = np.unique(np.stack([r, c], 1), axis=0)
        u = corridors._unit(tip_objs[0].out - tip_objs[1].out)
        ang = np.degrees(np.arccos(min(1.0, abs(float(corridors._unit(qc.verts[-1] - qc.verts[0]) @ u)))))
        row = dict(link_poly=ci, link_record=int(qc.part.record), link_len_km=Lc / 10,
                   A_record=int(polys[a].part.record), B_record=int(polys[b].part.record),
                   relay_admissible=ok, reject_reason=None if ok else why, link_obliquity_deg=float(ang))
        if ok:
            sub = [tip_objs[0], tip_objs[1]]
            lines, _ = corridors.generate(sub, polys)
            lines = [ln for ln in lines if ln.setting in ("relay", "pullapart")]
            P = np.vstack([traces.sample_polyline(np.vstack([ln.a, ln.b]), 0.25) for ln in lines]) if lines else np.zeros((0, 2))

            def recall(points):
                if len(points) == 0:
                    return 0.0, 0.0
                lr, lc = traces.rc_of(points)
                from scipy.spatial import cKDTree
                tr = cKDTree(np.stack([lr, lc], 1))
                d, _ = tr.query(link.astype(float))
                return float((d <= 3).mean()), float(np.clip(1 - d / 3.0, 0, 1).mean())
            rec300, kern = recall(P)
            # null: same tips, same number and lengths of traces, random azimuths
            nulls = []
            for _ in range(n_null):
                pts = []
                for ln in lines:
                    L = float(np.hypot(*(ln.b - ln.a)))
                    th = rng.uniform(0, 2 * np.pi)
                    start = tip_objs[rng.integers(0, 2)].pos
                    pts.append(traces.sample_polyline(np.vstack([start, start + L * np.array([np.sin(th), np.cos(th)])]), 0.25))
                nulls.append(recall(np.vstack(pts))[0] if pts else 0.0)
            row.update(n_traces=len(lines), recall_300m=rec300, kernel_recall=kern,
                       null_recall_300m_mean=float(np.mean(nulls)), null_recall_300m_p95=float(np.quantile(nulls, 0.95)))
        rows.append(row)
    adm = [r for r in rows if r["relay_admissible"]]
    summary = dict(links_found=len(rows), relay_admissible=len(adm),
                   reject_reasons={k: sum(1 for r in rows if r["reject_reason"] == k) for k in {r["reject_reason"] for r in rows if r["reject_reason"]}},
                   mean_recall_300m=float(np.mean([r["recall_300m"] for r in adm])) if adm else None,
                   mean_kernel_recall=float(np.mean([r["kernel_recall"] for r in adm])) if adm else None,
                   mean_null_recall_300m=float(np.mean([r["null_recall_300m_mean"] for r in adm])) if adm else None,
                   frac_links_recall_ge_0p5=float(np.mean([r["recall_300m"] >= 0.5 for r in adm])) if adm else None,
                   frac_links_beating_null_p95=float(np.mean([r["recall_300m"] > r["null_recall_300m_p95"] for r in adm])) if adm else None)
    return dict(summary=summary, rows=rows)


def e1(args):
    ctx = pipeline.Context()
    out = dict(experiment="E1 first test", started=now(), evidence_class="DIAGNOSTIC (feature AUC on HOLDOUT truth; not a score)",
               dip_receipt=ctx.dip_receipt)
    canary = {}
    band_hits = {}
    for seed in SEEDS[:1]:
        folds, quad = holdout.buffered_component_draw(ctx.grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        geo = pipeline.geometry(ctx, visible, removed_mask(folds[0]))
        d_vis = ndi.distance_transform_edt(~visible).astype(np.float32)
        feats = dict(grav_edge=ctx.layers["grav_edge"], mag_edge=ctx.layers["mag_edge"],
                     mag_low=ctx.layers["mag_low"], scarp=ctx.layers["scarp"], e_pix=ctx.e_pix,
                     neg_dist_visible_catalogue=-d_vis, corridor_score_band=geo["s_band"],
                     neg_dist_corridor_trace=-geo["dline"], neg_dist_visible_tip=-geo["d_tip"])
        rng = np.random.default_rng(seed)
        pooled = {k: ([], []) for k in feats}
        per_fold = []
        for f in folds:
            active = ctx.fp & f["region"] & ~f["masked_known"]
            pos_idx = np.flatnonzero((active & f["truth"]).ravel())
            neg_all = np.flatnonzero((active & ~f["truth"]).ravel())
            neg_idx = rng.choice(neg_all, size=min(300_000, neg_all.size), replace=False)
            row = dict(fold=f["name"], n_truth=int(pos_idx.size))
            for k, v in feats.items():
                fv = v.ravel()
                row[k] = pipeline.auc(fv[pos_idx], fv[neg_idx])
                pooled[k][0].append(fv[pos_idx]); pooled[k][1].append(fv[neg_idx])
            per_fold.append(row)
            band = geo["s_band"] > 0
            band_hits[f["name"]] = dict(
                truth_in_band=float((band & f["truth"] & active).sum() / max(1, (f["truth"] & active).sum())),
                band_fraction_of_active=float((band & active).sum() / max(1, active.sum())))
        pooled_auc = {k: pipeline.auc(np.concatenate(a), np.concatenate(b)) for k, (a, b) in pooled.items()}
        canary[f"seed{seed}"] = dict(per_fold=per_fold, pooled_auc=pooled_auc,
                                    leakage_flags=[k for k, v in pooled_auc.items() if v > 0.90],
                                    tip_receipt=geo["tip_receipt"], corridor_counts=geo["corridor_counts"],
                                    band_vs_truth=band_hits)
    out["leakage_canary"] = canary
    out["hardlink_test"] = hardlink_test(ctx)
    out["finished"] = now()
    dump("e1_first_test.json", out)
    print(json.dumps({k: out[k] for k in ("dip_receipt",)}, indent=1))
    print(json.dumps(canary, indent=1)[:4000])
    print(json.dumps(out["hardlink_test"]["summary"], indent=1))


# ----------------------------------------------------------------------------------------- E2
def run_arm(arm, ctx, geo, folds, d_vis, allowed_base, seed, a_counts=None):
    terms_sum = None
    fold_rows = []
    for k, f in enumerate(folds):
        train = np.zeros(ctx.fp.shape, bool)
        for j, g in enumerate(folds):
            if j != k:
                train |= allowed_base & g["region"]
        test = allowed_base & f["region"]
        truth_train = f["hidden_all"] & train
        if arm == "R_corridor_random":
            band_ok = test & (geo["s_band"] > 0)
            n = a_counts[k] if a_counts else 0
            emitted = pipeline.poisson_random(band_ok, n, seed * 100 + k)
            calib = dict(n_requested=n)
            alloc_info = dict(n_dots=int(emitted.sum()))
        else:
            code, n_codes, _edges = pipeline._codes(arm, ctx, geo, d_vis, train)
            cand_train = train
            cand_test = test
            if arm == "A_corridor":
                cand_train = train & (geo["s_band"] > 0)
                cand_test = test & (geo["s_band"] > 0)
            rate, calib = calibrate.fit_rates(code, truth_train, cand_train, n_codes)
            p = np.zeros(ctx.fp.shape, np.float32)
            p[cand_test] = rate[code[cand_test]]
            k_truth = pipeline.K_TRUTH_RATIO * float((f["visible"] & f["region"]).sum())
            alloc = emit.greedy_allocate(p, cand_test, k_truth)
            emitted = alloc.emitted
            alloc_info = dict(n_dots=alloc.n_dots, surrogate_dti=alloc.surrogate_dti, rounds=alloc.rounds,
                              k_truth_estimate=k_truth)
            del p, code
        res, terms = evaluate_holdout.evaluate(emitted.astype(np.float32), f, ctx.fp)
        terms_sum = terms if terms_sum is None else terms_sum + terms
        fold_rows.append(dict(fold=f["name"], dti=res["dti"], n_truth=res["n_truth"], tpw=res["tpw"],
                              fpw=res["fpw"], fnw=res["fnw"], n_dots=int(emitted.sum()),
                              calibration=calib, allocation=alloc_info))
    return terms_sum, fold_rows


def e2(args):
    ctx = pipeline.Context()
    out = dict(experiment="E2 gate", started=now(), evaluator_version=evaluate_holdout.VERSION,
               evaluator_hashes=evaluate_holdout.implementation_hashes(), seeds=list(SEEDS[:args.draws]),
               arms=list(pipeline.ARMS), flank_px=pipeline.FLANK_PX, k_truth_ratio=pipeline.K_TRUTH_RATIO,
               gate_rule=("PASS iff pooled HOLDOUT-DTI(A_corridor) - HOLDOUT-DTI(B1_halo) > 0 with the paired "
                          "spatial-block 95% CI lower bound > 0, on every draw and pooled over draws"),
               draws={})
    all_terms = {a: None for a in pipeline.ARMS}
    for seed in SEEDS[:args.draws]:
        t0 = time.time()
        folds, quad = holdout.buffered_component_draw(ctx.grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        geo = pipeline.geometry(ctx, visible, removed_mask(folds[0]))
        d_vis = ndi.distance_transform_edt(~visible).astype(np.float32)
        flank = d_vis <= pipeline.FLANK_PX
        allowed_base = ctx.fp & ~folds[0]["masked_known"] & ~flank
        draw = dict(receipts=[f["receipt"] for f in folds], tip_receipt=geo["tip_receipt"],
                    corridor_counts=geo["corridor_counts"], arms={})
        terms_by_arm = {}
        a_counts = None
        for arm in pipeline.ARMS:
            ta = time.time()
            terms, rows = run_arm(arm, ctx, geo, folds, d_vis, allowed_base, seed, a_counts)
            if arm == "A_corridor":
                a_counts = [r["n_dots"] for r in rows]
            terms_by_arm[arm] = terms
            all_terms[arm] = terms if all_terms[arm] is None else all_terms[arm] + terms
            draw["arms"][arm] = dict(folds=rows, seconds=time.time() - ta)
            print(f"seed {seed} {arm}: " + ", ".join(f"{r['fold']} {r['dti']:.4f}/{r['n_dots']}" for r in rows), flush=True)
        draw["pooled"] = evaluate_holdout.pooled_summary(terms_by_arm, candidate="A_corridor")
        draw["pooled_AP_vs_B1"] = evaluate_holdout.pooled_summary(
            {"AP_halo_corridor": terms_by_arm["AP_halo_corridor"], "B1_halo": terms_by_arm["B1_halo"]},
            candidate="AP_halo_corridor")
        draw["seconds"] = time.time() - t0
        out["draws"][f"seed{seed}"] = draw
        dump("e2_gate.json", out)
        del geo, d_vis, flank, allowed_base, folds
    out["pooled_over_draws"] = evaluate_holdout.pooled_summary(all_terms, candidate="A_corridor")
    out["pooled_over_draws_AP_vs_B1"] = evaluate_holdout.pooled_summary(
        {"AP_halo_corridor": all_terms["AP_halo_corridor"], "B1_halo": all_terms["B1_halo"]}, candidate="AP_halo_corridor")
    d = out["pooled_over_draws"]["paired_differences"]["B1_halo"]
    per_draw_ok = all(out["draws"][k]["pooled"]["paired_differences"]["B1_halo"]["ci95"][0] > 0 for k in out["draws"])
    out["gate"] = dict(comparator="B1_halo", delta=d["delta"], ci95=d["ci95"], per_draw_lower_bound_positive=per_draw_ok,
                       passed=bool(d["delta"] > 0 and d["ci95"][0] > 0 and per_draw_ok))
    out["finished"] = now()
    dump("e2_gate.json", out)
    print(json.dumps(out["pooled_over_draws"]["scores"], indent=1))
    print(json.dumps(out["gate"], indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["e1", "e2"])
    ap.add_argument("--draws", type=int, default=2)
    args = ap.parse_args()
    {"e1": e1, "e2": e2}[args.cmd](args)


if __name__ == "__main__":
    main()
