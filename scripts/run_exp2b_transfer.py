#!/usr/bin/env python3
"""Exp2b transfer-only holdout (registry/preregistration-2026-10-20-exp2b-transfer.json).

Same instrument/cells as Exp1 (scripts/run_relayfix_20261020.py gate);
comparators read from evidence/relayfix_gate.json per-cell receipts.
Emission (--emit) writes the TIF from the precheck-frozen full-catalogue
surface/dots in /tmp/gems69_relayfix (surface_transfer.npy/dots_transfer.npy).
"""
from __future__ import annotations
import datetime as dt, hashlib, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "vendor" / "template66")); sys.path.insert(0, str(ROOT / "vendor"))
EVIDENCE = ROOT / "evidence"; TMP = Path("/tmp/gems69_relayfix")

def utcnow(): return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
def log(m): print(f"[{utcnow()}] {m}", flush=True)
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

def transfer_corridors(catalogue, strands, shape, max_corridors=1200):
    from gems69.corridors import build_tip_pairs, corridor_from_pair, _priority, _pair_key
    pairs = build_tip_pairs(strands, catalogue)
    seen, chosen = set(), []
    for p in sorted(pairs, key=_priority):
        k = _pair_key(p)
        if k in seen: continue
        seen.add(k)
        if bool(p.dilatational): continue
        chosen.append(p)
        if len(chosen) >= max_corridors: break
    return [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(chosen)], chosen

def _auc(pos, neg):
    from scipy.stats import rankdata
    a = np.asarray(pos, float); b = np.asarray(neg, float)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if a.size < 10 or b.size < 10: return None
    r = rankdata(np.concatenate([a, b]))
    return float((r[:a.size].sum() - a.size*(a.size+1)/2) / (a.size*b.size))

