import json
import unittest

from fairhire.audit import (ADVERSE, EXCLUDED, OK, REFERENCE, WATCH, UNKNOWN,
                            audit_dimension, binarize, run_audit, two_proportion_p)
from fairhire.report import render_html, render_json, render_markdown, render_text


def rows(spec):
    """spec: {(sex, race): (n, selected)} -> list of row dicts."""
    out = []
    for (sex, race), (n, sel) in spec.items():
        out += [{"sex": sex, "race": race, "hired": int(i < sel)} for i in range(n)]
    return out


class TestStats(unittest.TestCase):
    def test_identical_rates_are_not_significant(self):
        self.assertAlmostEqual(two_proportion_p(30, 100, 30, 100), 1.0)

    def test_large_gap_is_significant(self):
        self.assertLess(two_proportion_p(10, 200, 60, 200), 0.001)

    def test_degenerate_inputs(self):
        self.assertEqual(two_proportion_p(0, 0, 5, 10), 1.0)
        self.assertEqual(two_proportion_p(0, 10, 0, 10), 1.0)


class TestBinarize(unittest.TestCase):
    def test_truthy_values(self):
        data = [{"o": v} for v in ["1", "Yes", "hired", "0", "no", ""]]
        self.assertEqual(binarize(data, outcome="o")[0], [True, True, True, False, False, False])

    def test_score_uses_strictly_above_median(self):
        data = [{"s": v} for v in [1, 2, 3, 4, 5]]
        hits, mode, cutoff = binarize(data, score="s")
        self.assertEqual((hits, mode, cutoff), ([False, False, False, True, True], "scoring", 3))

    def test_requires_exactly_one_target(self):
        with self.assertRaises(ValueError):
            binarize([], "a", "b")


class TestDimension(unittest.TestCase):
    def test_four_fifths_rule(self):
        # A: 50% , B: 30% -> IR 0.6 with n=400 each -> adverse
        labels = ["A"] * 400 + ["B"] * 400
        hits = [i < 200 for i in range(400)] + [i < 120 for i in range(400)]
        dim = audit_dimension("g", labels, hits)
        a, b = dim.groups
        self.assertEqual((a.name, a.status), ("A", REFERENCE))
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertEqual(b.status, ADVERSE)
        self.assertEqual(b.shortfall, 40)  # needs 0.8*0.5*400 = 160 selections, has 120

    def test_small_gap_is_ok_and_small_sample_is_watch(self):
        labels = ["A"] * 10 + ["B"] * 10 + ["C"] * 10
        hits = [i < 5 for i in range(10)] + [i < 3 for i in range(10)] + [i < 5 for i in range(10)]
        dim = audit_dimension("g", labels, hits)
        b = next(g for g in dim.groups if g.name == "B")
        self.assertEqual(b.status, WATCH)  # IR 0.6, but n=10 is too small to be sure
        self.assertEqual(next(g for g in dim.groups if g.name == "C").status, OK)

    def test_unknown_and_tiny_groups_are_excluded(self):
        labels = ["A"] * 98 + ["B"] + [UNKNOWN]
        hits = [True] * 50 + [False] * 48 + [False, False]
        dim = audit_dimension("g", labels, hits)
        statuses = {g.name: g.status for g in dim.groups}
        self.assertEqual(statuses, {"A": REFERENCE, "B": EXCLUDED, UNKNOWN: EXCLUDED})
        self.assertEqual(dim.status, REFERENCE)

    def test_zero_selections_overall(self):
        dim = audit_dimension("g", ["A", "B"] * 50, [False] * 100)
        self.assertTrue(all(g.impact_ratio is None for g in dim.groups))


class TestRunAudit(unittest.TestCase):
    def setUp(self):
        self.data = rows({("F", "X"): (200, 40), ("M", "X"): (200, 100),
                          ("F", "Y"): (200, 90), ("M", "Y"): (200, 100)})

    def test_dimensions_include_intersection(self):
        a = run_audit(self.data, ["sex", "race"], outcome="hired")
        self.assertEqual([d.name for d in a.dimensions], ["sex", "race", "sex × race"])
        inter = {g.name: g.status for g in a.dimensions[2].groups}
        self.assertEqual(inter["F · X"], ADVERSE)
        self.assertEqual(a.status, ADVERSE)

    def test_no_intersect(self):
        a = run_audit(self.data, ["sex", "race"], outcome="hired", intersect=False)
        self.assertEqual(len(a.dimensions), 2)

    def test_missing_column(self):
        with self.assertRaises(ValueError):
            run_audit(self.data, ["age"], outcome="hired")

    def test_renderers(self):
        a = run_audit(self.data, ["sex", "race"], outcome="hired")
        self.assertIn("Adverse impact", render_text(a))
        self.assertIn("| Status |", render_markdown(a))
        self.assertIn("<svg", render_html(a))
        self.assertEqual(json.loads(render_json(a))["status"], ADVERSE)


if __name__ == "__main__":
    unittest.main()
