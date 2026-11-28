import json
import os
import tempfile
import unittest

from fairhire import Record, load_csv, run_audit
from fairhire.__main__ import main
from fairhire.data import DataError
from fairhire.metrics import two_proportion_p
from fairhire.report import to_html, to_json, to_markdown, to_text

HERE = os.path.dirname(__file__)
SAMPLE = os.path.join(HERE, "..", "examples", "applicants.csv")


def people(group, n, selected, qualified=None):
    return [Record({"g": group}, i < selected, qualified=qualified) for i in range(n)]


class Metrics(unittest.TestCase):
    def test_impact_ratio_and_four_fifths(self):
        recs = people("A", 100, 50) + people("B", 100, 30)
        d = run_audit(recs, ["g"]).dimensions[0]
        a, b = d.groups
        self.assertEqual(d.reference, "A")
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertTrue(b.adverse and not a.adverse)

    def test_exactly_at_threshold_passes(self):
        recs = people("A", 100, 50) + people("B", 100, 40)
        self.assertTrue(run_audit(recs, ["g"]).passed)

    def test_small_groups_excluded_not_cleared(self):
        recs = people("A", 500, 250) + people("tiny", 5, 0)
        tiny = run_audit(recs, ["g"]).dimensions[0].groups[-1]
        self.assertTrue(tiny.excluded)
        self.assertIsNone(tiny.impact_ratio)
        self.assertFalse(tiny.adverse)

    def test_zero_selection_everywhere(self):
        recs = people("A", 50, 0) + people("B", 50, 0)
        self.assertTrue(run_audit(recs, ["g"]).passed)

    def test_p_value(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_p(10, 100, 50, 100), 0.001)
        self.assertIsNone(two_proportion_p(0, 0, 1, 1))

    def test_intersections(self):
        recs = [Record({"s": s, "r": r}, sel) for s in "MF" for r in "XY" for sel in (True, False) * 20]
        audit = run_audit(recs, ["s", "r"])
        self.assertEqual([d.name for d in audit.dimensions], ["s", "r", "s × r"])
        self.assertEqual(len(audit.dimensions[-1].groups), 4)

    def test_error_rates(self):
        recs = people("A", 10, 8, qualified=True) + people("B", 10, 4, qualified=True)
        d = run_audit(recs, ["g"]).dimensions[0]
        self.assertAlmostEqual(d.tpr_gap, 0.4)


class Data(unittest.TestCase):
    def write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_scoring_rate_uses_median(self):
        path = self.write("g,score\nA,0.9\nA,0.8\nB,0.2\nB,0.1\n")
        recs = load_csv(path, ["g"], score="score")
        self.assertEqual([r.selected for r in recs], [True, True, False, False])

    def test_friendly_errors(self):
        path = self.write("g,out\nA,maybe\n")
        with self.assertRaisesRegex(DataError, "row 2"):
            load_csv(path, ["g"], outcome="out")
        with self.assertRaisesRegex(DataError, "columns not found: race"):
            load_csv(path, ["race"], outcome="out")


class EndToEnd(unittest.TestCase):
    def test_sample_flags_proxy_bias(self):
        recs = load_csv(SAMPLE, ["sex", "race"], outcome="advanced", label="qualified")
        audit = run_audit(recs, ["sex", "race"])
        flagged = {g.name for d in audit.dimensions for g in d.flagged}
        self.assertIn("Black", flagged)
        self.assertNotIn("Female", flagged)          # passes alone…
        self.assertIn("Female · Black", flagged)      # …but not at the intersection
        for render in (to_text, to_markdown, to_html):
            self.assertTrue(render(audit))
        self.assertFalse(json.loads(to_json(audit))["passed"])

    def test_cli_exit_codes(self):
        devnull = open(os.devnull, "w")
        self.addCleanup(devnull.close)
        from contextlib import redirect_stderr, redirect_stdout

        with redirect_stdout(devnull), redirect_stderr(devnull):
            self.assertEqual(main([SAMPLE, "-g", "race", "-o", "advanced"]), 1)
            self.assertEqual(main([SAMPLE, "-g", "race", "-o", "advanced", "-t", "0.3"]), 0)
            self.assertEqual(main([SAMPLE, "-g", "nope", "-o", "advanced"]), 2)


if __name__ == "__main__":
    unittest.main()
