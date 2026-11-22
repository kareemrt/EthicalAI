import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from lineup.cli import main
from lineup.data import infer_kind
from lineup.detect import direct_identifiers, suggest_columns
from lineup.generalize import anonymize, build_hierarchy
from lineup.risk import assess, drivers

EXAMPLE = Path(__file__).parent.parent / "examples" / "patients.csv"

ROWS = [
    {"zip": "02139", "sex": "F", "dx": "flu"},
    {"zip": "02139", "sex": "F", "dx": "flu"},
    {"zip": "02139", "sex": "M", "dx": "asthma"},
    {"zip": "02139", "sex": "M", "dx": "flu"},
    {"zip": "02141", "sex": "F", "dx": "hiv"},
]


class RiskTests(unittest.TestCase):
    def test_metrics(self):
        r = assess(ROWS, ["zip", "sex"], ["dx"], k=2)
        self.assertEqual(r.k_min, 1)
        self.assertEqual(r.classes, 3)
        self.assertEqual(r.unique, 1)
        self.assertEqual(r.at_risk, 1)
        self.assertAlmostEqual(r.avg_risk, 3 / 5)
        self.assertEqual(r.max_risk, 1.0)
        self.assertFalse(r.passes)
        dx = r.diversity[0]
        self.assertEqual(dx.l_min, 1)
        self.assertEqual(dx.homogeneous_records, 3)  # (02139,F) all flu + the lone hiv row

    def test_empty(self):
        r = assess([], ["zip"], k=5)
        self.assertTrue(r.passes)
        self.assertEqual(r.records, 0)

    def test_drivers(self):
        ranked = drivers(ROWS, ["zip", "sex"])
        self.assertEqual(ranked[0][0], "zip")


class DetectTests(unittest.TestCase):
    def test_direct_identifiers(self):
        rows = [{"Email Address": f"u{i}@x.org", "contact": f"+1 617 555 {1000 + i}",
                 "dob": f"1990-01-{1 + i % 28:02d}", "id": f"A{i}x"} for i in range(30)]
        found = direct_identifiers(list(rows[0]), rows)
        self.assertIn("Email Address", found)
        self.assertIn("phone", found["contact"])
        self.assertIn("id", found)
        self.assertNotIn("dob", found)

    def test_suggestions(self):
        q, s = suggest_columns(["ZIP Code", "Birth Date", "gender", "diagnosis", "score"])
        self.assertEqual(q, ["ZIP Code", "Birth Date", "gender"])
        self.assertEqual(s, ["diagnosis"])

    def test_kinds(self):
        self.assertEqual(infer_kind("zip", ["02139", "10001"]), "zip")
        self.assertEqual(infer_kind("dob", ["1990-01-02"]), "date")
        self.assertEqual(infer_kind("age", ["31", "42.5"]), "numeric")
        self.assertEqual(infer_kind("job", ["nurse"]), "categorical")


class GeneralizeTests(unittest.TestCase):
    def test_hierarchies(self):
        z = build_hierarchy("zip", ["02139"], 5)
        self.assertEqual([m["02139"] for m in z.maps],
                         ["02139", "0213*", "021**", "02***", "0****", "*"])
        d = build_hierarchy("date", ["1984-07-12"], 5)
        self.assertEqual([m["1984-07-12"] for m in d.maps],
                         ["1984-07-12", "1984-07", "1984", "1980s", "*"])
        a = build_hierarchy("numeric", ["0", "37", "99"], 5)
        self.assertEqual(a.maps[1]["37"], "35-39")
        self.assertEqual(a.maps[-1]["37"], "*")
        c = build_hierarchy("categorical", ["a"] * 5 + ["b"], 5)
        self.assertEqual((c.maps[1]["a"], c.maps[1]["b"]), ("a", "Other"))

    def test_anonymize_reaches_k(self):
        result = anonymize(ROWS, ["zip", "sex"], {"zip": "zip", "sex": "categorical"},
                           k=2, max_suppress=0)
        self.assertEqual(result.suppressed, 0)
        self.assertTrue(assess(result.rows, ["zip", "sex"], k=2).passes)

    def test_suppression_budget(self):
        result = anonymize(ROWS, ["zip", "sex"], {"zip": "zip", "sex": "categorical"},
                           k=2, max_suppress=0.2)
        self.assertEqual(result.suppressed, 1)
        self.assertEqual(result.levels, {"zip": 0, "sex": 0})


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([str(a) for a in args])
        return code, buf.getvalue()

    def test_scan_fails_on_example(self):
        code, out = self.run_cli("scan", EXAMPLE, "--format", "json")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["risk"]["k_min"], 1)
        self.assertIn("email", data["direct_identifiers"])

    def test_fix_writes_safe_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "safe.csv"
            code, _ = self.run_cli("fix", EXAMPLE, "-o", out, "--k", "5")
            self.assertEqual(code, 0)
            header = out.read_text().splitlines()[0]
            self.assertNotIn("email", header)
            code, _ = self.run_cli("scan", out, "--qi", "zip,birth_date,sex,race")
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
