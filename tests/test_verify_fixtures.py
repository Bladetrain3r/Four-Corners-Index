import hashlib
import json

from checks import verify_fixtures as vf


def _entry(f, body, **kw):
    e = {"file": f, "url": "https://example.org/x", "fetched_at": "2026-09-29T00:00:00Z",
         "sha256": hashlib.sha256(body).hexdigest(), "note": "n", "source_kind": "live"}
    e.update(kw)
    return e


def _make(tmp_path, body=b"abc", **kw):
    d = tmp_path / "src"
    d.mkdir()
    (d / "a.json").write_bytes(body)
    (d / "MANIFEST.json").write_text(json.dumps([_entry("a.json", b"abc", **kw)]))
    return tmp_path


def test_good_manifest_passes(tmp_path):
    assert vf.main(["--root", str(_make(tmp_path))]) == 0


def test_tampered_fixture_fails(tmp_path):
    assert vf.main(["--root", str(_make(tmp_path, body=b"tampered"))]) == 1


def test_key_in_url_fails(tmp_path):
    assert vf.main(["--root", str(_make(tmp_path, url="https://x/y?api_key=abc123"))]) == 1


def test_redacted_key_in_url_passes(tmp_path):
    assert vf.main(["--root", str(_make(tmp_path, url="https://x/y?api_key=REDACTED"))]) == 0


def test_unlisted_file_fails(tmp_path):
    root = _make(tmp_path)
    (root / "src" / "extra.csv").write_text("x")
    assert vf.main(["--root", str(root)]) == 1


def test_missing_manifest_fails(tmp_path):
    (tmp_path / "src").mkdir()
    assert vf.main(["--root", str(tmp_path)]) == 1
