#!/usr/bin/env python3
"""Build the uniqueness corpus: every grid-matching prior raster the owner has published.

Two sources are unioned and de-duplicated by SHA-256:

1. ``registry/base_index_60GEMSDOE.json`` -- the 655-raster index published by
   ``buffedlizard55-lab/60GEMSDOE`` (``evidence/registry_full_index.json``),
   which lists historical blobs (including rasters later deleted from HEAD).
2. A fresh scan of the HEAD tree of every GEMSDOE-family repository that exists
   today (the base index stopped at ``56GEMSDOE``).

Blobs are fetched with blob-less partial clones and one batched
``git fetch --stdin`` per repository (no GitHub REST calls per file, so the
API rate limit is not touched).  Every candidate is opened with rasterio and
kept only if it is single-band on the competition grid (3730 x 3292,
EPSG:32611, transform (100, 0, 243350, 0, -100, 4508550)).

Output: ``registry/registry_index_69.json`` in the format
``gems57.uniqueness.records_from_index`` expects (``rasters`` rows with
``repo_first``, ``sources``, ``cache_file``, ``sha256``), plus a per-repo
receipt.  Cached rasters live outside the repository (``$GEMS_REGISTRY_CACHE``,
default ``/tmp/gems_registry_cache``) because they are prior artefacts, not
outputs of this lane.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
CACHE = Path(os.environ.get("GEMS_REGISTRY_CACHE", "/tmp/gems_registry_cache"))
CLONES = Path(os.environ.get("GEMS_REGISTRY_CLONES", "/tmp/regclone"))
BASE = ROOT / "registry" / "base_index_60GEMSDOE.json"
OUT = ROOT / "registry" / "registry_index_69.json"
SELF = "GEMSDOE69"
MAX_BYTES = 3_500_000
MIN_BYTES = 20_000
GRID = dict(shape=(3730, 3292), epsg=32611,
            transform=(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0))


def family() -> list[str]:
    names = ["GEMSDOE", "GEMSDOE2", "GEMSDOE3", "GEMSDOE4", "5GEMSDOE", "6GEMSDOE",
             "7GEMSDOE", "8GEMSDOE", "GEMSDOE9", "GEMSDOE10"]
    names += [f"{i}GEMSDOE" for i in range(11, 21)]
    names += [f"GEMSDOE{i}" for i in range(21, 55)]
    names += [f"{i}GEMSDOE" for i in range(55, 63)]
    names += [f"GEMSDOE{i}" for i in range(63, 73)]
    names += ["MasterSite", "LEARNGEMSDOE"]
    return [n for n in names if n != SELF]


def run(cmd, cwd=None, inp=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, input=inp, capture_output=True, text=True,
                          timeout=timeout)


def clone(repo: str) -> Path | None:
    dest = CLONES / repo
    if (dest / ".git").exists() or (dest / "HEAD").exists():
        return dest
    r = run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
             f"https://github.com/{OWNER}/{repo}.git", str(dest)])
    if r.returncode != 0:
        print(f"[clone-fail] {repo}: {r.stderr.strip()[:200]}", flush=True)
        return None
    return dest


def head_tifs(dest: Path) -> list[tuple[str, int, str]]:
    r = run(["git", "ls-tree", "-r", "-l", "HEAD"], cwd=dest)
    out = []
    if r.returncode != 0:
        return out
    for line in r.stdout.splitlines():
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) < 4 or parts[1] != "blob":
            continue
        if not path.lower().endswith((".tif", ".tiff")):
            continue
        try:
            size = int(parts[3])
        except ValueError:
            continue
        if MIN_BYTES <= size <= MAX_BYTES:
            out.append((parts[2], size, path))
    return out


def batch_fetch(dest: Path, blobs: list[str]) -> None:
    if not blobs:
        return
    for i in range(0, len(blobs), 200):
        chunk = "\n".join(blobs[i:i + 200]) + "\n"
        run(["git", "-c", "fetch.negotiationAlgorithm=noop", "fetch", "-q", "origin",
             "--no-tags", "--no-write-fetch-head", "--recurse-submodules=no",
             "--filter=blob:none", "--stdin"], cwd=dest, inp=chunk, timeout=1800)


def blob_bytes(dest: Path, blob: str) -> bytes | None:
    r = subprocess.run(["git", "cat-file", "blob", blob], cwd=dest, capture_output=True,
                       timeout=600)
    return r.stdout if r.returncode == 0 else None


def on_grid(path: Path) -> tuple[bool, str]:
    import rasterio
    try:
        with rasterio.open(path) as src:
            if src.count != 1:
                return False, f"bands={src.count}"
            if src.shape != GRID["shape"]:
                return False, f"shape={src.shape}"
            if src.crs is None or src.crs.to_epsg() != GRID["epsg"]:
                return False, f"crs={src.crs}"
            t = tuple(round(v, 6) for v in tuple(src.transform)[:6])
            if t != GRID["transform"]:
                return False, f"transform={t}"
        return True, "ok"
    except Exception as e:  # noqa: BLE001 - any unreadable file is simply not a grid raster
        return False, f"unreadable:{type(e).__name__}"


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    CLONES.mkdir(parents=True, exist_ok=True)
    base = json.loads(BASE.read_text())
    by_repo: dict[str, list[dict]] = {}
    for r in base["rasters"]:
        for src in r["sources"]:
            repo, path = src.split(":", 1)
            by_repo.setdefault(repo, []).append(dict(blob=r["blob"], sha256=r["sha256"],
                                                     path=path, bytes=r["bytes"]))
    index: dict[str, dict] = {}
    receipt = []
    errors = []
    t0 = time.time()
    for repo in family():
        dest = clone(repo)
        if dest is None:
            errors.append(f"{repo}: clone failed")
            receipt.append(dict(repo=repo, status="clone_failed"))
            continue
        want: dict[str, list[str]] = {}
        expected_sha: dict[str, str] = {}
        for row in by_repo.get(repo, []):
            want.setdefault(row["blob"], []).append(row["path"])
            expected_sha[row["blob"]] = row["sha256"]
        heads = head_tifs(dest)
        for blob, _size, path in heads:
            want.setdefault(blob, []).append(path)
        batch_fetch(dest, sorted(want))
        kept = skipped = failed = 0
        for blob, paths in want.items():
            data = blob_bytes(dest, blob)
            if data is None:
                failed += 1
                errors.append(f"{repo}:{paths[0]} blob {blob} unavailable")
                continue
            sha = hashlib.sha256(data).hexdigest()
            if blob in expected_sha and expected_sha[blob] != sha:
                failed += 1
                errors.append(f"{repo}:{paths[0]} sha mismatch vs base index")
                continue
            sources = [f"{repo}:{p}" for p in sorted(set(paths))]
            if sha in index:
                for s in sources:
                    if s not in index[sha]["sources"]:
                        index[sha]["sources"].append(s)
                kept += 1
                continue
            cache_file = CACHE / f"{sha[:16]}.tif"
            if not cache_file.exists():
                cache_file.write_bytes(data)
            ok, why = on_grid(cache_file)
            if not ok:
                skipped += 1
                continue
            index[sha] = dict(sha256=sha, bytes=len(data), blob=blob,
                              cache_file=str(cache_file), sources=sources, repo_first=repo)
            kept += 1
        receipt.append(dict(repo=repo, status="scanned", base_index_blobs=len(by_repo.get(repo, [])),
                            head_tif_blobs=len(heads), kept=kept, skipped_not_grid=skipped,
                            failed=failed))
        print(f"[{time.time()-t0:7.1f}s] {repo}: kept={kept} skipped={skipped} failed={failed} "
              f"total_unique={len(index)}", flush=True)
    out = dict(
        owner=OWNER,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        generated_by="scripts/fetch_registry.py",
        base_index="registry/base_index_60GEMSDOE.json (60GEMSDOE evidence/registry_full_index.json @ 3202471)",
        scope=("Union of the 60GEMSDOE historical index and a fresh HEAD scan of every "
               "GEMSDOE-family repository of the owner; grid-matching single-band rasters only. "
               "Not an organizer registry; private, external or never-committed files are absent."),
        grid=dict(shape=list(GRID["shape"]), crs="EPSG:32611", transform=list(GRID["transform"])),
        repos=receipt,
        errors=errors,
        complete_accessible_scan=len(errors) == 0,
        n_unique_grid_rasters=len(index),
        rasters=sorted(index.values(), key=lambda r: (r["repo_first"], r["sources"][0])),
    )
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT} with {len(index)} rasters, {len(errors)} errors", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
