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
    n = snapshot.restore(root / "snapshots" / "raw_2026-09-29.tar.gz", tmp_path, root / "snapshots" / "launch" / "manifest.jsonl")
    assert n == len({e["path"] for e in snapshot.read_manifest(root / "snapshots" / "launch" / "manifest.jsonl")})


def test_partial_restore_and_packing_only_the_new_snapshots(tmp_path):
    """A later daily run adds snapshots that live in another Release asset: pack them, restore each archive partially."""
    import json
    old = tmp_path / "old.jsonl"
    manifest = tmp_path / "m.jsonl"
    raw = tmp_path / "raw"
    (raw / "s" / "a").mkdir(parents=True)
    one, two = b"first", b"second"
    e1 = {"source": "s", "name": "a", "sha256": sha256_hex(one), "path": "s/a/1.raw", "url": "u", "retrieved_at": "t", "bytes": 5, "role": "primary"}
    e2 = {**e1, "sha256": sha256_hex(two), "path": "s/a/2.raw", "bytes": 6}
    (raw / e1["path"]).write_bytes(one)
    (raw / e2["path"]).write_bytes(two)
    old.write_text(json.dumps(e1) + "\n")
    manifest.write_text(json.dumps(e1) + "\n" + json.dumps(e2) + "\n")
    fresh = snapshot.new_entries(manifest, old)
    assert [e["path"] for e in fresh] == ["s/a/2.raw"]
    assert snapshot.archive(tmp_path / "new.tar.gz", raw, manifest, entries=fresh) == 1
    dest = tmp_path / "dest"
    with pytest.raises(SourceError, match="lacks 1 snapshot"):
        snapshot.restore(tmp_path / "new.tar.gz", dest, manifest)
    assert snapshot.restore(tmp_path / "new.tar.gz", dest, manifest, partial=True) == 1 and (dest / e2["path"]).read_bytes() == two


def test_a_partial_restore_skips_members_the_manifest_does_not_list_but_a_full_one_refuses_them(tmp_path):
    """A daily run can upload its raw files and then fail before its manifest commit lands: the asset must not break later restores."""
    import json
    raw = tmp_path / "raw"
    (raw / "s" / "a").mkdir(parents=True)
    body = b"orphan"
    entry = {"source": "s", "name": "a", "sha256": sha256_hex(body), "path": "s/a/9.raw", "url": "u", "retrieved_at": "t", "bytes": 6, "role": "primary"}
    (raw / entry["path"]).write_bytes(body)
    listed = tmp_path / "listed.jsonl"
    listed.write_text(json.dumps(entry) + "\n")
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    snapshot.archive(tmp_path / "a.tar.gz", raw, listed)
    with pytest.raises(SourceError, match="is not in the manifest"):
        snapshot.restore(tmp_path / "a.tar.gz", tmp_path / "o1", empty)
    assert snapshot.restore(tmp_path / "a.tar.gz", tmp_path / "o2", empty, partial=True) == 0 and not (tmp_path / "o2" / "s").exists()


def test_a_listed_but_missing_raw_file_is_kept_again_when_the_source_is_unchanged(tmp_path):
    from pipeline import fetch, registry
    req = registry.REQUESTS[0]
    body = b"same bytes"
    entry = {"source": req.source, "name": req.name, "sha256": sha256_hex(body), "path": f"{req.source}/{req.name}/x.raw", "url": "u", "retrieved_at": "t", "bytes": 10, "role": "primary"}
    loaded = fetch.Loaded(req, body, "2026-10-01T00:00:00Z", "live", "u")
    latest = {(req.source, req.name): entry}
    assert snapshot.record(loaded, tmp_path, latest) is None  # unchanged: no new manifest line
    assert (tmp_path / entry["path"]).read_bytes() == body  # but the file this checkout lacked is written
