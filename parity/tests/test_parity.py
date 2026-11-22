import json
import subprocess
import sys
import unittest
from pathlib import Path

from parity.data import outcomes
from parity.metrics import audit_attribute, intersect, two_proportion_p
from parity.proxies import cramers_v, find_proxies

ROOT = Path(__file__).resolve().parents[1]


def by_group(results):
    return {r.group: r for r in results}


class Metrics(unittest.TestCase):
    def test_impact_ratio_and_failure(self):
        groups = ["A"] * 100 + ["B"] * 100
        selected = [True] * 50 + [False] * 50 + [True] * 20 + [False] * 80
        r = by_group(audit_attribute(groups, selected))
        self.assertEqual(r["A"].status, "reference")
        self.assertAlmostEqual(r["B"].impact_ratio, 0.4)
        self.assertEqual(r["B"].status, "fail")

    def test_small_disparity_is_watch_not_fail(self):
        groups = ["A"] * 10 + ["B"] * 10
        selected = [True] * 5 + [False] * 5 + [True] * 3 + [False] * 7
        self.assertEqual(by_group(audit_attribute(groups, selected))["B"].status, "watch")

    def test_tiny_groups_are_excluded_from_reference(self):
        groups = ["A"] * 99 + ["B"] * 99 + ["C"]
        selected = [True] * 50 + [False] * 49 + [True] * 45 + [False] * 54 + [True]
        r = by_group(audit_attribute(groups, selected))
        self.assertEqual(r["C"].status, "excluded")
        self.assertEqual(r["A"].status, "reference")

    def test_p_value_bounds(self):
        self.assertAlmostEqual(two_proportion_p(5, 10, 5, 10), 1.0)
        self.assertLess(two_proportion_p(90, 100, 10, 100), 1e-6)

    def test_intersect_and_scoring_rate(self):
        rows = [{"s": "F", "r": "X", "score": "1"}, {"s": "M", "r": "", "score": "3"},
                {"s": "F", "r": "Y", "score": "2"}]
        self.assertEqual(intersect(rows, ["s", "r"]), ["F × X", "M × Unknown", "F × Y"])
        self.assertEqual(outcomes(rows, score="score"), [False, True, False])


class Proxies(unittest.TestCase):
    def test_cramers_v_extremes(self):
        x = ["a", "b"] * 200
        self.assertGreater(cramers_v(x, x), 0.99)
        self.assertLess(cramers_v(x, ["p"] * 100 + ["q"] * 100 + ["p"] * 100 + ["q"] * 100), 0.05)

    def test_find_proxies_ranks_leaky_feature_first(self):
        rows = [{"race": r, "zip": z, "noise": n}
                for r, z, n in zip(["A", "B"] * 200, ["1", "2"] * 200, ["x"] * 200 + ["y"] * 200)]
        top = find_proxies(rows, ["race"])[0]
        self.assertEqual((top["feature"], top["level"]), ("zip", "strong"))


class CLI(unittest.TestCase):
    def test_example_audit_fails_and_finds_proxies(self):
        cmd = [sys.executable, "-m", "parity", "audit", str(ROOT / "examples/hiring.csv"),
               "--outcome", "advanced", "--protected", "sex", "race_ethnicity",
               "--ignore", "score", "applicant_id", "--json", "-"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        audit = json.loads(proc.stdout)
        self.assertEqual(audit["verdict"], "fail")
        self.assertIn(("zip_code", "race_ethnicity"),
                      {(p["feature"], p["attribute"]) for p in audit["proxies"]})


if __name__ == "__main__":
    unittest.main()
