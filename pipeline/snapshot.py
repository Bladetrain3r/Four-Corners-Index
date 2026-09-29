"""Raw snapshots: fetch every registry request live, keep the bytes under raw_cache/, and append a manifest line.

raw_cache/ is not in git (raw snapshots go to monthly GitHub Release assets); `data/manifests/raw_snapshots.jsonl` is, with a
SHA-256 for every snapshot, so a rebuild can verify it is reading exactly the bytes that were fetched. Append-only: a
request whose bytes did not change adds no line.
"""
from __future__ import annotations

import gzip
import io
import json
import tarfile
from pathlib import Path
from typing import Any

from pipeline import fetch, http, registry
from pipeline.common import SourceError, sha256_hex

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifests" / "raw_snapshots.jsonl"
RAW = ROOT / "raw_cache"


def read_manifest(path: Path = MANIFEST) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _line(entry: dict[str, Any]) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def take(mode: str = "live", raw_dir: Path = RAW, manifest: Path = MANIFEST, only: str | None = None) -> list[dict[str, Any]]:
    """Fetch and store. Returns the manifest lines added (empty if nothing changed)."""
    existing = read_manifest(manifest)
    latest = {(e["source"], e["name"]): e for e in existing}
    added: list[dict[str, Any]] = []
    for req in registry.REQUESTS:
        if only and req.source != only:
            continue
        loaded = fetch.load(req, mode)
        if loaded.kind != "live":
            raise SourceError(req.source, f"{req.name}: a snapshot must come from a live fetch, got {loaded.kind}")
        digest = sha256_hex(loaded.raw)
        prev = latest.get((req.source, req.name))
        if prev and prev["sha256"] == digest:
            continue
        rel = f"{req.source}/{req.name}/{digest[:16]}.raw"
        path = raw_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(loaded.raw)
        entry = {"source": req.source, "name": req.name, "url": http.redact(loaded.url), "retrieved_at": loaded.retrieved_at,
                 "sha256": digest, "bytes": len(loaded.raw), "path": rel, "role": req.role}
        added.append(entry)
        latest[(req.source, req.name)] = entry
    if added:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("a") as f:
            for e in added:
                f.write(_line(e))
    return added


def load_snapshots(raw_dir: Path = RAW, manifest: Path = MANIFEST) -> dict[tuple[str, str], tuple[dict[str, Any], bytes]]:
    """Latest snapshot per request, each verified against its manifest SHA-256. No network."""
    out: dict[tuple[str, str], tuple[dict[str, Any], bytes]] = {}
    for e in read_manifest(manifest):
        out[(e["source"], e["name"])] = (e, b"")
    for key, (e, _) in list(out.items()):
        path = raw_dir / e["path"]
        if not path.is_file():
            raise SourceError(e["source"], f"{e['name']}: raw snapshot {e['path']} is missing from {raw_dir}")
        raw = path.read_bytes()
        if sha256_hex(raw) != e["sha256"]:
            raise SourceError(e["source"], f"{e['name']}: raw snapshot {e['path']} does not match its manifest SHA-256")
        out[key] = (e, raw)
    return out


def archive(out_path: Path, raw_dir: Path = RAW, manifest: Path = MANIFEST) -> int:
    """One deterministic gzipped tar of every snapshot file the manifest lists (sorted, fixed mtime and owner). Returns the file count."""
    entries = sorted({e["path"]: e for e in read_manifest(manifest)}.values(), key=lambda e: e["path"])
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for e in entries:
            raw = (raw_dir / e["path"]).read_bytes()
            if sha256_hex(raw) != e["sha256"]:
                raise SourceError(e["source"], f"{e['name']}: {e['path']} does not match its manifest SHA-256; refusing to archive it")
            info = tarfile.TarInfo(e["path"])
            info.size, info.mtime, info.uid, info.gid, info.uname, info.gname, info.mode = len(raw), 0, 0, 0, "", "", 0o644
            tar.addfile(info, io.BytesIO(raw))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f, gzip.GzipFile(filename="", fileobj=f, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(buf.getvalue())
    return len(entries)


def restore(archive_path: Path, raw_dir: Path = RAW, manifest: Path = MANIFEST) -> int:
    """Extract the archive into raw_dir, checking every member against its manifest SHA-256. Returns the file count."""
    expected = {e["path"]: e for e in read_manifest(manifest)}
    n = 0
    with tarfile.open(archive_path, mode="r:gz") as tar:
        for member in tar.getmembers():
            e = expected.get(member.name)
            if e is None or not member.isfile() or ".." in Path(member.name).parts or Path(member.name).is_absolute():
                raise SourceError("snapshot", f"archive member {member.name!r} is not in the manifest")
            raw = tar.extractfile(member).read()  # type: ignore[union-attr]
            if sha256_hex(raw) != e["sha256"]:
                raise SourceError(e["source"], f"{e['name']}: archive member {member.name} does not match its manifest SHA-256")
            dest = raw_dir / member.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            n += 1
    missing = sorted(set(expected) - {m for m in expected if (raw_dir / m).is_file()})
    if missing:
        raise SourceError("snapshot", f"the archive lacks {len(missing)} snapshot files the manifest lists, first {missing[0]}")
    return n


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Fetch live and store raw snapshots plus manifest lines.")
    ap.add_argument("--only")
    ap.add_argument("--archive", type=Path, help="write a deterministic tar.gz of every manifest snapshot and exit")
    ap.add_argument("--restore", type=Path, help="extract such an archive into raw_cache/, verifying every file, and exit")
    args = ap.parse_args(argv)
    if args.archive:
        print(f"archived {archive(args.archive)} files to {args.archive}")
        return 0
    if args.restore:
        print(f"restored {restore(args.restore)} files into {RAW}, all matching the manifest")
        return 0
    added = take("live", only=args.only)
    for e in added:
        print(f"snapshot {e['source']:10s} {e['name']:24s} {e['bytes']:10d} bytes  {e['sha256'][:12]}")
    print(f"{len(added)} new snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
