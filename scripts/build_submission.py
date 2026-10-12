#!/usr/bin/env python3
"""E3 -- live build of the lane artefact (relay-ramp / pull-apart corridor dots).

Steps (all deterministic):
 1. Calibration transfer: corridor-score edges and P(truth | bin) rates are
    fitted on the hide-and-recover holdout (both draws, all four regions as
    training, visible-only geometry) and frozen.
 2. Live geometry: every catalogue polyline visible; tips, corridors and scores
    recomputed; the frozen calibration maps each corridor-band pixel to p.
 3. Placement: template ``emit.greedy_allocate`` inside the corridor band,
    off the catalogue and outside the 2-px flank, ``|G| = 12,226`` (owner
    live-anchor model, labelled [model]).
 4. Uniqueness, surface phase (normalised p) and dot phase (final dots), against
    ``registry/registry_index_69.json`` with the template's comparator.
 5. Writer: template ``submission_writer.write_submission`` (all-finite, zeros
    outside footprint) + a NaN-outside twin with bit-identical footprint values.
 6. Per-corridor rationale CSV/JSON (layers, signature, source) for every
    corridor that received a dot.

The artefact's verdict (OK to submit or negative) is decided by the E2 gate
(``evidence/e2_gate.json``), never by this script.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems69 import calibrate, corridors, pipeline  # noqa: E402
from gems69.data import DATA  # noqa: E402
from gems57 import emit, holdout, submission_writer, uniqueness  # noqa: E402
from gems57.grid import TRANSFORM  # noqa: E402

EVID = ROOT / "evidence"
DOWN = ROOT / "docs" / "downloads"
K_TRUTH_LIVE = 12226          # [model] GEMSDOE32 live-anchor inversion of the owner-reported ladder
ARM = "A_corridor"
SEEDS = (20, 21)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def removed_mask(fold0):
    return ndi.distance_transform_edt(~fold0["hidden_all"]) <= 3


def fit_frozen_calibration(ctx):
    """Edges from draw 1, rates pooled over both draws (all regions = training)."""
    edges = None
    pos = cnt = None
    receipts = []
    for seed in SEEDS:
        folds, _ = holdout.buffered_component_draw(ctx.grid, seed=seed, hide_frac=0.20, buffer_px=3)
        vis = folds[0]["visible"]
        geo = pipeline.geometry(ctx, vis, removed_mask(folds[0]))
        d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
        allowed = ctx.fp & ~folds[0]["masked_known"] & ~(d_vis <= pipeline.FLANK_PX)
        regions = np.zeros(ctx.fp.shape, bool)
        for f in folds:
            regions |= f["region"]
        train = allowed & regions & (geo["s_band"] > 0)
        code, n, e = pipeline._codes(ARM, ctx, geo, d_vis, train, edges=edges)
        if edges is None:
            edges = e
        y = folds[0]["hidden_all"] & train
        c = code[train]
        b_cnt = np.bincount(c, minlength=n).astype(np.float64)
        b_pos = np.bincount(c, weights=y[train].astype(np.float64), minlength=n)
        cnt = b_cnt if cnt is None else cnt + b_cnt
        pos = b_pos if pos is None else pos + b_pos
        receipts.append(dict(seed=seed, train_pixels=int(train.sum()), train_truth=int(y.sum()),
                             tip_receipt=geo["tip_receipt"], corridor_counts=geo["corridor_counts"]))
        del geo, d_vis, allowed, folds
    base = float(pos.sum() / max(cnt.sum(), 1))
    rate = ((pos + 200.0 * base) / (cnt + 200.0)).astype(np.float32)
    table = [dict(code=int(k), score_bin=int(k // 3), dist_to_trace_px=int(k % 3), n=int(cnt[k]),
                  truth=int(pos[k]), rate=float(rate[k])) for k in range(len(rate))]
    return edges, rate, dict(base_rate=base, draws=receipts, table=table,
                             edges=[float(x) for x in edges if np.isfinite(x)])


def signature(ln) -> str:
    t = ln.terms
    m = ln.meta
    lay = (f"grav edge {t.get('grav_edge', 0):.2f}, mag edge {t.get('mag_edge', 0):.2f}, "
           f"mag low {t.get('mag_low', 0):.2f}, lidar scarp {t.get('scarp', 0):.2f}, "
           f"dilation tendency {t.get('td', 0):.2f}")
    if ln.setting == "relay":
        geo = (f"{'overlapping' if m.get('overlap') else 'underlapping'} same-dip relay, "
               f"W {m.get('W_km', 0):.2f} km, L {m.get('L_km', 0):.2f} km")
    elif ln.setting == "pullapart":
        geo = (f"{m.get('sense')} releasing step (pull-apart), W {m.get('W_km', 0):.2f} km, "
               f"L {m.get('L_km', 0):.2f} km")
    else:
        geo = f"{m.get('sense')} termination / displacement-transfer zone"
    return f"{ln.kind}: {geo}; {lay}"


def main():
    t0 = time.time()
    ctx = pipeline.Context()
    edges, rate, calib = fit_frozen_calibration(ctx)
    cat = ctx.cat
    geo = pipeline.geometry(ctx, cat, None)
    lines = geo["lines"]
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allowed = ctx.fp & ~cat & ~(d_cat <= pipeline.FLANK_PX)
    band = geo["s_band"] > 0
    cand = allowed & band
    code, n, _ = pipeline._codes(ARM, ctx, geo, d_cat, cand, edges=edges)
    p = np.zeros(ctx.fp.shape, np.float32)
    p[cand] = rate[code[cand]]
    alloc = emit.greedy_allocate(p, cand, float(K_TRUTH_LIVE))
    dots = alloc.emitted & cand
    pred = dots.astype(np.float32)
    assert not (pred[cat] > 0).any() and not (pred[~ctx.fp] > 0).any()
    surface = np.where(cand, p / max(float(p.max()), 1e-12), 0).astype(np.float32)

    # per-corridor rationale
    lid = corridors.line_id_raster(lines, ctx.fp.shape)
    on = lid >= 0
    _, (iy, ix) = ndi.distance_transform_edt(~on, return_indices=True)
    dy, dx = np.nonzero(dots)
    owner = lid[iy[dy, dx], ix[dy, dx]]
    counts = np.bincount(owner[owner >= 0], minlength=len(lines))
    rows = []
    for k in np.flatnonzero(counts):
        ln = lines[k]
        e_a = 243350 + 100 * ln.a[0]
        n_a = 4508550 + 100 * ln.a[1]
        e_b = 243350 + 100 * ln.b[0]
        n_b = 4508550 + 100 * ln.b[1]
        recs = ln.meta.get("records") or ((ln.meta.get("target_record"),) if ln.meta.get("target_record") is not None else ())
        rows.append(dict(corridor_id=int(k), setting=ln.setting, kind=ln.kind, n_dots=int(counts[k]),
                         utm11_start_E=round(e_a, 1), utm11_start_N=round(n_a, 1),
                         utm11_end_E=round(e_b, 1), utm11_end_N=round(n_b, 1),
                         azimuth_deg=round(ln.azimuth, 1), score=round(ln.score, 4),
                         **{f"layer_{kk}": round(v, 4) for kk, v in ln.terms.items()},
                         sense=ln.meta.get("sense"), dip_source=ln.meta.get("dip_source"),
                         ingenious_records=";".join(str(int(r)) for r in recs if r is not None),
                         signature=signature(ln),
                         source=("INGENIOUS Qfaults polylines (trace_segments_utm11.csv + qfault_attributes.csv); "
                                 "iso_grav_anom + rtp bands of training_features.tif; lidar_scarp_features_u8.tif")))
    rows.sort(key=lambda r: (-r["n_dots"], -r["score"]))
    EVID.mkdir(exist_ok=True)
    with open(EVID / "e3_corridor_rationale.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    setting_counts = {}
    for r in rows:
        setting_counts.setdefault(r["setting"], dict(corridors=0, dots=0))
        setting_counts[r["setting"]]["corridors"] += 1
        setting_counts[r["setting"]]["dots"] += r["n_dots"]

    # diagnostic: where does the live-scored champion (h33-2-b2, owner-reported 0.2778) sit vs our corridors?
    champ_diag = None
    champ_path = Path("/tmp/ref/60GEMSDOE/registry/rasters/GEMSDOE32__h33-2-b2-zeros.tif")
    if champ_path.exists():
        with rasterio.open(champ_path) as src:
            ch = np.nan_to_num(src.read(1)) > 0
        ch &= ctx.fp
        champ_diag = dict(file="GEMSDOE32 h33-2-b2 (sha256 c55bafc4...)", champion_dots=int(ch.sum()),
                          in_corridor_band=int((ch & band).sum()),
                          in_corridor_band_frac=float((ch & band).sum() / max(ch.sum(), 1)),
                          corridor_band_frac_of_allowed=float((band & allowed).sum() / max(allowed.sum(), 1)),
                          our_dots_within_3px_of_champion=float(((ndi.distance_transform_edt(~ch) <= 3)[dots]).mean()) if dots.any() else None)

    # uniqueness is run by scripts/check_uniqueness.py on the saved pre-placement surface and the final
    # dots (the registry corpus download runs concurrently); the surface is cached here.
    from gems69.data import CACHE
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "gems69_surface.npy", surface.astype(np.float32))
    uniq = "pending: run scripts/check_uniqueness.py"

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"gems69-relay-pullapart-corridors-{int(dots.sum())}-{stamp}"
    note = (f"GEMSDOE69 relay-ramp/pull-apart corridor dots ({int(dots.sum())}); "
            f"tip-graph corridors, gravity/mag/scarp scored; see repo run card")[:140]
    DOWN.mkdir(parents=True, exist_ok=True)
    out_tif = DOWN / f"{name}-zeros.tif"
    receipt = submission_writer.write_submission(out_tif, pred, DATA / "sample_submission.tif", ctx.fp,
                                                 note=note, name=name, catalogue=cat,
                                                 metadata=dict(lane="relay-ramp and pull-apart corridor generator",
                                                               arm=ARM, k_truth_live=K_TRUTH_LIVE))
    nan_tif = DOWN / f"{name}-nan.tif"
    twin = np.where(ctx.fp, pred, np.nan).astype(np.float32)
    with rasterio.open(DATA / "sample_submission.tif") as ref:
        prof = ref.profile.copy()
    prof.update(driver="GTiff", count=1, dtype="float32", nodata=np.nan, compress="deflate")
    with rasterio.open(nan_tif, "w", **prof) as dst:
        dst.write(twin, 1)
    with rasterio.open(nan_tif) as src:
        back = src.read(1)
    assert np.array_equal(back[ctx.fp], pred[ctx.fp]) and np.isnan(back[~ctx.fp]).all()

    out = dict(experiment="E3 live build", started_finished=[now()], seconds=time.time() - t0,
               arm=ARM, k_truth_live=K_TRUTH_LIVE, k_truth_class="[model] owner live-anchor inversion (GEMSDOE32)",
               calibration=calib, allocation=dict(n_dots=alloc.n_dots, surrogate_dti=alloc.surrogate_dti,
                                                  rounds=alloc.rounds, note="surrogate DTI under the frozen holdout calibration; NOT a score"),
               live_geometry=dict(tip_receipt=geo["tip_receipt"], corridor_counts=geo["corridor_counts"],
                                  corridor_band_pixels=int(band.sum()), candidate_pixels=int(cand.sum())),
               dots=dict(n=int(dots.sum()), on_catalogue=int((dots & cat).sum()),
                         min_dist_to_catalogue_px=float(d_cat[dots].min()) if dots.any() else None,
                         median_dist_to_catalogue_px=float(np.median(d_cat[dots])) if dots.any() else None,
                         p95_dist_to_catalogue_px=float(np.quantile(d_cat[dots], 0.95)) if dots.any() else None),
               corridors_with_dots=len(rows), corridors_by_setting=setting_counts,
               champion_vs_corridors=champ_diag,
               uniqueness=uniq,
               submission=dict(name=name, note=note, note_chars=len(note), zeros_tif=str(out_tif.relative_to(ROOT)),
                               zeros_sha256=receipt["sha256"], zeros_bytes=receipt["bytes"],
                               zip=str(out_tif.with_suffix('.zip').relative_to(ROOT)), zip_sha256=receipt["zip_sha256"],
                               nan_tif=str(nan_tif.relative_to(ROOT)), nan_sha256=sha(nan_tif), nan_bytes=nan_tif.stat().st_size,
                               validator=receipt["validator"]))
    (EVID / "e3_build.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("allocation", "dots", "corridors_by_setting", "champion_vs_corridors", "submission")}, indent=1, default=float))


if __name__ == "__main__":
    main()
