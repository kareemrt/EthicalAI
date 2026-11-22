"""Run with:  python -m unittest discover tests"""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from fairlens import load, report, run_audit
from fairlens.__main__ import main
from fairlens.metrics import two_proportion_p, wilson


def write_csv(rows: list[dict]) -> Path:
    fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
    writer = csv.DictWriter(fh, fieldnames=rows[0])
    writer.writeheader()
    writer.writerows(rows)
    fh.close()
    return Path(fh.name)


def people(group: str, selected: int, total: int, qualified: int | None = None) -> list[dict]:
    """`total` people from `group`, the first `selected` of whom were advanced."""
    q = total if qualified is None else qualified
    return [{"g": group, "hired": "yes" if i < selected else "no",
             "q": "yes" if i < q else "no", "score": str(100 - i)} for i in range(total)]


class StatsTest(unittest.TestCase):
    def test_wilson_contains_point_estimate(self):
        lo, hi = wilson(30, 100)
        self.assertLess(lo, 0.30)
        self.assertGreater(hi, 0.30)

    def test_wilson_empty(self):
        self.assertEqual(wilson(0, 0), (0.0, 0.0))

    def test_identical_rates_not_significant(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)

    def test_large_gap_significant(self):
        self.assertLess(two_proportion_p(60, 100, 20, 100), 0.001)


class AuditTest(unittest.TestCase):
    def audit(self, rows, **kw):
        return run_audit(load(write_csv(rows), outcome="hired", **kw), ["g"])

    def test_four_fifths_fail(self):
        # A: 60/100 selected, B: 30/100 → impact ratio 0.5, highly significant
        attr = self.audit(people("A", 60, 100) + people("B", 30, 100)).attributes[0]
        b = next(g for g in attr.groups if g.group == "B")
        self.assertEqual(attr.reference, "A")
        self.assertAlmostEqual(b.impact_ratio, 0.5)
        self.assertEqual(b.status, "fail")

    def test_small_gap_passes(self):
        audit = self.audit(people("A", 50, 100) + people("B", 45, 100))
        self.assertEqual(audit.status, "pass")

    def test_below_threshold_but_noisy_warns(self):
        audit = self.audit(people("A", 5, 10) + people("B", 3, 10))   # 0.6, tiny n
        self.assertEqual(audit.status, "warn")

    def test_small_groups_and_unknowns_are_not_judged(self):
        rows = people("A", 50, 100) + people("B", 48, 100) + people("C", 0, 2) + people("", 0, 5)
        attr = self.audit(rows).attributes[0]
        statuses = {g.group: g.status for g in attr.groups}
        self.assertEqual(statuses["C"], "n/a")
        self.assertEqual(statuses["Unknown"], "n/a")
        self.assertEqual(attr.status, "pass")

    def test_error_rates_with_labels(self):
        rows = people("A", 40, 100, qualified=50) + people("B", 40, 100, qualified=80)
        attr = self.audit(rows, label="q").attributes[0]
        a = next(g for g in attr.groups if g.group == "A")
        self.assertAlmostEqual(a.tpr, 40 / 50)
        self.assertAlmostEqual(attr.tpr_gap, 40 / 50 - 40 / 80)

    def test_scoring_mode_uses_median(self):
        ds = load(write_csv(people("A", 0, 10)), score="score")
        self.assertEqual(ds.mode, "scoring")
        self.assertEqual(sum(ds.selected), 5)

    def test_intersection(self):
        rows = [dict(r, h="x") for r in people("A", 6, 10)] + [dict(r, h="y") for r in people("B", 6, 10)]
        audit = run_audit(load(write_csv(rows), outcome="hired"), ["g", "h"], intersect=True)
        self.assertEqual(audit.attributes[-1].attribute, "g × h")
        self.assertIn("A · x", {g.group for g in audit.attributes[-1].groups})

    def test_bad_outcome_value(self):
        with self.assertRaises(ValueError):
            load(write_csv([{"g": "A", "hired": "maybe"}]), outcome="hired")


class OutputTest(unittest.TestCase):
    def setUp(self):
        self.path = write_csv(people("A", 60, 100) + people("B", 30, 100))
        self.audit = run_audit(load(self.path, outcome="hired"), ["g"])

    def test_renderers(self):
        self.assertIn("<svg", report.html(self.audit))
        self.assertIn("| B |", report.markdown(self.audit))
        self.assertEqual(json.loads(report.to_json(self.audit))["status"], "fail")
        self.assertIn("0.50× the rate of A", report.findings(self.audit)[0])

    def test_cli_strict_exit_code(self):
        self.assertEqual(main([str(self.path), "--outcome", "hired", "--attrs", "g", "--no-color"]), 0)
        self.assertEqual(main([str(self.path), "--outcome", "hired", "--attrs", "g",
                               "--strict", "--no-color"]), 1)
        self.assertEqual(main([str(self.path), "--outcome", "hired", "--attrs", "zzz"]), 2)


if __name__ == "__main__":
    unittest.main()