def cmd_gate() -> int:
    from scipy import ndimage as ndi
    from gems57 import holdout as thold
    from gems57.emit import greedy_allocate
    from gems69.holdout69 import load_template_grid, cell_allowed
    from gems69.physics import build_layer_stats, build_z_stack, corridor_evidence_from_z
    from gems69.tips import vectorize
    from gems69.scoring import build_propensity, score_corridor
    t_all = time.time()
    exp1 = json.loads((EVIDENCE / "relayfix_gate.json").read_text())
    g = load_template_grid(); shape = g.footprint.shape
    stats = build_layer_stats(g.footprint); zstack = build_z_stack(g.footprint, stats)
    ctx = thold.build_holdout(g, seeds=(20, 21), modes=("all",))
    offcat = ndi.distance_transform_edt(~g.catalogue) > 2
    rng_can = np.random.default_rng(20261022)
    per_cell, canary = {}, []
    for cell in ctx.cells:
        t0 = time.time()
        visible = ctx.visible(cell.key)
        strands = vectorize(visible)
        corridors, chosen = transfer_corridors(visible, strands, shape)
        for c in corridors: score_corridor(c, corridor_evidence_from_z(zstack, c), version="v1")
        p = build_propensity(corridors, shape)
        ty = cell.truth_yx[0] + cell.bbox[0].start; tx = cell.truth_yx[1] + cell.bbox[1].start
        is_truth = np.zeros(shape, bool); is_truth[ty, tx] = True
        ny_all, nx_all = np.nonzero(cell_allowed(cell, shape) & ~is_truth); del is_truth
        sel = rng_can.choice(len(ny_all), size=min(50_000, len(ny_all)), replace=False)
        canary.append(_auc(p[ty, tx], p[ny_all[sel], nx_all[sel]]))
        allowed = cell_allowed(cell, shape) & offcat
        alloc = greedy_allocate(p, allowed & (p > 0), cell.n_truth, floor=0.05, max_dots=250_000, candidate_cap=300_000)
        r = thold.score_cell(cell, alloc.emitted)
        per_cell[cell.key] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"], n_truth=cell.n_truth,
                                  n_dots=int((alloc.emitted & allowed).sum()), n_corridors=len(corridors))
        log(f"cell {cell.key}: transfer={r['dti']:.4f} v1={exp1['per_cell'][cell.key]['corridor_v1']['dti']:.4f} "
            f"ctrl={exp1['per_cell'][cell.key]['control_noprior']['dti']:.4f} ({time.time()-t0:.0f}s)")
        del corridors, strands, p, alloc
    keys = sorted(per_cell)
    def pooled(cells, arm_cells):
        tp = sum(arm_cells[k]["tp"] for k in cells); fp = sum(arm_cells[k]["fp"] for k in cells); fn = sum(arm_cells[k]["fn"] for k in cells)
        return float(tp / (tp + 0.2*fp + 0.8*fn + 1e-12))
    comp = {a: {k: exp1["per_cell"][k][a] for k in keys} for a in ("control_noprior", "corridor_v1")}
    pooled_t = pooled(keys, per_cell)
    rng = np.random.default_rng(20261022); d_ctrl, d_v1 = [], []
    for _ in range(2000):
        bk = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        d_ctrl.append(pooled(bk, per_cell) - pooled(bk, comp["control_noprior"]))
        d_v1.append(pooled(bk, per_cell) - pooled(bk, comp["corridor_v1"]))
    boot = {"transfer_minus_control": dict(mean=float(np.mean(d_ctrl)), ci95=[float(np.percentile(d_ctrl, 2.5)), float(np.percentile(d_ctrl, 97.5))]),
            "transfer_minus_v1": dict(mean=float(np.mean(d_v1)), ci95=[float(np.percentile(d_v1, 2.5)), float(np.percentile(d_v1, 97.5))])}
    out = dict(evidence_class="HOLDOUT-DTI", hypothesis="H69-H2-transfer-only",
               preregistration="registry/preregistration-2026-10-20-exp2b-transfer.json",
               evaluator=exp1["evaluator"], n_cells=len(keys),
               withheld_positive_px_total=int(sum(per_cell[k]["n_truth"] for k in keys)),
               pooled_dti=dict(transfer=pooled_t, corridor_v1=exp1["pooled_dti"]["corridor_v1"], control_noprior=exp1["pooled_dti"]["control_noprior"]),
               mean_of_cells_dti=float(np.mean([per_cell[k]["dti"] for k in keys])),
               paired_cell_bootstrap=boot, per_cell=per_cell,
               canary_propensity_transfer=dict(per_cell_auc=canary, auc_max=float(max(a for a in canary if a is not None))),
               prompt_gate_passed=bool(pooled_t > exp1["pooled_dti"]["control_noprior"] and boot["transfer_minus_control"]["ci95"][0] > 0),
               beats_current_best=bool(pooled_t > exp1["pooled_dti"]["corridor_v1"] and boot["transfer_minus_v1"]["ci95"][0] > 0),
               generated_utc=utcnow(), seconds=round(time.time()-t_all, 1))
    (EVIDENCE / "relayfix_exp2b_gate.json").write_text(json.dumps(out, indent=1))
    log(f"POOLED transfer={pooled_t:.6f} prompt_gate={out['prompt_gate_passed']} beats_v1={out['beats_current_best']}")
    return 0

