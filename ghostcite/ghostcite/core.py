"""The pipeline: extract → offline checks → (optional) registry lookups."""
from __future__ import annotations

import datetime as _dt
from concurrent.futures import ThreadPoolExecutor

from . import offline, resolve
from .extract import extract
from .models import MALFORMED, SEVERITY, UNCHECKED, Citation, Finding


def check_citation(c: Citation, online: bool = False, get: resolve.Get | None = None,
                   today: _dt.date | None = None) -> Finding:
    problem = offline.check(c, today)
    if problem:
        return Finding(c, MALFORMED, problem)
    if not online:
        return Finding(c, UNCHECKED, "well-formed (run with --online to verify)")
    try:
        return resolve.RESOLVERS[c.kind](c, get or resolve.http_get)
    except resolve.Offline as e:
        return Finding(c, UNCHECKED, str(e))
    except (ValueError, KeyError, TypeError) as e:  # unexpected registry payload
        return Finding(c, UNCHECKED, f"could not read registry response ({type(e).__name__})")


def check_text(text: str, online: bool = False, get: resolve.Get | None = None,
               workers: int = 4, kinds: set[str] | None = None,
               today: _dt.date | None = None) -> list[Finding]:
    """Check every citation in `text`; results are sorted worst-first, then by line."""
    cites = [c for c in extract(text) if not kinds or c.kind in kinds]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        findings = list(pool.map(lambda c: check_citation(c, online, get, today), cites))
    return sorted(findings, key=lambda f: (SEVERITY.index(f.verdict), f.citation.line))
