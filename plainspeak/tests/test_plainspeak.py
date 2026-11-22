"""Run with: python -m unittest discover tests"""
import json
import unittest
from pathlib import Path

from plainspeak import analyze, fix
from plainspeak.checks import find_jargon, find_passive
from plainspeak.cli import main
from plainspeak.report import to_html
from plainspeak.text import sentences, syllables

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
BEFORE = (EXAMPLES / "benefits_notice_before.txt").read_text()
AFTER = (EXAMPLES / "benefits_notice_after.txt").read_text()


class Text(unittest.TestCase):
    def test_syllables(self):
        for word, n in {"the": 1, "notice": 2, "benefit": 3, "determination": 5, "table": 2}.items():
            self.assertEqual(syllables(word), n, word)

    def test_sentences_respect_abbreviations(self):
        s = sentences("Call Dr. Smith at 9 a.m. today. Then send the form.")
        self.assertEqual([x.text for x in s], ["Call Dr. Smith at 9 a.m. today.", "Then send the form."])

    def test_hard_wrapped_lines_join(self):
        s = sentences("Your benefits will\nstop soon.\nCall us.")
        self.assertEqual(len(s), 2)

    def test_offsets_point_into_text(self):
        text = "Hello there.  Second one!"
        for s in sentences(text):
            self.assertEqual(text[s.start:s.end], s.text)


class Checks(unittest.TestCase):
    def test_longest_jargon_phrase_wins(self):
        [f] = find_jargon("We did this in order to help.")
        self.assertEqual((f.text, f.suggestion), ("in order to", "to"))

    def test_proper_names_are_not_jargon(self):
        self.assertEqual(find_jargon("the Supplemental Nutrition Assistance Program"), [])
        self.assertEqual(len(find_jargon("Additional help is here.")), 1)

    def test_passive(self):
        self.assertEqual(len(find_passive("The form was sent by the agency.")), 1)
        self.assertEqual(find_passive("We sent the form. I am interested."), [])


class Scoring(unittest.TestCase):
    def test_plain_beats_bureaucratic(self):
        bad, good = analyze(BEFORE), analyze(AFTER)
        self.assertLess(bad.score, 30)
        self.assertGreaterEqual(good.score, 90)
        self.assertTrue(all(e.ok for e in good.essentials))
        self.assertFalse(next(e for e in bad.essentials if e.key == "contact").ok)

    def test_empty_text(self):
        r = analyze("")
        self.assertEqual(r.readability.words, 0)
        self.assertGreaterEqual(r.score, 0)

    def test_fix_reduces_jargon(self):
        self.assertLess(len(analyze(fix(BEFORE)).of("jargon")), len(analyze(BEFORE).of("jargon")))
        self.assertIn("Nutrition Assistance Program", fix(BEFORE))
        self.assertEqual(fix("We will terminate it."), "We will end it.")


class Output(unittest.TestCase):
    def test_html_escapes_and_highlights(self):
        page = to_html(analyze("<script>x</script> Please utilize this form."))
        self.assertNotIn("<script>x", page)
        self.assertIn('<mark class="jargon"', page)

    def test_cli_fail_under(self):
        f = str(EXAMPLES / "benefits_notice_before.txt")
        self.assertEqual(main([f, "--json", "--fail-under", "50"]), 1)
        self.assertEqual(main([str(EXAMPLES / "benefits_notice_after.txt"), "--json", "--fail-under", "50"]), 0)

    def test_json_shape(self):
        d = analyze(AFTER).to_dict()
        json.dumps(d)
        self.assertEqual(set(d) >= {"score", "grade", "readability", "essentials", "findings"}, True)


if __name__ == "__main__":
    unittest.main()
