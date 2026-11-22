"""Tests: python -m unittest discover tests"""

import csv
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from fairgauge import Record, audit, load, run
from fairgauge.__main__ import main
from fairgauge.metrics import fisher_exact, z_test
from fairgauge.report import RENDERERS


def records(spec):
    """spec: {group: (n, selected)} -> list[Record]"""
    out = []
    for g, (n, k) in spec.items():
        out += [Record({"g": g}, i < k) for i in range(n)]
    return out


class Stats(unittest.TestCase):
    def test_fisher_matches_reference(self):
        # Classic tea-tasting table; scipy.stats.fisher_exact gives 0.4857
        self.assertAlmostEqual(fisher_exact(3, 1, 1, 3), 0.4857, places=4)

    def test_fisher_extreme(self):
        self.assertAlmostEqual(fisher_exact(10, 0, 0, 10), 1.0825e-05, places=8)

    def test_z_equal_rates(self):
        self.assertAlmostEqual(z_test(50, 100, 50, 100), 1.0)

    def test_z_degenerate(self):
        self.assertEqual(z_test(0, 10, 0, 10), 1.0)


class Metrics(unittest.TestCase):
    def test_impact_ratio_and_flags(self):
        a = audit(records({"A": (100, 60), "B": (100, 30)}), lambda r: r.groups["g"], "g")
        self.assertEqual(a.reference, "A")
        b = next(g for g in a.groups if g.name == "B")
        self.assertAlmostEqual(b.impact_ratio, 0.5)
        self.assertIn("adverse impact", b.flags)
        self.assertIn("statistically significant", b.flags)

    def test_no_flag_at_threshold(self):
        a = audit(records({"A": (100, 50), "B": (100, 40)}), lambda r: r.groups["g"], "g")
        self.assertFalse(a.flagged)  # 0.40 / 0.50 = 0.80 exactly passes

    def test_small_groups_never_reference_or_flagged(self):
        a = audit(records({"A": (200, 50), "B": (200, 40), "tiny": (3, 3), "low": (2, 0)}),
                  lambda r: r.groups["g"], "g")
        self.assertEqual(a.reference, "A")
        low = next(g for g in a.groups if g.name == "low")
        self.assertEqual(low.flags, ["small sample"])

    def test_equal_opportunity(self):
        rs = [Record({"g": "A"}, True, True)] * 10 + [Record({"g": "B"}, i < 4, True) for i in range(10)]
        a = audit(rs, lambda r: r.groups["g"], "g")
        b = next(g for g in a.groups if g.name == "B")
        self.assertAlmostEqual(b.tpr_ratio, 0.4)
        self.assertIn("unequal opportunity", b.flags)

    def test_intersectional(self):
        rs = [Record({"s": s, "r": r}, True) for s in "MF" for r in "XY"]
        audits = run(rs, ["s", "r"], intersectional=True)
        self.assertEqual(len(audits), 3)
        self.assertEqual({g.name for g in audits[-1].groups}, {"M · X", "M · Y", "F · X", "F · Y"})


class Loading(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["sex", "score", "hired"])
            w.writerows([["F", 1, "no"], ["M", 2, "Yes"], ["", 3, "1"], ["F", 4, "true"]])

    def tearDown(self):
        os.remove(self.path)

    def test_selected_column(self):
        rs = load(self.path, ["sex"], selected="hired")
        self.assertEqual([r.selected for r in rs], [False, True, True, True])
        self.assertEqual(rs[2].groups["sex"], "Unknown")

    def test_score_uses_median(self):
        rs = load(self.path, ["sex"], score="score")  # median 2.5
        self.assertEqual([r.selected for r in rs], [False, False, True, True])

    def test_errors(self):
        with self.assertRaises(ValueError):
            load(self.path, ["race"], selected="hired")
        with self.assertRaises(ValueError):
            load(self.path, ["sex"])

    def test_cli_exit_codes(self):
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(main([self.path, "-a", "sex", "-s", "hired", "-f", "json"]), 0)
        self.assertEqual(json.loads(out.getvalue())["records"], 4)
        self.assertEqual(main([self.path, "-a", "nope", "-s", "hired"]), 2)


class Rendering(unittest.TestCase):
    def test_all_formats_render(self):
        audits = run(records({"A": (100, 60), "B<script>": (100, 30)}), ["g"])
        for name, render in RENDERERS.items():
            text = render(audits, 200, "x.csv")
            self.assertIn("adverse impact", text, name)
        self.assertNotIn("<script>", RENDERERS["html"](audits, 200))


if __name__ == "__main__":
    unittest.main()
