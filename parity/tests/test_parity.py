"""Run:  python -m unittest discover tests"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from parity import audit, fisher_exact
from parity.__main__ import main
from parity.report import render_html, render_markdown, svg_chart


def rows_from(spec):
    """spec: {group: (n, selected)} -> list of row dicts."""
    rows = []
    for group, (n, sel) in spec.items():
        rows += [{"g": group, "y": "1" if i < sel else "0", "s": str(i)} for i in range(n)]
    return rows


class FisherTest(unittest.TestCase):
    def test_known_values(self):
        # Reference values from scipy.stats.fisher_exact
        self.assertAlmostEqual(fisher_exact(8, 2, 1, 5), 0.0349650, places=6)
        self.assertAlmostEqual(fisher_exact(1, 9, 11, 3), 0.0027594, places=6)
        self.assertAlmostEqual(fisher_exact(3, 1, 1, 3), 0.4857143, places=6)

    def test_degenerate(self):
        self.assertEqual(fisher_exact(0, 0, 3, 4), 1.0)
        self.assertEqual(fisher_exact(5, 0, 5, 0), 1.0)


class AuditTest(unittest.TestCase):
    def test_impact_ratio_and_flag(self):
        a = audit(rows_from({"A": (500, 250), "B": (500, 150)}), "g", outcome="y")
        by = {g.group: g for g in a.groups}
        self.assertEqual(a.reference, "A")
        self.assertAlmostEqual(by["B"].ratio, 0.6)
        self.assertEqual(by["B"].status, "flag")
        self.assertEqual(by["A"].status, "reference")

    def test_below_threshold_but_not_significant_is_review(self):
        a = audit(rows_from({"A": (20, 10), "B": (20, 7)}), "g", outcome="y")
        self.assertEqual(a.groups[1].status, "review")

    def test_four_fifths_boundary_passes(self):
        a = audit(rows_from({"A": (1000, 500), "B": (1000, 400)}), "g", outcome="y")
        self.assertEqual(a.groups[1].status, "ok")

    def test_small_group_never_reference_or_flagged(self):
        a = audit(rows_from({"A": (1000, 300), "B": (1000, 100), "tiny": (5, 5)}), "g", outcome="y")
        by = {g.group: g for g in a.groups}
        self.assertEqual(a.reference, "A")
        self.assertTrue(by["tiny"].small)
        self.assertEqual(by["B"].status, "flag")

    def test_unknown_counted_not_rated(self):
        rows = rows_from({"A": (10, 5)}) + [{"g": "Prefer not to say", "y": "1", "s": "0"}] * 3
        a = audit(rows, "g", outcome="y")
        self.assertEqual(a.unknown, 3)
        self.assertEqual([g.group for g in a.groups], ["A"])

    def test_intersection(self):
        rows = [{"a": "x", "b": "p", "y": "1"}, {"a": "x", "b": "q", "y": "0"}]
        a = audit(rows, ["a", "b"], outcome="y")
        self.assertEqual({g.group for g in a.groups}, {"x × p", "x × q"})

    def test_scoring_mode_uses_median(self):
        rows = [{"g": "A", "s": s} for s in "6789"] + [{"g": "B", "s": s} for s in "1234"]
        a = audit(rows, "g", score="s")
        self.assertEqual(a.median_score, 5.0)
        self.assertEqual([(g.group, g.rate) for g in a.groups], [("A", 1.0), ("B", 0.0)])

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            audit([{"g": "A"}], "g", outcome="missing")
        with self.assertRaises(ValueError):
            audit([{"g": "A", "y": "1"}], "g")


class OutputTest(unittest.TestCase):
    def setUp(self):
        self.a = audit(rows_from({"A <b>": (300, 150), "B": (300, 60)}), "g", outcome="y")

    def test_html_escapes_and_is_self_contained(self):
        html = render_html([self.a], "x.csv")
        self.assertIn("A &lt;b&gt;", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))

    def test_markdown_and_svg(self):
        self.assertIn("**Result: FAIL**", render_markdown([self.a]))
        self.assertTrue(svg_chart(self.a, standalone=True).startswith("<svg"))


class CliTest(unittest.TestCase):
    def run_cli(self, rows, *args):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "d.csv")
            with open(path, "w") as f:
                f.write("g,y\n" + "".join(f"{r['g']},{r['y']}\n" for r in rows))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([path, "--outcome", "y", "--groups", "g", *args])
            return code, out.getvalue(), err.getvalue()

    def test_exit_codes(self):
        fair = rows_from({"A": (100, 50), "B": (100, 48)})
        biased = rows_from({"A": (400, 200), "B": (400, 80)})
        self.assertEqual(self.run_cli(fair)[0], 0)
        self.assertEqual(self.run_cli(biased)[0], 1)
        self.assertEqual(self.run_cli(fair, "--groups", "nope")[0], 2)

    def test_json(self):
        code, out, _ = self.run_cli(rows_from({"A": (400, 200), "B": (400, 80)}), "--format", "json")
        self.assertEqual(json.loads(out)["result"], "fail")


if __name__ == "__main__":
    unittest.main()
