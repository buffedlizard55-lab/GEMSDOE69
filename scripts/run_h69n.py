#!/usr/bin/env python3
"""H69-N experiment runner (registry/preregistration-2026-10-20-h69n-evidence-quota.json).

Subcommands
  gate     16-cell holdout (seeds 20/21 x modes all/detached), 3 arms, canaries
  surface  full-catalogue H69-N surface (pre-placement) -> /tmp/gems69_h69n/surface.npy
  emit     greedy placement on the frozen surface -> submissions/ (zeros + nan twin)

Control and transfer arms, allocator, canary, pooling and bootstrap are imported from
scripts/run_h69m.py (byte-identical code paths to experiment 1).  Every DTI comes from
the byte-pinned template gems57.holdout.score_cell.  PYTHONPATH=src:vendor/template66:vendor.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "vendor" / "template66", ROOT / "vendor", ROOT / "scripts"):
    sys.path.insert(0, str(p))

import run_h69m as M  # noqa: E402  (shared helpers; experiment-1 provenance file, unmodified)

EVIDENCE = ROOT / "evidence"
TMP = Path("/tmp/gems69_h69n")
TMP.mkdir(parents=True, exist_ok=True)
PREREG = "registry/preregistration-2026-10-20-h69n-evidence-quota.json"
NEW = "h69n_evidence_quota"
ARMS = ("control_noprior", "transfer_ref", NEW)
log, utcnow, sha256_file = M.log, M.utcnow, M.sha256_file


def arm_surfaces(visible, shape, zstack, want=("transfer_ref", NEW)):
    from gems69_s3.corridors import build_tip_pairs
    from gems69_s3.evidence_quota import build_evidence_quota_corridors
    from gems69_s3.physics import corridor_evidence_from_z
    from gems69_s3.scoring import build_propensity, score_corridor
    from gems69_s3.scoring_joint import build_propensity_joint, score_corridor_joint
    from gems69_s3.tips import vectorize
    strands = vectorize(visible)
    pairs = build_tip_pairs(strands, visible)
    out, meta, objs = {}, dict(n_strands=len(strands), n_raw_pairs=len(pairs)), {}
    if "transfer_ref" in want:
        cs = M.transfer_ref_corridors(pairs, strands, shape)
        for c in cs:
            score_corridor(c, corridor_evidence_from_z(zstack, c), version="v1")
        out["transfer_ref"] = build_propensity(cs, shape)
        del cs
    if NEW in want:
        cs, m = build_evidence_quota_corridors(pairs, strands, shape, zstack)
        for c in cs:
            score_corridor_joint(c, corridor_evidence_from_z(zstack, c))
        out[NEW] = build_propensity_joint(cs, shape)
        meta.update(h69n=m)
        objs[NEW] = cs
    return out, meta, objs


def cmd_gate() -> int:
    from scipy import ndimage as ndi
    from gems57 import holdout as thold
    from gems57.emit import greedy_allocate
    from gems69_s3.evidence_first import JOINT_LAYERS
    from gems69_s3.holdout69 import cell_allowed
    t_all = time.time()
    g, _stats, zstack = M.load_inputs()
    shape = g.footprint.shape
    p_ctrl = M.control_surface(g, zstack)
    log("building holdout (seeds 20,21; modes all, detached)")
    ctx = thold.build_holdout(g, seeds=(20, 21), modes=("all", "detached"))
    partial = TMP / "gate_partial.json"
    state = json.loads(partial.read_text()) if partial.exists() else dict(per_cell={}, canary={}, meta={})
    rng_can = np.random.default_rng(20261021)
    for cell in ctx.cells:
        if cell.key in state["per_cell"]:
            log(f"skip {cell.key} (done)")
            continue
        t0 = time.time()
        visible = ctx.visible(cell.key)
        offcat = ndi.distance_transform_edt(~visible) > 2
        allowed = cell_allowed(cell, shape) & offcat
        surfaces, meta, _ = arm_surfaces(visible, shape, zstack)
        surfaces["control_noprior"] = p_ctrl
        ty = cell.truth_yx[0] + cell.bbox[0].start
        tx = cell.truth_yx[1] + cell.bbox[1].start
        is_truth = np.zeros(shape, bool); is_truth[ty, tx] = True
        ny_all, nx_all = np.nonzero(cell_allowed(cell, shape) & ~is_truth)
        del is_truth
        sel = rng_can.choice(len(ny_all), size=min(50_000, len(ny_all)), replace=False)
        ny, nx = ny_all[sel], nx_all[sel]
        can = {name: M._auc(zstack[name][ty, tx], zstack[name][ny, nx]) for name in JOINT_LAYERS}
        out = {}
        for arm in ARMS:
            p = surfaces[arm]
            can[f"propensity_{arm}"] = M._auc(p[ty, tx], p[ny, nx])
            alloc = greedy_allocate(p, allowed & (p > 0), cell.n_truth, floor=0.05,
                                    max_dots=250_000, candidate_cap=300_000)
            r = thold.score_cell(cell, alloc.emitted)
            out[arm] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"], n_truth=cell.n_truth,
                            n_dots=int((alloc.emitted & allowed).sum()))
        state["per_cell"][cell.key] = out
        state["canary"][cell.key] = can
        state["meta"][cell.key] = meta
        partial.write_text(json.dumps(state, indent=1))
        log(f"cell {cell.key} n_truth={cell.n_truth}: " + " ".join(
            f"{a}={out[a]['dti']:.4f}({out[a]['n_dots']})" for a in ARMS) + f" ({time.time() - t0:.0f}s)")
        del surfaces
    per_cell = state["per_cell"]
    res = {}
    for name, suffix in (("primary_detached", "_detached"), ("secondary_all", "_all")):
        keys = sorted(k for k in per_cell if k.endswith(suffix))
        res[name] = dict(
            cells=keys, withheld_positive_px=int(sum(per_cell[k]["control_noprior"]["n_truth"] for k in keys)),
            pooled_dti={a: M.pooled(per_cell, a, keys) for a in ARMS},
            mean_of_cells_dti={a: float(np.mean([per_cell[k][a]["dti"] for k in keys])) for a in ARMS},
            h69n_minus_control=M.boot(per_cell, keys, NEW, "control_noprior"),
            h69n_minus_transfer_ref=M.boot(per_cell, keys, NEW, "transfer_ref"),
            transfer_ref_minus_control=M.boot(per_cell, keys, "transfer_ref", "control_noprior"))
    P, S = res["primary_detached"], res["secondary_all"]
    gate = bool(P["pooled_dti"][NEW] > P["pooled_dti"]["control_noprior"] and P["h69n_minus_control"]["ci95"][0] > 0)
    best = bool(P["pooled_dti"][NEW] > P["pooled_dti"]["transfer_ref"]
                and P["h69n_minus_transfer_ref"]["ci95"][0] > 0
                and S["h69n_minus_transfer_ref"]["ci95"][1] > 0)
    worst_auc = {}
    for can in state["canary"].values():
        for f, a in can.items():
            if a is not None:
                worst_auc[f] = max(worst_auc.get(f, 0.0), a)
    canary_ok = all(a <= 0.90 for a in worst_auc.values())
    doc = dict(evidence_class="HOLDOUT-DTI", hypothesis="H69-N evidence-first selection with spatial quota",
               preregistration=PREREG, preregistration_sha256=sha256_file(ROOT / PREREG),
               evaluator=("vendor/template66 gems57.holdout.build_holdout+score_cell (alpha=0.2 beta=0.8 "
                          "R=300m triangular; seeds=[20,21] modes=[all,detached]; POOLED from summed TP/FP/FN)"),
               n_cells=len(per_cell), results=res, per_cell=per_cell, tipgraph_meta=state["meta"],
               canary_worst_auc=worst_auc, canary_ok=canary_ok, canary_per_cell=state["canary"],
               prompt_gate_passed=gate, current_best_beaten=best,
               allocator_note="k_truth = cell.n_truth for every arm (oracle hidden-size, identical across arms)",
               generated_utc=utcnow(), seconds=round(time.time() - t_all, 1))
    (EVIDENCE / "h69n_gate.json").write_text(json.dumps(doc, indent=1))
    log("PRIMARY detached pooled: " + " ".join(f"{a}={P['pooled_dti'][a]:.5f}" for a in ARMS))
    log("SECONDARY all pooled: " + " ".join(f"{a}={S['pooled_dti'][a]:.5f}" for a in ARMS))
    log(f"gate={gate} current_best={best} canary_ok={canary_ok}")
    return 0


def cmd_surface() -> int:
    g, _stats, zstack = M.load_inputs()
    shape = g.footprint.shape
    t0 = time.time()
    surfaces, meta, objs = arm_surfaces(g.catalogue, shape, zstack, want=(NEW,))
    p = surfaces[NEW].astype(np.float32)
    p[~g.footprint] = 0.0
    np.save(TMP / "surface.npy", p)
    with open(TMP / "rationales.pkl", "wb") as f:
        pickle.dump([dict(c.rationale) for c in objs[NEW]], f)
    frozen = dict(surface_file=str(TMP / "surface.npy"),
                  surface_decoded_sha256=hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest(),
                  frozen_utc=utcnow(), tipgraph=meta, positive_px=int((p > 0).sum()),
                  seconds=round(time.time() - t0, 1))
    (TMP / "surface_frozen.json").write_text(json.dumps(frozen, indent=1))
    log(f"surface frozen: {frozen['surface_decoded_sha256'][:16]} positive={frozen['positive_px']} meta={meta}")
    return 0


def cmd_emit() -> int:
    from scipy import ndimage as ndi
    from gems57 import grid as tgrid
    from gems57.emit import greedy_allocate
    from gems69_s3.holdout69 import load_template_grid
    g = load_template_grid()
    frozen = json.loads((TMP / "surface_frozen.json").read_text())
    p = np.load(frozen["surface_file"])
    assert hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest() == frozen["surface_decoded_sha256"]
    allowed = g.footprint & (ndi.distance_transform_edt(~g.catalogue) > 2) & (p > 0)
    alloc = greedy_allocate(p, allowed, M.K_EMIT, floor=0.05, max_dots=250_000, candidate_cap=300_000)
    dots = alloc.emitted & allowed
    assert not (dots & g.catalogue).any() and not (dots & ~g.footprint).any()
    values = np.zeros(g.footprint.shape, np.float32)
    values[dots] = 1.0
    n = int(dots.sum())
    stamp = utcnow()
    h8 = hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()[:8]
    base = f"h69n-evidencequota-corridors-{n}-{stamp}-{h8}"
    sub = ROOT / "submissions"
    rec_z = tgrid.write_submission(sub / f"{base}-zeros.tif", values, mode="zeros")
    vn = values.copy(); vn[~g.footprint] = np.nan
    rec_n = tgrid.write_submission(sub / f"{base}-nan.tif", vn, mode="nan")
    rationale = pickle.load(open(TMP / "rationales.pkl", "rb"))
    rationale.sort(key=lambda r: -r.get("score_S", 0.0))
    with open(EVIDENCE / "h69n_corridor_rationale.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "score_S", "line_score_S", "subtype_dilatational", "w_km", "along_km", "overlap_km",
                    "separation_km", "mean_az_deg", "W_orient", "E_grav", "E_mag", "E_joint_min",
                    "E_maglow_weighted", "E_lidar", "layers_used", "signature", "source", "strands", "tips_rowcol"])
        for i, r in enumerate(rationale):
            eg = r.get("evidence_groups", {})
            w.writerow([i, r.get("score_S"), r.get("line_score_S"), r.get("dilatational"), r.get("w_km"),
                        r.get("along_km"), r.get("overlap_km"), r.get("separation_km"), r.get("mean_az_deg"),
                        eg.get("W_orient"), eg.get("E_grav"), eg.get("E_mag"), eg.get("E_joint_min"),
                        eg.get("E_maglow_weighted"), eg.get("E_lidar"),
                        "grav HG s1/s2/s4+tilt+provided; mag HG s1/s2/s4+tilt+provided; -TMI,-RTP lows; lidar scarp",
                        r.get("signature"), r.get("source"), r.get("strands"), r.get("tips")])
    receipt = dict(evidence_class="EMISSION", hypothesis="H69-N", preregistration=PREREG,
                   surface_decoded_sha256=frozen["surface_decoded_sha256"], k_truth=M.K_EMIT, n_dots=n,
                   raster=dict(zeros=dict(path=str(Path(rec_z["path"]).relative_to(ROOT)),
                                          sha256=sha256_file(Path(rec_z["path"])),
                                          bytes=Path(rec_z["path"]).stat().st_size),
                               nan=dict(path=str(Path(rec_n["path"]).relative_to(ROOT)),
                                        sha256=sha256_file(Path(rec_n["path"])),
                                        bytes=Path(rec_n["path"]).stat().st_size)),
                   submission_name=f"{base}-zeros",
                   submission_note=f"H69-N evidence-quota relay/pull-apart corridors, joint grav+mag; {n} dots"[:140],
                   generated_utc=stamp)
    (EVIDENCE / "h69n_receipt.json").write_text(json.dumps(receipt, indent=1))
    log(f"wrote {receipt['raster']['zeros']['path']} sha={receipt['raster']['zeros']['sha256'][:16]} dots={n}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    return {"gate": cmd_gate, "surface": cmd_surface, "emit": cmd_emit}[cmd]()


if __name__ == "__main__":
    sys.exit(main())
