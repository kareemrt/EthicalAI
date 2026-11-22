"""Dark-pattern detectors.

Each rule is a plain function `(doc) -> Iterable[Finding]` registered with
`@rule(...)`. Rules are deliberately transparent heuristics: every finding
carries the evidence that triggered it and a concrete fix, so a human makes
the final call.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .dom import Document, Node
from .visual import deemphasis

SEVERITY_WEIGHT = {"high": 20, "medium": 10, "low": 4}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    line: int
    evidence: str
    why: str
    fix: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    severity: str
    summary: str
    reference: str
    check: object


RULES: list[Rule] = []


def rule(id, name, severity, summary, reference):
    def register(fn):
        RULES.append(Rule(id, name, severity, summary, reference, fn))
        return fn
    return register


def rx(*patterns: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I)


# -- shared vocabulary ------------------------------------------------------
CONSENT = rx(r"newsletter", r"marketing", r"promotion", r"special offers?", r"partners?",
             r"third[- ]part(y|ies)", r"share my (data|information|details)",
             r"(emails?|sms|texts?) (about|with|from)", r"personali[sz]ed ads",
             r"subscribe", r"updates (and|&) offers")
ADDON = rx(r"insurance", r"protection( plan)?", r"warranty", r"donat(e|ion)",
           r"priority (handling|support)", r"gift wrap", r"magazine",
           r"carbon offset", r"add[- ]on", r"\+\s*[$€£]\s?\d")
DECLINE = rx(r"\bno,? thanks\b", r"\bno thank you\b", r"^no\b", r"\bi don'?t\b", r"\bi'?d rather\b",
             r"\bi prefer\b", r"\bdecline\b", r"\breject\b", r"\bskip\b", r"\bnot now\b",
             r"\bmaybe later\b", r"\bcontinue without\b", r"\bnot interested\b", r"\bopt out\b")
SHAME = rx(r"don'?t (like|want|care|need) (to )?(sav|deal|discount|money|my|being|free|health|secur)",
           r"rather (pay|stay|miss|lose|remain|be)", r"\bhate\b",
           r"prefer (paying|to pay|missing|to miss|being|losing)",
           r"\b(i'?m|i am) (not|fine) (smart|interested in (sav|deal|better))",
           r"(full|more) price", r"stay (uninformed|broke|unsafe|unprotected)",
           r"miss out", r"(uninformed|unprotected|broke)\b", r"like (paying|wasting|losing)")
ACCEPT = rx(r"\baccept\b", r"\bagree\b", r"\ballow( all)?\b", r"\bgot it\b", r"\bok(ay)?\b",
            r"\byes\b", r"\bcontinue\b", r"\bi understand\b")
PRIMARY = rx(ACCEPT.pattern, r"\b(start|sign ?up|subscribe|buy|get|join|claim|submit|upgrade|order)\b")
SKIP_LINK = rx(r"skip (to|navigation)")  # accessibility links are hidden on purpose


def label_text(doc: Document, node: Node) -> str:
    """Best-effort human label for a form control."""
    if node.id and node.id in doc.labels:
        return doc.labels[node.id].text()
    for a in node.ancestors():
        if a.tag == "label":
            return a.text()
    if node.parent is not None:
        return node.parent.text()[:240]
    return node.attrs.get("aria-label", "")


def controls(doc: Document):
    """Clickable things: buttons, links, submit inputs, role=button."""
    for n in doc.nodes:
        if n.tag in ("button", "a") or n.attrs.get("role") == "button" or (
                n.tag == "input" and n.attrs.get("type") in ("submit", "button", "reset")):
            yield n


# -- rules --------------------------------------------------------------------
@rule("preselected-consent", "Pre-ticked consent", "high",
      "Marketing or data-sharing boxes ticked before the user chooses.",
      "GDPR Art. 4(11) & Recital 32; CJEU Planet49 (C-673/17); FTC Dark Patterns report (2022)")
def preselected_consent(doc):
    for n in doc.find("input"):
        if n.attrs.get("type") in ("checkbox", "radio") and "checked" in n.attrs:
            label = label_text(doc, n)
            if CONSENT.search(label) and not ADDON.search(label):
                yield Finding("preselected-consent", "high", n.line, label[:120],
                              "Consent must be an affirmative act; silence or a pre-ticked box is not consent.",
                              "Remove the `checked` attribute so the user opts in.")


@rule("sneak-into-basket", "Sneak into basket", "high",
      "Paid extras (insurance, donations, warranties) pre-selected at checkout.",
      "EU Consumer Rights Directive Art. 22; FTC Act §5; UK CMA guidance on online choice architecture")
def sneak_into_basket(doc):
    for n in doc.find("input"):
        if n.attrs.get("type") in ("checkbox", "radio") and "checked" in n.attrs:
            label = label_text(doc, n)
            if ADDON.search(label):
                yield Finding("sneak-into-basket", "high", n.line, label[:120],
                              "Extra paid items are added unless the user notices and removes them.",
                              "Leave optional extras unselected and show their price beside the choice.")
    for n in doc.find("option"):
        if "selected" in n.attrs and ADDON.search(n.text()) and not re.search(r"\bno\b|none", n.text(), re.I):
            yield Finding("sneak-into-basket", "high", n.line, n.snippet(),
                          "A paid extra is the default option in a dropdown.",
                          "Make 'None' the default option.")


@rule("confirmshaming", "Confirmshaming", "high",
      "Decline options worded to guilt or shame the user.",
      "FTC Dark Patterns report (2022) §'Confirmshaming'; EU DSA Art. 25")
def confirmshaming(doc):
    seen = set()
    for n in (*controls(doc), *doc.find("label")):
        t = n.text()
        if 3 < len(t) < 160 and DECLINE.search(t) and SHAME.search(t) and t not in seen:
            seen.add(t)
            yield Finding("confirmshaming", "high", n.line, t,
                          "Saying no should not require insulting yourself.",
                          "Use neutral wording such as “No thanks”.")


@rule("false-urgency", "False urgency & scarcity", "medium",
      "Countdown timers, low-stock and 'others are viewing' pressure.",
      "FTC Dark Patterns report (2022); UK CMA Online Choice Architecture (2022); EU UCPD Annex I #7")
def false_urgency(doc):
    pressure = rx(r"only \d+ (left|remaining)", r"\d+ (people|others|users) (are )?(viewing|looking|watching)",
                  r"(offer|deal|sale|price|discount) (ends|expires) (in|soon|today)", r"hurry\b",
                  r"selling (out )?fast", r"almost (gone|sold out)", r"last chance",
                  r"in (high|hot) demand", r"\d+ (bought|sold|booked) in the (last|past)")
    seen = set()
    for n in doc.nodes:
        if re.search(r"countdown|timer|expires?-?in", n.hint()):
            yield Finding("false-urgency", "medium", n.line, n.snippet(),
                          "A countdown timer pressures a decision against the clock.",
                          "Remove the timer unless the deadline is real and the same for everyone.")
            continue
        own = n.own_text()
        if own and (m := pressure.search(own)) and m.group(0).lower() not in seen:
            seen.add(m.group(0).lower())
            yield Finding("false-urgency", "medium", n.line, n.snippet(),
                          "Time or stock pressure discourages comparison. If it is not real, it is deceptive.",
                          "Show urgency only when it is genuine and verifiable, or remove it.")


@rule("hidden-costs", "Hidden costs", "medium",
      "Fees mentioned only in fine print, faded or hidden text.",
      "EU Consumer Rights Directive Art. 6(1)(e); FTC Junk Fees rule (16 CFR 464, 2025)")
def hidden_costs(doc):
    fee = rx(r"(service|processing|booking|convenience|handling|admin(istration)?|resort|platform) fee",
             r"non-?refundable", r"plus (tax|vat|shipping|fees)", r"\+\s*[$€£]\s?\d+(\.\d\d)?\s*(fee|surcharge)",
             r"surcharge")
    for n in doc.nodes:
        own = n.own_text()
        if fee.search(own) and (reason := deemphasis(doc, n)):
            yield Finding("hidden-costs", "medium", n.line, n.snippet(),
                          f"A cost is disclosed but {reason}.",
                          "Include all mandatory fees in the headline price, at the same size as the price.")


@rule("forced-continuity", "Forced continuity", "high",
      "Free trial that converts to a paid plan, with renewal terms buried.",
      "US ROSCA (15 U.S.C. 8403); California Automatic Renewal Law; EU Digital Fairness fitness check (2024)")
def forced_continuity(doc):
    page = doc.text()
    if not re.search(r"free (trial|for \d+|month|week)|try (it )?free|\$0 today", page, re.I):
        return
    renew = rx(r"(auto(matically)?[- ]?renew)", r"(will|then) (be )?(charged|billed)",
               r"after (the|your) (trial|free period)", r"per (month|year) (thereafter|after)",
               r"until (you )?cancel")
    hits = [n for n in doc.nodes
            if renew.search(n.own_text())]
    for n in hits:
        if reason := deemphasis(doc, n):
            yield Finding("forced-continuity", "high", n.line, n.snippet(),
                          f"Trial-to-paid renewal terms are {reason}.",
                          "State the renewal price and date next to the sign-up button, at full size.")
    if not re.search(r"cancel (any ?time|online|in (one|1|two|2) clicks?)|how to cancel", page, re.I) and (
            hits or doc.find("input") and any(re.search(r"card|cc-", n.hint() + n.attrs.get("autocomplete", ""))
                                               for n in doc.find("input"))):
        yield Finding("forced-continuity", "medium", 0, "free trial + payment details, no cancellation path",
                      "Collecting card details for a 'free' trial without saying how to cancel traps users.",
                      "Explain how to cancel (ideally online, in as few steps as signing up).")


@rule("trick-question", "Trick question", "medium",
      "Double negatives or inverted checkboxes that confuse opt-in vs opt-out.",
      "FTC Dark Patterns report (2022) §'Trick questions'; EDPB Guidelines 03/2022")
def trick_question(doc):
    tricky = rx(r"un-?(check|tick|select)\b.{0,60}\b(not|don'?t|no longer)",
                r"\b(not|don'?t)\b.{0,40}\bun-?(check|tick|select|subscribe)",
                r"(do not|don'?t) (want|wish) (to )?not",
                r"(check|tick) (this|the) box (if|to) (you )?(do not|don'?t)\b.{0,40}\b(not|un)",
                r"if you (do not|don'?t) want.{0,40}(leave|keep) (this|it) (checked|ticked)")
    for n in doc.find("label", "p", "span", "div", "li"):
        own = n.own_text()
        if tricky.search(own):
            yield Finding("trick-question", "medium", n.line, n.snippet(120),
                          "The wording makes it hard to tell what ticking the box will do.",
                          "Use one plain, positive sentence: “Send me offers by email.”")


@rule("visual-interference", "Asymmetric choice", "medium",
      "The 'no' option is hidden, tiny, faded or low-contrast next to 'yes'.",
      "EDPB Guidelines 03/2022 §'Hindering'; CNIL cookie guidance (2020); EU DSA Art. 25(1)")
def visual_interference(doc):
    clickable = list(controls(doc))
    for n in clickable:
        t = n.text()
        if not (t and len(t) < 80 and DECLINE.search(t) and not SKIP_LINK.search(t)):
            continue
        reason = deemphasis(doc, n)
        rival = _nearby_primary(n, clickable)
        if reason and rival is not None and not deemphasis(doc, rival):
            yield Finding("visual-interference", "medium", n.line, t,
                          f"The decline option is {reason}, while “{rival.snippet(40)}” is prominent.",
                          "Give accept and decline equal size, colour weight and placement.")


def _nearby_primary(node, clickable, depth=4):
    """Closest 'yes' action sharing a container with `node` (up to `depth` levels up)."""
    for level, box in enumerate(node.ancestors()):
        if level >= depth:
            break
        inside = {id(x) for x in box.iter()}
        for c in clickable:
            if c is not node and id(c) in inside and (
                    PRIMARY.search(c.text()) or c.attrs.get("type") == "submit"):
                return c
    return None


@rule("cookie-wall", "No real choice on cookies", "medium",
      "Consent banner with an 'Accept' button but no equally easy 'Reject'.",
      "GDPR Art. 7(3); EDPB Cookie Banner Taskforce report (2023); CNIL fines vs Google & Facebook (Dec 2021)")
def cookie_wall(doc):
    clickable = set(controls(doc))
    for n in doc.nodes:
        h = n.hint()
        if not (re.search(r"cookie|consent|gdpr|cmp", h) or
                (n.attrs.get("role") in ("dialog", "alertdialog") and "cookie" in n.text().lower())):
            continue
        if any(re.search(r"cookie|consent|gdpr|cmp", a.hint()) for a in n.ancestors()):
            continue  # judge the outermost banner only
        choices = [c for c in n.iter() if c in clickable]
        texts = [c.text().lower() for c in choices]
        has_accept = any(ACCEPT.search(t) for t in texts)
        has_reject = any(re.search(r"reject|decline|refuse|deny|necessary only|only (essential|necessary)", t)
                         for t in texts)
        if has_accept and not has_reject:
            only_settings = any(re.search(r"settings|manage|preferences|options|customi[sz]e", t) for t in texts)
            yield Finding("cookie-wall", "medium", n.line, n.snippet(),
                          "Accepting takes one click; refusing " +
                          ("is buried behind a settings screen." if only_settings else "is not offered at all."),
                          "Add a “Reject all” button on the first layer, styled like “Accept all”.")


@rule("disguised-ad", "Disguised advertising", "low",
      "Sponsored content without a visible 'Ad' or 'Sponsored' label.",
      "FTC Native Advertising guidance (2015); EU DSA Art. 26")
def disguised_ad(doc):
    ad = re.compile(r"(^|[\s_-])(ad|ads|advert|sponsored|promoted|native-ad)([\s_-]|$)")
    for n in doc.nodes:
        if n.tag in ("script", "style", "link", "meta", "iframe") or not n.text():
            continue  # empty slots are filled by JavaScript we cannot see
        if ad.search(n.hint()) and not any(ad.search(a.hint()) for a in n.ancestors()):
            if not re.search(r"\b(ad|advert(isement)?|sponsored|promoted|paid (post|partnership))\b",
                             n.text(), re.I):
                yield Finding("disguised-ad", "low", n.line, n.snippet(),
                              "Marked as an ad in the code but not to the reader.",
                              "Add a clear, visible “Sponsored” or “Ad” label.")
