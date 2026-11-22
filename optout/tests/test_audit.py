import json
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path

from optout import audit, cli, generate, report, signals
from optout.agents import AGENTS, ANSWER, SEARCH, TRAINING, USER
from optout.site import LocalSite, Page, WebSite

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class Examples(unittest.TestCase):
    def test_grades(self):
        grades = {d: audit.run(LocalSite(EXAMPLES / d)).grade for d in ("unprotected", "partial", "protected")}
        self.assertEqual(grades, {"unprotected": "F", "partial": "D", "protected": "A"})

    def test_partial_flags_blocked_search_engine(self):
        problems = audit.run(LocalSite(EXAMPLES / "partial")).problems
        self.assertTrue(any("Bingbot" in p for p in problems))

    def test_json_is_valid_and_complete(self):
        data = json.loads(report.as_json(audit.run(LocalSite(EXAMPLES / "protected"))))
        self.assertEqual(data["grade"], "A")
        self.assertEqual(len(data["verdicts"]), len(AGENTS))


class Generate(unittest.TestCase):
    def test_generated_rules_block_exactly_what_was_asked(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "robots.txt").write_text(generate.robots_txt([TRAINING]))
            result = audit.run(LocalSite(d))
        self.assertEqual(result.open(TRAINING), [])
        for cat in (ANSWER, USER, SEARCH):
            self.assertEqual(len(result.open(cat)), len(result.of(cat)))

    def test_refuses_search_and_unknown(self):
        for bad in ([SEARCH], ["nonsense"]):
            with self.assertRaises(ValueError):
                generate.robots_txt(bad)

    def test_tdmrep_round_trip(self):
        sig = signals.tdmrep(Page(200, generate.tdmrep_json("https://x/p")), Page(404))
        self.assertTrue(sig.present)
        self.assertIn("https://x/p", sig.detail)


class Signals(unittest.TestCase):
    def test_tdmrep_from_header_and_meta(self):
        self.assertTrue(signals.tdmrep(Page(404), Page(200, "", {"tdm-reservation": "1"})).present)
        meta = '<meta name="TDM-Reservation" content="1">'
        self.assertTrue(signals.tdmrep(Page(404), Page(200, meta)).present)
        self.assertFalse(signals.tdmrep(Page(200, "{oops"), Page(200)).present)

    def test_noai_tokens_not_substrings(self):
        self.assertTrue(signals.noai(Page(200, '<meta name="robots" content="index, noimageai">')).present)
        self.assertFalse(signals.noai(Page(200, '<meta name="robots" content="noaixyz">')).present)
        self.assertTrue(signals.noai(Page(200, "", {"x-robots-tag": "noai"})).present)


class _Handler(BaseHTTPRequestHandler):
    routes = {}

    def do_GET(self):
        status, body = self.routes.get(self.path, (404, ""))
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


class Web(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_live_site(self):
        _Handler.routes = {"/robots.txt": (200, "User-agent: GPTBot\nDisallow: /\n"), "/": (200, "<h1>hi</h1>")}
        result = audit.run(WebSite(self.url))
        self.assertEqual(len(result.open(TRAINING)), len(result.of(TRAINING)) - 1)

    def test_missing_robots_allows_all_and_5xx_disallows_all(self):
        _Handler.routes = {}
        self.assertEqual(audit.run(WebSite(self.url)).open(TRAINING), audit.run(WebSite(self.url)).of(TRAINING))
        _Handler.routes = {"/robots.txt": (503, "")}
        self.assertEqual(audit.run(WebSite(self.url)).open(TRAINING), [])

    def test_cli_strict_exit_code(self):
        _Handler.routes = {}
        with redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["check", self.url, "--strict"]), 1)
            self.assertEqual(cli.main(["check", str(EXAMPLES / "protected"), "--strict"]), 0)


if __name__ == "__main__":
    unittest.main()
