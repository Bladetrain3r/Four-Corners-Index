import json
import tarfile
from pathlib import Path

import pytest

from pipeline import snapshot
from pipeline.common import SourceError, sha256_hex


def _make(tmp_path: Path, files: dict[str, bytes]) -> tuple[Path, Path]:
    raw, manifest = tmp_path / "raw", tmp_path / "manifest.jsonl"
    lines = []
    for rel, data in files.items():
        (raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (raw / rel).write_bytes(data)
        src, name = rel.split("/")[:2]
        lines.append(json.dumps({"source": src, "name": name, "url": "https://example.org/x", "retrieved_at": "2026-09-29T00:00:00Z",
                                 "sha256": sha256_hex(data), "bytes": len(data), "path": rel, "role": "primary"}))
    manifest.write_text("\n".join(lines) + "\n")
    return raw, manifest


FILES = {"ecb/exr/aaaa.raw": b"one" * 1000, "eia/retail/bbbb.raw": b"two" * 2000, "ecb/exr/cccc.raw": b"three"}


def test_archive_is_deterministic_whatever_the_output_path(tmp_path):
    raw, manifest = _make(tmp_path, FILES)
    a, b = tmp_path / "x" / "one.tar.gz", tmp_path / "y" / "different_name.tar.gz"
    assert snapshot.archive(a, raw, manifest) == 3 and snapshot.archive(b, raw, manifest) == 3
    assert a.read_bytes() == b.read_bytes()


def test_restore_reproduces_every_file_and_checks_hashes(tmp_path):
    raw, manifest = _make(tmp_path, FILES)
    arc = tmp_path / "a.tar.gz"
    snapshot.archive(arc, raw, manifest)
    out = tmp_path / "restored"
    assert snapshot.restore(arc, out, manifest) == 3
    assert {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()} == FILES


def test_archiving_a_tampered_snapshot_is_refused(tmp_path):
    raw, manifest = _make(tmp_path, FILES)
    (raw / "eia/retail/bbbb.raw").write_bytes(b"tampered")
    with pytest.raises(SourceError, match=r"^\[eia\].*does not match its manifest SHA-256"):
        snapshot.archive(tmp_path / "a.tar.gz", raw, manifest)


def test_restore_rejects_a_modified_member_an_unlisted_member_and_a_missing_one(tmp_path):
    raw, manifest = _make(tmp_path, FILES)
    arc = tmp_path / "a.tar.gz"
    snapshot.archive(arc, raw, manifest)

    def rewrite(name: str, edit) -> Path:
        out = tmp_path / name
        with tarfile.open(arc, "r:gz") as src, tarfile.open(out, "w:gz") as dst:
            for m in src.getmembers():
                data = src.extractfile(m).read()
                for m2, d2 in edit(m, data):
                    import io
                    m2.size = len(d2)
                    dst.addfile(m2, io.BytesIO(d2))
        return out

    bad = rewrite("bad.tar.gz", lambda m, d: [(m, d + b"x" if m.name.startswith("ecb/exr/aaaa") else d)])
    with pytest.raises(SourceError, match=r"^\[ecb\].*does not match its manifest SHA-256"):
        snapshot.restore(bad, tmp_path / "o1", manifest)

    def add_unlisted(m, d):
        import copy
        extra = copy.copy(m)
        extra.name = "evil/other/zzzz.raw"
        return [(m, d), (extra, d)]
    with pytest.raises(SourceError, match=r"^\[snapshot\].*not in the manifest"):
        snapshot.restore(rewrite("extra.tar.gz", add_unlisted), tmp_path / "o2", manifest)

    with pytest.raises(SourceError, match=r"^\[snapshot\].*lacks 1 snapshot files"):
        snapshot.restore(rewrite("short.tar.gz", lambda m, d: [] if m.name.endswith("cccc.raw") else [(m, d)]), tmp_path / "o3", manifest)


def test_the_committed_archive_holds_exactly_the_manifests_snapshots(tmp_path):
    root = Path(__file__).resolve().parent.parent
    n = snapshot.restore(root / "snapshots" / "raw_2026-09-29.tar.gz", tmp_path)
    assert n == len({e["path"] for e in snapshot.read_manifest()})
