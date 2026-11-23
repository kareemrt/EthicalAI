"""The rulebook: each rule detects one deceptive-design pattern.

A rule is a plain function ``check(page) -> iterable of (element, evidence)``
registered with ``@rule(...)``. Metadata lives next to the code so the
explanation a user reads is never out of sync with what is detected.

Taxonomy follows Mathur et al., "Dark Patterns at Scale" (CSCW 2019) and the
FTC staff report "Bringing Dark Patterns to Light" (2022).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

from .page import Element, Page

SEVERITIES = ("high", "medium", "low")


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: str
    severity: str
    why: str      # why it harms people
    fix: str      # what to do instead
    refs: tuple   # laws, regulator guidance, research
    check: Callable[[Page], Iterable[tuple[Element, str]]]


RULES: list[Rule] = []


def rule(id, name, category, severity, why, fix, refs=()):
    def register(fn):
        RULES.append(Rule(id, name, category, severity, why, fix, tuple(refs), fn))
        return fn
    return register


def rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


def text_rule(pattern: re.Pattern, *, include_hidden=False, where=None):
    """Build a check that flags the innermost elements matching ``pattern``."""
    def check(page: Page):
        for el in page.deepest(pattern, include_hidden=include_hidden):
            if where is None or where(el):
                yield el, el.text
    return check


# --- Sneaking -----------------------------------------------------------------

CONSENT = rx(r"newsletter|marketing|promotion|offers|special deals|partners|"
             r"third[- ]part|share my|sell my|personali[sz]ed ads|subscribe|"
             r"updates (by|via) (e-?mail|sms|text)")
ADD_ON = rx(r"insurance|protection plan|warranty|donat|priority (handling|boarding|support)|"
            r"gift wrap|express (shipping|delivery)|\badd .*\bfor \W?\d|\btip\b|carbon offset|membership|\+\s?\W?\d")


def _preselected(page: Page, pattern: re.Pattern):
    for box in page.checkboxes:
        if "checked" in box.attrs:
            label = page.label_for(box)
            if pattern.search(label):
                yield box, label


rule("CD01", "Pre-ticked consent", "Sneaking", "high",
     why="Consent you didn't give is not consent. Pre-ticked boxes quietly sign people up "
         "for marketing or data sharing they never chose.",
     fix="Leave every consent checkbox unticked by default and let people opt in.",
     refs=("GDPR Recital 32 & Art. 7", "CJEU Planet49 (C-673/17, 2019)",
           "CCPA Regs, 11 CCR §7004"),
     )(lambda page: _preselected(page, CONSENT))

rule("CD02", "Sneak into basket", "Sneaking", "high",
     why="Paid extras that are pre-selected end up in the basket unless the shopper "
         "notices and removes them.",
     fix="Offer extras unticked; only add them to the order after an explicit choice.",
     refs=("EU Consumer Rights Directive 2011/83/EU, Art. 22", "FTC Act §5"),
     )(lambda page: (hit for hit in _preselected(page, ADD_ON)
                     if not CONSENT.search(hit[1])))

# --- Hidden costs and subscriptions ------------------------------------------

rule("CD03", "Drip pricing", "Sneaking", "medium",
     why="Advertising a low price and revealing mandatory fees later makes honest "
         "comparison impossible and exploits sunk-cost at checkout.",
     fix="Show the total price, including mandatory fees, wherever a price is shown.",
     refs=("FTC Rule on Unfair or Deceptive Fees, 16 CFR Part 464 (2025)",
           "California SB 478 (Honest Pricing Law, 2024)"),
     )(text_rule(rx(
         r"fees? (will be |are |is )?(calculated|added|applied|shown|due) (at|during) checkout|"
         r"(excluding|excl\.?|plus|\+)\s*(all\s+)?(service|booking|processing|convenience|"
         r"resort|handling|admin(istration)?) fees?|"
         r"(taxes and fees|fees and taxes|fees) (are )?not included")))

RENEWAL = rx(r"auto(matic(ally)?)?[- ]?renew|renews? automatically|recurring (charge|billing|payment)|"
             r"(will|you'll) (then )?be (automatically )?(charged|billed)|"
             r"automatically (charged|billed)|after (your|the) (free )?trial")
rule("CD04", "Hidden subscription terms", "Forced continuity", "high",
     why="Burying auto-renewal or post-trial charges in fine print turns a 'free trial' "
         "into a subscription people didn't knowingly agree to.",
     fix="State the price, billing frequency and renewal date clearly next to the "
         "sign-up button, at the same size as the offer.",
     refs=("ROSCA, 15 U.S.C. §8403", "California Automatic Renewal Law, "
           "Bus. & Prof. Code §17600 et seq."),
     )(text_rule(RENEWAL, include_hidden=True, where=lambda el: el.fine or el.hidden))

rule("CD05", "Obstructed cancellation", "Obstruction", "medium",
     why="Easy to join, hard to leave: forcing a phone call or letter to cancel keeps "
         "people paying for things they no longer want.",
     fix="Let people cancel the same way they signed up, online, in a few clicks.",
     refs=("ROSCA, 15 U.S.C. §8403(3)", "California Automatic Renewal Law, Bus. & Prof. Code §17602"),
     )(text_rule(rx(
         r"(to|you can only|you may only|you must) cancel,?.{0,40}?\b(call|phone|telephone|"
         r"write to|by (post|mail|letter|fax)|in writing|visit (a|one of our|our) (store|branch))|"
         r"cancell?ations? (is |are |must be )?(only )?(possible|available|accepted|made|"
         r"handled|requested) (by|via|over the) (phone|telephone|post|mail|letter|fax)")))

# --- Urgency and scarcity ----------------------------------------------------

COUNTDOWN_ATTR = rx(r"count-?down|timer|clock|time-?left|expires")


def _false_urgency(page: Page):
    yield from text_rule(rx(
        r"(offer|sale|deal|discount|price|promo(tion)?) (ends|expires|is reserved) (in|today|tonight|soon)|"
        r"\b(ends|expires) in \d|only \d+ (minutes?|hours?|mins?) (left|remaining)|"
        r"hurry[,!]|last chance|before it'?s too late|reserved for (the next )?\d+ ?(min|minutes)"))(page)
    for el in page.elements:
        attrs = el.attrs.get("id", "") + " " + el.attrs.get("class", "")
        if not el.hidden and COUNTDOWN_ATTR.search(attrs) and \
                re.search(r"\d{1,2}\s*:\s*\d{2}", el.text) and \
                not any(COUNTDOWN_ATTR.search(a.attrs.get("id", "") + " " + a.attrs.get("class", ""))
                        for a in el.ancestors()):
            yield el, f"countdown timer: {el.text}"


rule("CD06", "False urgency", "Urgency", "medium",
     why="Countdown timers and 'ends soon' banners pressure people into deciding before "
         "they can compare or think. They are often fake and reset on reload.",
     fix="Only show deadlines that are real, and state the actual end date.",
     refs=("EU Unfair Commercial Practices Directive, Annex I point 7",
           "FTC, Bringing Dark Patterns to Light (2022)"),
     )(lambda page: _dedupe(_false_urgency(page)))

rule("CD07", "Scarcity pressure", "Scarcity", "low",
     why="Low-stock and high-demand messages push people to buy now. They are legal "
         "when true, but often generated without real inventory data.",
     fix="Show stock levels only when they come from live inventory, and avoid "
         "manufactured 'people are looking' counters.",
     refs=("EU Unfair Commercial Practices Directive, Art. 6",
           "Mathur et al., Dark Patterns at Scale (2019)"),
     )(text_rule(rx(
         r"only \d+ (left|remaining|available)|\d+ (other )?(people|others|shoppers|users|customers) "
         r"(are )?(viewing|looking at|watching|have this in)|in high demand|selling fast|"
         r"almost (gone|sold out)|\d+ (people )?(bought|booked|purchased) (this )?in the (last|past)")))

rule("CD08", "Activity notifications", "Social proof", "medium",
     why="Pop-ups like 'Sarah in Leeds just bought this' simulate popularity and are "
         "frequently fabricated.",
     fix="Remove simulated activity feeds; if you show real activity, make it verifiable "
         "and aggregate.",
     refs=("EU Unfair Commercial Practices Directive, Art. 6 (misleading actions)",
           "Mathur et al., Dark Patterns at Scale (2019)"),
     )(text_rule(rx(
         r"\b(someone|a (customer|shopper|user|person)|[A-Z][a-z]+) (in|from) [A-Z][a-z]+.{0,30}?"
         r"\b(just )?(bought|purchased|ordered|booked|signed up|subscribed)\b|"
         r"\bjust (bought|purchased|ordered|booked) (this|one|a)\b")))

# --- Interface interference --------------------------------------------------

rule("CD09", "Confirmshaming", "Misdirection", "medium",
     why="Wording the 'no' option as a self-insult guilts people into accepting.",
     fix="Use neutral labels for every choice, e.g. 'No thanks'.",
     refs=("FTC, Bringing Dark Patterns to Light (2022)",
           "EU Digital Services Act, Art. 25"),
     )(lambda page: ((el, el.label) for el in page.actions if re.search(
         r"^\W*(no|nope|nah|not now|maybe later)\b[\s,.!]*(thanks?( you)?)?[\s,.!]*"
         r"\b(i|i'm|i'd|i'll|i've|my)\b|"
         r"^\W*i (don'?t|do not|prefer not to|would rather( not)?|'d rather( not)?) "
         r"(want|like|care|need)? ?(to )?(sav|save|deal|discount|money|smart|healthy|secure|"
         r"protect|grow|improve|win|pay(ing)? (full|more))",
         el.label, re.I)))

ACCEPT = rx(r"^\W*(accept|agree|allow|i agree|ok(ay)?|got it|yes|continue|sounds good)\b")
REJECT = rx(r"\b(reject|decline|refuse|deny|disagree|no,? thanks|necessary only|"
            r"only (necessary|essential|required)|essential only|required only|do not (accept|allow))\b")


def _cookie_choice(page: Page):
    seen, actions = set(), page.actions
    clickable = {id(a) for a in actions}
    for btn in actions:
        if not ACCEPT.search(btn.label):
            continue
        banner = next((a for a in btn.ancestors() if re.search(r"cookie|tracking", a.text, re.I)), None)
        if banner is None or id(banner) in seen:
            continue
        seen.add(id(banner))
        rejects = [a for a in banner.descendants() if id(a) in clickable and REJECT.search(a.label)]
        if not rejects:
            yield banner, f"'{btn.label}' offered with no equally easy way to refuse"
        elif all(r.fine or (r.tag == "a" and btn.tag != "a") for r in rejects):
            yield rejects[0], (f"'{btn.label}' is a {btn.tag}; '{rejects[0].label}' is "
                               f"a less prominent {'fine-print ' if rejects[0].fine else ''}{rejects[0].tag}")


rule("CD10", "Asymmetric consent", "Obstruction", "high",
     why="When 'Accept' is one bright click and 'Reject' is hidden, tiny or missing, "
         "the banner manufactures consent rather than asking for it.",
     fix="Put 'Reject all' on the first layer, with the same size, style and number "
         "of clicks as 'Accept all'.",
     refs=("ePrivacy Directive Art. 5(3) & GDPR Art. 7(3)",
           "EDPB Cookie Banner Taskforce report (2023)", "CNIL sanctions against Google & Meta (2021-22)"),
     )(_cookie_choice)

rule("CD11", "Trick question", "Misdirection", "medium",
     why="Double negatives and inverted checkboxes ('untick to not receive') make people "
         "choose the opposite of what they intend.",
     fix="Phrase every option positively: 'Send me offers by email' with an unticked box.",
     refs=("CCPA Regs, 11 CCR §7004", "FTC, Bringing Dark Patterns to Light (2022)"),
     )(lambda page: ((box, label) for box in page.checkboxes
                     for label in [page.label_for(box)] if re.search(
         r"\b(un-?check|un-?tick|do not (check|tick)|don'?t (check|tick)|leave .{0,20}(checked|ticked))\b"
         r".{0,60}\b(not|don'?t|no longer|never)\b|"
         r"\bif you (do not|don'?t) (wish|want) (to )?(not )?(receive|be contacted|hear)|"
         r"\bopt[- ]out of not\b|\bnot (opt|unsubscribe) out\b", label, re.I)))


def _dedupe(hits):
    seen = set()
    for el, ev in hits:
        if id(el) not in seen and not any(id(a) in seen for a in el.ancestors()):
            seen.add(id(el))
            yield el, ev
