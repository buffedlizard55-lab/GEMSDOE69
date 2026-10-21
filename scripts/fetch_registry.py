#!/usr/bin/env python3
"""Fetch every prior prediction-like raster in the family registry (lane-drift gate).

Restores BOTH:
1. Content-addressed git blobs in .cache/registry/<git_blob_sha>.tif (751 entries in
   registry/prior_rasters.json), AND
2. SHA-256-verified grid rasters in /tmp/gems_registry_cache/<sha16>.tif (all 862 entries
   in registry/registry_index_69.json).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "prior_rasters.json"
INDEX862 = ROOT / "registry" / "registry_index_69.json"
DEST = ROOT / ".cache" / "registry"
WORKERS = 8
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(entry: dict) -> tuple[str, str, str]:
    blob = entry["git_blob_sha"]
    out = DEST / f"{blob}.tif"
    if out.exists() and out.stat().st_size == entry["bytes"] and git_blob_sha(out.read_bytes()) == blob:
        return blob, "cached", ""
    last = ""
    for alias in entry["aliases"]:
        repo = alias["repository"]
        try:
            res = subprocess.run(
                ["gh", "api", f"repos/{repo}/git/blobs/{blob}", "-H", "Accept: application/vnd.github.raw"],
                capture_output=True, check=True, timeout=600)
            data = res.stdout
            if len(data) != entry["bytes"] or git_blob_sha(data) != blob:
                raise RuntimeError("blob verification failed")
            DEST.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            return blob, "ok", repo
        except Exception as exc:
            last = f"{repo}: {exc}"
    return blob, "error", last


def ensure_862(entry: dict) -> tuple[str, str]:
    dst = Path(entry["cache_file"])
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and sha256_file(dst) == entry["sha256"]:
        return "cached", ""
    local_cand = DEST / f"{entry['blob']}.tif"
    if local_cand.exists() and sha256_file(local_cand) == entry["sha256"]:
        shutil.copy2(local_cand, dst)
        return "linked", ""
    repos = [entry["repo_first"]] + [s.split(":")[0] for s in entry.get("sources", [])]
    last = ""
    for rname in dict.fromkeys(repos):
        try:
            res = subprocess.run(
                ["gh", "api", f"repos/buffedlizard55-lab/{rname}/git/blobs/{entry['blob']}",
                 "-H", "Accept: application/vnd.github.raw"],
                capture_output=True, check=True, timeout=600)
            data = res.stdout
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise RuntimeError("sha256 mismatch")
            dst.write_bytes(data)
            return "fetched", rname
        except Exception as exc:
            last = f"{rname}: {exc}"
    return "error", last


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    entries = manifest["rasters"]
    DEST.mkdir(parents=True, exist_ok=True)
    counts = {"ok": 0, "cached": 0, "error": 0}
    errors = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(fetch_one, e) for e in entries]
        for n, fut in enumerate(as_completed(futures), 1):
            blob, status, info = fut.result()
            counts[status] += 1
            if status == "error":
                errors.append({"blob": blob, "info": info})
            elif n % 100 == 0:
                log(f"[{n}/{len(entries)}] 751-census progress")

    idx862 = json.loads(INDEX862.read_text())
    c862 = {"cached": 0, "linked": 0, "fetched": 0, "error": 0}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for st, info in ex.map(ensure_862, idx862["rasters"]):
            c862[st] += 1
            if st == "error":
                errors.append({"index862": info})

    summary = {"prior_751": counts, "index_862": c862, "errors": errors}
    (DEST / "fetch_summary.json").write_text(json.dumps(summary, indent=1))
    log(f"SUMMARY 751={counts} 862={c862} errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
