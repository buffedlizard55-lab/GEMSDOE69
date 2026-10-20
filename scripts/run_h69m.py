#!/usr/bin/env python3
"""H69-M experiment runner (registry/preregistration-2026-10-20-h69m-evidence-first.json).

Subcommands
  gate     16-cell holdout (seeds 20/21 x modes all/detached), 4 arms, canaries
  surface  full-catalogue H69-M surface (pre-placement) -> /tmp/gems69_h69m/surface.npy
  emit     greedy placement on the frozen surface -> submissions/ (zeros + nan twin)

Every DTI here is computed by the byte-pinned shared template (vendor/template66
gems57.holdout.score_cell); nothing re-implements the metric.  Every number
written is HOLDOUT-DTI (evaluator named in the receipt).  Run with
PYTHONPATH=src:vendor/template66:vendor.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "vendor" / "template66", ROOT / "vendor"):
    sys.path.insert(0, str(p))

EVIDENCE = ROOT / "evidence"
TMP = Path("/tmp/gems69_h69m")
TMP.mkdir(parents=True, exist_ok=True)
PREREG = "registry/preregistration-2026-10-20-h69m-evidence-first.json"
ARMS = ("control_noprior", "transfer_ref", "joint_priority", "h69m_evidence_first")
K_EMIT = 12691
ALPHA, BETA, EPS = 0.2, 0.8, 1e-12


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log(msg: str) -> None:
    print(f"[{utcnow()}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _auc(pos, neg):
    from scipy.stats import rankdata
    a = np.asarray(pos, np.float64); b = np.asarray(neg, np.float64)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if a.size < 10 or b.size < 10:
        return None
    r = rankdata(np.concatenate([a, b]))
    return float((r[: a.size].sum() - a.size * (a.size + 1) / 2) / (a.size * b.size))


def load_inputs():
    from gems69.holdout69 import load_template_grid
    from gems69.physics import build_layer_stats, build_z_stack
    g = load_template_grid()
    stats = build_layer_stats(g.footprint)
    zstack = build_z_stack(g.footprint, stats)
    return g, stats, zstack


def control_surface(g, zstack):
    from gems69.scoring import S0_DEFAULT
    layers = ["grav_hg_s2", "grav_tilt_s2", "mag_hg_s2", "mag_tilt_s2", "mag_low_tmi", "mag_low_rtp", "lidar_scarp"]
    C = np.zeros(g.footprint.shape, np.float32)
    for name in layers:
        z = zstack[name].astype(np.float32)
        C += np.where(np.isfinite(z), z, 0.0)
    C /= len(layers)
    p = (1.0 / (1.0 + np.exp(-1.5 * (C - S0_DEFAULT)))).astype(np.float32)
    p[~g.footprint] = 0.0
    return p


def transfer_ref_corridors(pairs, strands, shape, max_corridors=1200):
    """Exp2b transfer-only selector, identical logic to scripts/run_exp2b_transfer.py."""
    from gems69.corridors import _pair_key, _priority, corridor_from_pair
    seen, chosen = set(), []
    for p in sorted(pairs, key=_priority):
        k = _pair_key(p)
        if k in seen:
            continue
        seen.add(k)
        if bool(p.dilatational):
            continue
        chosen.append(p)
        if len(chosen) >= max_corridors:
            break
    return [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(chosen)]


def arm_surfaces(visible, shape, zstack, want=("transfer_ref", "joint_priority", "h69m_evidence_first")):
    """Build every corridor arm's propensity from ONE visible catalogue (shared tip graph)."""
    from gems69.corridors import build_tip_pairs, corridor_from_pair, select_stratified
    from gems69.evidence_first import build_evidence_first_corridors
    from gems69.physics import corridor_evidence_from_z
    from gems69.scoring import build_propensity, score_corridor
    from gems69.scoring_joint import build_propensity_joint, score_corridor_joint
    from gems69.tips import vectorize
    strands = vectorize(visible)
    pairs = build_tip_pairs(strands, visible)
    out, meta, objs = {}, dict(n_strands=len(strands), n_raw_pairs=len(pairs)), {}
    if "transfer_ref" in want:
        cs = transfer_ref_corridors(pairs, strands, shape)
        for c in cs:
            score_corridor(c, corridor_evidence_from_z(zstack, c), version="v1")
        out["transfer_ref"] = build_propensity(cs, shape)
        del cs
    if "joint_priority" in want:
        chosen = select_stratified(pairs, max_corridors=1200)
        cs = [corridor_from_pair(i, p, strands, shape) for i, p in enumerate(chosen)]
        for c in cs:
            score_corridor_joint(c, corridor_evidence_from_z(zstack, c))
        out["joint_priority"] = build_propensity_joint(cs, shape)
        del cs
    if "h69m_evidence_first" in want:
        cs, m = build_evidence_first_corridors(pairs, strands, shape, zstack)
        for c in cs:
            score_corridor_joint(c, corridor_evidence_from_z(zstack, c))
        out["h69m_evidence_first"] = build_propensity_joint(cs, shape)
        meta.update(h69m=m)
        objs["h69m_evidence_first"] = cs
    return out, meta, objs


