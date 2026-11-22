import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import redflag
from redflag.cli import cross_validate, holdout, load_data, main
from redflag.model import Model
from redflag.server import make_handler
from redflag.signals import scan


@pytest.mark.parametrize("text, signal", [
    ("Pay with Google Play gift cards", "payment"),
    ("Reply with your verification code", "credentials"),
    ("Visit paypal-secure-login.com now", "risky_link"),
    ("Go to bit.ly/abc123", "risky_link"),
    ("Pay at http://185.23.44.12/dhl", "risky_link"),
    ("Hi Grandma, it's me", "family_emergency"),
    ("Install AnyDesk so we can help", "remote_access"),
    ("Don't tell anyone in the family", "secrecy"),
    ("A warrant will be issued for your arrest", "threat"),
    ("Respond within 24 hours", "urgency"),
])
def test_signal_fires(text, signal):
    assert signal in scan(text)


@pytest.mark.parametrize("text, signal", [
    ("We will never ask for your PIN", "credentials"),
    ("Don't share this code with anyone", "credentials"),
    ("Sign in at paypal.com", "risky_link"),
    ("Your driver is arriving in 3 minutes", "urgency"),
])
def test_signal_stays_quiet(text, signal):
    assert signal not in scan(text)


def test_evidence_spans_point_at_text():
    text = "URGENT: send Target gift cards"
    for hits in scan(text).values():
        for h in hits:
            assert text[h.start:h.end] == h.text


def test_verdicts_on_clear_cases():
    assert redflag.check("IRS final notice: pay today with gift cards or face arrest").level == "danger"
    assert redflag.check("See you at lunch on Saturday!").level == "ok"


def test_report_is_explainable():
    r = redflag.check("Dear customer, verify your password at apple-id-support.xyz immediately")
    d = r.to_dict()
    assert d["flags"] and all(f["advice"] and f["evidence"] for f in d["flags"])
    # risk is exactly the logistic of bias + the weights of fired flags
    import math
    m = Model.load()
    z = m.bias + sum(f.weight for f in r.flags)
    assert r.risk == pytest.approx(1 / (1 + math.exp(-z)))


def test_training_is_deterministic():
    texts, labels = load_data()
    assert Model.train(texts, labels).weights == Model.train(texts, labels).weights


def test_quality_floor():
    m = cross_validate(*load_data())
    assert m["accuracy"] >= 0.85 and m["false_positive_rate"] <= 0.10
    assert holdout(Model.load())["false_positive_rate"] <= 0.10


def test_cli_exit_codes(capsys):
    assert main(["check", "Lunch on Saturday?"]) == 0
    capsys.readouterr()
    assert main(["check", "--json", "Pay the IRS today with gift cards or face arrest"]) == 2
    assert json.loads(capsys.readouterr().out)["level"] == "danger"


def test_server_roundtrip():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Model.load()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}"
        assert b"RedFlag" in urllib.request.urlopen(url).read()
        req = urllib.request.Request(f"{url}/api/check", data=json.dumps({"text": "Send bitcoin now"}).encode())
        body = json.loads(urllib.request.urlopen(req).read())
        assert {"risk", "level", "verdict", "flags"} <= body.keys()
    finally:
        srv.shutdown()
