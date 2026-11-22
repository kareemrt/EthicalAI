"""Run with:  python -m unittest discover -s tests"""
import json
import unittest
from pathlib import Path

from candor import scan_html
from candor.cli import main
from candor.dom import Document
from candor.rules import RULES
from candor.visual import contrast, deemphasis, font_px, parse_color

EX = Path(__file__).resolve().parent.parent / "examples"


def rules_hit(html: str) -> set[str]:
    return {f.rule for f in scan_html(html).findings}


class Examples(unittest.TestCase):
    def test_dark_page_triggers_every_rule(self):
        report = scan_html((EX / "checkout_dark.html").read_text())
        self.assertEqual({f.rule for f in report.findings}, {r.id for r in RULES})
        self.assertEqual(report.grade, "F")

    def test_fair_page_is_clean(self):
        report = scan_html((EX / "checkout_fair.html").read_text())
        self.assertEqual(report.findings, [], [f.evidence for f in report.findings])
        self.assertEqual((report.score, report.grade), (100, "A"))


class Rules(unittest.TestCase):
    def test_preselected_consent_vs_unticked(self):
        self.assertIn("preselected-consent", rules_hit(
            '<label><input type="checkbox" checked> Subscribe to our newsletter</label>'))
        self.assertNotIn("preselected-consent", rules_hit(
            '<label><input type="checkbox"> Subscribe to our newsletter</label>'))

    def test_label_for_attribute(self):
        html = '<input type="checkbox" id="m" checked><label for="m">Share my data with partners</label>'
        self.assertIn("preselected-consent", rules_hit(html))

    def test_remember_me_is_not_consent(self):
        self.assertEqual(rules_hit('<label><input type="checkbox" checked> Remember me</label>'), set())

    def test_sneak_into_basket_dropdown(self):
        html = '<select><option>No insurance</option><option selected>Travel insurance +$19</option></select>'
        self.assertIn("sneak-into-basket", rules_hit(html))

    def test_confirmshaming_needs_shame(self):
        self.assertIn("confirmshaming", rules_hit("<a href=#>No thanks, I'd rather stay uninformed</a>"))
        self.assertIn("confirmshaming", rules_hit("<button>No, I don't like saving money</button>"))
        self.assertEqual(rules_hit("<button>No thanks</button>"), set())

    def test_false_urgency(self):
        self.assertIn("false-urgency", rules_hit("<p>Only 2 left in stock!</p>"))
        self.assertIn("false-urgency", rules_hit('<span id="deal-countdown">04:59</span>'))
        self.assertEqual(rules_hit("<p>In stock. Ships in 2 days.</p>"), set())

    def test_hidden_costs_only_when_deemphasised(self):
        self.assertIn("hidden-costs", rules_hit("<small>A booking fee applies.</small>"))
        self.assertEqual(rules_hit("<p>A booking fee of $3 applies.</p>"), set())

    def test_trick_question(self):
        self.assertIn("trick-question", rules_hit(
            "<label><input type=checkbox> Untick this box if you don't want to not hear from us</label>"))

    def test_asymmetric_choice_and_skip_link(self):
        self.assertIn("visual-interference", rules_hit(
            '<button>Accept</button><a style="opacity:.3">Decline</a>'))
        self.assertEqual(rules_hit('<a href="#main" style="display:none">Skip to content</a>'), set())

    def test_asymmetry_is_relative(self):
        # A banner hidden until JavaScript shows it hides both choices equally: not a dark pattern.
        self.assertEqual(rules_hit('<div hidden><button>Accept</button><button>Reject</button></div>'), set())

    def test_cookie_banner(self):
        wall = '<div class="cookie-banner">We use cookies. <button>Accept</button></div>'
        fair = '<div class="cookie-banner">We use cookies. <button>Accept</button><button>Reject</button></div>'
        self.assertIn("cookie-wall", rules_hit(wall))
        self.assertNotIn("cookie-wall", rules_hit(fair))

    def test_disguised_ad(self):
        self.assertIn("disguised-ad", rules_hit('<div class="ad-slot"><p>Great shoes</p></div>'))
        self.assertEqual(rules_hit('<div class="ad-slot"><p>Ad · Great shoes</p></div>'), set())
        self.assertEqual(rules_hit('<div class="header"><p>Welcome</p></div>'), set())
        self.assertEqual(rules_hit('<div class="ad-slot"></div>'), set())  # filled by JS later


class Visual(unittest.TestCase):
    def test_colors_and_contrast(self):
        self.assertEqual(parse_color("#fff"), (255, 255, 255))
        self.assertEqual(parse_color("rgb(10, 20, 30)"), (10, 20, 30))
        self.assertAlmostEqual(contrast((0, 0, 0), (255, 255, 255)), 21, places=0)

    def test_font_units(self):
        self.assertEqual(font_px("12pt"), 16)
        self.assertEqual(font_px("0.625rem"), 10)

    def test_stylesheet_classes_resolve(self):
        doc = Document('<style>.tiny{font-size:9px}</style><p class="tiny">x</p>')
        self.assertIn("tiny text", deemphasis(doc, doc.find("p")[0]))

    def test_inherited_from_parent(self):
        doc = Document('<div style="color:#eee"><span>faint</span></div>')
        self.assertIn("low contrast", deemphasis(doc, doc.find("span")[0]))


class Robustness(unittest.TestCase):
    def test_malformed_html_does_not_crash(self):
        scan_html("<div><p>unclosed <b>tags <input type=checkbox checked>newsletter</div></i>")

    def test_scripts_are_ignored(self):
        self.assertEqual(rules_hit("<script>var s='Only 2 left!'</script>"), set())


class CLI(unittest.TestCase):
    def test_fail_on_exit_codes(self):
        self.assertEqual(main([str(EX / "checkout_fair.html"), "--fail-on", "low", "-o", "/dev/null"]), 0)
        self.assertEqual(main([str(EX / "checkout_dark.html"), "--fail-on", "high", "-o", "/dev/null"]), 1)

    def test_missing_file(self):
        self.assertEqual(main(["does-not-exist.html"]), 2)

    def test_json_output(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main([str(EX / "checkout_dark.html"), "-f", "json"])
        data = json.loads(buf.getvalue())
        self.assertEqual(data[0]["grade"], "F")
        self.assertTrue(all({"rule", "severity", "line", "evidence", "why", "fix"} <= f.keys()
                            for f in data[0]["findings"]))


if __name__ == "__main__":
    unittest.main()
