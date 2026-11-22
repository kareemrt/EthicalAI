"""Run with:  python -m unittest discover -s tests"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parity import run_audit  # noqa: E402
from parity.audit import ADVERSE, LOW_DATA, NOT_ASSESSED, OK, REVIEW, _judge  # noqa: E402
from parity.cli import main  # noqa: E402
from parity.io import to_binary  # noqa: E402
from parity.report import RENDERERS, to_svg  # noqa: E402
from parity.stats import fisher_exact, two_proportion_z, wilson_interval  # noqa: E402


def rows_for(spec: dict[str, tuple[int, int]], label=None) -> list[dict]:
    """Build rows from {group: (n, selected)}."""
    rows = []
    for group, (n, k) in spec.items():
        for i in range(n):
            row = {"g": group, "y": "yes" if i < k else "no"}
            if label:
                row["q"] = label(group, i)
            rows.append(row)
    return rows


class StatsTest(unittest.TestCase):
    def test_wilson_matches_reference_values(self):
        lo, hi = wilson_interval(50, 100)
        self.assertAlmostEqual(lo, 0.4038, places=3)
        self.assertAlmostEqual(hi, 0.5962, places=3)
        self.assertEqual(wilson_interval(0, 0), (0.0, 0.0))

    def test_z_test(self):
        self.assertAlmostEqual(two_proportion_z(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_z(30, 100, 60, 100), 0.001)

    def test_fisher_matches_scipy(self):
        # scipy.stats.fisher_exact([[8, 2], [1, 5]]) -> p = 0.03496
        self.assertAlmostEqual(fisher_exact(8, 10, 1, 6), 0.03497, places=4)
        self.assertAlmostEqual(fisher_exact(3, 6, 3, 6), 1.0)


class OutcomeParsingTest(unittest.TestCase):
    def test_yes_no(self):
        self.assertEqual(to_binary(["Yes", "no", "1", "0"])[:2], ([True, False, True, False], "selection"))

    def test_scores_use_median(self):
        selected, mode, cutoff = to_binary(["1.5", "9", "3", "7"])
        self.assertEqual((mode, cutoff), ("score", 5.0))
        self.assertEqual(selected, [False, True, False, True])

    def test_explicit_threshold(self):
        self.assertEqual(to_binary(["10", "80", "75"], threshold=75)[0], [False, True, False])

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            to_binary(["yes", "maybe"])


class AuditTest(unittest.TestCase):
    def test_four_fifths_rule(self):
        audit = run_audit(rows_for({"A": (500, 250), "B": (500, 150)}), "y", ["g"])
        a, b = audit.dimensions[0].groups
        self.assertEqual(audit.dimensions[0].reference, "A")
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertEqual((a.verdict, b.verdict, audit.verdict), (OK, ADVERSE, ADVERSE))

    def test_parity_is_ok(self):
        audit = run_audit(rows_for({"A": (400, 120), "B": (400, 118)}), "y", ["g"])
        self.assertEqual(audit.verdict, OK)

    def test_small_and_unknown_groups_are_not_judged(self):
        spec = {"A": (500, 250), "B": (480, 240), "C": (10, 0), "": (40, 0)}
        groups = {g.name: g for g in run_audit(rows_for(spec), "y", ["g"]).dimensions[0].groups}
        self.assertEqual(groups["C"].verdict, LOW_DATA)
        self.assertEqual(groups["Unknown"].verdict, NOT_ASSESSED)
        self.assertIsNone(groups["Unknown"].impact_ratio)

    def test_intersections(self):
        rows = [{"a": a, "b": b, "y": "1"} for a in "XY" for b in "PQ" for _ in range(50)]
        audit = run_audit(rows, "y", ["a", "b"])
        self.assertEqual([d.name for d in audit.dimensions], ["a", "b", "a × b"])
        self.assertEqual(len(audit.dimensions[2].groups), 4)
        self.assertEqual(len(run_audit(rows, "y", ["a", "b"], intersect=False).dimensions), 2)

    def test_equal_opportunity_escalates_to_review(self):
        # Equal selection rates, but B's selections go to unqualified people.
        label = lambda g, i: "1" if (i < 100) == (g == "A") or i >= 300 else "0"  # noqa: E731
        audit = run_audit(rows_for({"A": (400, 100), "B": (400, 100)}, label), "y", ["g"], label="q")
        a, b = audit.dimensions[0].groups
        self.assertGreater(a.tpr, b.tpr)
        self.assertEqual(b.verdict, REVIEW)

    def test_judge_matrix(self):
        self.assertEqual(_judge(0.70, 0.01), ADVERSE)
        self.assertEqual(_judge(0.70, 0.40), REVIEW)
        self.assertEqual(_judge(0.85, 0.01), REVIEW)
        self.assertEqual(_judge(0.95, 0.01), OK)

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "missing column"):
            run_audit([{"y": "1"}], "y", ["sex"])


class RenderAndCliTest(unittest.TestCase):
    def setUp(self):
        self.audit = run_audit(rows_for({"A": (500, 250), "B": (500, 150)}), "y", ["g"])

    def test_all_renderers(self):
        for name, render in RENDERERS.items():
            self.assertIn("B", render(self.audit), name)
        self.assertEqual(json.loads(RENDERERS["json"](self.audit))["verdict"], ADVERSE)
        self.assertTrue(to_svg(self.audit.dimensions[0]).startswith("<svg"))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "d.csv")
            path.write_text("g,y\n" + "".join(f"{r['g']},{r['y']}\n" for r in rows_for({"A": (500, 250), "B": (500, 150)})))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main([str(path), "-y", "y", "-g", "g"]), 0)
                self.assertEqual(main([str(path), "-y", "y", "-g", "g", "--fail-on", "adverse"]), 1)
                self.assertEqual(main([str(path), "-y", "nope", "-g", "g"]), 2)
            self.assertIn("Adverse impact", out.getvalue())


if __name__ == "__main__":
    unittest.main()
