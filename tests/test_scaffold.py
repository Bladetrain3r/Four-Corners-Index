import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from checks import repo_size

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("name", ["series", "index"])
def test_schema_is_valid_json_schema(name):
    schema = json.loads((ROOT / "schema" / f"{name}.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)


def test_series_schema_accepts_and_rejects():
    schema = json.loads((ROOT / "schema" / "series.schema.json").read_text())
    good = {
        "source": "eia", "series_id": "x", "region": "US", "layer": "cost", "buyer_type": "household",
        "period_start": "2026-01-01", "period_end": "2026-01-31", "value": 0.17, "unit": "USD/kWh",
        "currency": "USD", "as_of": "2026-03-01", "retrieved_at": "2026-09-29T19:00:00Z",
        "raw_sha256": "0" * 64, "confidence": "primary",
    }
    jsonschema.validate(good, schema)
    bad = dict(good, value="n/a")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
    missing = {k: v for k, v in good.items() if k != "raw_sha256"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(missing, schema)


def test_repo_size_check_passes_and_can_fail():
    assert repo_size.main(["--root", str(ROOT)]) == 0
    assert repo_size.main(["--root", str(ROOT), "--limit-mb", "0.0001"]) == 1


def test_repo_size_cli_exit_code():
    r = subprocess.run([sys.executable, "checks/repo_size.py", "--limit-mb", "0.0001"], cwd=ROOT, check=False)
    assert r.returncode == 1
