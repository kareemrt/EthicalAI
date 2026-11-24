import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from equitas.audit import run_audit
from equitas.cli import main

CSV = """id,sex,race,score,hired
1,F,X,90,yes
2,F,X,40,no
3,F,Y,30,no
4,F,Y,20,no
5,M,X,95,yes
6,M,X,85,yes
7,M,Y,80,yes
8,M,Y,35,no
9,,X,70,yes
"""


class AuditPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "d.csv"
        self.csv.write_text(CSV)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_dimensions_and_unknowns(self):
        a = run_audit(self.csv, "hired", ["sex", "race"], min_share=0)
        self.assertEqual([d.name for d in a.dimensions], ["sex", "race", "sex × race"])
        self.assertEqual(a.dimensions[0].unknown, 1)  # blank sex
        rates = {g.group: g.rate for g in a.dimensions[0].groups}
        self.assertEqual(rates, {"F": 0.25, "M": 0.75})

    def test_score_mode_uses_median(self):
        a = run_audit(self.csv, "score", ["sex"], score=True, min_share=0)
        self.assertEqual(a.median_cut, 70)
        self.assertEqual(a.mode, "scoring")

    def test_json_output(self):
        code, out, _ = self.run_cli("audit", str(self.csv), "-o", "hired", "-g", "sex",
                                    "--format", "json", "--min-share", "0")
        data = json.loads(out)
        self.assertEqual(data["population"], 9)
        self.assertIn(data["status"], {"ok", "review", "adverse"})
        self.assertIn(code, {0, 1})

    def test_writes_report(self):
        out_dir = Path(self.tmp.name) / "r"
        self.run_cli("audit", str(self.csv), "-o", "hired", "-g", "sex", "race",
                     "--out", str(out_dir))
        self.assertTrue((out_dir / "report.md").exists())
        self.assertTrue((out_dir / "charts" / "sex-race.svg").exists())
        self.assertIn("<svg", (out_dir / "charts" / "sex.svg").read_text())

    def test_strict_fails_on_review(self):
        # Tiny sample: gap is below threshold but not significant -> review
        code, _, _ = self.run_cli("audit", str(self.csv), "-o", "hired", "-g", "sex",
                                  "--strict", "--min-share", "0")
        self.assertEqual(code, 1)

    def test_helpful_errors(self):
        code, _, err = self.run_cli("audit", str(self.csv), "-o", "nope", "-g", "sex")
        self.assertEqual(code, 2)
        self.assertIn("missing column", err)
        code, _, err = self.run_cli("audit", str(self.csv), "-o", "score", "-g", "sex")
        self.assertEqual(code, 2)
        self.assertIn("--score", err)


if __name__ == "__main__":
    unittest.main()
