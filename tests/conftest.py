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
