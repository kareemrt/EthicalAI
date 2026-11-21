import os
import tempfile
import unittest

from auditlens import audit, synth, to_html, to_json, to_markdown
from auditlens.audit import STATUS_ADVERSE, STATUS_INSUFFICIENT, STATUS_OK, STATUS_REFERENCE, STATUS_WATCH
from auditlens.cli import main


def make_rows(spec):
    """spec: {(sex, race): (n, selected)} -> list of row dicts."""
    rows = []
    for (sex, race), (n, k) in spec.items():
        rows += [{"sex": sex, "race": race, "hired": "1" if i < k else "0", "score": str(100 - i)} for i in range(n)]
    return rows


class SelectionAuditTests(unittest.TestCase):
    def test_four_fifths_textbook_example(self):
        # EEOC Uniform Guidelines example: 48/80 (60%) vs 12/40 (30%) -> ratio 0.5.
        rows = make_rows({("M", "x"): (80, 48), ("F", "x"): (40, 12)})
        r = audit(rows, "hired", {"Sex": "sex"})
        sex = r.dimensions[0]
        self.assertEqual(sex.reference, "M")
        f = next(g for g in sex.groups if g.category == "F")
        self.assertAlmostEqual(f.impact_ratio, 0.5)
        self.assertEqual(f.status, STATUS_ADVERSE)
        self.assertEqual(r.verdict, "ADVERSE IMPACT DETECTED")

    def test_no_impact(self):
        rows = make_rows({("M", "x"): (200, 60), ("F", "x"): (200, 58)})
        r = audit(rows, "hired", {"Sex": "sex"})
        statuses = {g.category: g.status for g in r.dimensions[0].groups}
        self.assertEqual(statuses, {"M": STATUS_REFERENCE, "F": STATUS_OK})
        self.assertEqual(r.verdict, "NO ADVERSE IMPACT DETECTED")

    def test_below_threshold_but_not_significant(self):
        rows = make_rows({("M", "x"): (60, 30), ("F", "x"): (40, 14)})  # ratio 0.7, p ~ 0.13
        r = audit(rows, "hired", {"Sex": "sex"})
        f = next(g for g in r.dimensions[0].groups if g.category == "F")
        self.assertEqual(f.status, STATUS_WATCH)
        self.assertEqual(r.verdict, "REVIEW RECOMMENDED")

    def test_small_group_insufficient(self):
        rows = make_rows({("M", "x"): (400, 200), ("F", "x"): (20, 2)})
        r = audit(rows, "hired", {"Sex": "sex"}, min_share=0.0)
        f = next(g for g in r.dimensions[0].groups if g.category == "F")
        self.assertEqual(f.status, STATUS_INSUFFICIENT)
        self.assertTrue(any("collect more data" in w for w in r.warnings))

    def test_tiny_group_excluded_and_not_reference(self):
        # A 1%-of-sample group with a perfect rate must not become the reference.
        rows = make_rows({("M", "x"): (500, 150), ("F", "x"): (490, 145), ("X", "x"): (10, 10)})
        r = audit(rows, "hired", {"Sex": "sex"})
        d = r.dimensions[0]
        self.assertEqual(d.reference, "M")
        self.assertTrue(next(g for g in d.groups if g.category == "X").excluded)

    def test_unknowns_counted(self):
        rows = make_rows({("M", "x"): (100, 50), ("F", "x"): (100, 50), ("", "x"): (7, 1), ("Prefer not to say", "x"): (3, 1)})
        r = audit(rows, "hired", {"Sex": "sex"})
        self.assertEqual(r.dimensions[0].unknown, 10)
        self.assertEqual(r.total, 210)

    def test_intersectional_reveals_hidden_bias(self):
        # Neither sex nor race alone shows impact, but Black women are disadvantaged.
        spec = {("M", "W"): (250, 75), ("M", "B"): (250, 90), ("F", "W"): (250, 90), ("F", "B"): (250, 45)}
        r = audit(make_rows(spec), "hired", {"Sex": "sex", "Race": "race"}, intersections=[("Sex", "Race")])
        by = {d.name: d for d in r.dimensions}
        self.assertFalse(by["Sex"].flagged)
        self.assertFalse(by["Race"].flagged)
        self.assertEqual([g.category for g in by["Sex × Race"].flagged], ["F × B"])

    def test_bad_columns(self):
        with self.assertRaises(ValueError):
            audit(make_rows({("M", "x"): (10, 5)}), "nope", {"Sex": "sex"})
        with self.assertRaises(ValueError):
            audit(make_rows({("M", "x"): (10, 5)}), "hired", {"Sex": "sex"}, intersections=[("Sex", "Age")])

    def test_unparseable_outcome(self):
        rows = [{"sex": "M", "hired": "maybe"}]
        with self.assertRaises(ValueError):
            audit(rows, "hired", {"Sex": "sex"})


class ScoringAuditTests(unittest.TestCase):
    def test_scoring_rate_uses_median(self):
        rows = [{"g": "A", "s": str(v)} for v in (10, 9, 8, 7, 6)] + [{"g": "B", "s": str(v)} for v in (5, 4, 3, 2, 1)]
        r = audit(rows, "s", {"G": "g"}, mode="scoring", min_group_size=1)
        self.assertEqual(r.median_score, 5.5)
        rates = {g.category: g.rate for g in r.dimensions[0].groups}
        self.assertEqual(rates, {"A": 1.0, "B": 0.0})
        b = next(g for g in r.dimensions[0].groups if g.category == "B")
        self.assertEqual(b.status, STATUS_ADVERSE)


class EndToEndTests(unittest.TestCase):
    def test_synthetic_demo_detects_planted_bias_and_drift(self):
        rows = synth.generate(n=6000, seed=7)
        r = audit(rows, "advanced", {"Sex": "sex", "Race": "race_ethnicity", "Age": "age_band"},
                  intersections=[("Sex", "Race")], period="quarter")
        by = {d.name: d for d in r.dimensions}
        self.assertIn("40 and over", [g.category for g in by["Age"].flagged])
        self.assertTrue(by["Race"].flagged)
        sex_drift = [p.min_impact_ratio for p in r.timeline if p.dimension == "Sex"]
        self.assertLess(sex_drift[-1], sex_drift[0])  # gap penalty grows each quarter

    def test_reports_render(self):
        rows = synth.generate(n=1500, seed=1)
        r = audit(rows, "advanced", {"Sex": "sex"}, period="quarter")
        md = to_markdown(r, suppress_below=5)
        html = to_html(r)
        self.assertIn("# Bias Audit", md)
        self.assertIn("<svg", html)
        self.assertIn('"verdict"', to_json(r))

    def test_small_cell_suppression(self):
        rows = make_rows({("M", "x"): (100, 50), ("F", "x"): (100, 3)})
        md = to_markdown(audit(rows, "hired", {"Sex": "sex"}), suppress_below=5)
        self.assertIn("| <5 |", md)

    def test_cli_audit_and_ci_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "d.csv")
            synth.write_csv(path, synth.generate(n=3000, seed=3))
            out = os.path.join(tmp, "r.html")
            rc = main(["audit", path, "--outcome", "advanced", "--attr", "Age=age_band", "--html", out, "--fail-on-adverse"])
            self.assertEqual(rc, 2)
            self.assertTrue(os.path.getsize(out) > 1000)
            self.assertEqual(main(["audit", path, "--outcome", "missing", "--attr", "Age=age_band"]), 1)


if __name__ == "__main__":
    unittest.main()
