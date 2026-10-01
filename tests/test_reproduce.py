import shutil
from pathlib import Path

import pytest

from checks import reproduce
from pipeline import build, snapshot
from pipeline.common import SourceError

ROOT = Path(__file__).resolve().parent.parent
LAUNCH = ROOT / "snapshots" / "launch"  # the state the committed archive was taken at; the daily job moves the live manifest, not this
MANIFEST = LAUNCH / "manifest.jsonl"


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory):
    """The raw snapshots restored from the archive committed to git, so these tests run in CI as well as locally."""
    d = tmp_path_factory.mktemp("raw")
    snapshot.restore(ROOT / "snapshots" / "raw_2026-09-29.tar.gz", d, MANIFEST)
    return d


def test_two_offline_rebuilds_from_the_committed_archive_are_byte_identical_and_match_the_outputs(raw_dir):
    assert reproduce.main(["--raw", str(raw_dir), "--manifest", str(MANIFEST), "--ledger-seed", str(LAUNCH / "ledger.jsonl"),
                           "--expect", str(LAUNCH / "outputs.sha256.json")]) == 0


def test_a_modified_raw_snapshot_is_rejected_by_its_manifest_hash(raw_dir, tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(raw_dir, raw)
    latest = {(e["source"], e["name"]): e for e in snapshot.read_manifest(MANIFEST)}[("ecb", "exr_monthly")]
    victim = raw / latest["path"]
    victim.write_bytes(victim.read_bytes() + b"\n")
    with pytest.raises(SourceError, match=r"^\[ecb\].*does not match its manifest SHA-256"):
        build.build(raw, tmp_path / "out", MANIFEST)


def test_the_manifest_lists_every_required_request_with_a_sha256_and_nothing_unregistered():
    from pipeline import registry
    required = {(r.source, r.name) for r in registry.REQUESTS if not r.optional}
    every = {(r.source, r.name) for r in registry.REQUESTS}
    for path in (MANIFEST, snapshot.MANIFEST):  # the launch manifest and the live one (which the daily job extends)
        entries = {(e["source"], e["name"]) for e in snapshot.read_manifest(path)}
        assert required <= entries <= every  # optional requests (added after launch) may or may not be there yet
        assert all(len(e["sha256"]) == 64 and "api_key=" not in e["url"].replace("api_key=REDACTED", "") for e in snapshot.read_manifest(path))


def test_rebuilding_never_appends_to_the_ledger_when_no_value_changed(raw_dir, tmp_path):
    seed = LAUNCH / "ledger.jsonl"
    info = build.build(raw_dir, tmp_path, MANIFEST, ledger_seed=seed)
    assert info["_added"] == 0 and info["ledger_lines"] == len(seed.read_text().splitlines())


def test_the_rebuilt_build_info_equals_the_launch_one_except_the_method_document_version(raw_dir, tmp_path):
    """The pinned comparison leaves build_info.json out because it records the method document version (3 at launch, 4 since the air tab and Eskom)."""
    import json
    build.build(raw_dir, tmp_path, MANIFEST, ledger_seed=LAUNCH / "ledger.jsonl")
    rebuilt = json.loads((tmp_path / "data" / "index" / "build_info.json").read_text())
    launch = json.loads((LAUNCH / "build_info.json").read_text())
    assert launch["method_doc_version"] == 3 and rebuilt["method_doc_version"] == build.METHOD_DOC_VERSION
    launch["method_doc_version"] = rebuilt["method_doc_version"]
    assert rebuilt == launch  # same inputs hash, same snapshots, same ledger lines, same months
