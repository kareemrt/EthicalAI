"""The dark-pattern taxonomy: what Candor looks for, why it matters, how to fix it.

Each `Pattern` is pure data. Text patterns carry compiled regexes; structural
patterns (detected from HTML markup itself) are matched in `markup.py`.
Taxonomy follows Mathur et al. (2019) and the FTC 2022 staff report.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Penalty points per finding, subtracted from a page's 100-point score.
WEIGHTS = {"high": 25, "medium": 10, "low": 3}
SEVERITIES = ("high", "medium", "low")

# Within one sentence: any char except terminal punctuation, but allow decimals like "$4.99".
SENT = r"(?:[^.!?\n]|\.(?=\d))"

# Short citations reused across patterns.
FTC = "FTC Staff Report, 'Bringing Dark Patterns to Light' (2022)"
DSA = "EU Digital Services Act, Art. 25"
UCPD = "EU Unfair Commercial Practices Directive, Annex I §7"
GDPR = "GDPR Art. 4(11) & 7; CJEU Planet49 (C-673/17)"
ROSCA = "Restore Online Shoppers' Confidence Act, 15 U.S.C. §8403"
FEES = "FTC Rule on Unfair or Deceptive Fees, 16 CFR Part 464"
CCPA = "California CCPA Regulations §7004 (symmetry in choice)"
MATHUR = "Mathur et al., 'Dark Patterns at Scale' (CSCW 2019)"


@dataclass(frozen=True)
class Pattern:
    id: str
    name: str
    category: str
    severity: str
    why: str
    fix: str
    refs: tuple[str, ...]
    regexes: tuple[re.Pattern, ...] = field(default=(), repr=False, compare=False)

    @property
    def weight(self) -> int:
        return WEIGHTS[self.severity]


def _p(id, name, category, severity, why, fix, refs, *regexes) -> Pattern:
    compiled = tuple(re.compile(r, re.IGNORECASE) for r in regexes)
    return Pattern(id, name, category, severity, why, fix, tuple(refs), compiled)


PATTERNS: tuple[Pattern, ...] = (
    # ── Shaming & pressure ────────────────────────────────────────────────
    _p("confirmshaming", "Confirmshaming", "Shaming", "high",
       "The opt-out is worded to guilt or shame the user into accepting.",
       "Use a neutral decline label such as 'No thanks' or 'Not now'.",
       [FTC, DSA, MATHUR],
       r"\b(?:no,? thanks?|nope|no)[,.!]? i(?:'m| am)? ?(?:don't|do not|hate|prefer|would rather|'d rather|like|enjoy|not interested)\b[^.!?\n]{0,60}",
       r"\bi(?:'d| would) rather (?:pay full price|miss out|not save|stay (?:uninformed|unprotected))\b",
       r"\bi(?:'m| am) not interested in (?:saving|savings|free|being|getting|improving|protecting|my health)\b[^.!?\n]{0,40}"),
    _p("false_urgency", "False urgency", "Urgency", "medium",
       "Deadline language pressures users to decide before they can compare or think.",
       "Only state a deadline if it is real, fixed, and applies to everyone; otherwise remove it.",
       [FTC, UCPD, MATHUR],
       r"\b(?:offer|sale|deal|discount|price|promo(?:tion)?|pricing) (?:ends|expires) (?:in|soon|today|tonight|at midnight)\b",
       r"\bonly \d+\s*(?:minutes?|mins?|hours?|hrs?|seconds?|secs?) left\b",
       r"\b(?:hurry|act (?:now|fast)|don't miss out|last chance|before it's (?:too late|gone))\b",
       r"\b(?:reserved|held) for (?:the next |only )?\d+(?::\d\d)?\s*(?:minutes?|mins?)\b"),
    _p("countdown_timer", "Countdown timer", "Urgency", "medium",
       "A countdown element was found. Fake or resetting timers are a leading deceptive practice.",
       "Remove the timer, or guarantee it reflects a real deadline that does not reset on reload.",
       [FTC, UCPD, MATHUR]),
    _p("false_scarcity", "False scarcity", "Scarcity", "medium",
       "Low-stock or high-demand claims push users to buy before considering alternatives.",
       "Show stock levels only when they are accurate and live; drop vague 'selling fast' claims.",
       [FTC, MATHUR],
       r"\bonly \d+ (?:left|remaining|available)\b",
       r"\b(?:almost|nearly) (?:gone|sold out)\b",
       r"\bselling (?:out )?fast\b|\bin high demand\b|\blow stock\b"),
    _p("activity_notice", "Activity notification", "Social proof", "low",
       "Claims about other shoppers' activity are frequently fabricated or inflated.",
       "Only show activity counts that come from real, recent, verifiable data.",
       [FTC, MATHUR],
       r"\b\d+ (?:people|others|shoppers|customers|travell?ers|users) (?:are )?(?:viewing|looking at|watching|have (?:this|it) in (?:their|a) (?:cart|basket)|booked|bought|purchased)\b",
       r"\bjust (?:bought|purchased|booked|ordered)\b"),
    # ── Hidden information ────────────────────────────────────────────────
    _p("drip_pricing", "Drip pricing", "Hidden costs", "medium",
       "Mandatory fees revealed outside the headline price make the true cost hard to compare.",
       "Include every mandatory fee in the first price shown. Itemize, don't hide.",
       [FEES, FTC, MATHUR],
       r"(?<!no )(?<!zero )\b(?:service|convenience|processing|booking|handling|resort|facility|admin(?:istrative)?) fees?\b",
       r"\bplus (?:applicable )?(?:taxes and fees|fees|taxes & fees)\b",
       r"\b(?:fees?|taxes and fees) (?:not included|added at checkout|calculated at checkout)\b"),
    _p("hidden_terms", "Fine-print terms", "Hidden costs", "high",
       "Costs, renewals, or cancellation terms appear in tiny or faded text.",
       "Show material terms at the same size and contrast as the main call to action.",
       [FTC, ROSCA, DSA]),
    _p("forced_continuity", "Forced continuity", "Subscription", "medium",
       "A trial or plan silently turns into a paid, recurring charge.",
       "Disclose the price and renewal date next to the button, get express consent, and send a reminder before charging.",
       [ROSCA, FTC],
       r"\b(?:renews?|billed|charged|converts?)\b" + SENT + r"{0,60}\bunless (?:you )?cancel",
       r"\bfree trial\b" + SENT + r"{0,80}\b(?:after which|automatically|will be (?:charged|billed)|auto-?renews?)"),
    _p("obstruction", "Cancellation obstruction", "Obstruction", "high",
       "Cancelling is made harder than signing up (phone calls, letters, in-person visits).",
       "Let users cancel online, through the same channel and with the same effort they used to sign up.",
       [ROSCA, FTC, DSA],
       r"\bto cancel,? (?:please |you (?:must|need to|will need to) )?(?:call|phone|contact|email|write|mail|visit|speak)\b",
       r"\bcancell?ations? (?:requests? )?(?:must|can only|may only) be (?:made|submitted|requested|done) (?:by|via|over|in) (?:phone|telephone|mail|post|writing|person)\b",
       r"\bcannot be cancell?ed online\b|\bcall (?:us )?to cancel\b"),
    # ── Sneaking & interface interference ─────────────────────────────────
    _p("sneak_into_basket", "Sneak into basket", "Sneaking", "high",
       "Items or add-ons are added to the order without the user choosing them.",
       "Never add items by default. Offer add-ons as an explicit, unselected choice.",
       [FTC, DSA, MATHUR],
       r"\bwe(?:'ve| have) (?:automatically |also )?added\b" + SENT + r"{0,60}\bto your (?:cart|order|basket|bag|booking|subscription)\b",
       r"\b(?:has|have) been (?:automatically )?added to your (?:cart|order|basket|bag|booking)\b"),
    _p("preselection", "Pre-checked consent", "Sneaking", "high",
       "A consent, marketing, or paid add-on checkbox is ticked by default.",
       "Leave consent and add-on checkboxes unchecked. Consent must be an active choice.",
       [GDPR, FTC, DSA]),
    _p("trick_question", "Trick question", "Interference", "high",
       "Double negatives or inverted checkboxes make users choose the opposite of what they intend.",
       "Phrase choices positively: 'Send me product updates' with an unchecked box.",
       [FTC, CCPA, MATHUR],
       r"\b(?:un-?check|un-?tick|deselect) (?:this|the) box (?:if|unless|to)\b",
       r"\b(?:check|tick) (?:this|the) box if you (?:do not|don't)\b"),
    _p("implied_consent", "Implied consent", "Privacy", "medium",
       "Consent to tracking or data sharing is assumed from simply using the product.",
       "Ask for consent with equally prominent 'Accept' and 'Reject' options before tracking.",
       [GDPR, CCPA, DSA],
       r"\bby (?:continuing|using|browsing|staying on|visiting)(?: to (?:use|browse))? (?:this|our) (?:site|website|app|service)\b" + SENT + r"{0,40}\b(?:agree|consent|accept)",
       r"\bby (?:continuing|clicking)\b" + SENT + r"{0,40}\byou (?:agree|consent) to (?:share|sharing|the sale|sell|receive marketing|marketing)"),
    _p("nagging", "Nagging", "Interference", "low",
       "'Later' without 'never' means the prompt will keep coming back.",
       "Offer a permanent 'Don't ask again' option alongside 'Later'.",
       [FTC, MATHUR],
       r"\b(?:remind me later|maybe later|ask me later)\b"),
    _p("asterisk_claim", "Asterisked claim", "Hidden costs", "low",
       "A headline promise is qualified by an asterisk pointing to conditions elsewhere.",
       "State the condition right next to the claim, in the same size text.",
       [FTC],
       r"\b(?:free|guaranteed|no commitment|cancel any ?time|unlimited|lifetime)\s?\*+"),
)

BY_ID = {p.id: p for p in PATTERNS}
TEXT_PATTERNS = tuple(p for p in PATTERNS if p.regexes)
