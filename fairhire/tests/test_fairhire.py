import json
import math
import os
import tempfile
import unittest

from fairhire import Status, audit
from fairhire.cli import main
from fairhire.data import category, outcomes, parse_outcome
from fairhire.metrics import holm, two_proportion_p


def rows(spec):
    """spec: {(sex, race): (n, selected)} -> list of row dicts."""
    out = []
    for (sex, race), (n, sel) in spec.items():
        out += [{"sex": sex, "race": race, "hired": "yes" if i < sel else "no", "score": str(i)} for i in range(n)]
    return out


class DataTests(unittest.TestCase):
    def test_parse_outcome(self):
        self.assertTrue(parse_outcome(" Hired "))
        self.assertFalse(parse_outcome("0"))
        with self.assertRaises(ValueError):
            parse_outcome("maybe")

    def test_score_uses_strictly_above_median(self):
        r = [{"s": str(v)} for v in (1, 2, 3, 4, 5)]
        self.assertEqual(outcomes(r, score="s"), [False, False, False, True, True])

    def test_category_and_unknown(self):
        self.assertEqual(category({"a": "F", "b": "X"}, ["a", "b"]), "F × X")
        self.assertEqual(category({"a": "F", "b": ""}, ["a", "b"]), "Unknown")

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            audit(rows({("M", "W"): (10, 5)}), ["gender"], outcome="hired")


class MetricTests(unittest.TestCase):
    def test_z_test_matches_known_value(self):
        # 50/100 vs 30/100 -> z ≈ 2.887, p ≈ 0.00389
        self.assertAlmostEqual(two_proportion_p(50, 100, 30, 100), 0.00389, places=4)
        self.assertEqual(two_proportion_p(0, 0, 3, 10), 1.0)

    def test_holm(self):
        adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(adj["a"], 0.03)
        self.assertAlmostEqual(adj["c"], 0.06)
        self.assertAlmostEqual(adj["b"], 0.06)  # monotone: never below the previous step

    def test_impact_ratio_and_statuses(self):
        a = audit(rows({("M", "W"): (500, 250), ("F", "W"): (500, 150)}), ["sex"], outcome="hired")
        g = {x.name: x for x in a.groups}
        self.assertEqual(a.reference, "M")
        self.assertAlmostEqual(g["F"].impact_ratio, 0.6)
        self.assertIs(g["F"].status, Status.ADVERSE)
        self.assertIs(g["M"].status, Status.OK)

    def test_small_sample_is_review_not_adverse(self):
        a = audit(rows({("M", "W"): (10, 5), ("F", "W"): (10, 3)}), ["sex"], outcome="hired")
        self.assertIs({x.name: x for x in a.groups}["F"].status, Status.REVIEW)

    def test_large_sample_small_gap_is_watch(self):
        a = audit(rows({("M", "W"): (20000, 10000), ("F", "W"): (20000, 9400)}), ["sex"], outcome="hired")
        self.assertIs({x.name: x for x in a.groups}["F"].status, Status.WATCH)

    def test_min_share_excludes_and_unknown_counted(self):
        a = audit(rows({("M", "W"): (98, 49), ("X", "W"): (1, 0), ("", "W"): (5, 1)}), ["sex"], outcome="hired")
        g = {x.name: x for x in a.groups}
        self.assertIs(g["X"].status, Status.EXCLUDED)
        self.assertIsNone(g["X"].impact_ratio)
        self.assertEqual(a.unknown, 5)

    def test_intersection(self):
        a = audit(rows({("M", "W"): (100, 50), ("F", "B"): (100, 20)}), ["sex", "race"], outcome="hired")
        self.assertEqual(a.dimension, "sex × race")
        self.assertIn("F × B", [g.name for g in a.groups])


class CliTests(unittest.TestCase):
    def setUp(self):
        fd, self.csv = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w") as f:
            f.write("sex,race,hired\n" + "M,W,yes\n" * 60 + "M,W,no\n" * 40 + "F,B,yes\n" * 30 + "F,B,no\n" * 70)
        self.addCleanup(os.remove, self.csv)

    def test_strict_exit_code_and_json(self):
        out = self.csv + ".json"
        self.addCleanup(lambda: os.path.exists(out) and os.remove(out))
        self.assertEqual(main([self.csv, "--outcome", "hired", "--attrs", "sex", "--strict", "--format", "json", "-o", out]), 1)
        with open(out) as f:
            data = json.load(f)
        self.assertEqual(data[0]["worst"], "adverse")
        self.assertTrue(math.isclose(data[0]["groups"][1]["impact_ratio"], 0.5))

    def test_bad_column_returns_2(self):
        self.assertEqual(main([self.csv, "--outcome", "nope", "--attrs", "sex"]), 2)


if __name__ == "__main__":
    unittest.main()
