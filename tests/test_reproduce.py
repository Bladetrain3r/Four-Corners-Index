import shutil
from pathlib import Path

import pytest

from checks import reproduce
from pipeline import build
from pipeline.common import SourceError

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_cache"
needs_raw = pytest.mark.skipif(not RAW.exists(), reason="raw_cache/ is not in git (raw snapshots live in Release assets)")


@needs_raw
def test_two_offline_rebuilds_are_byte_identical_and_match_the_outputs():
    assert reproduce.main(["--raw", str(RAW)]) == 0


@needs_raw
def test_a_modified_raw_snapshot_is_rejected_by_its_manifest_hash(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(RAW, raw, copy_function=lambda s, d: Path(d).symlink_to(Path(s).resolve()))
    victim = next((raw / "ecb" / "exr_monthly").glob("*.raw"))
    victim.unlink()
    victim.write_bytes(next((RAW / "ecb" / "exr_monthly").glob("*.raw")).read_bytes() + b"\n")
    with pytest.raises(SourceError, match=r"^\[ecb\].*does not match its manifest SHA-256"):
        build.build(raw, tmp_path / "out")


def test_the_manifest_lists_every_registered_request_with_a_sha256():
    from pipeline import registry, snapshot
    entries = {(e["source"], e["name"]) for e in snapshot.read_manifest()}
    assert entries == {(r.source, r.name) for r in registry.REQUESTS}
    assert all(len(e["sha256"]) == 64 and "api_key=" not in e["url"].replace("api_key=REDACTED", "") for e in snapshot.read_manifest())
