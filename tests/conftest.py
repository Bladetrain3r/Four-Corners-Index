import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"


def load_manifest(source: str) -> dict[str, dict]:
    return {e["file"]: e for e in json.loads((FIXTURES / source / "MANIFEST.json").read_text())}


@pytest.fixture
def fixture_bytes():
    def _load(source: str, name: str) -> tuple[bytes, dict]:
        return (FIXTURES / source / name).read_bytes(), load_manifest(source)[name]
    return _load


@pytest.fixture
def series_schema():
    import jsonschema
    schema = json.loads((ROOT / "schema" / "series.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


@pytest.fixture(scope="session")
def launch_site(tmp_path_factory):
    """The site as published from the launch bundle (snapshots/launch/: archive, manifest, ledger), built offline.

    Tests that pin VALUES (a price, a date, a count) use this and never the committed data/, which the daily job rewrites every day:
    a number that was true at launch stays true here, whatever the sources publish next. Tests of the committed data assert
    relations and structure only (see tests/README.md).
    """
    import shutil

    from pipeline import build, publish, site_data, snapshot
    launch = ROOT / "snapshots" / "launch"
    raw, data_root, out = (tmp_path_factory.mktemp(n) for n in ("launch_raw", "launch_data", "launch_site"))
    snapshot.restore(ROOT / "snapshots" / "raw_2026-09-29.tar.gz", raw, launch / "manifest.jsonl")
    build.build(raw, data_root, launch / "manifest.jsonl", ledger_seed=launch / "ledger.jsonl")
    shutil.copytree(ROOT / "data" / "manual", data_root / "data" / "manual")
    (data_root / "data" / "manifests").mkdir(exist_ok=True)
    shutil.copy(launch / "manifest.jsonl", data_root / "data" / "manifests" / "raw_snapshots.jsonl")
    shutil.copy(launch / "ledger.jsonl", data_root / "ledger" / "index.jsonl")
    health = data_root / "data" / "health.json"
    health.write_text('{"sources": {}}\n')
    saved = (site_data.DATA, site_data.ROOT, publish.DATA, publish.ROOT, publish.MANIFEST)
    site_data.DATA, publish.DATA = data_root / "data", data_root / "data"
    site_data.ROOT = publish.ROOT = data_root  # ledger/index.jsonl is read from ROOT; METHOD.md is copied below
    publish.MANIFEST = data_root / "data" / "manifests" / "raw_snapshots.jsonl"
    shutil.copy(saved[1] / "METHOD.md", data_root / "METHOD.md")
    try:
        publish.publish(out, health=health)
    finally:
        site_data.DATA, site_data.ROOT, publish.DATA, publish.ROOT, publish.MANIFEST = saved
    return out
