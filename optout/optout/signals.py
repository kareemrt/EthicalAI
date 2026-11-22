"""Opt-out signals beyond robots.txt.

  * TDMRep  — W3C Community Group protocol for the EU DSM Directive Art. 4(3)
              "machine-readable" text-and-data-mining reservation. The EU AI Act
              requires general-purpose AI providers to honour such reservations.
              Looked for in /.well-known/tdmrep.json, a `tdm-reservation` HTTP
              header, and a <meta name="tdm-reservation"> tag.
  * noai    — informal `noai` / `noimageai` directives in <meta name="robots">
              or the X-Robots-Tag header (popularised by art platforms).
"""

import json
from dataclasses import dataclass
from html.parser import HTMLParser

from .site import Page


@dataclass
class Signal:
    name: str
    present: bool
    detail: str


class _Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            if a.get("name"):
                prev = self.tags.get(a["name"].lower())
                val = (a.get("content") or "").lower()
                self.tags[a["name"].lower()] = f"{prev}, {val}" if prev else val


def meta_tags(html: str) -> dict[str, str]:
    p = _Meta()
    try:
        p.feed(html)
    except Exception:  # malformed HTML should never crash an audit
        pass
    return p.tags


def tdmrep(well_known: Page, home: Page, path: str = "/") -> Signal:
    name = "TDMRep (EU DSM Art. 4 reservation)"
    if well_known.ok:
        try:
            for entry in json.loads(well_known.body):
                loc = str(entry.get("location", ""))
                covers = loc in ("/*", "*", "/") or path.startswith(loc.rstrip("*"))
                if covers and str(entry.get("tdm-reservation")) == "1":
                    policy = entry.get("tdm-policy")
                    return Signal(name, True, f"tdmrep.json reserves {loc}" + (f", policy {policy}" if policy else ""))
        except (ValueError, AttributeError, TypeError):
            return Signal(name, False, "/.well-known/tdmrep.json is not valid TDMRep JSON")
    if home.headers.get("tdm-reservation", "").strip() == "1":
        return Signal(name, True, "tdm-reservation: 1 HTTP header")
    if meta_tags(home.body).get("tdm-reservation", "").strip() == "1":
        return Signal(name, True, '<meta name="tdm-reservation" content="1">')
    return Signal(name, False, "no tdmrep.json, header, or meta tag")


def noai(home: Page) -> Signal:
    name = "noai / noimageai directives"
    sources = {"X-Robots-Tag": home.headers.get("x-robots-tag", ""),
               "meta robots": meta_tags(home.body).get("robots", "")}
    found = []
    for src, val in sources.items():
        hits = [d for d in ("noai", "noimageai") if d in _tokens(val)]
        if hits:
            found.append(f"{src}: {', '.join(hits)}")
    return Signal(name, bool(found), "; ".join(found) or "not set (informal, few crawlers honour it)")


def _tokens(value: str) -> set[str]:
    return {t.strip().lower() for t in value.replace(";", ",").split(",")}
