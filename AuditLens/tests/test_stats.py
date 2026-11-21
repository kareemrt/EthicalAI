import math
import unittest

from auditlens import stats


class StatsTests(unittest.TestCase):
    def test_normal_cdf(self):
        self.assertAlmostEqual(stats.normal_cdf(0), 0.5)
        self.assertAlmostEqual(stats.normal_cdf(1.959963984540054), 0.975, places=6)

    def test_wilson_known_value(self):
        # Reference values for k=8, n=10 (Wilson 95%): 0.4902, 0.9433
        lo, hi = stats.wilson_interval(8, 10)
        self.assertAlmostEqual(lo, 0.4902, places=3)
        self.assertAlmostEqual(hi, 0.9433, places=3)

    def test_wilson_edges(self):
        self.assertEqual(stats.wilson_interval(0, 0), (0.0, 0.0))
        lo, hi = stats.wilson_interval(0, 20)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_two_proportion(self):
        # 50/100 vs 30/100 -> z ~ 2.887, p ~ 0.0039
        p = stats.two_proportion_p_value(50, 100, 30, 100)
        self.assertAlmostEqual(p, 0.0039, places=3)
        self.assertIsNone(stats.two_proportion_p_value(0, 10, 0, 10))
        self.assertIsNone(stats.two_proportion_p_value(1, 0, 1, 10))

    def test_ratio_interval_contains_point(self):
        lo, hi = stats.ratio_interval(30, 100, 50, 100)
        self.assertLess(lo, 0.6)
        self.assertGreater(hi, 0.6)
        self.assertIsNone(stats.ratio_interval(0, 100, 50, 100))

    def test_median(self):
        self.assertEqual(stats.median([3, 1, 2]), 2)
        self.assertEqual(stats.median([4, 1, 2, 3]), 2.5)
        with self.assertRaises(ValueError):
            stats.median([])


if __name__ == "__main__":
    unittest.main()
