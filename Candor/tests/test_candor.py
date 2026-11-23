"""Run with: python -m unittest discover -s tests"""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from candor import scan
from candor.cli import main
from candor.page import Page
from candor.report import FORMATS
from candor.rules import RULES

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def ids(html):
    return [f.rule.id for f in scan(html).findings]


class ParserTest(unittest.TestCase):
    def test_inherited_flags_and_skipped_content(self):
        p = Page('<div style="display:none"><p>a</p></div><small><span>b</span></small>'
                 '<script>var x = "<p>no</p>"</script><svg><path></path><text>no</text></svg><p>c</p>')
        by_text = {e.text: e for e in p.elements}
        self.assertTrue(by_text["a"].hidden)
        self.assertTrue(by_text["b"].fine)
        self.assertNotIn("no", p.root.text)
        self.assertEqual(p.root.text, "a b c")

    def test_unclosed_paragraphs_and_labels(self):
        p = Page('<p>one<p>two<input type="checkbox" id="x"><label for="x">Tick</label>')
        self.assertEqual([e.text for e in p.elements if e.tag == "p"], ["one", "two Tick"])
        self.assertEqual(p.label_for(p.checkboxes[0]), "Tick")

    def test_faint_and_tiny_text(self):
        p = Page('<i style="font-size:9px">a</i><i style="color:#ddd">b</i>'
                 '<i style="font-size:14px;color:#333">c</i><i style="background-color:#eee">d</i>')
        self.assertEqual([e.fine for e in p.elements], [True, True, False, False])


class RuleTest(unittest.TestCase):
    """One positive and at least one honest look-alike per rule."""

    cases = {
        "CD01": ('<label><input type="checkbox" checked> Email me special deals</label>',
                 ['<label><input type="checkbox"> Email me special deals</label>',
                  '<label><input type="checkbox" checked> Remember me</label>']),
        "CD02": ('<label><input type="checkbox" checked> Add travel insurance (+£12)</label>',
                 ['<label><input type="checkbox"> Add travel insurance (+£12)</label>']),
        "CD03": ('<p>$29 per night, resort fee added at checkout</p>',
                 ['<p>$41 per night, all fees included</p>']),
        "CD04": ('<button>Free trial</button><small>Then automatically billed $20/month</small>',
                 ['<p>Free for 7 days, then automatically billed $20/month.</p>']),
        "CD05": ('<p>To cancel your subscription, please call 0800 123 456.</p>',
                 ['<p>Cancel anytime online in your account settings.</p>']),
        "CD06": ('<div class="countdown">04:59</div>',
                 ['<p>Sale ends 31 May 2026.</p>', '<p class="time">Opening hours 09:00</p>']),
        "CD07": ('<p>Only 2 left in stock!</p>', ['<p>In stock</p>']),
        "CD08": ('<div>Someone in Berlin just purchased this jacket</div>',
                 ['<p>Ships from Berlin.</p>']),
        "CD09": ('<a href="#">No thanks, I hate saving money</a>',
                 ['<a href="#">No thanks</a>', '<button>No, cancel</button>']),
        "CD10": ('<div>We use cookies. <button>Accept</button> <a href="#">Settings</a></div>',
                 ['<div>We use cookies. <button>Accept all</button> <button>Reject all</button></div>',
                  '<div><button>OK</button></div>']),
        "CD11": ('<label><input type="checkbox"> Untick this box if you would not like to not hear from us</label>',
                 ['<label><input type="checkbox"> Send me news by email</label>']),
    }

    def test_every_rule_has_cases(self):
        self.assertEqual(set(self.cases), {r.id for r in RULES})

    def test_positive_and_negative(self):
        for rid, (bad, goods) in self.cases.items():
            with self.subTest(rule=rid):
                self.assertIn(rid, ids(bad))
                for good in goods:
                    self.assertNotIn(rid, ids(good), good)

    def test_reject_as_fine_print_link_is_asymmetric(self):
        html = ('<div>Cookies help us. <button>Accept all</button>'
                '<a href="#" style="font-size:10px">Reject</a></div>')
        self.assertEqual(ids(html), ["CD10"])

    def test_hidden_text_is_ignored_except_for_renewal_terms(self):
        self.assertEqual(ids('<p hidden>Only 1 left!</p>'), [])
        self.assertEqual(ids('<p hidden>Your plan renews automatically.</p>'), ["CD04"])


class ExampleTest(unittest.TestCase):
    def test_dark_page_triggers_every_rule(self):
        r = scan((EXAMPLES / "dark-checkout.html").read_text())
        self.assertEqual({f.rule.id for f in r.findings}, {x.id for x in RULES})
        self.assertEqual(r.grade, "F")

    def test_fair_page_is_clean(self):
        r = scan((EXAMPLES / "fair-checkout.html").read_text())
        self.assertEqual(r.findings, [])
        self.assertEqual((r.score, r.grade), (100, "A"))

    def test_all_formats_render(self):
        reports = [scan((EXAMPLES / n).read_text(), n) for n in ("dark-checkout.html", "fair-checkout.html")]
        for name, render in FORMATS.items():
            with self.subTest(fmt=name):
                self.assertIn("dark-checkout.html", render(reports))
        self.assertEqual(json.loads(FORMATS["json"](reports))["reports"][1]["score"], 100)


class CliTest(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue()

    def test_exit_codes(self):
        dark, fair = str(EXAMPLES / "dark-checkout.html"), str(EXAMPLES / "fair-checkout.html")
        self.assertEqual(self.run_cli(dark)[0], 1)
        self.assertEqual(self.run_cli(dark, "--fail-on", "never")[0], 0)
        self.assertEqual(self.run_cli(fair, "--fail-on", "low")[0], 0)
        self.assertEqual(self.run_cli(dark, "--only", "cd07", "--fail-on", "medium")[0], 0)
        self.assertEqual(self.run_cli("does-not-exist.html")[0], 2)

    def test_folder_scan_and_rule_list(self):
        code, out = self.run_cli(str(EXAMPLES), "-f", "md", "--fail-on", "never")
        self.assertEqual((code, out.count("## `")), (0, 2))
        self.assertEqual(self.run_cli("--rules")[1].count("\n"), len(RULES))


if __name__ == "__main__":
    unittest.main()
