import contextlib
import io
import pathlib
import unittest

from tether import Source, check, SUPPORTED, WEAK, UNSUPPORTED, SKIPPED
from tether import text
from tether.cli import main, load_sources
from tether.report import to_html, to_json, terminal

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ["The bridge opened in 1932 and carries 48,000 vehicles a day.",
           "Boiling water does not remove lead. Filters certified for lead reduction help."]


def one(answer, sources=SOURCES):
    return check(answer, sources).claims[0]


class TextTests(unittest.TestCase):
    def test_sentences_respect_abbreviations_and_decimals(self):
        s = "Dr. Lee measured 3.5 mg, e.g. in tap water. It was high! Was it? Yes."
        got = [s[a:b] for a, b in text.sentence_spans(s)]
        self.assertEqual(got, ["Dr. Lee measured 3.5 mg, e.g. in tap water.", "It was high!", "Was it?", "Yes."])

    def test_list_items_and_trailing_citations(self):
        s = "- First claim here.[1] Second one [2].\n1. Third item"
        got = [s[a:b] for a, b in text.sentence_spans(s)]
        self.assertEqual(got, ["First claim here.[1]", "Second one [2].", "Third item"])

    def test_citations(self):
        self.assertEqual(text.citations("x [1] y [2, 4] z [5-6]"), [1, 2, 4, 5, 6])

    def test_numbers_are_canonical(self):
        self.assertEqual(text.numbers("18,412 lines, 70.0% and 2.50 [3]"), {"18412", "70", "2.5"})


class CheckTests(unittest.TestCase):
    def test_supported(self):
        c = one("The bridge opened in 1932 [1].")
        self.assertEqual(c.verdict, SUPPORTED)
        self.assertEqual(c.flags, [])

    def test_invented_number(self):
        c = one("The bridge carries 84,000 vehicles a day.")
        self.assertEqual(c.verdict, UNSUPPORTED)
        self.assertIn("number 84000 not found in any source", c.flags)

    def test_fabricated_quote(self):
        c = one('Officials said the bridge "will stand for a thousand years".')
        self.assertEqual(c.verdict, UNSUPPORTED)
        self.assertTrue(any(f.startswith("quote not found") for f in c.flags))

    def test_real_quote_passes(self):
        c = one('The advisory says "boiling water does not remove lead" [2].')
        self.assertFalse(any(f.startswith("quote") for f in c.flags))

    def test_contradiction(self):
        c = one("Boiling water removes lead [2].")
        self.assertEqual(c.verdict, UNSUPPORTED)
        self.assertTrue(c.flags[0].startswith("contradicts [2]"))

    def test_miscitation(self):
        c = one("The bridge opened in 1932 [2].")
        self.assertEqual(c.verdict, WEAK)
        self.assertTrue(any(f.startswith("miscited") for f in c.flags))

    def test_missing_source(self):
        c = one("The bridge opened in 1932 [7].")
        self.assertEqual(c.verdict, WEAK)

    def test_unrelated_claim(self):
        self.assertEqual(one("Penguins migrate across Antarctica every winter.").verdict, UNSUPPORTED)

    def test_headers_and_questions_are_skipped(self):
        r = check("Here is a summary:\nWhy does it matter?", SOURCES)
        self.assertTrue(all(c.verdict == SKIPPED for c in r.claims))
        self.assertEqual(r.groundedness, 1.0)


class ExampleTests(unittest.TestCase):
    def setUp(self):
        self.report = check((ROOT / "examples/answer.txt").read_text(),
                            load_sources([ROOT / "examples/sources"]))

    def test_example_verdicts(self):
        got = [c.verdict for c in self.report.claims]
        self.assertEqual(got, [SKIPPED, SUPPORTED, SUPPORTED, UNSUPPORTED, WEAK, UNSUPPORTED,
                               UNSUPPORTED, SUPPORTED, WEAK, UNSUPPORTED])

    def test_renderers(self):
        self.assertIn('"groundedness": 0.333', to_json(self.report))
        self.assertIn("Groundedness 33%", terminal(self.report, color=False))
        page = to_html(self.report)
        self.assertIn('class="unsupported"', page)
        self.assertNotIn("<script", page)

    def test_cli_exit_code(self):
        args = [str(ROOT / "examples/answer.txt"), str(ROOT / "examples/sources"), "--no-color"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args + ["--fail-under", "0.8"]), 1)


if __name__ == "__main__":
    unittest.main()
