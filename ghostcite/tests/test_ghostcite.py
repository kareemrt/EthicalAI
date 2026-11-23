"""Offline test-suite. Run with:  python -m unittest discover -s tests"""
import datetime as dt
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ghostcite import check_citation, check_text, extract  # noqa: E402
from ghostcite import cli, match, offline, report  # noqa: E402
from ghostcite.models import Citation, Record  # noqa: E402

TODAY = dt.date(2026, 11, 23)
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "ai_answer.md"


def fake_get(routes):
    """Return a `get` function that serves canned (status, body) by URL substring."""
    def get(url):
        for key, resp in routes.items():
            if key in url:
                return resp
        return 404, ""
    return get


def crossref(title, year, doi="10.1234/x"):
    return 200, json.dumps({"message": {"title": [title], "DOI": doi,
                                        "issued": {"date-parts": [[year]]}}})


class Extract(unittest.TestCase):
    def kinds(self, text):
        return [(c.kind, c.value) for c in extract(text)]

    def test_identifiers(self):
        text = ("See doi:10.1038/nature14539. Also https://doi.org/10.1016/S0140-6736(20)30183-5, "
                "arXiv:1706.03762v5, ISBN 978-0-262-03561-3, PMID: 34265844 and "
                "https://example.org/page.")
        self.assertEqual(self.kinds(text), [
            ("doi", "10.1038/nature14539"),
            ("doi", "10.1016/S0140-6736(20)30183-5"),
            ("arxiv", "1706.03762"),
            ("isbn", "9780262035613"),
            ("pmid", "34265844"),
            ("url", "https://example.org/page"),
        ])

    def test_arxiv_url_is_not_double_counted(self):
        self.assertEqual(self.kinds("https://arxiv.org/abs/2106.09685"), [("arxiv", "2106.09685")])

    def test_duplicates_collapse(self):
        self.assertEqual(len(extract("doi:10.1234/abc and again DOI:10.1234/ABC")), 1)

    def test_bare_references_only_in_lists_or_reference_sections(self):
        prose = "In 2021 many people wrote many things about many topics."
        refs = "## References\nSmith, J. (2020). A study of things. Journal of Stuff, 3, 1-9."
        self.assertEqual(self.kinds(prose), [])
        self.assertEqual(self.kinds(refs)[0][0], "ref")

    def test_context_spans_wrapped_lines(self):
        c = extract('The book *Deep Learning* is useful\n(ISBN 978-0-262-03561-3).')[0]
        self.assertIn("Deep Learning", c.context)


class Offline(unittest.TestCase):
    def test_isbn(self):
        self.assertIsNone(offline.isbn_problem("9780262035613"))
        self.assertIsNone(offline.isbn_problem("0306406152"))
        self.assertIn("checksum", offline.isbn_problem("9780262035614"))
        self.assertIn("checksum", offline.isbn_problem("0306406153"))

    def test_arxiv(self):
        self.assertIsNone(offline.arxiv_problem("1706.03762", TODAY))
        self.assertIsNone(offline.arxiv_problem("hep-th/9901001", TODAY))
        self.assertIn("month", offline.arxiv_problem("2313.01234", TODAY))
        self.assertIn("future", offline.arxiv_problem("2705.12345", TODAY))
        self.assertIn("5-digit", offline.arxiv_problem("2101.1234", TODAY))
        self.assertIn("2007", offline.arxiv_problem("0612.1234", TODAY))

    def test_future_year_needs_citation_shape(self):
        prose = Citation("doi", "10.1234/x", 1, "Targets for 2030 are set, doi:10.1234/x")
        cited = Citation("doi", "10.1234/x", 1, "Lee (2029). Things. doi:10.1234/x")
        self.assertIsNone(offline.check(prose, TODAY))
        self.assertIn("future", offline.check(cited, TODAY))

    def test_placeholder_url(self):
        self.assertIn("placeholder", offline.url_problem("https://www.example.com/a"))


