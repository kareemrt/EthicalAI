"""Run with:  python -m unittest discover -s tests"""

import doctest
import io
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from veil import Vault, Veil  # noqa: E402
from veil.cli import main  # noqa: E402
from veil.detectors import iban, luhn  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def labels(text, **kw):
    return [(f.label, f.value) for f in Veil(**kw).scan(text)]


class Detects(unittest.TestCase):
    """Things that must be caught."""

    cases = {
        "EMAIL":          "write to jane.doe+billing@example.co.uk today",
        "PHONE":          "call +1 (415) 555-0132 after 5",
        "CREDIT_CARD":    "card 4111-1111-1111-1111 expired",
        "IBAN":           "pay DE89 3704 0044 0532 0130 00 please",
        "SSN":            "ssn 078-05-1120 on file",
        "IP_ADDRESS":     "origin 203.0.113.42 blocked",
        "AWS_KEY":        "key AKIAIOSFODNN7EXAMPLE leaked",
        "GITHUB_TOKEN":   "token ghp_" + "a1B2c3D4" * 5 + " in .env",
        "JWT":            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
        "SECRET":         'db_password: "S3cure!Pass"',
        "URL_CREDENTIAL": "postgres://admin:pa55word@db.internal:5432/app",
        "PRIVATE_KEY":    "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n-----END RSA PRIVATE KEY-----",
        "HIGH_ENTROPY":   "X-Internal-Key: Zx8Qp2Lm7Rt4Vw9Ks3Nd6Hy1Bf5Gc0Ja",
    }

    def test_each_label(self):
        for label, text in self.cases.items():
            with self.subTest(label=label):
                self.assertIn(label, [lb for lb, _ in labels(text)], text)

    def test_secret_redacts_value_only(self):
        self.assertEqual(Veil().scrub('password = "hunter2-prod"'), 'password = "[SECRET_1]"')


class Ignores(unittest.TestCase):
    """Things that look numeric or random but identify nobody."""

    benign = [
        "Deployed 2026-11-22 14:32:07 UTC",
        "version 1.2.3 build 4521",
        "commit 3f9a2c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39",
        "request 550e8400-e29b-41d4-a716-446655440000",
        "order 1234 5678 shipped",
        "card 4111 1111 1111 1112",           # fails Luhn
        "ssn 000-12-3456",                     # invalid area number
        "listening on 127.0.0.1:8080",
        "the quick brown fox jumps over the lazy dog",
        "camelCaseIdentifierNameIsQuiteLong",
    ]

    def test_no_false_positives(self):
        for text in self.benign:
            with self.subTest(text=text):
                self.assertEqual(labels(text), [])


class Validators(unittest.TestCase):
    def test_luhn(self):
        self.assertTrue(luhn("4111111111111111"))
        self.assertFalse(luhn("4111111111111112"))
        self.assertFalse(luhn("0000000000000000"))

    def test_iban(self):
        self.assertTrue(iban("GB82 WEST 1234 5698 7654 32"))
        self.assertFalse(iban("GB82 WEST 1234 5698 7654 33"))


class RoundTrip(unittest.TestCase):
    def test_scrub_then_restore_is_lossless(self):
        text = (EXAMPLES / "support_ticket.txt").read_text()
        v = Veil(terms=["PERSON: Marcus Oyelaran", "PERSON: Dana Whitfield"])
        safe = v.scrub(text)
        self.assertNotIn("4111", safe)
        self.assertNotIn("AKIA", safe)
        self.assertEqual(v.restore(safe), text)

    def test_same_value_same_placeholder(self):
        v = Veil()
        self.assertEqual(v.scrub("a@x.io, A@X.io, b@x.io"), "[EMAIL_1], [EMAIL_1], [EMAIL_2]")

    def test_restore_tolerates_model_reformatting(self):
        v = Veil()
        v.scrub("mail a@x.io")
        self.assertEqual(v.restore("Sent to [ email_1 ]."), "Sent to a@x.io.")

    def test_unknown_placeholder_left_alone(self):
        self.assertEqual(Veil().restore("see [EMAIL_9]"), "see [EMAIL_9]")

    def test_terms_are_whole_word_and_case_insensitive(self):
        v = Veil(terms=["ORG: Acme"])
        self.assertEqual(v.scrub("ACME and acme, not Acmeville"), "[ORG_1] and [ORG_1], not Acmeville")

    def test_term_never_splits_an_email(self):
        self.assertEqual(Veil(terms=["acme"]).scrub("ops@acme.com"), "[EMAIL_1]")

    def test_only_and_skip(self):
        text = "a@x.io 203.0.113.42"
        self.assertEqual(labels(text, only=["email"]), [("EMAIL", "a@x.io")])
        self.assertEqual(labels(text, skip=["EMAIL"]), [("IP_ADDRESS", "203.0.113.42")])


class VaultFile(unittest.TestCase):
    def test_persisted_owner_only_and_reusable(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "vault.json"
            v1 = Veil()
            v1.scrub("a@x.io")
            v1.vault.save(path)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            v2 = Veil(vault=Vault.load(path))
            self.assertEqual(v2.scrub("b@x.io then a@x.io"), "[EMAIL_2] then [EMAIL_1]")


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = main(list(argv))
        return code, out.getvalue()

    def test_scan_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            clean, dirty = Path(d) / "c.txt", Path(d) / "d.txt"
            clean.write_text("nothing to see")
            dirty.write_text("mail a@x.io")
            self.assertEqual(self.run_cli("scan", str(clean))[0], 0)
            self.assertEqual(self.run_cli("scan", str(dirty))[0], 1)

    def test_scrub_restore_files(self):
        with tempfile.TemporaryDirectory() as d:
            src, safe, back, vault = (Path(d) / n for n in ("in.txt", "safe.txt", "out.txt", "v.json"))
            src.write_text("card 4111 1111 1111 1111")
            self.run_cli("scrub", str(src), "-o", str(safe), "-v", str(vault), "-q")
            self.assertEqual(safe.read_text(), "card [CREDIT_CARD_1]")
            self.run_cli("restore", str(safe), "-o", str(back), "-v", str(vault))
            self.assertEqual(back.read_text(), src.read_text())


def load_tests(loader, tests, _pattern):
    import veil.core
    tests.addTests(doctest.DocTestSuite(veil.core))   # README-style examples stay true
    return tests


if __name__ == "__main__":
    unittest.main()
