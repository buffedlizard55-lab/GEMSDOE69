#!/usr/bin/env python3
"""Refresh the prior-raster registry: 862-blob 2026-10-12 index + a fresh HEAD scan.

Why: the parallel-run protocol requires a hash/pixel-agreement and lane-drift
check against *all* prior rasters.  ``registry/registry_index_69.json`` was frozen
on 2026-10-12; sibling repositories (GEMSDOE63..82, 12/16/60GEMSDOE, ...) have
published rasters since.  This script

1. loads every entry of the frozen index (git blob sha + sha256 pins);
2. lists the HEAD tree of every ``*GEMSDOE*`` repository of the owner through the
   GitHub REST trees API (sizes come from the tree, no blob download needed);
3. downloads every needed blob through the git-blobs API, verifies it is
   content-addressed (sha1 of the git blob header + bytes == blob sha) and, for
   frozen-index entries, that its sha256 matches the pin;
4. keeps grid-matching single-band rasters (3730x3292, EPSG:32611, competition
   transform) and writes ``registry/registry_index_69_v2.json`` in the format the
   shared template's ``gems57.uniqueness.compare_array_to_registry`` consumes.

Cached files live in /tmp/gems_registry_cache/<sha256[:16]>.tif (outside the
repository; nothing large is committed).  Any download/verification failure is
listed in ``errors`` and makes ``complete_accessible_scan`` false (fail closed).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
OLD = ROOT / "registry" / "registry_index_69.json"
OUT = ROOT / "registry" / "registry_index_69_v2.json"
CACHE = Path("/tmp/gems_registry_cache")
MIN_BYTES, MAX_BYTES = 50_000, 100_000_000
_lock = threading.Lock()


def log(msg):
    with _lock:
        print(msg, flush=True)


def gh_json(path):
    res = subprocess.run(["gh", "api", path], capture_output=True, check=True, timeout=300)
    return json.loads(res.stdout)


def gh_blob(repo, blob):
    res = subprocess.run(["gh", "api", f"repos/{OWNER}/{repo}/git/blobs/{blob}",
                          "-H", "Accept: application/vnd.github.raw"],
                         capture_output=True, check=True, timeout=900)
    return res.stdout


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def grid_ok(path: Path):
    import rasterio
    from affine import Affine
    want = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    try:
        with rasterio.open(path) as src:
            ok = (src.count == 1 and src.shape == (3730, 3292) and src.crs is not None
                  and src.crs.to_epsg() == 32611 and src.transform == want)
            return ok, None
    except Exception as exc:  # unreadable raster -> not a grid raster
        return False, str(exc)[:200]


def list_repos():
    out, page = [], 1
    while True:
        batch = gh_json(f"users/{OWNER}/repos?per_page=100&page={page}")
        if not batch:
            break
        out += [r["name"] for r in batch if "GEMSDOE" in r["name"].upper()]
        page += 1
    return sorted(set(out))


def head_tifs(repo):
    try:
        meta = gh_json(f"repos/{OWNER}/{repo}")
        tree = gh_json(f"repos/{OWNER}/{repo}/git/trees/{meta['default_branch']}?recursive=1")
    except subprocess.CalledProcessError as exc:
        return repo, None, f"tree: {exc.stderr[:200]!r}"
    items = [dict(path=t["path"], blob=t["sha"], bytes=t.get("size", 0))
             for t in tree.get("tree", []) if t.get("type") == "blob"
             and t["path"].lower().endswith((".tif", ".tiff"))
             and MIN_BYTES <= t.get("size", 0) <= MAX_BYTES]
    return repo, dict(items=items, truncated=tree.get("truncated", False)), None


def fetch(rec):
    """rec: dict(blob, repo_candidates, bytes, sha256 or None). Returns final record or error."""
    blob = rec["blob"]
    if rec.get("sha256"):
        dest = CACHE / f"{rec['sha256'][:16]}.tif"
        if dest.exists() and dest.stat().st_size == rec["bytes"]:
            data = dest.read_bytes()
            if hashlib.sha256(data).hexdigest() == rec["sha256"]:
                return dict(rec, cache_file=str(dest), status="cached")
    last = "no repo candidates"
    for repo in rec["repo_candidates"]:
        try:
            data = gh_blob(repo, blob)
            if git_blob_sha(data) != blob:
                raise ValueError("git blob sha mismatch")
            sha = hashlib.sha256(data).hexdigest()
            if rec.get("sha256") and sha != rec["sha256"]:
                raise ValueError("sha256 pin mismatch")
            dest = CACHE / f"{sha[:16]}.tif"
            dest.write_bytes(data)
            return dict(rec, sha256=sha, bytes=len(data), cache_file=str(dest), status="ok")
        except Exception as exc:
            last = f"{repo}: {str(exc)[:160]}"
    return dict(rec, status="error", error=last)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    old = json.loads(OLD.read_text())
    by_blob = {}
    for r in old["rasters"]:
        repos = [s.split(":", 1)[0] for s in r["sources"]]
        by_blob[r["blob"]] = dict(blob=r["blob"], sha256=r["sha256"], bytes=r["bytes"],
                                  sources=list(r["sources"]), repo_candidates=list(dict.fromkeys(repos)),
                                  origin="frozen-index-2026-10-12")
    repos = list_repos()
    log(f"{len(repos)} GEMSDOE-family repos")
    tree_errors, scanned = [], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for repo, res, err in ex.map(head_tifs, repos):
            if err:
                tree_errors.append(dict(repo=repo, error=err))
                continue
            scanned.append(dict(repo=repo, head_tifs=len(res["items"]), truncated=res["truncated"]))
            if res["truncated"]:
                tree_errors.append(dict(repo=repo, error="tree truncated"))
            for it in res["items"]:
                src = f"{repo}:{it['path']}"
                if it["blob"] in by_blob:
                    e = by_blob[it["blob"]]
                    if src not in e["sources"]:
                        e["sources"].append(src)
                    if repo not in e["repo_candidates"]:
                        e["repo_candidates"].append(repo)
                else:
                    by_blob[it["blob"]] = dict(blob=it["blob"], sha256=None, bytes=it["bytes"],
                                               sources=[src], repo_candidates=[repo],
                                               origin="head-scan-2026-10-20")
    log(f"{len(by_blob)} candidate blobs ({sum(e['origin'].startswith('head') for e in by_blob.values())} new)")
    done, errors = [], []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch, e) for e in by_blob.values()]
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            (errors if r["status"] == "error" else done).append(r)
            if n % 50 == 0:
                log(f"[{n}/{len(futs)}] fetched; errors={len(errors)}")
    rasters, skipped = [], []
    seen_sha = {}
    for r in done:
        ok, why = grid_ok(Path(r["cache_file"]))
        if not ok:
            skipped.append(dict(blob=r["blob"], sources=r["sources"][:3], reason=why or "not competition grid"))
            continue
        if r["sha256"] in seen_sha:  # identical bytes under two blob ids cannot happen; guard anyway
            seen_sha[r["sha256"]]["sources"] += r["sources"]
            continue
        rec = dict(sha256=r["sha256"], bytes=r["bytes"], blob=r["blob"], cache_file=r["cache_file"],
                   sources=r["sources"], repo_first=r["sources"][0].split(":", 1)[0], origin=r["origin"])
        seen_sha[r["sha256"]] = rec
        rasters.append(rec)
    rasters.sort(key=lambda x: (x["repo_first"], x["sources"][0]))
    doc = dict(owner=OWNER, generated_utc=datetime.now(timezone.utc).isoformat(),
               generated_by="scripts/refresh_registry_v2.py",
               base_index="registry/registry_index_69.json (862 rasters, 2026-10-12)",
               scope=("Union of the frozen 2026-10-12 family index and a fresh HEAD scan of every "
                      "GEMSDOE-family repository of the owner (REST trees API); grid-matching single-band "
                      "rasters only. Not an organizer registry; private/never-committed files are absent."),
               grid=dict(shape=[3730, 3292], crs="EPSG:32611",
                         transform=[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]),
               repos=scanned, errors=tree_errors + [dict(blob=e["blob"], sources=e["sources"][:2], error=e["error"]) for e in errors],
               skipped_not_grid=len(skipped), skipped_examples=skipped[:20],
               complete_accessible_scan=not tree_errors and not errors,
               n_unique_grid_rasters=len(rasters),
               n_new_since_frozen_index=sum(r["origin"].startswith("head") for r in rasters),
               rasters=rasters)
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    log(f"WROTE {OUT.name}: {len(rasters)} grid rasters ({doc['n_new_since_frozen_index']} new), "
        f"{len(skipped)} skipped, {len(doc['errors'])} errors, complete={doc['complete_accessible_scan']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
