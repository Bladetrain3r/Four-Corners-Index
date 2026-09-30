"""G6: the workflow files validate, and every command they run exists and takes the flags they pass."""

import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"
NAMES = ["ci", "daily", "pages"]


def load(name):
    d = yaml.safe_load((WF / f"{name}.yml").read_text())
    d["on"] = d.pop(True, d.get("on"))  # YAML 1.1 reads the key `on` as True
    return d


def steps(d):
    return [s for j in d["jobs"].values() for s in j.get("steps", [])]


def commands(d):
    return [ln.strip() for s in steps(d) if "run" in s for ln in s["run"].splitlines() if ln.strip()]


@pytest.mark.parametrize("name", NAMES)
def test_workflow_files_are_valid_and_pin_their_actions(name):
    d = load(name)
    assert d["name"] and d["on"] and d["jobs"]
    for job in d["jobs"].values():
        assert "runs-on" in job or "uses" in job
    for s in steps(d):
        if "uses" in s:
            assert re.fullmatch(r"[\w./-]+@v\d+", s["uses"]), f"unpinned action {s['uses']}"


def test_daily_is_scheduled_daily_can_be_dispatched_and_has_minimal_permissions():
    d = load("daily")
    cron = d["on"]["schedule"][0]["cron"]
    assert len(cron.split()) == 5 and cron.split()[2:] == ["*", "*", "*"]
    assert "workflow_dispatch" in d["on"] and "force_fail" in d["on"]["workflow_dispatch"]["inputs"]
    assert d["permissions"] == {"contents": "write", "issues": "write"}
    assert d["jobs"]["deploy"]["uses"] == "./.github/workflows/pages.yml" and d["jobs"]["deploy"]["needs"] == "pipeline"
    assert d["jobs"]["deploy"]["if"] == "${{ !cancelled() }}"  # a failing source still redeploys, so the site shows its last good date


def test_pages_builds_from_the_default_branch_and_deploys_with_the_official_actions():
    d = load("pages")
    assert "workflow_call" in d["on"] and d["on"]["push"]["branches"] == ["main"]
    assert d["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    used = {s["uses"].split("@")[0] for s in steps(d) if "uses" in s}
    assert {"actions/configure-pages", "actions/upload-pages-artifact", "actions/deploy-pages"} <= used
    assert d["jobs"]["deploy"]["environment"]["name"] == "github-pages"
    assert "python -m pipeline.publish --out site" in commands(d)


def test_secrets_are_only_passed_through_env_and_never_echoed():
    for name in NAMES:
        text = (WF / f"{name}.yml").read_text()
        for m in re.finditer(r"^(.*)\$\{\{\s*secrets\.(\w+)", text, re.MULTILINE):
            assert m.group(1).strip().endswith(":") or m.group(1).strip() == "", f"{name}: secret {m.group(2)} used outside an env mapping"
        assert not re.search(r"echo[^\n]*(secrets\.|EIA_API_KEY|ENTSOE_TOKEN)", text)


@pytest.mark.parametrize("name", NAMES)
def test_every_command_a_workflow_runs_exists_and_accepts_its_flags(name):
    for cmd in commands(load(name)):
        m = re.search(r"python -m (pipeline\.\w+|pytest|checks\.\w+)", cmd)
        if m and m.group(1) != "pytest":
            mod = importlib.import_module(m.group(1))
            assert hasattr(mod, "main"), f"{m.group(1)} has no main()"
            src = Path(mod.__file__).read_text()
            for flag in re.findall(r"(--[a-z][a-z-]+)", cmd):
                assert f'"{flag}"' in src, f"{name}: {m.group(1)} has no {flag}"
        for path in re.findall(r"(?:python|verify\.py)\s+(ledger/verify\.py|checks/\w+\.py)", cmd) + re.findall(r"\b(snapshots/[\w.-]+)", cmd):
            assert (ROOT / path).exists(), f"{name}: {path} does not exist"
    daily = "\n".join(commands(load("daily")))
    for flag in ("--issue-file", "--force-fail"):
        assert flag in daily
    assert "python ledger/verify.py ledger/index.jsonl" in daily


def test_the_ledger_and_snapshot_commands_run_locally_the_way_the_workflow_runs_them(tmp_path):
    ok = subprocess.run([sys.executable, "ledger/verify.py", "ledger/index.jsonl"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert ok.returncode == 0 and "0 problems, chain intact" in ok.stdout
    manifest = ROOT / "data" / "manifests" / "raw_snapshots.jsonl"
    none = subprocess.run([sys.executable, "-m", "pipeline.snapshot", "--pack-new", str(tmp_path / "x.tar.gz"), "--since", str(manifest)],
                          cwd=ROOT, capture_output=True, text=True, check=False)
    assert none.returncode == 0 and "0 new snapshot files" in none.stdout and not (tmp_path / "x.tar.gz").exists()
    restore = subprocess.run([sys.executable, "-m", "pipeline.snapshot", "--restore", "snapshots/raw_2026-09-29.tar.gz", "--partial"],
                             cwd=ROOT, capture_output=True, text=True, check=False, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert restore.returncode == 0 and "all matching the manifest" in restore.stdout


def test_each_run_uploads_its_raw_snapshots_under_a_name_no_other_run_uses():
    """A second run on the same day must not collide with the first one's Release asset (it did, on 2026-09-30)."""
    pack = next(c for c in commands(load("daily")) if "--pack-new" in c)
    assert "${GITHUB_RUN_ID}" in pack and "--clobber" not in "\n".join(commands(load("daily")))  # unique names; append-only, never overwrite
