import json
import tempfile
import unittest
from pathlib import Path

from fairhire.cli import main
from fairhire.data import load
from fairhire.metrics import audit, median, two_proportion_p_value

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "applicants.csv"


def records(**groups):
    """records(A=(10, 6)) -> 10 rows of group A, 6 of them selected."""
    return [(g, i < x) for g, (n, x) in groups.items() for i in range(n)]


class Metrics(unittest.TestCase):
    def test_impact_ratio_against_most_favoured(self):
        res = {r.group: r for r in audit(records(A=(100, 60), B=(100, 30)))}
        self.assertEqual(res["A"].impact_ratio, 1.0)
        self.assertAlmostEqual(res["B"].impact_ratio, 0.5)
        self.assertEqual(res["B"].status, "adverse impact")
        self.assertFalse(res["A"].flagged)

    def test_four_fifths_boundary_is_not_flagged(self):
        res = {r.group: r for r in audit(records(A=(100, 50), B=(100, 40)))}
        self.assertAlmostEqual(res["B"].impact_ratio, 0.8)
        self.assertFalse(res["B"].flagged)

    def test_small_groups_are_not_judged_and_not_reference(self):
        res = {r.group: r for r in audit(records(A=(500, 250), B=(500, 200), Tiny=(5, 5)))}
        self.assertIsNone(res["Tiny"].impact_ratio)
        self.assertEqual(res["Tiny"].status, "too few")
        self.assertEqual(res["A"].impact_ratio, 1.0)

    def test_low_ratio_small_sample_is_marked_not_significant(self):
        res = {r.group: r for r in audit(records(A=(20, 10), B=(20, 7)))}
        self.assertEqual(res["B"].status, "adverse (n.s.)")

    def test_nobody_selected(self):
        self.assertTrue(all(r.impact_ratio is None for r in audit(records(A=(10, 0), B=(10, 0)))))
        self.assertEqual(audit([]), [])

    def test_p_value(self):
        self.assertAlmostEqual(two_proportion_p_value(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_p_value(30, 100, 60, 100), 0.001)
        self.assertEqual(two_proportion_p_value(0, 0, 5, 10), 1.0)

    def test_median(self):
        self.assertEqual(median([3, 1, 2]), 2)
        self.assertEqual(median([4, 1, 2, 3]), 2.5)


class Data(unittest.TestCase):
    def test_views_unknowns_and_intersection(self):
        ds = load(SAMPLE, ["sex", "race_ethnicity"], selected="advanced")
        self.assertEqual([v.name for v in ds.views], ["sex", "race_ethnicity", "sex × race_ethnicity"])
        for v in ds.views:
            self.assertEqual(len(v.records) + v.unknown, ds.rows)

    def test_scoring_mode_uses_median(self):
        ds = load(SAMPLE, ["sex"], score="screen_score")
        self.assertEqual(ds.mode, "scoring")
        self.assertIsNotNone(ds.threshold)

    def test_bad_column(self):
        with self.assertRaises(ValueError):
            load(SAMPLE, ["nope"], selected="advanced")


class Cli(unittest.TestCase):
    def test_finds_planted_intersectional_bias(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.json"
            code = main([str(SAMPLE), "-g", "sex", "-g", "race_ethnicity", "-s", "advanced", "-o", str(out), "--strict"])
            report = json.loads(out.read_text())
        self.assertEqual(code, 1)
        flagged = {g["group"] for v in report["views"] for g in v["groups"] if g["status"].startswith("adverse")}
        self.assertIn("Female · Black", flagged)

    def test_all_formats_render(self):
        with tempfile.TemporaryDirectory() as d:
            for ext in ("md", "html", "json"):
                out = Path(d) / f"r.{ext}"
                self.assertEqual(main([str(SAMPLE), "-g", "age_band", "--score", "screen_score", "-o", str(out)]), 0)
                self.assertGreater(out.stat().st_size, 500)

    def test_missing_file_exits_2(self):
        self.assertEqual(main(["missing.csv", "-g", "sex", "-s", "advanced"]), 2)


if __name__ == "__main__":
    unittest.main()
