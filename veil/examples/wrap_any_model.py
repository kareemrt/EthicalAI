"""Wrap any chat model so it never sees the raw data.

`ask` is whatever function sends a prompt to your model and returns text —
an SDK call, an HTTP request, a local model. veil doesn't care which.

    python examples/wrap_any_model.py
"""

import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from veil import Veil  # noqa: E402


def private(ask: Callable[[str], str], veil: Veil) -> Callable[[str], str]:
    """Return a drop-in replacement for `ask` that redacts on the way out
    and restores on the way back. Reuse one Veil per conversation so
    placeholders stay stable across turns."""
    def wrapped(prompt: str) -> str:
        return veil.restore(ask(veil.scrub(prompt)))
    return wrapped


def demo_model(prompt: str) -> str:
    """Stand-in for a real model: shows exactly what it received."""
    print("── what the model sees ──────────────────────────")
    print(prompt)
    print("─────────────────────────────────────────────────\n")
    return ("Hi [PERSON_3], sorry about the double charge on card [CREDIT_CARD_1]. "
            "The webhook is failing because the password in the URL is rejected — "
            "rotate [URL_CREDENTIAL_1] and move it out of the URL.")


if __name__ == "__main__":
    ticket = (Path(__file__).parent / "support_ticket.txt").read_text()
    ask = private(demo_model, Veil(terms=["PERSON: Marcus Oyelaran", "PERSON: Marcus",
                                          "PERSON: Dana Whitfield", "ORG: Northwind"]))
    reply = ask(ticket)
    print("── what you get back ────────────────────────────")
    print(reply)