def pooled(per_cell, arm, keys):
    tp = sum(per_cell[k][arm]["tp"] for k in keys)
    fp = sum(per_cell[k][arm]["fp"] for k in keys)
    fn = sum(per_cell[k][arm]["fn"] for k in keys)
    return float(tp / (tp + ALPHA * fp + BETA * fn + EPS))


def boot(per_cell, keys, a, b, n=2000, seed=20261021):
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(n):
        bk = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        d.append(pooled(per_cell, a, bk) - pooled(per_cell, b, bk))
    return dict(mean=float(np.mean(d)), ci95=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))])


def cmd_gate(limit: int | None = None) -> int:
    from scipy import ndimage as ndi
    from gems57 import holdout as thold
    from gems57.emit import greedy_allocate
    from gems69.evidence_first import JOINT_LAYERS
    from gems69.holdout69 import cell_allowed
    t_all = time.time()
    g, _stats, zstack = load_inputs()
    shape = g.footprint.shape
    p_ctrl = control_surface(g, zstack)
    log("building holdout (seeds 20,21; modes all, detached)")
    ctx = thold.build_holdout(g, seeds=(20, 21), modes=("all", "detached"))
    cells = ctx.cells[:limit] if limit else ctx.cells
    partial = TMP / "gate_partial.json"
    state = json.loads(partial.read_text()) if partial.exists() and not limit else dict(per_cell={}, canary={}, meta={})
    rng_can = np.random.default_rng(20261021)
    for cell in cells:
        if cell.key in state["per_cell"]:
            log(f"skip {cell.key} (done)")
            continue
        t0 = time.time()
        visible = ctx.visible(cell.key)
        offcat = ndi.distance_transform_edt(~visible) > 2   # flank rule from VISIBLE catalogue only
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
        can = {name: _auc(zstack[name][ty, tx], zstack[name][ny, nx]) for name in JOINT_LAYERS}
        out = {}
        for arm in ARMS:
            p = surfaces[arm]
            can[f"propensity_{arm}"] = _auc(p[ty, tx], p[ny, nx])
            alloc = greedy_allocate(p, allowed & (p > 0), cell.n_truth, floor=0.05,
                                    max_dots=250_000, candidate_cap=300_000)
            r = thold.score_cell(cell, alloc.emitted)
            out[arm] = dict(dti=r["dti"], tp=r["tp"], fp=r["fp"], fn=r["fn"], n_truth=cell.n_truth,
                            n_dots=int((alloc.emitted & allowed).sum()))
        state["per_cell"][cell.key] = out
        state["canary"][cell.key] = can
        state["meta"][cell.key] = meta
        if not limit:
            partial.write_text(json.dumps(state, indent=1))
        log(f"cell {cell.key} n_truth={cell.n_truth}: " + " ".join(f"{a}={out[a]['dti']:.4f}" for a in ARMS)
            + f" ({time.time() - t0:.0f}s)")
        del surfaces
    if limit:
        log("limited dry run; no evidence written")
        return 0
    per_cell = state["per_cell"]
    keys_all = sorted(k for k in per_cell if k.endswith("_all"))
    keys_det = sorted(k for k in per_cell if k.endswith("_detached"))
    res = {}
    for name, keys in (("primary_detached", keys_det), ("secondary_all", keys_all)):
        res[name] = dict(
            cells=keys, withheld_positive_px=int(sum(per_cell[k]["control_noprior"]["n_truth"] for k in keys)),
            pooled_dti={a: pooled(per_cell, a, keys) for a in ARMS},
            mean_of_cells_dti={a: float(np.mean([per_cell[k][a]["dti"] for k in keys])) for a in ARMS},
            h69m_minus_control=boot(per_cell, keys, "h69m_evidence_first", "control_noprior"),
            h69m_minus_transfer_ref=boot(per_cell, keys, "h69m_evidence_first", "transfer_ref"),
            h69m_minus_joint_priority=boot(per_cell, keys, "h69m_evidence_first", "joint_priority"),
            joint_priority_minus_control=boot(per_cell, keys, "joint_priority", "control_noprior"),
            transfer_ref_minus_control=boot(per_cell, keys, "transfer_ref", "control_noprior"))
    P, S = res["primary_detached"], res["secondary_all"]
    gate = bool(P["pooled_dti"]["h69m_evidence_first"] > P["pooled_dti"]["control_noprior"]
                and P["h69m_minus_control"]["ci95"][0] > 0)
    best = bool(P["pooled_dti"]["h69m_evidence_first"] > P["pooled_dti"]["transfer_ref"]
                and P["h69m_minus_transfer_ref"]["ci95"][0] > 0
                and S["h69m_minus_transfer_ref"]["ci95"][1] > 0)
    worst_auc = {}
    for k, can in state["canary"].items():
        for f, a in can.items():
            if a is not None:
                worst_auc[f] = max(worst_auc.get(f, 0.0), a)
    canary_ok = all(a <= 0.90 for a in worst_auc.values())
    doc = dict(evidence_class="HOLDOUT-DTI", hypothesis="H69-M evidence-first corridor selection",
               preregistration=PREREG,
               evaluator=("vendor/template66 gems57.holdout.build_holdout+score_cell (alpha=0.2 beta=0.8 "
                          "R=300m triangular; seeds=[20,21] modes=[all,detached]; POOLED from summed TP/FP/FN)"),
               n_cells=len(per_cell), results=res, per_cell=per_cell, tipgraph_meta=state["meta"],
               canary_worst_auc=worst_auc, canary_ok=canary_ok, canary_per_cell=state["canary"],
               prompt_gate_passed=gate, current_best_beaten=best,
               allocator_note="k_truth = cell.n_truth for every arm (oracle hidden-size, identical across arms)",
               generated_utc=utcnow(), seconds=round(time.time() - t_all, 1))
    (EVIDENCE / "h69m_gate.json").write_text(json.dumps(doc, indent=1))
    log(f"PRIMARY detached pooled: " + " ".join(f"{a}={P['pooled_dti'][a]:.5f}" for a in ARMS))
    log(f"SECONDARY all pooled: " + " ".join(f"{a}={S['pooled_dti'][a]:.5f}" for a in ARMS))
    log(f"gate={gate} current_best={best} canary_ok={canary_ok}")
    return 0


