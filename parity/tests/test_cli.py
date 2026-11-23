import json
from pathlib import Path

from parity.cli import main

SAMPLE = Path(__file__).parent.parent / "examples" / "applicants.csv"


def test_planted_bias_is_detected(capsys):
    assert main([str(SAMPLE), "-o", "advanced", "-b", "sex", "race", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["has_adverse_impact"]
    adverse = {g["name"] for d in data["dimensions"] for g in d["groups"] if g["status"] == "adverse"}
    assert {"Female", "Black or African American", "Female · Black or African American"} <= adverse


def test_fail_on_adverse_exit_code():
    assert main([str(SAMPLE), "-o", "advanced", "-b", "race", "--fail-on-adverse"]) == 1


def test_reports_written(tmp_path):
    html, md = tmp_path / "r.html", tmp_path / "r.md"
    main([str(SAMPLE), "-o", "score", "--score", "-b", "sex", "--html", str(html), "--md", str(md)])
    assert "<svg" in html.read_text() and "http" not in html.read_text().replace("http://www.w3.org", "")
    assert md.read_text().startswith("# Parity audit")


def test_bad_input_returns_2(tmp_path, capsys):
    assert main([str(tmp_path / "nope.csv"), "-o", "y", "-b", "g"]) == 2
    assert "error" in capsys.readouterr().err
