#!/usr/bin/env python3
"""Uniqueness of the lane artefact against every prior raster (protocol rule 1).

Phase ``surface``: the pre-placement corridor probability surface (normalised to
[0, 1], zero outside the candidate band) -- Spearman rank correlation over the
full footprint plus the inherited 3-px dot-overlap statistics.
Phase ``dots``: the final written raster (binary dots) -- same statistics plus
byte-level and decoded-pixel identity against every registry file.

Comparator: the shared template's ``uniqueness.compare_array_to_registry``
(Spearman with tied ranks, 3-px Euclidean disk overlap, Jaccard) and
``two_phase_summary`` (literal vs like-for-like reading).  Corpus:
``registry/registry_index_69.json`` built by ``scripts/fetch_registry.py``.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems69.data import CACHE, load_grid  # noqa: E402
from gems57 import uniqueness  # noqa: E402
from gems57.grid import TRANSFORM  # noqa: E402

EVID = ROOT / "evidence"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["surface", "dots", "all"], default="all")
    ap.add_argument("--merge", action="store_true", help="merge per-phase outputs into e3_uniqueness.json / e3_build.json")
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
    reg = Path(__import__("os").environ.get("GEMS69_REGISTRY", str(ROOT / "registry" / "registry_index_69.json")))
    index = json.loads(reg.read_text())
    expected = ((3730, 3292), rasterio.crs.CRS.from_epsg(32611), TRANSFORM)
    out = dict(index=(str(reg.relative_to(ROOT)) if reg.is_relative_to(ROOT) else str(reg)), index_rasters=index["n_unique_grid_rasters"],
               index_complete_accessible_scan=index["complete_accessible_scan"], index_errors=index["errors"],
               order_note=("Both phases were computed after placement because the corpus download ran concurrently with the "
                           "build; the surface phase still compares the pre-placement surface. A duplicate verdict in either "
                           "phase would have stopped promotion."), phases={})

    def progress(i, n, row):
        if i % 50 == 0 or i == n:
            print(f"  {i}/{n} {time.time()-t0:6.0f}s", flush=True)

    for phase, arr, fsha in (("surface", surface, None), ("dots", dots, build["submission"]["zeros_sha256"])):
        if args.phase not in ("all", phase):
            continue
        print(f"phase {phase}", flush=True)
        res = uniqueness.compare_array_to_registry(arr, index, fp, file_sha256=fsha, expected_grid=expected,
                                                   progress=progress)
        rows = res.get("rows", [])
        ok_rows = [r for r in rows if "error" not in r]
        two = uniqueness.two_phase_summary(ok_rows, int(fp.sum()), expected_rasters=len(rows)) if ok_rows else None
        (EVID / f"e3_uniqueness_{phase}_rows.jsonl").write_text("\n".join(json.dumps(r, default=float) for r in rows))
        summ = {k: v for k, v in res.items() if k != "rows"}
        out["phases"][phase] = dict(summary=summ, two_phase=two, rows_checked=len(ok_rows),
                                    rows_with_errors=len(rows) - len(ok_rows))
        print(json.dumps(two["literal_reading"] if two else summ, indent=1, default=float)[:1500], flush=True)
        (EVID / f"e3_uniqueness_{phase}.json").write_text(json.dumps(dict(out, phases={phase: out["phases"][phase]},
                                                                           seconds=time.time() - t0), indent=1, default=float))
    if args.phase != "all":
        return
    nan_sha = build["submission"]["nan_sha256"]
    out["nan_twin_identical_bytes_in_registry"] = any(r["sha256"] == nan_sha for r in index["rasters"])
    out["zeros_identical_bytes_in_registry"] = any(r["sha256"] == build["submission"]["zeros_sha256"] for r in index["rasters"])
    out["seconds"] = time.time() - t0
    (EVID / "e3_uniqueness.json").write_text(json.dumps(out, indent=1, default=float))
    build["uniqueness"] = {ph: dict(summary=v["summary"], two_phase=v["two_phase"]) for ph, v in out["phases"].items()}
    (EVID / "e3_build.json").write_text(json.dumps(build, indent=1, default=float))
    print("done", round(out["seconds"]), "s")


def merge():
    build = json.loads((EVID / "e3_build.json").read_text())
    parts = [json.loads((EVID / f"e3_uniqueness_{ph}.json").read_text()) for ph in ("surface", "dots")]
    out = {k: v for k, v in parts[0].items() if k not in ("phases", "seconds")}
    out["phases"] = {**parts[0]["phases"], **parts[1]["phases"]}
    out["seconds_by_phase"] = {"surface": parts[0]["seconds"], "dots": parts[1]["seconds"]}
    index = json.loads(Path(__import__("os").environ.get("GEMS69_REGISTRY", str(ROOT / "registry" / "registry_index_69.json"))).read_text())
    shas = {r["sha256"] for r in index["rasters"]}
    out["zeros_identical_bytes_in_registry"] = build["submission"]["zeros_sha256"] in shas
    out["nan_twin_identical_bytes_in_registry"] = build["submission"]["nan_sha256"] in shas
    # Degeneracy diagnostic for every raster that fires the 70% dot-overlap rule on the final dots:
    # how much of the allowed domain its 3-px halo covers, and what random dots in our candidate band score.
    from scipy import ndimage as ndi
    sys.path.insert(0, str(ROOT / "src"))
    from gems69 import pipeline
    grid = load_grid()
    fp, cat = grid.footprint, grid.catalogue
    allowed = fp & ~cat & (ndi.distance_transform_edt(~cat) > 2)
    band = np.load(CACHE / "gems69_surface.npy") > 0
    with rasterio.open(ROOT / build["submission"]["zeros_tif"]) as src:
        mine = src.read(1) > 0
    rows = [json.loads(l) for l in (EVID / "e3_uniqueness_dots_rows.jsonl").read_text().splitlines() if l.strip()]
    firing = [r for r in rows if "error" not in r and r["my_dots_within_3px_of_theirs"] > 0.70]
    rand_sets = [pipeline.poisson_random(band, int(mine.sum()), sd) for sd in range(3)]   # shared baselines
    diag = []
    for r in firing:
        with rasterio.open(r["file"]) as src:
            th = (np.nan_to_num(src.read(1)) > 0) & fp
        near = ndi.distance_transform_edt(~th) <= 3
        rnd = [float(near[rs].mean()) for rs in rand_sets]
        cov = float(near[allowed].mean())
        diag.append(dict(submission=r["submission"], repo=r.get("repo"), their_dots=r["their_dots"],
                         representation=("continuous_surface" if r["their_dots"] / float(fp.sum()) > 0.20 else "dot_field"),
                         support_fraction=r["their_dots"] / float(fp.sum()), forward_overlap=r["my_dots_within_3px_of_theirs"],
                         halo_coverage_of_allowed_domain=cov, random_dots_in_our_band_overlap=rnd,
                         excess_over_random=r["my_dots_within_3px_of_theirs"] - float(np.mean(rnd)),
                         non_discriminating=bool(np.mean(rnd) > 0.70)))
    out["dot_overlap_firings_diagnostic"] = dict(
        rule=("a firing is 'non-discriminating' when random 2-px Poisson dots placed in the same candidate band (same count) "
              "already exceed the 70% limit against that raster: the rule then fires for any candidate in the band and cannot "
              "separate lane drift from domain overlap. excess_over_random measures genuine similarity."),
        firings=diag, n_firings=len(diag), n_non_discriminating=sum(d["non_discriminating"] for d in diag),
        n_discriminating_firings=sum(not d["non_discriminating"] for d in diag),
        max_excess_over_random=max([d["excess_over_random"] for d in diag], default=None))
    (EVID / "e3_uniqueness.json").write_text(json.dumps(out, indent=1, default=float))
    build["uniqueness"] = {ph: dict(summary=v["summary"], two_phase=v["two_phase"]) for ph, v in out["phases"].items()}
    build["uniqueness"]["dot_overlap_firings_diagnostic"] = out["dot_overlap_firings_diagnostic"]
    (EVID / "e3_build.json").write_text(json.dumps(build, indent=1, default=float))
    print("merged; identical bytes:", out["zeros_identical_bytes_in_registry"], out["nan_twin_identical_bytes_in_registry"])
    print(json.dumps(out["dot_overlap_firings_diagnostic"], indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