def cmd_surface() -> int:
    """Full-catalogue H69-M surface, frozen to disk BEFORE placement."""
    import pickle
    g, _stats, zstack = load_inputs()
    shape = g.footprint.shape
    t0 = time.time()
    surfaces, meta, objs = arm_surfaces(g.catalogue, shape, zstack, want=("h69m_evidence_first",))
    p = surfaces["h69m_evidence_first"].astype(np.float32)
    p[~g.footprint] = 0.0
    np.save(TMP / "surface.npy", p)
    rationale = [dict(c.rationale) for c in objs["h69m_evidence_first"]]
    with open(TMP / "rationales.pkl", "wb") as f:
        pickle.dump(rationale, f)
    frozen = dict(surface_file=str(TMP / "surface.npy"),
                  surface_decoded_sha256=hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest(),
                  frozen_utc=utcnow(), tipgraph=meta, positive_px=int((p > 0).sum()),
                  seconds=round(time.time() - t0, 1))
    (TMP / "surface_frozen.json").write_text(json.dumps(frozen, indent=1))
    log(f"surface frozen: {frozen['surface_decoded_sha256'][:16]} positive={frozen['positive_px']} meta={meta}")
    return 0


def cmd_emit() -> int:
    import csv
    import pickle
    from scipy import ndimage as ndi
    from gems57 import grid as tgrid
    from gems57.emit import greedy_allocate
    from gems69.holdout69 import load_template_grid
    g = load_template_grid()
    frozen = json.loads((TMP / "surface_frozen.json").read_text())
    p = np.load(frozen["surface_file"])
    assert hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest() == frozen["surface_decoded_sha256"]
    allowed = g.footprint & (ndi.distance_transform_edt(~g.catalogue) > 2) & (p > 0)
    alloc = greedy_allocate(p, allowed, K_EMIT, floor=0.05, max_dots=250_000, candidate_cap=300_000)
    dots = alloc.emitted & allowed
    assert not (dots & g.catalogue).any() and not (dots & ~g.footprint).any()
    values = np.zeros(g.footprint.shape, np.float32)
    values[dots] = 1.0
    n = int(dots.sum())
    stamp = utcnow()
    h8 = hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()[:8]
    base = f"h69m-evidencefirst-corridors-{n}-{stamp}-{h8}"
    sub = ROOT / "submissions"
    rec_z = tgrid.write_submission(sub / f"{base}-zeros.tif", values, mode="zeros")
    vn = values.copy(); vn[~g.footprint] = np.nan
    rec_n = tgrid.write_submission(sub / f"{base}-nan.tif", vn, mode="nan")
    rationale = pickle.load(open(TMP / "rationales.pkl", "rb"))
    rationale.sort(key=lambda r: -r.get("score_S", 0.0))
    with open(EVIDENCE / "h69m_corridor_rationale.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "score_S", "line_score_S", "subtype_dilatational", "w_km", "along_km", "overlap_km",
                    "separation_km", "mean_az_deg", "W_orient", "E_grav", "E_mag", "E_joint_min", "E_maglow_weighted",
                    "E_lidar", "layers_used", "signature", "source", "strands", "tips_rowcol"])
        for i, r in enumerate(rationale):
            eg = r.get("evidence_groups", {})
            w.writerow([i, r.get("score_S"), r.get("line_score_S"), r.get("dilatational"), r.get("w_km"),
                        r.get("along_km"), r.get("overlap_km"), r.get("separation_km"), r.get("mean_az_deg"),
                        eg.get("W_orient"), eg.get("E_grav"), eg.get("E_mag"), eg.get("E_joint_min"),
                        eg.get("E_maglow_weighted"), eg.get("E_lidar"),
                        "grav HG s1/s2/s4+tilt+provided; mag HG s1/s2/s4+tilt+provided; -TMI,-RTP lows; lidar scarp",
                        r.get("signature"), r.get("source"), r.get("strands"), r.get("tips")])
    receipt = dict(evidence_class="EMISSION", hypothesis="H69-M", preregistration=PREREG,
                   surface_decoded_sha256=frozen["surface_decoded_sha256"], k_truth=K_EMIT, n_dots=n,
                   raster=dict(zeros=dict(path=str(Path(rec_z["path"]).relative_to(ROOT)),
                                          sha256=sha256_file(Path(rec_z["path"])),
                                          bytes=Path(rec_z["path"]).stat().st_size),
                               nan=dict(path=str(Path(rec_n["path"]).relative_to(ROOT)),
                                        sha256=sha256_file(Path(rec_n["path"])),
                                        bytes=Path(rec_n["path"]).stat().st_size)),
                   submission_name=f"{base}-zeros",
                   submission_note=f"H69-M evidence-first relay/pull-apart corridors, joint grav+mag; {n} dots"[:140],
                   generated_utc=stamp)
    (EVIDENCE / "h69m_receipt.json").write_text(json.dumps(receipt, indent=1))
    log(f"wrote {receipt['raster']['zeros']['path']} sha={receipt['raster']['zeros']['sha256'][:16]} dots={n}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    if cmd == "gate":
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
        return cmd_gate(lim)
    return {"surface": cmd_surface, "emit": cmd_emit}[cmd]()


if __name__ == "__main__":
    sys.exit(main())
