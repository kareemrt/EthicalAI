import csv
import json
import tempfile
import unittest
from pathlib import Path

from parity import Policy, Record, load, run
from parity.cli import main
from parity.metrics import FAIL, WARN, audit
from parity.report import to_html, to_json, to_markdown, to_text
from parity.stats import two_proportion_p, wilson

EXAMPLE = Path(__file__).parents[1] / "examples" / "hiring.csv"


def records(spec):
    """spec: {group: (n, selected)} -> list[Record]"""
    out = []
    for g, (n, k) in spec.items():
        out += [Record((g,), i < k, None) for i in range(n)]
    return out


def by_group(rs):
    return audit(rs, "g", lambda r: r.groups[0])


class Stats(unittest.TestCase):
    def test_wilson_contains_rate_and_is_bounded(self):
        lo, hi = wilson(5, 10)
        self.assertLess(lo, .5); self.assertGreater(hi, .5)
        self.assertEqual(wilson(0, 0), (0.0, 0.0))
        self.assertGreaterEqual(wilson(0, 5)[0], 0.0)
        self.assertLessEqual(wilson(5, 5)[1], 1.0)

    def test_two_proportion(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_p(20, 100, 60, 100), 1e-6)
        self.assertEqual(two_proportion_p(0, 0, 3, 10), 1.0)


class Metrics(unittest.TestCase):
    def test_four_fifths_fail(self):
        a = by_group(records({"A": (500, 250), "B": (500, 150)}))
        b = next(g for g in a.groups if g.name == "B")
        self.assertEqual(a.reference, "A")
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertEqual(a.status, FAIL)

    def test_parity_passes(self):
        a = by_group(records({"A": (500, 250), "B": (500, 240)}))
        self.assertEqual(a.status, "pass")
        self.assertEqual(a.findings, [])

    def test_low_ratio_small_sample_is_only_a_warning(self):
        a = by_group(records({"A": (500, 250), "B": (10, 2)}))
        self.assertEqual(a.status, WARN)
        self.assertTrue(any(f.level == "info" for f in a.findings))

    def test_tiny_group_cannot_become_reference(self):
        a = by_group(records({"A": (500, 200), "Tiny": (3, 3)}))
        self.assertEqual(a.reference, "A")

    def test_equal_opportunity_gap(self):
        rs = ([Record(("A",), i < 80, True) for i in range(100)]
              + [Record(("A",), False, False) for _ in range(100)]
              + [Record(("B",), i < 50, True) for i in range(100)]
              + [Record(("B",), i < 30, False) for i in range(100)])
        a = by_group(rs)
        msgs = " ".join(f.message for f in a.findings)
        self.assertIn("Equal-opportunity gap", msgs)
        self.assertIn("False-positive gap", msgs)

    def test_intersectional_audit_added(self):
        rs = [Record(("x", "1"), True, None), Record(("y", "2"), False, None)]
        audits = run(rs, ["a", "b"], Policy(min_n=1))
        self.assertEqual([a.attribute for a in audits], ["a", "b", "a × b"])


class EndToEnd(unittest.TestCase):
    def test_example_detects_planted_bias(self):
        rs = load(EXAMPLE, ["gender", "age_band"], "advanced", "qualified")
        audits = run(rs, ["gender", "age_band"])
        self.assertEqual(audits[0].status, FAIL)   # gender
        self.assertEqual(audits[1].status, FAIL)   # age
        for render in (to_text, to_markdown, to_html):
            self.assertIn("gender", render(audits))
        self.assertEqual(json.loads(to_json(audits))["status"], FAIL)

    def test_load_handles_blanks_and_cutoff(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
            w = csv.writer(fh)
            w.writerows([["grp", "score"], ["a", "0.9"], ["", "0.1"], ["b", ""]])
        rs = load(fh.name, ["grp"], "score", cutoff=0.5)
        self.assertEqual([(r.groups[0], r.decision) for r in rs], [("a", True), ("Unknown", False)])

    def test_missing_column_is_clear_error(self):
        self.assertRaisesRegex(ValueError, "not found: nope",
                               load, EXAMPLE, ["nope"], "advanced")

    def test_cli_exit_codes(self):
        argv = [str(EXAMPLE), "-g", "gender", "-d", "advanced", "-f", "json",
                "-o", tempfile.mktemp(suffix=".json")]
        self.assertEqual(main(argv), 1)
        self.assertEqual(main([str(EXAMPLE), "-g", "bogus", "-d", "advanced"]), 3)


if __name__ == "__main__":
    unittest.main()
