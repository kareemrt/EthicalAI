"""Run with:  python -m unittest discover tests"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from faircheck import metrics, run_audit
from faircheck.cli import main
from faircheck.report import to_json, to_markdown

SAMPLE = Path(__file__).parent.parent / "examples" / "screening_sample.csv"


def rows(spec):
    """spec: {(sex, race): (selected, total)} -> list of row dicts."""
    out = []
    for (sex, race), (k, n) in spec.items():
        out += [{"sex": sex, "race": race, "hired": "yes" if i < k else "no"} for i in range(n)]
    return out


class Metrics(unittest.TestCase):
    def test_impact_ratios(self):
        self.assertEqual(metrics.impact_ratios({"a": 0.5, "b": 0.25}), {"a": 1.0, "b": 0.5})

    def test_p_value_identical_groups(self):
        self.assertAlmostEqual(metrics.two_proportion_p(30, 100, 30, 100), 1.0)

    def test_p_value_large_gap_is_significant(self):
        self.assertLess(metrics.two_proportion_p(10, 200, 60, 200), 0.001)

    def test_p_value_degenerate(self):
        self.assertEqual(metrics.two_proportion_p(0, 0, 5, 10), 1.0)
        self.assertEqual(metrics.two_proportion_p(0, 10, 0, 10), 1.0)

    def test_median(self):
        self.assertEqual(metrics.median([3, 1, 2]), 2)
        self.assertEqual(metrics.median([4, 1, 2, 3]), 2.5)


class Audit(unittest.TestCase):
    def test_four_fifths_rule(self):
        # Women selected at 30%, men at 50% -> ratio 0.6.
        a = run_audit(rows({("F", "x"): (30, 100), ("M", "x"): (50, 100)}), "hired", ["sex"])
        g = {s.group: s for s in a.dimensions[0].groups}
        self.assertAlmostEqual(g["F"].impact_ratio, 0.6)
        self.assertEqual(a.dimensions[0].reference, "M")
        self.assertEqual(len(a.adverse()), 1)

    def test_intersectional_blind_spot(self):
        # Each single axis looks fine; only Black women are disadvantaged.
        spec = {("F", "W"): (50, 100), ("F", "B"): (20, 100),
                ("M", "W"): (35, 100), ("M", "B"): (50, 100)}
        a = run_audit(rows(spec), "hired", ["sex", "race"])
        by_dim = {d.name: d for d in a.dimensions}
        self.assertFalse([g for g in by_dim["sex"].groups if g.impact_ratio < 0.8])
        self.assertFalse([g for g in by_dim["race"].groups if g.impact_ratio < 0.8])
        flagged = [g.group for d, g in a.adverse()]
        self.assertEqual(flagged, ["F / B", "M / W"])

    def test_small_groups_excluded_from_reference(self):
        spec = {("F", "x"): (40, 100), ("M", "x"): (40, 100), ("X", "x"): (2, 2)}
        a = run_audit(rows(spec), "hired", ["sex"], min_share=0.05)
        g = {s.group: s for s in a.dimensions[0].groups}
        self.assertTrue(g["X"].excluded)
        self.assertNotEqual(a.dimensions[0].reference, "X")
        self.assertTrue(any("not judged" in w for w in a.warnings))

    def test_score_mode_uses_median(self):
        data = [{"g": "a", "s": str(v)} for v in (1, 2, 3, 4)] + \
               [{"g": "b", "s": str(v)} for v in (5, 6, 7, 8)]
        a = run_audit(data, "s", ["g"])
        self.assertEqual(a.mode, "score")
        self.assertEqual(a.cutoff, 4.5)
        rates = {g.group: g.rate for g in a.dimensions[0].groups}
        self.assertEqual(rates, {"a": 0.0, "b": 1.0})

    def test_missing_demographics_skipped(self):
        data = rows({("F", "x"): (5, 10)}) + [{"sex": "", "race": "x", "hired": "yes"}]
        a = run_audit(data, "hired", ["sex"])
        self.assertEqual(a.total, 10)
        self.assertTrue(a.warnings)

    def test_bad_column(self):
        with self.assertRaises(ValueError):
            run_audit(rows({("F", "x"): (1, 2)}), "nope", ["sex"])

    def test_ground_truth_rates(self):
        data = [{"g": "a", "y": "1", "t": "1"}, {"g": "a", "y": "0", "t": "1"},
                {"g": "a", "y": "1", "t": "0"}, {"g": "a", "y": "0", "t": "0"}]
        g = run_audit(data, "y", ["g"], label="t").dimensions[0].groups[0]
        self.assertEqual((g.tpr, g.fpr), (0.5, 0.5))


class EndToEnd(unittest.TestCase):
    def test_reports_render(self):
        a = run_audit(rows({("F", "x"): (30, 100), ("M", "x"): (50, 100)}), "hired", ["sex"])
        self.assertIn("ADVERSE IMPACT", to_markdown(a))
        self.assertEqual(json.loads(to_json(a))["dimensions"][0]["groups"][0]["status"], "adverse*")

    @unittest.skipUnless(SAMPLE.exists(), "run examples/make_sample.py first")
    def test_cli_on_sample(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            code = main([str(SAMPLE), "--outcome", "advanced", "--attr", "sex",
                         "--attr", "race", "--label", "qualified", "--out", d])
            self.assertEqual(code, 1)  # the sample contains intersectional bias
            for f in ("report.md", "report.json", "impact_ratios.svg"):
                self.assertTrue((Path(d) / f).stat().st_size > 0)

    def test_cli_bad_file(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["/no/such.csv", "--outcome", "x", "--attr", "y"]), 2)


if __name__ == "__main__":
    unittest.main()
