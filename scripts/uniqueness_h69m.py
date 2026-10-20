#!/usr/bin/env python3
"""Two-phase lane-drift / duplicate check for H69-M (protocol rule 1).

Comparator: the byte-pinned shared template ``gems57.uniqueness.compare_array_to_registry``
(Spearman with tied ranks over the full footprint, forward/reverse 3 px Euclidean-disk
overlap, Jaccard, byte + decoded-pixel identity) and ``two_phase_summary`` (literal vs
like-for-like reading).  Corpus: ``registry/registry_index_69_v2.json`` (942 grid rasters,
complete scan, refreshed 2026-10-20) PLUS every TIFF already in this repo's
``submissions/`` (our own prior lane emissions).

Additional, stricter reading for continuous surfaces (support > 20 % of the footprint,
non-binary values): their "dots" are defined as their rank-matched top-K pixels
(K = my dot count) -- what that surface would emit at the same budget -- and the same
0.70 / 3 px rule is applied.  Dense binary rasters (support > 20 %, single positive
value) have no rank order; they are reported (literal) and still face the Spearman test.

Usage: uniqueness_h69m.py surface|dots [h69m|h69n]   (dots reads evidence/<id>_receipt.json;
surface reads /tmp/gems69_<id>/surface_frozen.json; default id h69m)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "vendor" / "template66", ROOT / "vendor"):
    sys.path.insert(0, str(p))

from gems57 import uniqueness as U  # noqa: E402

EVIDENCE = ROOT / "evidence"
TMP = Path("/tmp/gems69_h69m")
INDEX = ROOT / "registry" / "registry_index_69_v2.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def corpus(exclude_sha: set[str]):
    idx = json.loads(INDEX.read_text())
    own = []
    for tif in sorted((ROOT / "submissions").glob("*.tif")):
        sha = sha256_file(tif)
        if sha in exclude_sha:
            continue
        own.append(dict(sha256=sha, bytes=tif.stat().st_size, blob=None, cache_file=str(tif),
                        sources=[f"GEMSDOE69:submissions/{tif.name}"], repo_first="GEMSDOE69", origin="own-repo"))
    known = {r["sha256"] for r in idx["rasters"]}
    own = [r for r in own if r["sha256"] not in known]
    rasters = [r for r in idx["rasters"] if r["sha256"] not in exclude_sha] + own
    return dict(idx, rasters=rasters, n_own_added=len(own)), len(idx["rasters"])


def topk_overlap_rows(mine, rows, footprint, k):
    """Rank-matched top-K overlap for non-binary continuous surfaces."""
    fp = footprint
    my = (mine > 0) & fp
    out = []
    for r in rows:
        if "error" in r or r.get("representation") != "continuous_surface":
            continue
        with rasterio.open(r["file"]) as src:
            t = src.read(1).astype(np.float32)
        t = np.where(np.isfinite(t), t, 0.0)
        t[~fp] = 0
        tv = t[fp]
        pos = tv[tv > 0]
        if pos.size == 0 or np.unique(pos[: min(pos.size, 2_000_000)]).size <= 1:
            out.append(dict(submission=r["submission"], kind="dense_binary_no_rank", their_dots=r["their_dots"]))
            continue
        flat = np.flatnonzero(fp)
        order = np.argsort(-tv, kind="stable")[:k]
        top = np.zeros(fp.shape, bool)
        top.ravel()[flat[order]] = True
        ov = float(U._near(top)[my].mean()) if my.any() else 0.0
        out.append(dict(submission=r["submission"], kind="continuous_rank_matched_topk", k=int(k),
                        my_dots_within_3px_of_their_topk=ov, duplicate_by_topk_overlap=bool(ov > U.OVERLAP_LIMIT)))
    return out


def main():
    phase = sys.argv[1]
    cid = sys.argv[2] if len(sys.argv) > 2 else "h69m"
    tmp = Path(f"/tmp/gems69_{cid}")
    from gems69_s3.holdout69 import load_template_grid
    g = load_template_grid()
    fp = g.footprint
    if phase == "surface":
        frozen = json.loads((tmp / "surface_frozen.json").read_text())
        arr = np.load(frozen["surface_file"]).astype(np.float32)
        file_sha = None
        cand = dict(kind="pre-placement surface", decoded_sha256=frozen["surface_decoded_sha256"],
                    frozen_utc=frozen["frozen_utc"])
        exclude = set()
    else:
        rec = json.loads((EVIDENCE / f"{cid}_receipt.json").read_text())
        tif = ROOT / rec["raster"]["zeros"]["path"]
        file_sha = sha256_file(tif)
        assert file_sha == rec["raster"]["zeros"]["sha256"]
        with rasterio.open(tif) as src:
            arr = src.read(1).astype(np.float32)
        cand = dict(kind="final dots (zeros variant)", file=str(tif.relative_to(ROOT)), file_sha256=file_sha)
        # the twin -nan file of the SAME candidate is not a prior raster
        exclude = {rec["raster"]["zeros"]["sha256"], rec["raster"]["nan"]["sha256"]}
    idx, n_registry = corpus(exclude)
    t0 = time.time()
    res = U.compare_array_to_registry(arr, idx, fp, file_sha256=file_sha)
    rows = res.pop("rows")
    two = U.two_phase_summary(rows, int(fp.sum()), expected_rasters=len(idx["rasters"]))
    my_k = int(((arr > 0) & fp).sum())
    # For the surface phase "my dots" = the surface support; the top-K reading is only
    # meaningful for the final dots (K = emitted dot count).
    topk = topk_overlap_rows(arr, rows, fp, my_k) if phase == "dots" else []
    topk_fire = [t for t in topk if t.get("duplicate_by_topk_overlap")]
    rho_fire = [r for r in rows if r.get("duplicate_by_rho")]
    ident = [r for r in rows if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
    like = two["like_for_like_reading"]
    if phase == "surface":
        # Pre-placement gate: rank correlation vs every raster + identity. Dot overlap is a
        # property of placed dots; the surface's support is reported, not gated.
        stop = bool(rho_fire or ident or not res["complete_accessible_scan"])
    else:
        stop = bool(rho_fire or ident or like["forward_overlap_firings"] or topk_fire
                    or not res["complete_accessible_scan"])
    summary = dict(evidence_class="REGISTRY-MEASUREMENT", candidate_id=cid, phase=phase, candidate=cand,
                   corpus=dict(index=str(INDEX.relative_to(ROOT)), registry_rasters=n_registry,
                               own_repo_rasters_added=idx["n_own_added"], compared=len(rows),
                               errors=[r for r in rows if "error" in r][:20],
                               complete_accessible_scan=res["complete_accessible_scan"]),
                   my_dots=my_k, worst_spearman=res["worst_spearman_full_footprint"],
                   worst_spearman_submission=res["worst_rho_submission"],
                   literal_worst_overlap=res["worst_dot_overlap"],
                   literal_worst_overlap_submission=res["worst_overlap_submission"],
                   literal_overlap_firings=two["literal_reading"]["forward_overlap_firings"],
                   like_for_like=like, rank_matched_topk_firings=len(topk_fire),
                   rank_matched_topk_worst=max((t["my_dots_within_3px_of_their_topk"] for t in topk
                                                if "my_dots_within_3px_of_their_topk" in t), default=None),
                   rho_firings=len(rho_fire), identical=len(ident),
                   dense_binary_no_rank=sum(t.get("kind") == "dense_binary_no_rank" for t in topk),
                   stop_required=stop, seconds=round(time.time() - t0, 1),
                   policy=("rho<=0.90 vs every raster; identity none; dots phase: forward 3px overlap<=0.70 vs every "
                           "dot field (template like-for-like) and vs rank-matched top-K of every non-binary continuous "
                           "surface; literal all-positive-pixel reading reported (non-discriminating: a whole-footprint "
                           "surface overlaps any dot set, template saturation_certificate)."))
    (EVIDENCE / f"{cid}_uniqueness_{phase}.json").write_text(json.dumps(summary, indent=1))
    (tmp / f"uniq_rows_{phase}.json").write_text(json.dumps(dict(rows=rows, topk=topk), default=str))
    print(json.dumps({k: summary[k] for k in ("phase", "my_dots", "worst_spearman", "literal_worst_overlap",
                                              "rank_matched_topk_worst", "stop_required", "seconds")}, indent=1))
    print("like_for_like worst dot-field overlap:", like["worst_forward_overlap_dot_fields"],
          like["worst_forward_overlap_dot_field_submission"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
