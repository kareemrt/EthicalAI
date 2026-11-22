"""Run with:  python -m unittest discover tests"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from equitas import audit, load
from equitas.cli import main
from equitas.data import UNKNOWN, Record
from equitas.metrics import ADVERSE, EXCLUDED, OK, REFERENCE, REVIEW
from equitas.report import RENDERERS
from equitas.stats import fisher_exact, two_proportion_p, wilson_interval

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "applicants.csv"


def records(spec):
    """spec: {category: (selected, total)} -> list[Record] on attribute 'g'."""
    out = []
    for cat, (k, n) in spec.items():
        out += [Record({"g": cat}, i < k) for i in range(n)]
    return out


class Stats(unittest.TestCase):
    def test_wilson_known_value(self):
        lo, hi = wilson_interval(50, 100)
        self.assertAlmostEqual(lo, 0.4038, places=3)
        self.assertAlmostEqual(hi, 0.5962, places=3)

    def test_wilson_edges(self):
        self.assertEqual(wilson_interval(0, 0), (0.0, 0.0))
        self.assertEqual(wilson_interval(0, 10)[0], 0.0)

    def test_fisher_lady_tasting_tea(self):
        # Classic textbook table: [[3, 1], [1, 3]] -> p = 0.4857
        self.assertAlmostEqual(fisher_exact(3, 1, 1, 3), 0.4857, places=3)

    def test_identical_rates_not_significant(self):
        self.assertAlmostEqual(two_proportion_p(30, 100, 30, 100), 1.0)

    def test_large_gap_significant(self):
        self.assertLess(two_proportion_p(20, 200, 60, 200), 1e-4)


class Metrics(unittest.TestCase):
    def status(self, spec, **kw):
        a = audit(records(spec), ["g"], **kw).attributes[0]
        return {g.category: g.status for g in a.groups}, a

    def test_four_fifths_and_significant_is_adverse(self):
        s, a = self.status({"A": (60, 200), "B": (30, 200)})
        self.assertEqual(s, {"A": REFERENCE, "B": ADVERSE})
        self.assertAlmostEqual(a.worst.impact_ratio, 0.5)

    def test_low_ratio_small_sample_is_review(self):
        s, _ = self.status({"A": (6, 10), "B": (4, 10)})
        self.assertEqual(s["B"], REVIEW)

    def test_equal_rates_ok(self):
        s, _ = self.status({"A": (50, 100), "B": (49, 100)})
        self.assertEqual(s["B"], OK)

    def test_small_and_unknown_groups_excluded(self):
        s, _ = self.status({"A": (50, 100), "B": (45, 100), "tiny": (0, 2), UNKNOWN: (0, 20)})
        self.assertEqual((s["tiny"], s[UNKNOWN]), (EXCLUDED, EXCLUDED))

    def test_intersections(self):
        recs = [Record({"x": x, "y": y}, sel) for x in "ab" for y in "cd" for sel in (True, False) for _ in range(30)]
        names = [a.name for a in audit(recs, ["x", "y"]).attributes]
        self.assertEqual(names, ["x", "y", "x × y"])


class Sample(unittest.TestCase):
    """The sample dataset has planted bias; the audit must find it and nothing spurious on sex alone."""

    @classmethod
    def setUpClass(cls):
        recs = load(SAMPLE, ["sex", "age_band", "race_ethnicity"], outcome="advanced", label="qualified")
        cls.audit = audit(recs, ["sex", "age_band", "race_ethnicity"])
        cls.flagged = {(a.name, g.category) for a, g in cls.audit.findings(ADVERSE)}

    def test_finds_age_bias(self):
        self.assertIn(("age_band", "40 and over"), self.flagged)

    def test_finds_intersectional_bias(self):
        self.assertIn(("sex × race_ethnicity", "Female · Black or African American"), self.flagged)

    def test_intersection_classified(self):
        attrs = {a.name: a for a in self.audit.attributes}
        kinds = {g.category: self.audit.kind(attrs["sex × race_ethnicity"], g)
                 for g in attrs["sex × race_ethnicity"].groups if g.status == ADVERSE}
        self.assertEqual(kinds["Female · Black or African American"], "compounded")
        headline = {(a.name, g.category) for a, g in self.audit.headline()}
        self.assertNotIn(("sex × age_band", "Male · 40 and over"), headline)  # inherited from age

    def test_hidden_bias_without_flagged_parent(self):
        recs = load(SAMPLE, ["sex", "race_ethnicity"], outcome="advanced")
        recs = [r for r in recs if r.groups["race_ethnicity"] in ("White", "Black or African American")]
        result = audit(recs, ["sex", "race_ethnicity"], ratio=0.6)  # lenient: single axes pass
        kinds = {g.category: result.kind(a, g) for a, g in result.findings(ADVERSE)}
        self.assertEqual(kinds.get("Female · Black or African American"), "hidden")

    def test_sex_alone_not_flagged(self):
        self.assertFalse([c for n, c in self.flagged if n == "sex"])

    def test_all_renderers(self):
        for name, render in RENDERERS.items():
            self.assertTrue(render(self.audit), name)
        json.loads(RENDERERS["json"](self.audit))


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            return main([str(SAMPLE), *args]), err.getvalue()

    def test_strict_exit_code(self):
        self.assertEqual(self.run_cli("-y", "advanced", "-a", "age_band", "--strict")[0], 2)
        self.assertEqual(self.run_cli("-y", "advanced", "-a", "sex", "--strict")[0], 0)

    def test_missing_column_is_clean_error(self):
        code, err = self.run_cli("-y", "nope", "-a", "sex")
        self.assertEqual(code, 1)
        self.assertIn("column(s) not found", err)

    def test_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.html"
            self.run_cli("-s", "score", "-a", "sex", "-f", "html", "-o", str(out))
            self.assertIn("<svg", out.read_text())


if __name__ == "__main__":
    unittest.main()
