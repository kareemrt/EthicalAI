import io
import itertools
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from recourse import Model, audit, best_plan, single_changes
from recourse.cli import main
from recourse.report import audit_svg, explain_data

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "credit"


def toy(**over):
    spec = {
        "intercept": -10, "threshold": 0,
        "features": {
            "a": {"weight": 1.0, "mutable": True, "direction": "increase", "max": 6, "cost": 1.0},
            "b": {"weight": 2.0, "mutable": True, "direction": "increase", "max_change": 2, "cost": 1.0},
            "c": {"weight": -1.0, "mutable": True, "direction": "decrease", "min": 0, "cost": 4.0},
            "z": {"weight": 5.0, "note": "fixed"},
        },
    }
    for k, v in over.items():
        spec["features"][k].update(v)
    return Model.from_dict(spec)


class SolverTests(unittest.TestCase):
    def test_approved_needs_nothing(self):
        m = toy()
        plan = best_plan(m, {"a": 0, "b": 0, "c": 0, "z": 3})
        self.assertTrue(plan.feasible)
        self.assertEqual(plan.changes, [])

    def test_prefers_most_efficient_lever_first(self):
        m = toy()
        x = {"a": 0, "b": 0, "c": 0, "z": 1}  # gap = 5
        plan = best_plan(m, x)
        self.assertTrue(plan.feasible)
        self.assertEqual(plan.changes[0].feature.name, "b")   # 2 pts / effort
        self.assertEqual(plan.changes[0].after, 2)            # capped by max_change
        self.assertEqual(plan.changes[1].feature.name, "a")
        self.assertAlmostEqual(plan.cost, 3.0)
        self.assertGreaterEqual(m.score({**x, "b": 2, "a": 1}), 0)

    def test_matches_brute_force_on_integer_grid(self):
        m = toy(a={"step": 1}, b={"step": 1}, c={"step": 1})
        for z, c0 in itertools.product([0, 1], [0, 2, 4]):
            x = {"a": 0, "b": 0, "c": c0, "z": z}
            best = min(
                (da + db + 4 * dc for da in range(7) for db in range(3) for dc in range(c0 + 1)
                 if m.score({"a": da, "b": db, "c": c0 - dc, "z": z}) >= 0),
                default=None)
            plan = best_plan(m, x)
            self.assertEqual(plan.feasible, best is not None, x)
            if best is not None:
                self.assertAlmostEqual(plan.cost, best, msg=x)

    def test_respects_immutability_direction_and_bounds(self):
        m = toy()
        x = {"a": 5, "b": 0, "c": 0, "z": 0}
        for c in best_plan(m, x).changes:
            self.assertNotEqual(c.feature.name, "z")
            self.assertGreaterEqual(c.after, c.before if c.feature.direction == "increase" else -1e9)
            self.assertLessEqual(c.after, c.feature.max)

    def test_reports_no_recourse_with_shortfall(self):
        m = toy()
        plan = best_plan(m, {"a": 0, "b": 0, "c": 0, "z": -1})  # gap 15, max reachable 10
        self.assertFalse(plan.feasible)
        self.assertAlmostEqual(plan.shortfall, 5.0)

    def test_single_changes_each_suffice_alone(self):
        m = toy()
        x = {"a": 0, "b": 0, "c": 3, "z": 2}  # gap = 3
        singles = single_changes(m, x)
        self.assertEqual({p.changes[0].feature.name for p in singles}, {"a", "b", "c"})
        for p in singles:
            c = p.changes[0]
            self.assertGreaterEqual(m.score({**x, c.feature.name: c.after}), 0)

    def test_bad_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            toy(a={"direction": "sideways"})
        with self.assertRaises(KeyError):
            toy().vector({"a": 1})


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.model = Model.load(EXAMPLE / "model.json")
        from recourse.audit import read_csv
        self.rows = read_csv(EXAMPLE / "applicants.csv")

    def test_example_flags_burden_gap(self):
        r = audit(self.model, self.rows, "group")
        a, b = r.groups
        self.assertGreater(b.median_cost, a.median_cost)
        self.assertGreater(b.no_recourse_rate, a.no_recourse_rate)
        self.assertTrue(any(f.severity == "flag" and "burden" in f.text for f in r.findings))

    def test_identical_groups_are_not_flagged(self):
        rows = [dict(r, group=g) for r in self.rows[:200] for g in ("X", "Y")]
        r = audit(self.model, rows, "group")
        self.assertFalse(any(f.severity == "flag" and "ratio" in f.text for f in r.findings))

    def test_svg_is_well_formed(self):
        import xml.dom.minidom
        xml.dom.minidom.parseString(audit_svg(audit(self.model, self.rows)))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([str(a) for a in args])
        return code, buf.getvalue()

    def test_explain_json_roundtrip(self):
        code, out = self.run_cli("explain", EXAMPLE / "model.json", EXAMPLE / "applicant.json", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["decision"], "declined")
        m = Model.load(EXAMPLE / "model.json")
        x = m.vector(json.loads((EXAMPLE / "applicant.json").read_text()))
        for ch in data["best_plan"]["changes"]:
            x[ch["feature"]] = ch["to"]
        self.assertTrue(m.approves(x))
        self.assertEqual(data, explain_data(m, m.vector(json.loads((EXAMPLE / "applicant.json").read_text()))))

    def test_audit_strict_exits_nonzero_and_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            code, out = self.run_cli("audit", EXAMPLE / "model.json", EXAMPLE / "applicants.csv",
                                     "--strict", "--md", f"{d}/r.md", "--svg", f"{d}/r.svg")
            self.assertEqual(code, 1)
            self.assertIn("Findings", out)
            self.assertTrue(Path(d, "r.md").read_text().startswith("# Recourse audit"))
            self.assertIn("<svg", Path(d, "r.svg").read_text())

    def test_inspect(self):
        code, out = self.run_cli("inspect", EXAMPLE / "model.json")
        self.assertEqual(code, 0)
        self.assertIn("cannot be changed", out)


if __name__ == "__main__":
    unittest.main()
