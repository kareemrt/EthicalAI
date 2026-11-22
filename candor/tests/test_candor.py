import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from candor import PATTERNS, scan_paths, scan_text
from candor.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def ids(source, kind=None):
    return {f.pattern.id for f in scan_text(source, kind=kind).findings}


class TextPatterns(unittest.TestCase):
    POSITIVE = {
        "confirmshaming": "No thanks, I don't want to save money",
        "false_urgency": "Hurry, this deal ends soon",
        "false_scarcity": "Only 2 left in stock!",
        "activity_notice": "14 people are viewing this hotel",
        "drip_pricing": "Price shown plus taxes and fees",
        "forced_continuity": "You will be billed $9.99 monthly unless you cancel.",
        "obstruction": "To cancel, you must call 1-800-555-0100.",
        "sneak_into_basket": "We've added travel insurance ($14.99) to your booking.",
        "trick_question": "Untick the box if you want to stop emails",
        "implied_consent": "By using this site you agree to our tracking.",
        "nagging": "Maybe later",
        "asterisk_claim": "Shipping is FREE*",
    }
    NEGATIVE = [
        "No thanks",
        "Cancel anytime in Settings, it takes two clicks.",
        "Total: $42.00, tax included. No service fees.",
        "We added dark mode to the app.",
        "Our team has 12 people working on accessibility.",
        "Start free trial, then $17.99/month",
    ]

    def test_every_text_pattern_has_a_positive_case(self):
        text_ids = {p.id for p in PATTERNS if p.regexes}
        self.assertEqual(text_ids, set(self.POSITIVE))

    def test_positive_cases(self):
        for pid, text in self.POSITIVE.items():
            with self.subTest(pid):
                self.assertIn(pid, ids(text, "text"))

    def test_negative_cases(self):
        for text in self.NEGATIVE:
            with self.subTest(text):
                self.assertEqual(ids(text, "text"), set())

    def test_curly_quotes_are_normalised(self):
        self.assertIn("confirmshaming", ids("No thanks, I don’t like saving", "text"))


class Markup(unittest.TestCase):
    def test_prechecked_consent_box(self):
        html = '<label><input type="checkbox" checked> Email me partner offers</label>'
        self.assertIn("preselection", ids(html))

    def test_prechecked_benign_box_is_fine(self):
        html = '<label><input type="checkbox" checked> Remember this device</label>'
        self.assertNotIn("preselection", ids(html))

    def test_countdown_element(self):
        self.assertIn("countdown_timer", ids('<div class="deal-timer">04:59</div>'))

    def test_fine_print(self):
        html = '<p style="font-size:8px">Renews at $29/month.</p>'
        self.assertIn("hidden_terms", ids(html))

    def test_scripts_are_not_scanned(self):
        self.assertEqual(ids("<script>const s = 'Hurry! Only 2 left';</script><p>Hello</p>"), set())

    def test_line_numbers(self):
        result = scan_text("<p>Hi</p>\n\n<p>Hurry up!</p>")
        self.assertEqual(result.findings[0].line, 3)

    def test_ignore_marker(self):
        html = "<!-- candor-ignore: real, audited deadline -->\n<p>Sale ends tonight</p>"
        self.assertEqual(ids(html), set())


class Scoring(unittest.TestCase):
    def test_examples(self):
        report = scan_paths([str(EXAMPLES / "checkout_honest.html")])
        self.assertEqual((report.score, report.grade), (100, "A"))
        report = scan_paths([str(EXAMPLES)])
        self.assertEqual(report.grade, "F")
        self.assertGreaterEqual(report.counts()["high"], 8)

    def test_min_severity_filter(self):
        report = scan_paths([str(EXAMPLES)], min_severity="high")
        self.assertTrue(all(f.pattern.severity == "high" for f in report.findings))


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_fail_under_gates_ci(self):
        code, _ = self.run_cli("scan", str(EXAMPLES / "checkout_deceptive.html"), "--fail-under", "80")
        self.assertEqual(code, 1)
        code, _ = self.run_cli("scan", str(EXAMPLES / "checkout_honest.html"), "--fail-under", "80")
        self.assertEqual(code, 0)

    def test_json_output(self):
        _, out = self.run_cli("scan", str(EXAMPLES), "-f", "json")
        data = json.loads(out)
        self.assertEqual(set(data), {"score", "grade", "counts", "files", "findings"})
        self.assertTrue(all("fix" in f and "refs" in f for f in data["findings"]))

    def test_other_formats_render(self):
        for fmt in ("md", "html", "text"):
            with self.subTest(fmt):
                code, out = self.run_cli("scan", str(EXAMPLES), "-f", fmt, "--no-color")
                self.assertEqual(code, 0)
                self.assertIn("Candor", out)


if __name__ == "__main__":
    unittest.main()
