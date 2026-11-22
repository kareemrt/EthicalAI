import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from secondlook import check
from secondlook.cli import main, render
from secondlook.evaluate import evaluate
from secondlook.links import analyze_url, extract_urls, registrable

ROOT = Path(__file__).resolve().parent.parent


def ids(text):
    return {f.id for f in check(text).flags}


class Signals(unittest.TestCase):
    def test_gift_card_payment(self):
        self.assertIn("pay_giftcard", ids("Pay the fine today with Google Play gift cards."))

    def test_secrecy(self):
        self.assertIn("secrecy", ids("Please don't tell your family about this."))

    def test_code_request_flagged(self):
        self.assertIn("ask_code", ids("Read me back the code we sent you to cancel the charge."))

    def test_legit_2fa_not_flagged(self):
        r = check("Your code is 123456. Never share this code with anyone.")
        self.assertEqual(r.level, "low")

    def test_urgency_alone_is_not_a_scam(self):
        self.assertEqual(check("Last chance! Sale ends tonight.").level, "low")

    def test_plain_message_is_clean(self):
        r = check("See you at the park at noon?")
        self.assertEqual((r.level, r.flags), ("low", []))


class Links(unittest.TestCase):
    def test_extracts_bare_and_full_urls(self):
        urls = extract_urls("go to usps-track.top/x or https://a.com/b, thanks. email me@a.com")
        self.assertEqual(urls, ["usps-track.top/x", "https://a.com/b"])

    def test_registrable_handles_multi_suffix(self):
        self.assertEqual(registrable("login.amazon.co.uk"), "amazon.co.uk")
        self.assertEqual(registrable("paypal.com.evil.net"), "evil.net")

    def test_official_domains_are_trusted(self):
        self.assertEqual(analyze_url("https://www.paypal.com/activity"), [])
        self.assertEqual(analyze_url("https://tools.usps.com/go"), [])

    def test_lookalike(self):
        for url in ("paypa1.com", "amaz0n-support.com", "rnicrosoft.com", "gooogle.com"):
            self.assertIn("link_lookalike", {f.id for f in analyze_url(url)}, url)

    def test_brand_bait(self):
        self.assertIn("link_brand_bait", {f.id for f in analyze_url("paypal.com.secure-id.net")})
        self.assertIn("link_brand_bait", {f.id for f in analyze_url("usps-redelivery.top")})

    def test_short_brand_needs_whole_word(self):
        # "ups" inside "groups" must not trip the UPS rule
        self.assertNotIn("link_brand_bait", {f.id for f in analyze_url("mygroups.org")})

    def test_ip_and_shortener(self):
        self.assertIn("link_ip", {f.id for f in analyze_url("http://10.0.0.5/login")})
        self.assertIn("link_short", {f.id for f in analyze_url("https://bit.ly/abc")})

    def test_brand_mismatch(self):
        self.assertIn("brand_mismatch", ids("Netflix: update billing at https://renew-now.com"))


class Scoring(unittest.TestCase):
    def test_same_category_counts_once(self):
        once = check("Act now.").risk
        many = check("Act now! Urgent! Immediately! ASAP!").risk
        self.assertAlmostEqual(once, many)

    def test_flags_combine_and_stay_below_one(self):
        r = check("IRS: warrant issued. Pay with gift cards now. Don't tell anyone. "
                  "Install AnyDesk. http://irs-gov.top")
        self.assertEqual(r.level, "high")
        self.assertLess(r.risk, 1.0)

    def test_report_is_json_serialisable(self):
        json.dumps(check("hello").to_dict())


class Corpus(unittest.TestCase):
    def test_tuning_corpus(self):
        m = evaluate(ROOT / "examples" / "corpus.jsonl")
        self.assertGreaterEqual(m["recall"], 0.95)
        self.assertGreaterEqual(m["precision"], 0.95)

    def test_holdout_has_no_false_alarms(self):
        self.assertEqual(evaluate(ROOT / "examples" / "holdout.jsonl")["fp"], 0)


class Interfaces(unittest.TestCase):
    def test_cli_exit_codes(self):
        self.assertEqual(main(["hi, lunch tomorrow?"]), 0)
        self.assertEqual(main(["Buy gift cards and read me the numbers, urgent, don't tell anyone"]), 3)

    def test_render_without_color(self):
        out = render(check("Pay with Bitcoin now"), color=False)
        self.assertIn("What to do", out)
        self.assertNotIn("\033[", out)

    def test_web_api(self):
        from secondlook.web import Handler
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_port}"
            self.assertIn(b"Second Look", urllib.request.urlopen(base).read())
            req = urllib.request.Request(base + "/api/check", method="POST",
                                         data=json.dumps({"message": "Send Bitcoin now"}).encode())
            body = json.loads(urllib.request.urlopen(req).read())
            self.assertIn("pay_crypto", {f["id"] for f in body["flags"]})
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
