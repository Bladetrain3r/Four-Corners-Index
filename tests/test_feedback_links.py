"""Feedback is a pair of links to pre-filled GitHub issue forms: no backend, no request until a visitor submits on GitHub."""

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"
JS = (ROOT / "site" / "js" / "feedback.js").read_text()


@pytest.mark.parametrize("name,emoji", [("feedback-up.yml", "👍"), ("feedback-down.yml", "👎")])
def test_the_issue_forms_are_valid_public_and_have_the_fields_the_links_prefill(name, emoji):
    form = yaml.safe_load((TEMPLATES / name).read_text())
    assert form["name"] and form["description"] and form["title"].startswith(emoji) and form["labels"] == ["feedback"]
    fields = {b["id"]: b for b in form["body"] if "id" in b}
    assert set(fields) == {"page", "comment"} and fields["page"]["type"] == "input" and fields["comment"]["type"] == "textarea"
    assert fields["comment"]["validations"]["required"] is False  # a bare thumb is a complete answer
    note = next(b for b in form["body"] if b["type"] == "markdown")["attributes"]["value"]
    assert "public" in note and "personal details" in note
    assert all(b["type"] in ("markdown", "input", "textarea") for b in form["body"])  # nothing that cannot be prefilled by a URL


def test_the_urls_the_footer_builds_use_the_templates_and_field_ids_that_exist():
    assert 'new URLSearchParams({ template: f.template, title:' in JS and ", page })" in JS
    for t in re.findall(r'template: "([^"]+)"', JS):
        assert (TEMPLATES / t).is_file(), t
    assert (TEMPLATES / "config.yml").is_file() and yaml.safe_load((TEMPLATES / "config.yml").read_text())["blank_issues_enabled"] is True
    assert 'REPO = "https://github.com/Bladetrain3r/Four-Corners-Index"' in JS


def test_there_is_no_backend_in_the_repo_and_the_script_makes_no_request():
    assert not list((ROOT / "feedback").glob("*.py")) and not (ROOT / "pipeline" / "site_feedback.py").exists()  # a stray __pycache__ is not source
    assert not (ROOT / "data" / "manual" / "feedback.json").exists()
    for needle in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "document.cookie", "FormData", '"POST"'):
        assert needle not in JS, needle
    layout = (ROOT / "site" / "js" / "layout.js").read_text()
    assert "feedbackLinks()" in layout and "meta.feedback" not in layout
