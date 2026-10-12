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
    t0 = time.time()
    grid = load_grid()
    fp = grid.footprint
    build = json.loads((EVID / "e3_build.json").read_text())
    zeros = ROOT / build["submission"]["zeros_tif"]
    with rasterio.open(zeros) as src:
        dots = src.read(1).astype(np.float32)
    surface = np.load(CACHE / "gems69_surface.npy").astype(np.float32)
    reg = ROOT / "registry" / "registry_index_69.json"
    index = json.loads(reg.read_text())
    expected = ((3730, 3292), rasterio.crs.CRS.from_epsg(32611), TRANSFORM)
    out = dict(index=str(reg.relative_to(ROOT)), index_rasters=index["n_unique_grid_rasters"],
               index_complete_accessible_scan=index["complete_accessible_scan"], index_errors=index["errors"],
               order_note=("Both phases were computed after placement because the corpus download ran concurrently with the "
                           "build; the surface phase still compares the pre-placement surface. A duplicate verdict in either "
                           "phase would have stopped promotion."), phases={})

    def progress(i, n, row):
        if i % 50 == 0 or i == n:
            print(f"  {i}/{n} {time.time()-t0:6.0f}s", flush=True)

    for phase, arr, fsha in (("surface", surface, None), ("dots", dots, build["submission"]["zeros_sha256"])):
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
    nan_sha = build["submission"]["nan_sha256"]
    out["nan_twin_identical_bytes_in_registry"] = any(r["sha256"] == nan_sha for r in index["rasters"])
    out["zeros_identical_bytes_in_registry"] = any(r["sha256"] == build["submission"]["zeros_sha256"] for r in index["rasters"])
    out["seconds"] = time.time() - t0
    (EVID / "e3_uniqueness.json").write_text(json.dumps(out, indent=1, default=float))
    build["uniqueness"] = {ph: dict(summary=v["summary"], two_phase=v["two_phase"]) for ph, v in out["phases"].items()}
    (EVID / "e3_build.json").write_text(json.dumps(build, indent=1, default=float))
    print("done", round(out["seconds"]), "s")


if __name__ == "__main__":
    main()
