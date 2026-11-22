"""Link analysis: spot web addresses dressed up to look like ones you trust.

Nothing here touches the network. Every check reads the address itself:
lookalike spellings, brand names tucked into someone else's domain,
link shorteners that hide the destination, and so on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# Brand -> official registrable domains. Extend freely.
BRANDS: dict[str, tuple[str, ...]] = {
    "amazon": ("amazon.com", "amazon.co.uk", "amazon.ca", "amazon.de"),
    "apple": ("apple.com", "icloud.com"),
    "microsoft": ("microsoft.com", "live.com", "outlook.com", "office.com"),
    "google": ("google.com", "gmail.com", "youtube.com"),
    "paypal": ("paypal.com",),
    "netflix": ("netflix.com",),
    "usps": ("usps.com",),
    "ups": ("ups.com",),
    "fedex": ("fedex.com",),
    "dhl": ("dhl.com",),
    "irs": ("irs.gov",),
    "ssa": ("ssa.gov",),
    "medicare": ("medicare.gov",),
    "chase": ("chase.com",),
    "wellsfargo": ("wellsfargo.com",),
    "bankofamerica": ("bankofamerica.com", "bofa.com"),
    "citi": ("citi.com", "citibank.com"),
    "coinbase": ("coinbase.com",),
    "venmo": ("venmo.com",),
    "zelle": ("zellepay.com",),
    "facebook": ("facebook.com", "meta.com"),
    "instagram": ("instagram.com",),
    "whatsapp": ("whatsapp.com",),
    "ezpass": ("e-zpassny.com", "ezpassnj.com", "e-zpassiag.com"),
}

# How a brand might be named in message text (for "claims to be X" checks).
BRAND_MENTIONS: dict[str, re.Pattern] = {
    b: re.compile(p, re.I) for b, p in {
        "amazon": r"\bamazon\b", "apple": r"\b(apple|icloud)\b",
        "microsoft": r"\b(microsoft|windows|outlook)\b", "google": r"\b(google|gmail)\b",
        "paypal": r"\bpaypal\b", "netflix": r"\bnetflix\b", "usps": r"\b(usps|postal service)\b",
        "ups": r"\bups\b", "fedex": r"\bfedex\b", "dhl": r"\bdhl\b",
        "irs": r"\b(irs|internal revenue)\b", "ssa": r"\b(ssa|social security administration)\b",
        "medicare": r"\bmedicare\b", "chase": r"\bchase\b", "wellsfargo": r"\bwells ?fargo\b",
        "bankofamerica": r"\bbank of america\b", "citi": r"\bciti(bank)?\b",
        "coinbase": r"\bcoinbase\b", "venmo": r"\bvenmo\b", "zelle": r"\bzelle\b",
        "facebook": r"\bfacebook\b", "instagram": r"\binstagram\b",
        "whatsapp": r"\bwhatsapp\b", "ezpass": r"\be-?z ?pass\b",
    }.items()
}

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly",
    "rb.gy", "t.ly", "shorturl.at", "rebrand.ly", "tiny.cc", "s.id", "v.gd",
}
# TLDs heavily over-represented in phishing reports (Spamhaus, Interisle).
RISKY_TLDS = {
    "top", "xyz", "zip", "mov", "click", "icu", "cyou", "buzz", "rest", "cfd", "sbs",
    "live", "shop", "online", "site", "info", "vip", "work", "support", "lol", "bond",
}
# Second-level suffixes where the registrable domain is three labels deep.
MULTI_SUFFIXES = {"co.uk", "org.uk", "ac.uk", "com.au", "co.nz", "co.jp", "com.br", "co.in"}

DISPLAY = {"wellsfargo": "Wells Fargo", "bankofamerica": "Bank of America", "ezpass": "E-ZPass",
           "paypal": "PayPal", "fedex": "FedEx"}


def display(brand: str) -> str:
    return DISPLAY.get(brand, brand.upper() if len(brand) <= 4 else brand.title())


HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "7": "t", "@": "a", "$": "s"})

URL_RE = re.compile(
    r"(?:(?:https?://|www\.)[^\s<>\"')\]]+)|"
    r"(?:(?<![@\w.-])(?:[a-z0-9-]+\.)+(?:com|net|org|gov|co|us|uk|io|info|"
    + "|".join(sorted(RISKY_TLDS)) +
    r")(?:/[^\s<>\"')\]]*)?)", re.I)


@dataclass(frozen=True)
class LinkFinding:
    url: str
    host: str
    id: str
    weight: float
    title: str
    why: str


def extract_urls(text: str) -> list[str]:
    seen, out = set(), []
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;:!?")
        if url.lower() not in seen:
            seen.add(url.lower())
            out.append(url)
    return out


def host_of(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    netloc = urlsplit(url).netloc.lower()
    return netloc.rsplit("@", 1)[-1].split(":")[0]


def registrable(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _official(domain: str) -> str | None:
    for brand, domains in BRANDS.items():
        if domain in domains:
            return brand
    return None


def analyze_url(url: str) -> list[LinkFinding]:
    host = host_of(url)
    if not host:
        return []
    reg = registrable(host)
    label = reg.split(".")[0]
    tld = host.rsplit(".", 1)[-1]
    out: list[LinkFinding] = []

    def add(id, weight, title, why):
        out.append(LinkFinding(url, host, id, weight, title, why))

    if _official(reg):
        return out  # a real brand domain: nothing to flag

    if re.fullmatch(r"[\d.]+", host):
        add("link_ip", 0.7, "Link goes to a raw number address",
            "Real companies use names, not bare IP numbers, for their websites.")
    if "xn--" in host:
        add("link_punycode", 0.6, "Link uses disguised characters",
            "Foreign look-alike letters can make a fake address look identical to a real one.")
    if "@" in urlsplit(url if "://" in url else "http://" + url).netloc:
        add("link_at", 0.6, "Link hides its real destination after an '@'",
            "Everything before the '@' is ignored by your browser; it's there to fool you.")
    if reg in SHORTENERS:
        add("link_short", 0.35, "Shortened link hides where it goes",
            "Shorteners are handy, but they also hide a scam site's real address.")
    if tld in RISKY_TLDS:
        add("link_tld", 0.35, f"Unusual web ending '.{tld}'",
            f"Addresses ending in '.{tld}' are cheap and common in phishing campaigns.")

    # Brand name inside someone else's domain: paypal.secure-login.net, usps-track.top
    # (Short brands like "ups" or "irs" only count as whole hyphen/dot-separated words.)
    words = set(re.split(r"[.-]", host))
    for brand in BRANDS:
        if brand in words or (len(brand) >= 5 and brand in host):
            name = display(brand)
            add("link_brand_bait", 0.75, f"Uses the name {name} but isn't {name}'s site",
                f"The real owner of this address is '{reg}', not {name}. "
                "Scammers borrow a trusted name to look official.")
            return out

    # Lookalike spelling: paypa1.com, amaz0n-support.com, rnicrosoft.com, gooogle.com
    for word in words:
        squashed = word.translate(HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
        for brand in BRANDS:
            if squashed == brand or (len(brand) >= 6 and _edit_distance(squashed, brand) == 1):
                add("link_lookalike", 0.85, f"Look-alike of {display(brand)}'s website",
                    f"'{reg}' is spelled to look like {display(brand)}'s real site, but it isn't.")
                return out
    return out


def brand_mismatch(text: str, urls: list[str]) -> list[LinkFinding]:
    """Message names a brand, but none of its links belong to that brand."""
    if not urls:
        return []
    regs = {registrable(host_of(u)) for u in urls}
    out = []
    for brand, pat in BRAND_MENTIONS.items():
        if pat.search(text) and not regs & set(BRANDS[brand]):
            stranger = sorted(regs)[0]
            out.append(LinkFinding(stranger, stranger, "brand_mismatch", 0.6,
                                   f"Claims to be {display(brand)} but links elsewhere",
                                   f"The message mentions {display(brand)}, yet its link "
                                   f"goes to '{stranger}'."))
            break
    return out
