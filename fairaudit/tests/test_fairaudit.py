import io
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from fairaudit import audit, two_proportion_p
from fairaudit.__main__ import main
from fairaudit.metrics import binarize

ROOT = Path(__file__).resolve().parents[1]


class Metrics(unittest.TestCase):
    def test_impact_ratio_and_flags(self):
        # A: 50/100 selected, B: 30/100 selected -> ratio 0.6
        groups = ["A"] * 100 + ["B"] * 100
        selected = [True] * 50 + [False] * 50 + [True] * 30 + [False] * 70
        a, b = audit(groups, selected)
        self.assertEqual((a.group, a.impact_ratio), ("A", 1.0))
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertIn("adverse-impact", b.flags)
        self.assertIn("significant", b.flags)

    def test_four_fifths_boundary_is_not_flagged(self):
        groups = ["A"] * 10 + ["B"] * 10
        selected = [True] * 5 + [False] * 5 + [True] * 4 + [False] * 6   # 0.4/0.5 = 0.8 exactly
        self.assertEqual(audit(groups, selected)[1].flags, ())

    def test_small_groups_never_become_reference(self):
        groups = ["Big"] * 99 + ["Tiny"]
        selected = [True] * 40 + [False] * 59 + [True]
        stats = {s.group: s for s in audit(groups, selected)}
        self.assertEqual(stats["Big"].impact_ratio, 1.0)
        self.assertEqual(stats["Tiny"].flags, ("small-sample",))

    def test_equal_opportunity_gap(self):
        groups = ["A"] * 4 + ["B"] * 4
        selected = [True, True, False, False, True, False, False, True]
        qualified = [True, True, False, False, True, True, True, False]
        stats = {s.group: s for s in audit(groups, selected, qualified)}
        self.assertEqual(stats["A"].tpr, 1.0)
        self.assertAlmostEqual(stats["B"].tpr, 1 / 3)
        self.assertIn("opportunity-gap", stats["B"].flags)

    def test_p_value(self):
        self.assertEqual(two_proportion_p(5, 10, 5, 10), 1.0)
        self.assertLess(two_proportion_p(80, 100, 20, 100), 1e-10)
        self.assertEqual(two_proportion_p(0, 0, 1, 2), 1.0)

    def test_binarize_uses_median(self):
        flags, cut = binarize([1, 2, 3, 4, 5])
        self.assertEqual((cut, flags), (3, [False, False, False, True, True]))

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            audit(["A"], [True, False])


class CLI(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_end_to_end_on_sample(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = self.run_cli(str(ROOT / "examples/screening.csv"), "--outcome", "advanced",
                                        "--groups", "sex", "age_band", "--intersect", "sex", "age_band",
                                        "--label", "qualified", "--out", d, "--fail-under", "0.8")
            self.assertEqual(code, 1)                       # the planted age bias is caught
            self.assertIn("50+", out)
            files = sorted(p.name for p in Path(d).iterdir())
            self.assertEqual(files, ["chart-age-band.svg", "chart-sex-age-band.svg", "chart-sex.svg",
                                     "report.json", "report.md"])
            self.assertIn("four-fifths", (Path(d) / "report.md").read_text())

    def test_missing_column_is_a_clean_error(self):
        code, _, err = self.run_cli(str(ROOT / "examples/screening.csv"), "--outcome", "nope", "--groups", "sex")
        self.assertEqual(code, 2)
        self.assertIn("missing column", err)


if __name__ == "__main__":
    unittest.main()
