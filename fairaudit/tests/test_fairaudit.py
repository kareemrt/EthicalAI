import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from fairaudit import audit
from fairaudit.chart import to_svg
from fairaudit.cli import main
from fairaudit.metrics import to_outcomes
from fairaudit.report import to_markdown, to_text
from fairaudit.stats import two_proportion_p


def rows(spec):
    """spec: {(sex, race): (n, selected)} → list of row dicts."""
    out = []
    for (sex, race), (n, sel) in spec.items():
        out += [{"sex": sex, "race": race, "hired": "1" if i < sel else "0"} for i in range(n)]
    return out


class TestStats(unittest.TestCase):
    def test_identical_rates_not_significant(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)

    def test_large_gap_significant(self):
        self.assertLess(two_proportion_p(20, 200, 80, 200), 0.001)

    def test_degenerate_inputs(self):
        self.assertEqual(two_proportion_p(0, 0, 5, 10), 1.0)
        self.assertEqual(two_proportion_p(0, 10, 0, 10), 1.0)


class TestOutcomes(unittest.TestCase):
    def test_binary_labels(self):
        vals, mode, mid = to_outcomes(["Yes", "no", "HIRED", "0"])
        self.assertEqual((vals, mode, mid), ([True, False, True, False], "selection", None))

    def test_scores_use_median(self):
        vals, mode, mid = to_outcomes(["10", "20", "30", "40"])
        self.assertEqual((vals, mode, mid), ([False, False, True, True], "scoring", 25))

    def test_bad_values(self):
        with self.assertRaises(ValueError):
            to_outcomes(["maybe", "yes"], mode="selection")
        with self.assertRaises(ValueError):
            to_outcomes(["maybe", "12"])


class TestAudit(unittest.TestCase):
    def test_four_fifths_rule(self):
        # Classic EEOC example: 48/80 = 60% vs 12/40 = 30% → ratio 0.50
        data = rows({("Male", "X"): (80, 48), ("Female", "X"): (40, 12)})
        res = audit(data, "hired", ["sex"])
        sex = res.attributes[0]
        ref, other = sex.groups
        self.assertEqual((ref.group, ref.impact_ratio), ("Male", 1.0))
        self.assertTrue(ref.is_reference)
        self.assertAlmostEqual(other.impact_ratio, 0.5)
        self.assertFalse(res.passed)
        self.assertEqual([g.group for _, g in res.flagged()], ["Female"])

    def test_passes_when_fair(self):
        data = rows({("Male", "X"): (100, 50), ("Female", "X"): (100, 45)})
        self.assertTrue(audit(data, "hired", ["sex"]).passed)  # 0.90 ≥ 0.80

    def test_intersectional_and_unknown(self):
        data = rows({("Male", "A"): (50, 25), ("Female", "B"): (50, 10), ("", "A"): (10, 5)})
        res = audit(data, "hired", ["sex", "race"])
        self.assertEqual([a.attribute for a in res.attributes], ["sex", "race", "sex × race"])
        self.assertEqual(res.attributes[0].unknown, 10)
        self.assertEqual(res.attributes[2].unknown, 10)
        self.assertEqual({g.group for g in res.attributes[2].groups}, {"Male × A", "Female × B"})

    def test_min_share_excludes_small_groups(self):
        data = rows({("Male", "X"): (99, 50), ("Female", "X"): (1, 0)})
        g = audit(data, "hired", ["sex"], min_share=0.02).attributes[0].groups[-1]
        self.assertTrue(g.excluded)
        self.assertIsNone(g.p_value)

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            audit(rows({("M", "X"): (2, 1)}), "hired", ["age"])


class TestOutputs(unittest.TestCase):
    def setUp(self):
        self.res = audit(rows({("Male", "A"): (80, 48), ("Female", "B"): (40, 12)}), "hired", ["sex", "race"])

    def test_renderers(self):
        self.assertIn("FAIL", to_text(self.res, color=False))
        self.assertIn("| Female |", to_markdown(self.res))
        svg = to_svg(self.res)
        self.assertTrue(svg.startswith("<svg") and "threshold" in svg)

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            csv_path = Path(d, "data.csv")
            csv_path.write_text("sex,race,hired\n" + "\n".join(
                f"{r['sex']},{r['race']},{r['hired']}" for r in rows({("M", "A"): (10, 8), ("F", "A"): (10, 2)})))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main([str(csv_path), "-o", "hired", "-a", "sex", "--check",
                             "--json", f"{d}/r.json", "--md", f"{d}/r.md", "--svg", f"{d}/r.svg"])
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(Path(d, "r.json").read_text())["passed"])
            self.assertIn("![Impact ratios](r.svg)", Path(d, "r.md").read_text())

    def test_cli_bad_column_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "x.csv").write_text("a,b\n1,2\n")
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([f"{d}/x.csv", "-o", "hired", "-a", "sex"]), 2)


if __name__ == "__main__":
    unittest.main()
