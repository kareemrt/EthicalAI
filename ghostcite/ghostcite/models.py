"""Plain data types shared across the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field

# Verdicts, ordered from most to least alarming.
MALFORMED = "malformed"    # cannot exist: bad checksum, impossible date, invalid syntax
NOT_FOUND = "not_found"    # authoritative registry says this identifier does not exist
MISMATCH = "mismatch"      # identifier exists but points to a different work
UNMATCHED = "unmatched"    # no close match found (weaker evidence; coverage gaps happen)
UNCHECKED = "unchecked"    # well-formed, but not looked up (offline or network error)
VERIFIED = "verified"      # exists and matches the surrounding text

SEVERITY = [MALFORMED, NOT_FOUND, MISMATCH, UNMATCHED, UNCHECKED, VERIFIED]
FAILING = {MALFORMED, NOT_FOUND, MISMATCH}


@dataclass(frozen=True)
class Citation:
    kind: str      # doi | arxiv | isbn | pmid | url | ref
    value: str     # normalized identifier (or the reference text for kind="ref")
    line: int      # 1-based line number in the source
    context: str   # the full source line, used to compare against registry metadata


@dataclass
class Record:
    """Metadata returned by a registry for an identifier."""
    title: str = ""
    year: int | None = None
    authors: list[str] = field(default_factory=list)
    source: str = ""
    id: str = ""


@dataclass
class Finding:
    citation: Citation
    verdict: str
    reason: str
    record: Record | None = None

    def to_dict(self) -> dict:
        out = {
            "kind": self.citation.kind,
            "value": self.citation.value,
            "line": self.citation.line,
            "verdict": self.verdict,
            "reason": self.reason,
        }
        if self.record:
            out["record"] = {k: v for k, v in vars(self.record).items() if v}
        return out
