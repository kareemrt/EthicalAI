import csv
import json
import tempfile
import unittest
from pathlib import Path

from impartial import audit_dimension, load_csv, run_audit
from impartial.cli import main
from impartial.report import to_html, to_json, to_markdown, to_svg
from impartial.stats import two_proportion_p, wilson_interval

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "hiring_sample.csv"


def make(groups):
    """groups: {name: (total, selected)} -> records for one attribute 'g'."""
    out = []
    for name, (n, k) in groups.items():
        out += [({"g": name}, i < k) for i in range(n)]
    return out


class Stats(unittest.TestCase):
    def test_wilson_bounds(self):
        lo, hi = wilson_interval(50, 100)
        self.assertAlmostEqual(lo, 0.4038, places=3)
        self.assertAlmostEqual(hi, 0.5962, places=3)
        self.assertEqual(wilson_interval(0, 0), (0.0, 0.0))

    def test_p_value(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_p(20, 100, 50, 100), 0.001)


class Metrics(unittest.TestCase):
    def test_four_fifths_fail(self):
        r = audit_dimension(make({"A": (500, 250), "B": (500, 100)}), ["g"])
        b = next(g for g in r.groups if g.group == "B")
        self.assertEqual(r.reference, "A")
        self.assertAlmostEqual(b.ratio, 0.4)
        self.assertEqual(b.status, "FAIL")
        self.assertEqual(r.verdict, "FAIL")

    def test_pass_at_threshold(self):
        r = audit_dimension(make({"A": (100, 50), "B": (100, 40)}), ["g"])
        self.assertEqual(r.verdict, "PASS")

    def test_small_gap_is_review_not_fail(self):
        r = audit_dimension(make({"A": (30, 15), "B": (30, 9)}), ["g"])
        self.assertEqual(r.verdict, "REVIEW")

    def test_tiny_group_excluded_and_not_reference(self):
        r = audit_dimension(make({"A": (990, 300), "B": (10, 10)}), ["g"])
        self.assertEqual(r.reference, "A")
        self.assertEqual(next(g for g in r.groups if g.group == "B").status, "EXCLUDED")

    def test_unknown_counted(self):
        recs = make({"A": (10, 5)}) + [({"g": None}, True)] * 3
        self.assertEqual(audit_dimension(recs, ["g"]).unknown, 3)

    def test_intersection_added(self):
        recs = [({"a": "x", "b": "y"}, True), ({"a": "x", "b": "z"}, False)]
        dims = [d.dimension for d in run_audit(recs, ["a", "b"])]
        self.assertEqual(dims, ["a", "b", "a × b"])


class EndToEnd(unittest.TestCase):
    def test_sample_detects_bias(self):
        records, meta = load_csv(str(SAMPLE), ["sex", "race_ethnicity"], outcome="hired")
        results = run_audit(records, ["sex", "race_ethnicity"])
        self.assertEqual(meta["rows"], 2400)
        self.assertTrue(all(r.verdict == "FAIL" for r in results))
        self.assertIn("<svg", to_svg(results[0]))
        self.assertIn("<!doctype html>", to_html(results, meta, 0.8))
        self.assertIn("| Group |", to_markdown(results, meta, 0.8))
        self.assertEqual(json.loads(to_json(results, meta))["overall"], "FAIL")

    def test_score_mode(self):
        records, meta = load_csv(str(SAMPLE), ["sex"], score="model_score")
        self.assertIn("threshold", meta)
        self.assertEqual(len(records), 2400)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fair = Path(tmp, "fair.csv")
            with fair.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["g", "ok"])
                w.writerows([["A", i % 2] for i in range(100)] + [["B", i % 2] for i in range(100)])
            self.assertEqual(main([str(fair), "-g", "g", "-o", "ok", "--out", str(Path(tmp, "r.md")), "-f", "md"]), 0)
            self.assertEqual(main([str(SAMPLE), "-g", "sex", "-o", "hired", "--out", str(Path(tmp, "r.json")), "-f", "json"]), 1)
            self.assertEqual(main([str(fair), "-g", "missing", "-o", "ok"]), 2)


if __name__ == "__main__":
    unittest.main()
