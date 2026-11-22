"""Run with:  python -m unittest discover -s tests"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fairlens.cli import main  # noqa: E402
from fairlens.data import is_positive, tally  # noqa: E402
from fairlens.metrics import GroupStats, analyse, two_proportion_p, wilson_interval  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "hiring.csv"


def group(name, n, k):
    g = GroupStats(name)
    g.n, g.selected = n, k
    return g


class Metrics(unittest.TestCase):
    def test_wilson_known_value(self):
        lo, hi = wilson_interval(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)

    def test_wilson_edges(self):
        self.assertEqual(wilson_interval(0, 0), (0.0, 0.0))
        lo, hi = wilson_interval(0, 20)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_two_proportion(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_p(60, 100, 30, 100), 0.001)
        self.assertEqual(two_proportion_p(0, 0, 1, 2), 1.0)

    def test_four_fifths_rule(self):
        # Classic EEOC example: 48/80 men (60%) vs 12/40 women (30%) → ratio 0.5.
        audit = analyse("sex", [group("Women", 40, 12), group("Men", 80, 48)])
        self.assertEqual(audit.reference, "Men")
        women = audit.groups[1]
        self.assertAlmostEqual(women.impact_ratio, 0.5)
        self.assertIn("adverse-impact", women.flags)
        self.assertIn("significant", women.flags)

    def test_boundary_is_not_flagged(self):
        audit = analyse("x", [group("A", 100, 50), group("B", 100, 40)])
        self.assertAlmostEqual(audit.groups[1].impact_ratio, 0.8)
        self.assertEqual(audit.flagged, [])

    def test_small_and_rare_groups(self):
        audit = analyse("x", [group("Big", 1000, 300), group("Tiny", 10, 3)])
        self.assertIn("small-sample", audit.groups[1].flags)
        self.assertIn("under-2%", audit.groups[1].flags)

    def test_nobody_selected(self):
        audit = analyse("x", [group("A", 10, 0), group("B", 10, 0)])
        self.assertIsNone(audit.groups[0].impact_ratio)
        self.assertEqual(audit.flagged, [])


class Data(unittest.TestCase):
    ROWS = [
        {"sex": "F", "race": "B", "y": "yes", "q": "1"},
        {"sex": "F", "race": "W", "y": "no", "q": "1"},
        {"sex": "M", "race": "W", "y": "1", "q": "0"},
        {"sex": "M", "race": "", "y": "0", "q": "0"},
    ]

    def test_truthy(self):
        self.assertTrue(is_positive(" Hired "))
        self.assertFalse(is_positive("rejected"))
        self.assertTrue(is_positive("Offer", positive="offer"))

    def test_tally_with_labels_and_missing(self):
        stats, seen = tally(self.ROWS, ["sex", "race", "sex*race"], "y", label="q")
        self.assertEqual(seen, 4)
        f = {g.name: g for g in stats["sex"]}["F"]
        self.assertEqual((f.n, f.selected, f.tp, f.fn), (2, 1, 1, 1))
        self.assertEqual(sum(g.n for g in stats["race"]), 3)  # blank race skipped
        self.assertIn("F × B", {g.name for g in stats["sex*race"]})

    def test_missing_column(self):
        with self.assertRaises(KeyError):
            tally(self.ROWS, ["gender"], "y")


class CLI(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([str(EXAMPLE), *args])
        return code, out.getvalue(), err.getvalue()

    def test_json_detects_injected_bias(self):
        code, out, _ = self.run_cli("-o", "advanced", "-g", "sex,age_band", "-l", "qualified", "-f", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        sex = data["attributes"][0]
        self.assertEqual(sex["reference"], "Male")
        self.assertLess(sex["min_impact_ratio"], 0.8)
        self.assertGreater(sex["tpr_gap"], 0.1)

    def test_strict_gate_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, _ = self.run_cli("-o", "advanced", "-g", "sex", "--strict", "--report", d)
            self.assertEqual(code, 1)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["audit.json", "impact.svg", "report.md"])
            self.assertTrue((Path(d) / "impact.svg").read_text().startswith("<svg"))

    def test_bad_column_exits_2(self):
        code, _, err = self.run_cli("-o", "advanced", "-g", "gender")
        self.assertEqual(code, 2)
        self.assertIn("gender", err)


if __name__ == "__main__":
    unittest.main()
