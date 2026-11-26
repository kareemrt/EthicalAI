import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from fairscope.cli import main
from fairscope.data import outcomes, to_bool
from fairscope.metrics import FAIL, PASS, REVIEW, audit, two_proportion_p

HERE = os.path.dirname(__file__)
SAMPLE = os.path.join(HERE, "..", "examples", "screening.csv")


def make(spec):
    """spec: {group: (n, selected)} → parallel group/selected lists."""
    g, s = [], []
    for name, (n, k) in spec.items():
        g += [name] * n
        s += [True] * k + [False] * (n - k)
    return g, s


class Metrics(unittest.TestCase):
    def test_impact_ratio_is_relative_to_best_group(self):
        a = audit("x", *make({"A": (100, 50), "B": (100, 25)}))
        by = {g.name: g for g in a.groups}
        self.assertAlmostEqual(by["A"].impact_ratio, 1.0)
        self.assertAlmostEqual(by["B"].impact_ratio, 0.5)

    def test_significant_disparity_fails(self):
        a = audit("x", *make({"A": (500, 250), "B": (500, 100)}))
        self.assertEqual(a.verdict, FAIL)

    def test_low_ratio_on_tiny_sample_is_review_not_fail(self):
        a = audit("x", *make({"A": (1000, 500), "B": (25, 9)}))
        self.assertEqual(a.verdict, REVIEW)

    def test_parity_passes(self):
        a = audit("x", *make({"A": (300, 90), "B": (300, 87)}))
        self.assertEqual(a.verdict, PASS)

    def test_small_groups_are_excluded_from_benchmark(self):
        # C is 1% of data and has a 100% rate; it must not become the benchmark.
        a = audit("x", *make({"A": (500, 200), "B": (490, 190), "C": (10, 10)}))
        self.assertEqual(a.verdict, PASS)
        self.assertTrue(next(g for g in a.groups if g.name == "C").excluded)

    def test_equal_opportunity_gap_triggers_review(self):
        groups, sel = make({"A": (100, 50), "B": (100, 50)})
        labels = [True] * 50 + [False] * 50 + [False] * 50 + [True] * 50  # B selects only unqualified
        a = audit("x", groups, sel, labels)
        self.assertEqual(a.verdict, REVIEW)
        self.assertAlmostEqual(a.tpr_gap, 1.0)

    def test_above_average_group_is_compared_to_benchmark_not_rest(self):
        # B sits above the average but well below A; it is the A-vs-B gap that matters.
        a = audit("x", *make({"A": (400, 240), "B": (400, 176), "C": (400, 40)}))
        by = {g.name: g for g in a.groups}
        self.assertEqual(by["A"].p_value, 1.0)
        self.assertLess(by["B"].p_value, 0.05)
        self.assertIn("adverse impact", by["B"].flags)

    def test_p_value_bounds(self):
        self.assertEqual(two_proportion_p(0, 0, 5, 10), 1.0)
        self.assertGreater(two_proportion_p(50, 100, 50, 100), 0.99)
        self.assertLess(two_proportion_p(80, 100, 20, 100), 1e-6)


class Data(unittest.TestCase):
    def test_bool_parsing(self):
        self.assertTrue(to_bool(" Yes ", "c"))
        self.assertFalse(to_bool("0", "c"))
        with self.assertRaises(ValueError):
            to_bool("maybe", "c")

    def test_score_uses_median_by_default(self):
        rows = [{"s": str(v)} for v in (1, 2, 3, 4, 5)]
        self.assertEqual(outcomes(rows, score="s"), [False, False, False, True, True])
        self.assertEqual(outcomes(rows, score="s", cutoff=1.5), [False, True, True, True, True])


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_sample_detects_planted_bias(self):
        code, out, _ = self.run_cli("audit", SAMPLE, "--by", "race", "--outcome", "advanced", "--format", "json")
        self.assertEqual(code, 1)
        report = json.loads(out)
        flagged = {g["name"] for g in report["audits"][0]["groups"] if "adverse impact" in g["flags"]}
        self.assertEqual(flagged, {"Black", "Hispanic"})

    def test_fail_on_never_exits_zero(self):
        code, *_ = self.run_cli("audit", SAMPLE, "--by", "race", "--outcome", "advanced", "--fail-on", "never")
        self.assertEqual(code, 0)

    def test_all_formats_render_to_file(self):
        with tempfile.TemporaryDirectory() as d:
            for ext in ("md", "html", "json"):
                path = os.path.join(d, f"r.{ext}")
                self.run_cli("audit", SAMPLE, "--by", "gender", "--by", "race", "--intersect",
                             "--score", "score", "--label", "qualified", "-o", path)
                self.assertGreater(os.path.getsize(path), 500)

    def test_missing_column_is_a_clean_error(self):
        code, _, err = self.run_cli("audit", SAMPLE, "--by", "zipcode", "--outcome", "advanced")
        self.assertEqual(code, 2)
        self.assertIn("missing column", err)


if __name__ == "__main__":
    unittest.main()
