#!/usr/bin/env python3
"""Fetch every prior prediction-like raster in the family registry (lane-drift gate).

Source manifest: registry/prior_rasters.json (vendored from GEMSDOE63, built
2026-10-11 from user-listed repositories, "prediction-like paths only"; 751 unique
git blobs). Each blob is verified CONTENT-ADDRESSED:
sha1(b"blob <size>\\0" + bytes) must equal the manifest's git_blob_sha. A blob that
does not verify is excluded (comparing against wrong bytes is worse than no comparison).

Fast path: groups missing blobs by repository, runs a blob-less partial clone per
repository, and streams all requested blobs in a single ``git cat-file --batch`` pass
(avoiding hundreds of individual REST API calls). Falls back to ``gh api`` for any
unreferenced git object SHA.

Rasters land in .cache/registry/<git_blob_sha>.tif (git-ignored).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import threading
from collections import defaultdict
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


def is_valid_cached(entry: dict) -> bool:
    blob = entry["git_blob_sha"]
    out = DEST / f"{blob}.tif"
    return (out.exists() and out.stat().st_size == entry["bytes"]
            and git_blob_sha(out.read_bytes()) == blob)


def fetch_repo_batch(repo: str, items: list[dict]) -> tuple[list[str], list[dict]]:
    """Clone ``repo`` blob-lessly once and extract all blobs via ``git cat-file --batch``."""
    saved: list[str] = []
    remaining: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td) / "repo.git"
        try:
            subprocess.run(
                ["git", "clone", "-q", "--bare", "--filter=blob:none",
                 f"https://github.com/{repo}.git", str(rdir)],
                check=True, capture_output=True, timeout=300,
            )
            stdin_payload = "".join(e["git_blob_sha"] + "\n" for e in items).encode()
            res = subprocess.run(
                ["git", "cat-file", "--batch"],
                cwd=rdir, input=stdin_payload, capture_output=True, check=True, timeout=600,
            )
            buf = memoryview(res.stdout)
            pos = 0
            by_sha = {e["git_blob_sha"]: e for e in items}
            for e in items:
                nl = res.stdout.find(b"\n", pos)
                if nl < 0:
                    remaining.append(e)
                    continue
                header = bytes(buf[pos:nl]).decode("ascii", errors="replace").split()
                pos = nl + 1
                if len(header) >= 3 and header[1] == "blob":
                    sz = int(header[2])
                    raw = bytes(buf[pos:pos + sz])
                    pos += sz + 1  # trailing newline
                    if len(raw) == e["bytes"] and git_blob_sha(raw) == e["git_blob_sha"]:
                        (DEST / f"{e['git_blob_sha']}.tif").write_bytes(raw)
                        saved.append(e["git_blob_sha"])
                    else:
                        remaining.append(by_sha[e["git_blob_sha"]])
                else:
                    remaining.append(e)
        except Exception:
            remaining = list(items)
    return saved, remaining


def fetch_one_gh(entry: dict) -> tuple[str, str, str]:
    blob = entry["git_blob_sha"]
    if is_valid_cached(entry):
        return blob, "cached", ""
    last = "no aliases"
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
            (DEST / f"{blob}.tif").write_bytes(data)
            return blob, "ok", repo
        except Exception as exc:
            last = f"{repo}: {exc}"
    return blob, "error", last


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    entries = manifest["rasters"]
    DEST.mkdir(parents=True, exist_ok=True)
    counts = {"ok": 0, "cached": 0, "error": 0}
    todo = []
    for e in entries:
        if is_valid_cached(e):
            counts["cached"] += 1
        else:
            todo.append(e)
    log(f"Initial check: {counts['cached']} cached, {len(todo)} missing out of {len(entries)}")

    by_repo: dict[str, list[dict]] = defaultdict(list)
    for e in todo:
        by_repo[e["aliases"][0]["repository"]].append(e)

    fallback: list[dict] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_repo_batch, repo, items): repo for repo, items in by_repo.items()}
        for fut in as_completed(futs):
            repo = futs[fut]
            saved, rem = fut.result()
            counts["ok"] += len(saved)
            fallback.extend(rem)
            log(f"[batch] {repo}: +{len(saved)} ok, {len(rem)} fallback")

    errors = []
    if fallback:
        log(f"Running gh-api fallback for {len(fallback)} blobs...")
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs2 = [ex.submit(fetch_one_gh, e) for e in fallback]
            for fut in as_completed(futs2):
                blob, status, info = fut.result()
                counts[status] += 1
                if status == "error":
                    errors.append({"blob": blob, "info": info})
                    log(f"[fallback] ERR {blob[:12]} {info[:120]}")

    summary = {"total": len(entries), **counts, "errors": errors}
    (DEST / "fetch_summary.json").write_text(json.dumps(summary, indent=1))
    log(f"SUMMARY {summary['ok']} ok, {summary['cached']} cached, {summary['error']} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
