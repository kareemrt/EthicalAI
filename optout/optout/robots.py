"""A small, faithful robots.txt evaluator following RFC 9309.

Semantics implemented:
  * consecutive User-agent lines share one group; repeated groups merge
  * a crawler obeys the group naming its product token (case-insensitive),
    otherwise the "*" group, otherwise everything is allowed
  * the longest matching path pattern wins; on a tie, Allow wins
  * "*" matches any run of characters, a trailing "$" anchors the end
  * an empty "Disallow:" is not a rule; /robots.txt is always allowed
"""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rule:
    allow: bool
    pattern: str
    line: int

    def __str__(self) -> str:
        return f"{'Allow' if self.allow else 'Disallow'}: {self.pattern}"

    def matches(self, path: str) -> bool:
        return _compile(self.pattern).match(path) is not None


@dataclass
class Decision:
    allowed: bool
    group: str | None  # the user-agent token whose group applied, or None
    rule: Rule | None  # the deciding rule, or None if no rule matched

    @property
    def reason(self) -> str:
        if self.group is None:
            return "no matching group"
        where = "own group" if self.group != "*" else "* group"
        return f"{where}: {self.rule}" if self.rule else f"{where}: no rule matches"


@dataclass
class Robots:
    groups: dict[str, list[Rule]] = field(default_factory=dict)
    disallow_all: bool = False  # set when robots.txt was unreachable (5xx)

    def decide(self, agent: str, path: str = "/") -> Decision:
        if self.disallow_all:
            return Decision(False, None, None)
        token = agent.lower()
        group = token if token in self.groups else "*" if "*" in self.groups else None
        if group is None or path == "/robots.txt":
            return Decision(True, group, None)
        hits = [r for r in self.groups[group] if r.matches(path)]
        if not hits:
            return Decision(True, group, None)
        best = max(hits, key=lambda r: (len(r.pattern), r.allow))
        return Decision(best.allow, group, best)

    def can_fetch(self, agent: str, path: str = "/") -> bool:
        return self.decide(agent, path).allowed

    def names(self, agent: str) -> bool:
        """True if robots.txt has a group addressed to this exact agent."""
        return agent.lower() in self.groups


def parse(text: str) -> Robots:
    robots = Robots()
    agents: list[str] = []
    in_rules = False
    for n, raw in enumerate(text.lstrip("﻿").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (s.strip() for s in line.split(":", 1))
        key = key.lower()
        if key in ("user-agent", "useragent"):
            if in_rules:  # a new group starts
                agents, in_rules = [], False
            token = value.split("/")[0].strip().lower()
            if token:
                agents.append(token)
                robots.groups.setdefault(token, [])
        elif key in ("allow", "disallow"):
            in_rules = True
            if value and agents:
                rule = Rule(key == "allow", value, n)
                for a in agents:
                    robots.groups[a].append(rule)
        # other keys (sitemap, crawl-delay, ...) neither start nor end a group
    return robots


_cache: dict[str, re.Pattern] = {}


def _compile(pattern: str) -> re.Pattern:
    if pattern not in _cache:
        anchored = pattern.endswith("$")
        body = pattern[:-1] if anchored else pattern
        rx = ".*".join(re.escape(part) for part in body.split("*"))
        _cache[pattern] = re.compile(rx + ("$" if anchored else ""))
    return _cache[pattern]
