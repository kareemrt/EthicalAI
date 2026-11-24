import unittest

from equitas.metrics import (ADVERSE, EXCLUDED, OK, REVIEW, audit_groups,
                             shortfall, two_proportion_p, worst_status)


def pairs(**groups):
    """pairs(A=(selected, total), ...) -> [(group, bool), ...]"""
    out = []
    for g, (s, t) in groups.items():
        out += [(g, True)] * s + [(g, False)] * (t - s)
    return out


class ImpactRatio(unittest.TestCase):
    def test_reference_group_has_ratio_one(self):
        stats = {s.group: s for s in audit_groups(pairs(A=(50, 100), B=(25, 100)))}
        self.assertEqual(stats["A"].impact_ratio, 1.0)
        self.assertIsNone(stats["A"].p_value)
        self.assertAlmostEqual(stats["B"].impact_ratio, 0.5)

    def test_large_gap_is_adverse(self):
        stats = {s.group: s for s in audit_groups(pairs(A=(500, 1000), B=(250, 1000)))}
        self.assertEqual(stats["B"].status, ADVERSE)
        self.assertLess(stats["B"].p_value, 1e-6)

    def test_small_sample_gap_is_review_not_adverse(self):
        stats = {s.group: s for s in audit_groups(pairs(A=(6, 10), B=(4, 10)))}
        self.assertEqual(stats["B"].status, REVIEW)

    def test_at_threshold_is_ok(self):
        stats = {s.group: s for s in audit_groups(pairs(A=(50, 100), B=(40, 100)))}
        self.assertEqual(stats["B"].status, OK)
        self.assertEqual(stats["B"].shortfall, 0)

    def test_small_groups_excluded_and_never_reference(self):
        # C has a perfect rate but only 1% of the population.
        stats = {s.group: s for s in audit_groups(
            pairs(A=(50, 100), B=(40, 98), C=(2, 2)))}
        self.assertEqual(stats["C"].status, EXCLUDED)
        self.assertIsNone(stats["C"].impact_ratio)
        self.assertEqual(stats["A"].impact_ratio, 1.0)

    def test_empty_input(self):
        self.assertEqual(audit_groups([]), [])

    def test_nobody_selected(self):
        stats = audit_groups(pairs(A=(0, 50), B=(0, 50)))
        self.assertTrue(all(s.status == OK for s in stats))


class Helpers(unittest.TestCase):
    def test_shortfall(self):
        # 25/100 selected, target 40% -> needs 15 more
        self.assertEqual(shortfall(25, 100, 0.40), 15)
        self.assertEqual(shortfall(50, 100, 0.40), 0)

    def test_p_value_identical_rates(self):
        self.assertAlmostEqual(two_proportion_p(30, 100, 30, 100), 1.0)

    def test_p_value_known(self):
        # 60/100 vs 40/100: z ≈ 2.828, two-sided p ≈ 0.00468
        self.assertAlmostEqual(two_proportion_p(60, 100, 40, 100), 0.00468, places=4)

    def test_worst_status(self):
        stats = audit_groups(pairs(A=(500, 1000), B=(250, 1000)))
        self.assertEqual(worst_status(stats), ADVERSE)


if __name__ == "__main__":
    unittest.main()
