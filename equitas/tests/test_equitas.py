import csv
import json
import tempfile
import unittest
from pathlib import Path

from equitas import Config, load, run
from equitas.cli import main
from equitas.data import Record, to_binary
from equitas.metrics import EXCLUDED, FAIL, OK, WARN
from equitas.report import RENDERERS
from equitas.sample import generate, write
from equitas.stats import two_proportion_p, wilson


def recs(spec):
    """spec: {group: (n, selected)} -> records for attribute 'g'."""
    out = []
    for name, (n, k) in spec.items():
        out += [Record({"g": name}, int(i < k), None) for i in range(n)]
    return out


class Stats(unittest.TestCase):
    def test_wilson_bounds(self):
        lo, hi = wilson(50, 100)
        self.assertAlmostEqual(lo, 0.404, places=3)
        self.assertAlmostEqual(hi, 0.596, places=3)
        self.assertEqual(wilson(0, 0), (0.0, 0.0))
        self.assertEqual(wilson(0, 10)[0], 0.0)

    def test_two_proportion(self):
        self.assertAlmostEqual(two_proportion_p(50, 100, 50, 100), 1.0)
        self.assertLess(two_proportion_p(20, 100, 50, 100), 0.001)
        self.assertEqual(two_proportion_p(0, 0, 1, 2), 1.0)


class Metrics(unittest.TestCase):
    def test_four_fifths_fail(self):
        a = run(recs({"A": (500, 250), "B": (500, 150)}), ["g"], "x", "t").audits[0]
        b = next(g for g in a.groups if g.name == "B")
        self.assertEqual(a.reference, "A")
        self.assertAlmostEqual(b.impact_ratio, 0.6)
        self.assertEqual(b.status, FAIL)
        self.assertAlmostEqual(a.parity_gap, 0.2)

    def test_small_sample_is_review_not_fail(self):
        a = run(recs({"A": (20, 10), "B": (20, 7)}), ["g"], "x", "t").audits[0]
        self.assertEqual(next(g for g in a.groups if g.name == "B").status, WARN)

    def test_equal_rates_pass(self):
        r = run(recs({"A": (200, 60), "B": (200, 58)}), ["g"], "x", "t")
        self.assertEqual(r.status, OK)

    def test_tiny_and_unknown_groups_excluded(self):
        a = run(recs({"A": (500, 250), "B": (5, 0), "Unknown": (50, 0)}), ["g"], "x", "t",
                Config(min_share=0.02)).audits[0]
        statuses = {g.name: g.status for g in a.groups}
        self.assertEqual(statuses, {"A": OK, "B": EXCLUDED, "Unknown": EXCLUDED})

    def test_intersections(self):
        rows = [Record({"s": s, "r": r}, 1, None) for s in "MF" for r in "XY" for _ in range(10)]
        r = run(rows, ["s", "r"], "x", "t")
        self.assertEqual([a.attribute for a in r.audits], ["s", "r", "s × r"])
        self.assertEqual(len(r.audits[2].groups), 4)


class Data(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "d.csv"
        write(generate(400, seed=1), self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_to_binary(self):
        self.assertEqual(to_binary("Yes", "c"), 1)
        self.assertEqual(to_binary("0", "c"), 0)
        with self.assertRaises(ValueError):
            to_binary("maybe", "c")

    def test_load_outcome_and_score(self):
        r1, how1 = load(self.path, ["sex"], outcome="advanced", label="qualified")
        r2, how2 = load(self.path, ["sex"], score="score")
        self.assertEqual(len(r1), 400)
        self.assertIn("median", how2)
        self.assertIn(r1[0].label, (0, 1))
        self.assertIsNone(r2[0].label)

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "Missing column"):
            load(self.path, ["nope"], outcome="advanced")

    def test_blank_group_is_unknown(self):
        with open(self.path, newline="") as fh:
            races = {row["race"] for row in csv.DictReader(fh)}
        records, _ = load(self.path, ["race"], outcome="advanced")
        if "" in races:
            self.assertIn("Unknown", {r.groups["race"] for r in records})


class Sample(unittest.TestCase):
    def test_biased_sample_is_detected_and_fair_one_is_not(self):
        biased = [Record({"race": r["race"] or "Unknown"}, int(r["advanced"] == "yes"), None) for r in generate(3000)]
        fair = [Record({"race": r["race"] or "Unknown"}, int(r["advanced"] == "yes"), None) for r in generate(3000, fair=True)]
        self.assertEqual(run(biased, ["race"], "x", "t").status, FAIL)
        self.assertNotEqual(run(fair, ["race"], "x", "t").status, FAIL)

    def test_deterministic(self):
        self.assertEqual(generate(50, seed=3), generate(50, seed=3))


class Cli(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            csv_path, out = Path(d) / "h.csv", Path(d) / "r.json"
            self.assertEqual(main(["sample", "-n", "1500", "-o", str(csv_path)]), 0)
            args = ["audit", str(csv_path), "-g", "sex", "race", "--outcome", "advanced", "--label", "qualified"]
            self.assertEqual(main(args + ["-o", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["status"], FAIL)
            self.assertEqual(main(args + ["--strict", "-o", str(out)]), 1)
            self.assertEqual(main(["audit", str(csv_path), "-g", "x", "--outcome", "advanced"]), 2)

    def test_all_renderers(self):
        r = run(recs({"A": (100, 50), "B": (100, 20)}), ["g"], "x", "t")
        for name, fn in RENDERERS.items():
            self.assertTrue(fn(r), name)
        self.assertIn("<svg", RENDERERS["html"](r))


if __name__ == "__main__":
    unittest.main()
