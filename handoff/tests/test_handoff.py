import os
import random
import tempfile
import unittest

from handoff import Prediction, load_csv, run_audit
from handoff import metrics as m
from handoff.cli import main


def calibrated(n=3000, seed=1, group="all"):
    """Predictions whose confidence is exactly the chance of being right."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        c = rng.uniform(0.5, 1.0)
        out.append(Prediction(c, rng.random() < c, group))
    return out


def overconfident(n=3000, seed=2, group="all"):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        c = rng.uniform(0.7, 1.0)
        out.append(Prediction(c, rng.random() < c - 0.2, group))
    return out


class Metrics(unittest.TestCase):
    def test_ece_low_when_calibrated(self):
        self.assertLess(m.ece(m.reliability_bins(calibrated())), 0.03)

    def test_ece_high_when_overconfident(self):
        self.assertGreater(m.ece(m.reliability_bins(overconfident())), 0.15)

    def test_wilson_bounds(self):
        self.assertEqual(m.wilson_lower(0, 0), 0.0)
        self.assertLess(m.wilson_lower(10, 10), 1.0)            # small n stays cautious
        self.assertGreater(m.wilson_lower(990, 1000), 0.98)

    def test_coverage_curve_handles_ties(self):
        preds = [Prediction(0.9, True), Prediction(0.9, False), Prediction(0.6, True)]
        curve = m.coverage_curve(preds)
        self.assertEqual([round(p.coverage, 2) for p in curve], [0.67, 1.0])
        self.assertEqual(curve[0].accuracy, 0.5)

    def test_threshold_meets_target(self):
        curve = m.coverage_curve(calibrated(5000))
        op = m.pick_threshold(curve, 0.9)
        self.assertIsNotNone(op)
        self.assertGreaterEqual(op.lower, 0.9)
        self.assertIsNone(m.pick_threshold(curve, 0.999))

    def test_platt_shrinks_overconfidence(self):
        preds = overconfident()
        a, b = m.fit_platt(preds)
        fixed = m.apply_platt(preds, a, b)
        self.assertLess(m.ece(m.reliability_bins(fixed)), 0.03)

    def test_platt_is_near_identity_when_calibrated(self):
        a, b = m.fit_platt(calibrated(5000))
        self.assertAlmostEqual(a, 1.0, delta=0.2)
        self.assertAlmostEqual(b, 0.0, delta=0.2)


class Audit(unittest.TestCase):
    def test_calibrated_model_passes(self):
        a = run_audit(calibrated(4000), target=0.9)
        self.assertTrue(a.passed, a.findings)

    def test_group_gap_fails(self):
        preds = calibrated(3000, group="A") + overconfident(1000, group="B")
        a = run_audit(preds, target=0.9)
        self.assertFalse(a.passed)
        self.assertTrue(any("'B'" in f and f.startswith("FAIL") for f in a.findings))


class Cli(unittest.TestCase):
    def _csv(self, text):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_binary_layout(self):
        preds = load_csv(self._csv("score,label\n0.9,1\n0.2,1\n0.1,0\n"))
        self.assertEqual([p.correct for p in preds], [True, False, True])
        self.assertAlmostEqual(preds[2].confidence, 0.9)

    def test_bad_input_exits_2(self):
        self.assertEqual(main([self._csv("foo,bar\n1,2\n")]), 2)
        self.assertEqual(main([self._csv("confidence,correct\n1.4,1\n")]), 2)

    def test_example_writes_report(self):
        here = os.path.dirname(__file__)
        with tempfile.TemporaryDirectory() as out:
            code = main([os.path.join(here, "..", "examples", "triage.csv"), "-g", "skin_type", "-o", out])
            self.assertEqual(code, 1)  # the demo model is meant to fail
            self.assertTrue({"report.md", "summary.json", "reliability.svg", "coverage.svg",
                             "groups.svg"} <= set(os.listdir(out)))


if __name__ == "__main__":
    unittest.main()
