import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from fairlens import audit, data, report
from fairlens.cli import main
from fairlens.metrics import EXCLUDED, FAIL, OK, WARN, two_proportion_p

HERE = os.path.dirname(__file__)
SAMPLE = os.path.join(HERE, "..", "examples", "hiring.csv")


def recs(group, n, selected, label=None):
    return [(group, i < selected, label) for i in range(n)]


class Metrics(unittest.TestCase):
    def test_four_fifths_fail(self):
        a = audit(recs("A", 100, 50) + recs("B", 100, 30))
        b = {g.name: g for g in a.groups}["B"]
        self.assertEqual(a.reference, "A")
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertEqual(b.status, FAIL)
        self.assertEqual(a.status, FAIL)

    def test_small_sample_is_warn_not_fail(self):
        a = audit(recs("A", 10, 5) + recs("B", 10, 3))
        self.assertEqual({g.name: g.status for g in a.groups}["B"], WARN)

    def test_parity_passes(self):
        a = audit(recs("A", 200, 80) + recs("B", 200, 76))
        self.assertEqual(a.status, OK)

    def test_min_share_excludes_tiny_group(self):
        a = audit(recs("A", 100, 50) + recs("B", 100, 48) + recs("C", 2, 0), min_share=0.02)
        self.assertEqual({g.name: g.status for g in a.groups}["C"], EXCLUDED)
        self.assertEqual(a.status, OK)

    def test_error_rates(self):
        # A: 10 qualified, 8 selected; B: 10 qualified, 4 selected
        a = audit(recs("A", 10, 8, True) + recs("B", 10, 4, True))
        self.assertTrue(a.has_labels)
        self.assertAlmostEqual(a.gap("tpr"), 0.4)

    def test_p_value(self):
        self.assertEqual(two_proportion_p(5, 10, 5, 10), 1.0)
        self.assertLess(two_proportion_p(50, 100, 20, 100), 0.001)

    def test_empty(self):
        with self.assertRaises(ValueError):
            audit([])


class Data(unittest.TestCase):
    def test_to_bool(self):
        self.assertTrue(data.to_bool(" Hired "))
        self.assertFalse(data.to_bool("no"))
        self.assertTrue(data.to_bool("Advance", positive="advance"))

    def test_median_scoring_rate(self):
        rows = [{"s": str(v)} for v in (1, 2, 3, 4)]
        self.assertEqual(data.decisions_from_scores(rows, "s"), [False, False, True, True])

    def test_intersection_and_missing(self):
        self.assertEqual(data.group_key({"g": "F", "r": ""}, ["g", "r"]), "F × (unknown)")


class CLI(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([SAMPLE, *args])
        return code, buf.getvalue()

    def test_sample_detects_planted_bias(self):
        code, out = self.run_cli("-g", "gender", "race", "-d", "advanced", "--min-share", "0.02")
        self.assertEqual(code, 1)
        self.assertIn("Black", out)

    def test_reports_written(self):
        with tempfile.TemporaryDirectory() as d:
            md, sv = os.path.join(d, "r.md"), os.path.join(d, "c.svg")
            self.run_cli("-g", "gender", "-s", "model_score", "-l", "qualified", "--md", md, "--svg", sv)
            with open(md) as f:
                self.assertIn("![Impact ratios](c.svg)", f.read())
            with open(sv) as f:
                self.assertTrue(f.read().startswith("<svg"))

    def test_missing_column_exit_2(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main([SAMPLE, "-g", "nope", "-d", "advanced"]), 2)

    def test_json(self):
        _, out = self.run_cli("-g", "age_band", "-d", "advanced", "--json")
        self.assertEqual(json.loads(out)[0]["reference"], "<40")


if __name__ == "__main__":
    unittest.main()
