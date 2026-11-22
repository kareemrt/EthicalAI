"""Regenerate the visuals used in the README from the sample dataset.

    python docs/build.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from equitas import audit, load  # noqa: E402
from equitas.report import chart_svg, to_html, to_markdown  # noqa: E402

HERE = Path(__file__).resolve().parent
ATTRS = ["sex", "age_band", "race_ethnicity"]

records = load(HERE.parent / "examples" / "applicants.csv", ATTRS, outcome="advanced", label="qualified")
result = audit(records, ATTRS)
by_name = {a.name: a for a in result.attributes}

(HERE / "impact-ratios.svg").write_text(chart_svg([by_name["sex"], by_name["age_band"]]) + "\n")
(HERE / "intersection.svg").write_text(chart_svg([by_name["sex"], by_name["sex × race_ethnicity"]]) + "\n")
(HERE / "sample-report.html").write_text(to_html(result, "Sample bias audit — synthetic applicants") + "\n")
(HERE / "sample-report.md").write_text(to_markdown(result))
print("docs regenerated")
