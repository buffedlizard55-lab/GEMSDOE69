#!/usr/bin/env python3
"""Fetch every prior prediction-like raster in the family registry (lane-drift gate).

Source manifest: registry/prior_rasters.json (vendored from GEMSDOE63, built
2026-10-11 from user-listed repositories, "prediction-like paths only"; 751 unique
git blobs). Each blob is fetched via the git-blobs API and verified CONTENT-ADDRESSED:
sha1(b"blob <size>\\0" + bytes) must equal the manifest's git_blob_sha. A blob that
does not verify is excluded (comparing against wrong bytes is worse than no comparison).

Rasters land in .cache/registry/<git_blob_sha>.tif (git-ignored).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "prior_rasters.json"
DEST = ROOT / ".cache" / "registry"
WORKERS = 8
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch_one(entry: dict) -> tuple[str, str, str]:
    blob = entry["git_blob_sha"]
    out = DEST / f"{blob}.tif"
    if out.exists() and out.stat().st_size == entry["bytes"] and \
            git_blob_sha(out.read_bytes()) == blob:
        return blob, "cached", ""
    for alias in entry["aliases"]:
        repo = alias["repository"]
        try:
            res = subprocess.run(
                ["gh", "api", f"repos/{repo}/git/blobs/{blob}",
                 "-H", "Accept: application/vnd.github.raw"],
                capture_output=True, check=True, timeout=600)
            data = res.stdout
            if len(data) != entry["bytes"]:
                raise RuntimeError(f"size {len(data)} != {entry['bytes']}")
            if git_blob_sha(data) != blob:
                raise RuntimeError("git blob sha mismatch")
            DEST.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            return blob, "ok", repo
        except Exception as exc:  # try next alias
            last = f"{repo}: {exc}"
    return blob, "error", last


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
                log(f"[{n}/{len(entries)}] ERR {blob[:12]} {info[:120]}")
            elif n % 50 == 0 or status == "ok":
                log(f"[{n}/{len(entries)}] {status} {blob[:12]} {info}")
    summary = {"total": len(entries), **counts, "errors": errors}
    (DEST / "fetch_summary.json").write_text(json.dumps(summary, indent=1))
    log(f"SUMMARY {summary['ok']} ok, {summary['cached']} cached, {summary['error']} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
