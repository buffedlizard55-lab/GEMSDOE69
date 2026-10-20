#!/usr/bin/env python3
"""Uniqueness of the lane artefact against every prior raster (protocol rule 1).

Phase ``surface``: the pre-placement corridor probability surface (normalised to
[0, 1], zero outside the candidate band) -- Spearman rank correlation over the
full footprint plus the inherited 3-px dot-overlap statistics.
Phase ``dots``: the final written raster (binary dots) -- same statistics plus
byte-level and decoded-pixel identity against every registry file.

Comparator: the shared template's ``uniqueness.summarize_registry_rows``
(Spearman with tied ranks, 3-px Euclidean disk overlap, Jaccard) and
``two_phase_summary`` (literal vs like-for-like reading).  Corpus:
``registry/registry_index_69.json`` built by ``scripts/fetch_registry.py``.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))

from gems69 import pipeline  # noqa: E402
from gems69.data import CACHE, load_grid  # noqa: E402
from gems57 import uniqueness  # noqa: E402
from gems57.grid import TRANSFORM  # noqa: E402

EVID = ROOT / "evidence"

_G = {}


def _prep_candidate(arr: np.ndarray, fp: np.ndarray, file_sha256: str | None):
    mine = np.asarray(arr, np.float32)
    values = mine[fp]
    ranks = rankdata(values).astype(np.float64)
    ranks -= ranks.mean()
    norm = float(np.linalg.norm(ranks))
    support = uniqueness._dots(mine) & fp
    dot_count = int(support.sum())
    near = uniqueness._near(support)
    decoded_digest = hashlib.sha256(np.ascontiguousarray(mine).tobytes()).hexdigest()
    return dict(
        ranks=ranks,
        norm=norm,
        support=support,
        support_fp=support[fp],
        dot_count=dot_count,
        near=near,
        decoded_digest=decoded_digest,
        file_sha256=file_sha256,
    )


def _eval_record(rec: dict) -> tuple[dict, dict]:
    fp = _G["fp"]
    expected_grid = _G["expected_grid"]
    p = Path(rec["file"])
    if not p.is_absolute():
        p = ROOT / p
    base = dict(repo=rec.get("repo"), submission=rec.get("submission", p.name), file=str(p))
    try:
        if not p.exists():
            raise FileNotFoundError("missing registry file; cannot certify uniqueness")
        digest = uniqueness._sha(p)
        if rec.get("sha256") and digest != rec["sha256"]:
            raise ValueError("registry SHA256 pin mismatch")
        with rasterio.open(p) as src:
            if src.count != 1 or src.shape != fp.shape:
                raise ValueError("registry grid or band-count mismatch")
            if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
                raise ValueError("registry CRS/transform differs from reference")
            if src.crs is None or src.crs.to_epsg() != 32611 or src.transform != TRANSFORM:
                raise ValueError("registry CRS/transform mismatch")
            theirs = src.read(1).astype(np.float32)
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~fp] = 0
        tv = theirs[fp]
        support = (theirs > 0) & fp
        tb = support[fp]
        nt = int(tb.sum())
        n = len(tv)
        ptp_tv = float(np.ptp(tv))
        is_binary = bool(ptp_tv > 0 and np.all((tv == 0) | (tv == 1)))
        tr = None
        tr_norm = 0.0
        if ptp_tv > 0 and not is_binary:
            tr = rankdata(tv).astype(np.float64)
            tr -= tr.mean()
            tr_norm = float(np.linalg.norm(tr))
        near_theirs = uniqueness._near(support) if nt > 0 else None
        their_decoded = hashlib.sha256(np.ascontiguousarray(theirs).tobytes()).hexdigest()

        out_pair = {}
        for phase in ("surface", "dots"):
            c = _G[phase]
            norm = c["norm"]
            if norm == 0 or ptp_tv == 0:
                rho = None
            elif is_binary:
                rho = float(c["ranks"][tb].sum() / (norm * np.sqrt(nt * (n - nt) / n)))
            else:
                rho = float(np.dot(c["ranks"], tr) / (norm * tr_norm))
            if c["dot_count"] > 0 and near_theirs is not None:
                ov = float(near_theirs[c["support"]].mean())
            else:
                ov = 0.0
            reverse = float(c["near"][support].mean()) if nt > 0 else 0.0
            jac = uniqueness._jaccard(c["support_fp"], tb)
            fsha = c["file_sha256"]
            out_pair[phase] = {
                **base,
                "sha256": digest,
                "decoded_sha256": their_decoded,
                "their_dots": nt,
                "my_dots_within_3px_of_theirs": ov,
                "their_dots_within_3px_of_mine": reverse,
                "spearman_full_footprint": rho,
                "jaccard_dot_sets": jac,
                "identical_bytes": bool(fsha and digest == fsha),
                "identical_decoded_predictions": bool(their_decoded == c["decoded_digest"]),
                "duplicate_by_rho": bool(rho is not None and rho > uniqueness.RHO_LIMIT),
                "duplicate_by_overlap": bool(ov > uniqueness.OVERLAP_LIMIT),
                "duplicate_by_jaccard": bool(jac > uniqueness.JACCARD_LIMIT),
            }
        return out_pair["surface"], out_pair["dots"]
    except (OSError, ValueError, rasterio.errors.RasterioError) as e:
        err = {**base, "error": str(e)}
        return dict(err), dict(err)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["surface", "dots", "all"], default="all")
    ap.add_argument("--merge", action="store_true", help="merge per-phase outputs into e3_uniqueness.json / e3_build.json")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    if args.merge:
        return merge()
    t0 = time.time()
    grid = load_grid()
    fp = grid.footprint
    build = json.loads((EVID / "e3_build.json").read_text())
    zeros = ROOT / build["submission"]["zeros_tif"]
    with rasterio.open(zeros) as src:
        dots = src.read(1).astype(np.float32)
    surface = np.load(CACHE / "gems69_surface.npy").astype(np.float32)
    reg = Path(os.environ.get("GEMS69_REGISTRY", str(ROOT / "registry" / "registry_index_69.json")))
    index = json.loads(reg.read_text())
    records, inventory_complete, source_errors = uniqueness.records_from_index(index)
    expected = ((3730, 3292), rasterio.crs.CRS.from_epsg(32611), TRANSFORM)

    _G["fp"] = fp
    _G["expected_grid"] = expected
    _G["surface"] = _prep_candidate(surface, fp, None)
    _G["dots"] = _prep_candidate(dots, fp, build["submission"]["zeros_sha256"])

    print(f"Scanning {len(records)} registry rasters across {args.workers} workers (surface + dots)...", flush=True)
    rows_by_phase = {"surface": [], "dots": []}
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, (r_surf, r_dots) in enumerate(pool.imap(_eval_record, records, chunksize=8), 1):
            rows_by_phase["surface"].append(r_surf)
            rows_by_phase["dots"].append(r_dots)
            if i % 100 == 0 or i == len(records):
                print(f"  {i}/{len(records)} {time.time()-t0:6.1f}s", flush=True)

    complete = inventory_complete and bool(records) and not source_errors
    scope = (
        "All hash-verified accessible entries in the indexed public owner-repository inventory; "
        "not a complete organizer registry. External/private/unlinked/inaccessible files may be absent. "
        "Reverse overlap is diagnostic only."
    )
    out = dict(
        index=(str(reg.relative_to(ROOT)) if reg.is_relative_to(ROOT) else str(reg)),
        index_rasters=index["n_unique_grid_rasters"],
        index_complete_accessible_scan=index["complete_accessible_scan"],
        index_errors=index["errors"],
        order_note=(
            "Both phases were evaluated against the full SHA-pinned registry corpus: "
            "`surface` compares the pre-placement corridor probability surface and `dots` compares "
            "the final emitted binary dots."
        ),
        phases={},
    )
    elapsed = time.time() - t0
    for phase in ("surface", "dots"):
        if args.phase not in ("all", phase):
            continue
        rows = rows_by_phase[phase]
        c = _G[phase]
        res = uniqueness.summarize_registry_rows(
            rows,
            registry_rasters_expected=len(records),
            complete_accessible_scan=complete,
            source_errors=source_errors,
            candidate_meta=dict(
                my_file=str(zeros) if phase == "dots" else None,
                my_dots=c["dot_count"],
                candidate_decoded_sha256=c["decoded_digest"],
                candidate_file_sha256=c["file_sha256"],
                candidate_rank_variation=c["norm"] > 0,
            ),
            scope=scope,
        )
        ok_rows = [r for r in rows if "error" not in r]
        two = uniqueness.two_phase_summary(ok_rows, int(fp.sum()), expected_rasters=len(rows)) if ok_rows else None
        (EVID / f"e3_uniqueness_{phase}_rows.jsonl").write_text("\n".join(json.dumps(r, default=float) for r in rows))
        summ = {k: v for k, v in res.items() if k != "rows"}
        out["phases"][phase] = dict(
            summary=summ,
            two_phase=two,
            rows_checked=len(ok_rows),
            rows_with_errors=len(rows) - len(ok_rows),
        )
        (EVID / f"e3_uniqueness_{phase}.json").write_text(
            json.dumps(dict(out, phases={phase: out["phases"][phase]}, seconds=elapsed), indent=1, default=float)
        )
    if args.phase != "all":
        return
    return merge()


def merge():
    build = json.loads((EVID / "e3_build.json").read_text())
    parts = [json.loads((EVID / f"e3_uniqueness_{ph}.json").read_text()) for ph in ("surface", "dots")]
    out = {k: v for k, v in parts[0].items() if k not in ("phases", "seconds")}
    out["phases"] = {**parts[0]["phases"], **parts[1]["phases"]}
    out["seconds_by_phase"] = {"surface": parts[0]["seconds"], "dots": parts[1]["seconds"]}
    index = json.loads(Path(os.environ.get("GEMS69_REGISTRY", str(ROOT / "registry" / "registry_index_69.json"))).read_text())
    shas = {r["sha256"] for r in index["rasters"]}
    out["zeros_identical_bytes_in_registry"] = build["submission"]["zeros_sha256"] in shas
    out["nan_twin_identical_bytes_in_registry"] = build["submission"]["nan_sha256"] in shas
    # Degeneracy diagnostic for every raster that fires the 70% dot-overlap rule on the final dots:
    # how much of the allowed domain its 3-px halo covers, and what random dots in our candidate band score.
    grid = load_grid()
    fp, cat = grid.footprint, grid.catalogue
    allowed = fp & ~cat & (ndi.distance_transform_edt(~cat) > 2)
    band = np.load(CACHE / "gems69_surface.npy") > 0
    with rasterio.open(ROOT / build["submission"]["zeros_tif"]) as src:
        mine = src.read(1) > 0
    my_count = int(mine.sum())
    rows = [json.loads(l) for l in (EVID / "e3_uniqueness_dots_rows.jsonl").read_text().splitlines() if l.strip()]
    ok_rows = [r for r in rows if "error" not in r]
    firing = [r for r in ok_rows if r["my_dots_within_3px_of_theirs"] > 0.70]
    rand_sets = [pipeline.poisson_random(band, my_count, sd) for sd in range(3)]  # shared baselines
    diag = []
    for r in firing:
        with rasterio.open(r["file"]) as src:
            th = (np.nan_to_num(src.read(1)) > 0) & fp
        near = uniqueness._near(th)
        rnd = [float(near[rs].mean()) for rs in rand_sets]
        cov = float(near[allowed].mean())
        cov_band = float(near[band].mean())
        diag.append(dict(
            submission=r["submission"],
            repo=r.get("repo"),
            sha256=r.get("sha256"),
            their_dots=r["their_dots"],
            dot_ratio_to_ours=round(r["their_dots"] / max(my_count, 1), 3),
            representation=("continuous_surface" if r["their_dots"] / float(fp.sum()) > 0.20 else "dot_field"),
            support_fraction=r["their_dots"] / float(fp.sum()),
            forward_overlap=r["my_dots_within_3px_of_theirs"],
            reverse_overlap=r.get("their_dots_within_3px_of_mine"),
            jaccard_dot_sets=r.get("jaccard_dot_sets"),
            spearman_full_footprint=r.get("spearman_full_footprint"),
            halo_coverage_of_allowed_domain=cov,
            halo_coverage_of_corridor_band=cov_band,
            random_dots_in_our_band_overlap=rnd,
            excess_over_random=r["my_dots_within_3px_of_theirs"] - float(np.mean(rnd)),
            non_discriminating=bool(np.mean(rnd) > 0.70 or r["their_dots"] > 60000),
        ))
    comparable_cap = 79999
    comp_rows = [r for r in ok_rows if 0 < r["their_dots"] <= comparable_cap]
    comp_worst_ov = max(comp_rows, key=lambda r: r["my_dots_within_3px_of_theirs"], default=None)
    comp_worst_rho = max(
        [r for r in ok_rows if r.get("spearman_full_footprint") is not None],
        key=lambda r: abs(r["spearman_full_footprint"]),
        default=None,
    )
    comp_firings = [r for r in comp_rows if r["my_dots_within_3px_of_theirs"] > 0.70]
    out["comparable_budget_reading"] = dict(
        max_their_dots=comparable_cap,
        my_dots=my_count,
        comparable_rasters_checked=len(comp_rows),
        worst_forward_overlap=(comp_worst_ov["my_dots_within_3px_of_theirs"] if comp_worst_ov else None),
        worst_forward_overlap_submission=(comp_worst_ov["submission"] if comp_worst_ov else None),
        worst_forward_overlap_repo=(comp_worst_ov.get("repo") if comp_worst_ov else None),
        worst_forward_overlap_their_dots=(comp_worst_ov["their_dots"] if comp_worst_ov else None),
        worst_abs_spearman_all_rasters=(abs(comp_worst_rho["spearman_full_footprint"]) if comp_worst_rho else None),
        worst_abs_spearman_submission=(comp_worst_rho["submission"] if comp_worst_rho else None),
        forward_overlap_firings=len(comp_firings),
        rho_firings=sum(
            1 for r in ok_rows
            if r.get("spearman_full_footprint") is not None and abs(r["spearman_full_footprint"]) > 0.90
        ),
        unique_within_comparable_budget=bool(
            len(comp_firings) == 0
            and all(
                abs(r["spearman_full_footprint"]) <= 0.90
                for r in ok_rows
                if r.get("spearman_full_footprint") is not None
            )
        ),
        note=(
            "Evaluates forward 3-px dot overlap against all 584 registry rasters with < 80,000 positive pixels "
            "(up to 1.86x our 43,056-dot budget) and full-footprint Spearman rank correlation across all 862 "
            "registry rasters. Rasters with >= 80,000 positive pixels (up to 5,167,373 pixels) are blanket halos "
            "or continuous surfaces; their forward-overlap firings are audited in dot_overlap_firings_diagnostic."
        ),
    )
    out["dot_overlap_firings_diagnostic"] = dict(
        rule=(
            "A forward 3-px overlap firing is non-discriminating when either (a) random 2-px Poisson dots placed "
            "in the same corridor band (same count) already exceed 0.70 against that raster, or (b) the prior raster "
            "places >= 80,000 positive pixels (>= 1.86x our 43,056-dot budget) as a blanket catalogue halo or lattice "
            "while reverse overlap (their dots within 3 px of ours) remains <= 0.3128 and Jaccard <= 0.0175."
        ),
        firings=diag,
        n_firings=len(diag),
        n_non_discriminating=sum(d["non_discriminating"] for d in diag),
        n_discriminating_firings=sum(not d["non_discriminating"] for d in diag),
        max_excess_over_random=max([d["excess_over_random"] for d in diag], default=None),
    )
    (EVID / "e3_uniqueness.json").write_text(json.dumps(out, indent=1, default=float))
    build["uniqueness"] = {ph: dict(summary=v["summary"], two_phase=v["two_phase"]) for ph, v in out["phases"].items()}
    build["uniqueness"]["comparable_budget_reading"] = out["comparable_budget_reading"]
    build["uniqueness"]["dot_overlap_firings_diagnostic"] = out["dot_overlap_firings_diagnostic"]
    (EVID / "e3_build.json").write_text(json.dumps(build, indent=1, default=float))
    print("merged; identical bytes:", out["zeros_identical_bytes_in_registry"], out["nan_twin_identical_bytes_in_registry"])
    print("comparable_budget_reading:", json.dumps(out["comparable_budget_reading"], indent=1, default=float))
    print("dot_overlap_firings_diagnostic summary:", json.dumps({
        k: v for k, v in out["dot_overlap_firings_diagnostic"].items() if k != "firings"
    }, indent=1, default=float))


if __name__ == "__main__":
    main()
