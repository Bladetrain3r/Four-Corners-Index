"""The feedback form is off until its settings are complete and safe; a half-set configuration fails the build rather than ship a form with no contact."""

import json

import pytest

from pipeline import site_data, site_feedback

GOOD = {"endpoint": "https://feedback.example.org/feedback", "contact": "me@example.org", "retention_days": 90}


def with_cfg(monkeypatch, cfg):
    real = site_data.manual
    monkeypatch.setattr(site_data, "manual", lambda n: cfg if n == "feedback.json" else real(n))
    return site_feedback.config()


def test_the_committed_configuration_is_off_so_merging_changes_nothing_for_visitors():
    cfg = site_feedback.config()
    committed = json.loads((site_data.DATA / "manual" / "feedback.json").read_text())
    assert (cfg is None) == (committed["endpoint"] is None and committed["contact"] is None)


def test_a_complete_configuration_gives_the_page_what_it_needs(monkeypatch):
    assert with_cfg(monkeypatch, GOOD) == {"endpoint": GOOD["endpoint"], "host": "feedback.example.org", "contact": "me@example.org", "retention_days": 90, "max_comment": 1000}


@pytest.mark.parametrize("patch,why", [
    ({"contact": None}, "both"), ({"endpoint": None}, "both"), ({"endpoint": "http://feedback.example.org/feedback"}, "https"),
    ({"endpoint": "https://feedback.example.org/other"}, "/feedback"), ({"endpoint": "https://feedback.example.org/feedback?x=1"}, "/feedback"),
    ({"endpoint": "https://user:pw@feedback.example.org/feedback"}, "/feedback"), ({"endpoint": "https://203.0.113.9/feedback"}, "host name"),
    ({"retention_days": 0}, "retention_days"), ({"retention_days": 400}, "retention_days"), ({"retention_days": "90"}, "retention_days"),
    ({"contact": "x" * 201}, "contact"),
])
def test_an_unsafe_or_half_set_configuration_is_refused(monkeypatch, patch, why):
    with pytest.raises(ValueError, match=why):
        with_cfg(monkeypatch, {**GOOD, **patch})


def test_meta_json_carries_the_settings_or_null(tmp_path):
    from pipeline import publish
    publish.publish(tmp_path)
    assert "feedback" in json.loads((tmp_path / "data" / "meta.json").read_text())


def test_the_receiver_uses_only_the_standard_library_and_the_widget_sends_nothing_but_the_form():
    import ast
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    imported = {n.split(".")[0] for f in (root / "feedback").glob("*.py") for node in ast.walk(ast.parse(f.read_text()))
                for n in ([a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else [])}
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)
    js = (root / "site" / "js" / "feedback.js").read_text()
    assert 'credentials: "omit"' in js and 'referrerPolicy: "no-referrer"' in js and "cfg.endpoint" in js
    assert "localStorage" not in js and "document.cookie" not in js and "sessionStorage" not in js and "navigator.sendBeacon" not in js and js.count("fetch(") == 1


def test_the_deployment_files_agree_with_the_site_config_and_the_readme():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    default = json.loads((root / "data" / "manual" / "feedback.json").read_text())["retention_days"]
    assert f"--days {default}" in (root / "feedback" / "deploy" / "feedback-prune.service").read_text()  # what visitors are told is what the timer does
    unit = (root / "feedback" / "deploy" / "feedback.service").read_text()
    assert "--host 127.0.0.1" in unit and "--trust-proxy" in unit and "NoNewPrivileges=true" in unit and "ReadWritePaths=/var/lib/feedback" in unit
    assert "reverse_proxy 127.0.0.1:8787" in (root / "feedback" / "deploy" / "Caddyfile.example").read_text()
    assert "127.0.0.1:8787" in (root / "feedback" / "README.md").read_text()