class Match(unittest.TestCase):
    def test_coverage_ignores_case_accents_and_stopwords(self):
        self.assertEqual(match.coverage("The Évolution of Trust", "evolution of TRUST, 2020"), 1.0)

    def test_short_context_is_not_judged(self):
        self.assertIsNone(match.compare(Record(title="Anything at all"), "doi:10.1234/x"))


class Online(unittest.TestCase):
    def check(self, kind, value, context, routes):
        return check_citation(Citation(kind, value, 1, context), True, fake_get(routes), TODAY)

    def test_doi_verified_and_mismatch(self):
        routes = {"api.crossref.org/works/10.1234/x": crossref("Deep learning", 2015)}
        ok = self.check("doi", "10.1234/x", 'LeCun et al., "Deep learning", Nature 2015', routes)
        bad = self.check("doi", "10.1234/x", '"Quantum gravity for cats and other pets", 2015', routes)
        self.assertEqual(ok.verdict, "verified")
        self.assertEqual(bad.verdict, "mismatch")

    def test_doi_falls_back_to_handle_system(self):
        routes = {"doi.org/api/handles/10.5061/dryad.x": (200, '{"responseCode": 1}')}
        self.assertEqual(self.check("doi", "10.5061/dryad.x", "", routes).verdict, "verified")
        self.assertEqual(self.check("doi", "10.9999/missing", "", {}).verdict, "not_found")

    def test_arxiv_not_found(self):
        feed = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        f = self.check("arxiv", "2101.00001", "", {"export.arxiv.org": (200, feed)})
        self.assertEqual(f.verdict, "not_found")

    def test_url_dead_domain(self):
        f = self.check("url", "https://made-up.org/x", "", {"made-up.org": (0, "")})
        self.assertEqual(f.verdict, "not_found")

    def test_bare_reference(self):
        body = json.dumps({"message": {"items": [
            {"title": ["A survey on bias and fairness in machine learning"], "DOI": "10.1145/3457607",
             "issued": {"date-parts": [[2021]]}}]}})
        routes = {"api.crossref.org/works?": (200, body)}
        real = self.check("ref", "Mehrabi, N. (2021). A survey on bias and fairness in machine "
                          "learning. ACM Computing Surveys.", "", routes)
        fake = self.check("ref", "Chen, L. (2022). Quantifying hallucination in clinical "
                          "copilots. J. Med. AI Safety.", "", routes)
        self.assertEqual(real.verdict, "verified")
        self.assertEqual(fake.verdict, "unmatched")

    def test_network_failure_is_unchecked_not_fabricated(self):
        from ghostcite.resolve import Offline as NetDown

        def down(url):
            raise NetDown("could not connect")
        f = check_citation(Citation("doi", "10.1234/x", 1, ""), True, down, TODAY)
        self.assertEqual(f.verdict, "unchecked")


class EndToEnd(unittest.TestCase):
    def test_example_offline(self):
        findings = check_text(EXAMPLE.read_text(), today=TODAY)
        verdicts = {(f.citation.kind, f.verdict) for f in findings}
        self.assertIn(("arxiv", "malformed"), verdicts)
        self.assertIn(("isbn", "malformed"), verdicts)
        self.assertEqual(findings[0].verdict, "malformed")  # worst first

    def test_reports_render(self):
        findings = check_text(EXAMPLE.read_text(), today=TODAY)
        self.assertIn("MALFORMED", report.text(findings, color=False))
        self.assertIn("| Verdict |", report.markdown(findings))
        self.assertEqual(json.loads(report.as_json(findings))["summary"]["total"], len(findings))

    def test_cli_exit_codes(self):
        os.environ["NO_COLOR"] = "1"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([str(EXAMPLE)]), 1)
            self.assertEqual(cli.main([str(EXAMPLE), "--only", "doi,pmid"]), 0)
            self.assertEqual(cli.main([str(EXAMPLE), "--only", "nope"]), 2)


if __name__ == "__main__":
    unittest.main()