def cmd_emit() -> int:
    import pickle, csv as _csv
    from gems57 import grid as tgrid
    from gems69.holdout69 import load_template_grid
    gate = json.loads((EVIDENCE / "relayfix_exp2b_gate.json").read_text())
    pre = json.loads((EVIDENCE / "relayfix_exp2b_precheck.json").read_text())
    g = load_template_grid(); shape = g.footprint.shape
    dots = np.load(TMP / "dots_transfer.npy"); surf = np.load(TMP / "surface_transfer.npy")
    assert dots.shape == shape and not (dots & g.catalogue).any() and not (dots & ~g.footprint).any()
    surf_decoded = hashlib.sha256(np.ascontiguousarray(surf).tobytes()).hexdigest()
    (TMP / "surface_transfer_frozen.json").write_text(json.dumps(dict(
        surface_file=str(TMP / "surface_transfer.npy"), surface_decoded_sha256=surf_decoded,
        note="Surface computed and saved by the Exp2b precheck BEFORE holdout and TIF writing; dots allocated from this surface in the same precheck run."), indent=1))
    values = np.zeros(shape, np.float32); values[dots] = 1.0
    n_dots = int(dots.sum()); stamp = utcnow()
    h8 = hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()[:8]
    base = f"h69-transferonly-{n_dots}-{stamp}-{h8}"
    sub = ROOT / "submissions"
    rec_z = tgrid.write_submission(sub / f"{base}-zeros.tif", values, mode="zeros")
    vn = values.copy(); vn[~g.footprint] = np.nan
    rec_n = tgrid.write_submission(sub / f"{base}-nan.tif", vn, mode="nan")
    rationale = pickle.load(open(TMP / "transfer_rationales.pkl", "rb"))
    rationale = [r for r in rationale if "score_S" in r]; rationale.sort(key=lambda r: -r["score_S"])
    with open(EVIDENCE / "relayfix_transfer_rationale.csv", "w", newline="") as f:
        wtr = _csv.writer(f)
        wtr.writerow(["rank","score_S","w_km","along_km","separation_km","overlap_km","mean_az_deg","dilatational","signature","source","E_grav","E_mag","E_maglow","E_lidar","E_subsurface","E_radiometric","strands","tips"])
        for i, r in enumerate(rationale):
            eg = r.get("evidence_groups", {})
            wtr.writerow([i, r.get("score_S"), r.get("w_km"), r.get("along_km"), r.get("separation_km"), r.get("overlap_km"),
                          r.get("mean_az_deg"), r.get("dilatational"), r.get("signature"), r.get("source"),
                          eg.get("E_grav"), eg.get("E_mag"), eg.get("E_maglow"), eg.get("E_lidar"), eg.get("E_subsurface"), eg.get("E_radiometric"), r.get("strands"), r.get("tips")])
    receipt = dict(evidence_class="SUBMISSION-RECEIPT", generated_utc=stamp, hypothesis_id="H69-H2-transfer-only",
                   preregistration="registry/preregistration-2026-10-20-exp2b-transfer.json",
                   scoring_version="v1", n_corridors=1200, n_dots=n_dots, catalogue_collision_px=0,
                   surface=dict(decoded_sha256=surf_decoded, frozen_before_tif=True),
                   raster=dict(zeros=dict(path=rec_z["path"], sha256=sha256_file(Path(rec_z["path"])), bytes=Path(rec_z["path"]).stat().st_size),
                               nan=dict(path=rec_n["path"], sha256=sha256_file(Path(rec_n["path"])), bytes=Path(rec_n["path"]).stat().st_size)),
                   holdout=dict(pooled_dti=gate["pooled_dti"], prompt_gate_passed=gate["prompt_gate_passed"], beats_current_best=gate["beats_current_best"]),
                   precheck=pre, top_corridors=rationale[:25],
                   submission_name=f"{base}-zeros",
                   submission_note=f"H69 transfer-only relay corridors; repaired tip graph; {n_dots} dots"[:140],
                   note="PORTAL FILE = -zeros (all-finite in [0,1]). -nan twin diagnostic only; do not upload.")
    (EVIDENCE / "relayfix_transfer_receipt.json").write_text(json.dumps(receipt, indent=1, default=str))
    log(f"wrote {base} zeros sha={receipt['raster']['zeros']['sha256']}")
    return 0

if __name__ == "__main__":
    sys.exit({"gate": cmd_gate, "emit": cmd_emit}[sys.argv[1] if len(sys.argv) > 1 else "gate"]())
