"""Run with:  python -m unittest discover tests"""
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from hireaudit import Config, audit, audit_all, fisher_exact, load
from hireaudit.cli import main
from hireaudit.metrics import classify


def write_csv(rows, header=("sex", "race", "outcome", "score")):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)
    f.close()
    return f.name


def population(spec):
    """spec: {(sex, race): (applicants, selected)} -> CSV rows."""
    rows = []
    for (sex, race), (n, k) in spec.items():
        rows += [(sex, race, "yes" if i < k else "no", i) for i in range(n)]
    return rows


class FisherExact(unittest.TestCase):
    def test_matches_reference_values(self):
        # Reference values from scipy.stats.fisher_exact (two-sided).
        self.assertAlmostEqual(fisher_exact(8, 2, 1, 5), 0.034965034965, places=9)
        self.assertAlmostEqual(fisher_exact(1, 9, 11, 3), 0.002759456185, places=9)
        self.assertAlmostEqual(fisher_exact(3, 1, 1, 3), 0.485714285714, places=9)

    def test_identical_groups_are_not_significant(self):
        self.assertAlmostEqual(fisher_exact(50, 50, 50, 50), 1.0)

    def test_large_counts_are_fast_and_finite(self):
        p = fisher_exact(4000, 16000, 5000, 15000)
        self.assertTrue(0 <= p < 1e-10)


class Metrics(unittest.TestCase):
    def setUp(self):
        self.path = write_csv(population({
            ("Male", "A"): (200, 100),      # 50%
            ("Female", "A"): (200, 60),     # 30% -> ratio 0.6
            ("Female", "B"): (5, 0),        # tiny group -> excluded at 2%
            ("", "A"): (10, 5),             # unknown sex
        }))

    def test_rates_ratios_and_reference(self):
        ds = load(self.path, ["sex", "race"], outcome="outcome")
        a = audit(ds, ("sex",))
        by = {g.name: g for g in a.groups}
        self.assertEqual(a.reference, "Male")
        self.assertEqual(a.unknown, 10)
        self.assertAlmostEqual(by["Female"].rate, 60 / 205)
        self.assertAlmostEqual(by["Female"].impact_ratio, (60 / 205) / 0.5)
        self.assertEqual(by["Female"].status, "FAIL")
        self.assertEqual(by["Male"].status, "PASS")

    def test_small_groups_excluded_but_reported(self):
        ds = load(self.path, ["sex", "race"], outcome="outcome")
        inter = audit(ds, ("sex", "race"))
        tiny = next(g for g in inter.groups if g.name == "Female × B")
        self.assertEqual(tiny.status, "EXCLUDED")
        self.assertIsNone(tiny.impact_ratio)
        self.assertEqual(inter.groups[-1].name, "Female × B")  # excluded sorted last

    def test_intersection_toggle(self):
        ds = load(self.path, ["sex", "race"], outcome="outcome")
        self.assertEqual(len(audit_all(ds)), 3)
        self.assertEqual(len(audit_all(ds, Config(intersect=False))), 2)

    def test_classification(self):
        self.assertEqual(classify(0.7, 0.01, 0.8, 0.05), "FAIL")
        self.assertEqual(classify(0.7, 0.40, 0.8, 0.05), "REVIEW")   # low but noisy
        self.assertEqual(classify(0.9, 0.01, 0.8, 0.05), "REVIEW")   # significant gap
        self.assertEqual(classify(0.9, 0.40, 0.8, 0.05), "PASS")

    def test_zero_selections_does_not_crash(self):
        path = write_csv(population({("Male", "A"): (10, 0), ("Female", "A"): (10, 0)}))
        a = audit(load(path, ["sex"], outcome="outcome"), ("sex",))
        self.assertEqual(a.status, "N/A")


class Loading(unittest.TestCase):
    def test_scoring_mode_uses_median(self):
        path = write_csv([("M", "A", "", s) for s in (1, 2, 3, 4)])
        ds = load(path, ["sex"], score="score")
        self.assertEqual(ds.cutoff, 2.5)
        self.assertEqual([hit for _, hit in ds.rows], [False, False, True, True])

    def test_custom_positive_values(self):
        path = write_csv([("M", "A", "Interview", 0), ("M", "A", "Reject", 0)])
        ds = load(path, ["sex"], outcome="outcome", positive=["interview"])
        self.assertEqual([hit for _, hit in ds.rows], [True, False])

    def test_helpful_errors(self):
        path = write_csv([("M", "A", "yes", "n/a?")])
        with self.assertRaisesRegex(ValueError, "not found"):
            load(path, ["gender"], outcome="outcome")
        with self.assertRaisesRegex(ValueError, "line 2"):
            load(path, ["sex"], score="score")


class Cli(unittest.TestCase):
    def test_writes_reports_and_strict_exit_code(self):
        path = write_csv(population({("Male", "A"): (300, 150), ("Female", "A"): (300, 60)}))
        with tempfile.TemporaryDirectory() as out, redirect_stdout(io.StringIO()):
            self.assertEqual(main([path, "-g", "sex", "-o", "outcome", "--out", out]), 0)
            self.assertEqual(main([path, "-g", "sex", "-o", "outcome", "--strict"]), 1)
            report = json.loads(Path(out, "report.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            for name in ("report.md", "report.html", "charts/sex.svg"):
                self.assertTrue(Path(out, name).stat().st_size > 0, name)

    def test_bad_input_returns_2(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["missing.csv"])  # argparse: --groups is required
            self.assertEqual(main(["missing.csv", "-g", "sex", "-o", "x"]), 2)


if __name__ == "__main__":
    unittest.main()
