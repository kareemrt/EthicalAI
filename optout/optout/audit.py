"""The audit: one pass over a site, producing plain data for any renderer."""

from dataclasses import dataclass

from . import robots, signals
from .agents import AGENTS, SEARCH, TRAINING, Agent


@dataclass
class Verdict:
    agent: Agent
    decision: robots.Decision
    named: bool  # robots.txt addresses this bot by name


@dataclass
class Audit:
    site: str
    path: str
    robots_status: int
    robots_groups: int  # distinct user-agent tokens named
    verdicts: list[Verdict]
    signals: list[signals.Signal]

    def open(self, category: str) -> list[Verdict]:
        return [v for v in self.verdicts if v.agent.category == category and v.decision.allowed]

    def of(self, category: str) -> list[Verdict]:
        return [v for v in self.verdicts if v.agent.category == category]

    @property
    def problems(self) -> list[str]:
        out = []
        if n := len(self.open(TRAINING)):
            out.append(f"{n} AI training crawler{'s' if n > 1 else ''} can still read {self.path}")
        blocked = [v.agent.token for v in self.of(SEARCH) if not v.decision.allowed]
        if blocked:
            out.append(f"search engines blocked too ({', '.join(blocked)}) — this hides you from search")
        return out

    @property
    def grade(self) -> str:
        total, shut = len(self.of(TRAINING)), len(self.of(TRAINING)) - len(self.open(TRAINING))
        has_tdm = any(s.present for s in self.signals if s.name.startswith("TDMRep"))
        if shut == total:
            return "A" if has_tdm else "B"
        return "C" if shut >= total / 2 else "D" if shut else "F"


def run(site, path: str = "/") -> Audit:
    page = site.get("/robots.txt")
    if page.ok:
        rules = robots.parse(page.body)
    else:  # RFC 9309: 4xx = no restrictions, 5xx/unreachable = assume full disallow
        rules = robots.Robots(disallow_all=page.status >= 500)
    home = site.get(path)
    verdicts = [Verdict(a, rules.decide(a.token, path), rules.names(a.token)) for a in AGENTS]
    sigs = [signals.tdmrep(site.get("/.well-known/tdmrep.json"), home, path), signals.noai(home)]
    return Audit(site.label, path, page.status, len(rules.groups), verdicts, sigs)
