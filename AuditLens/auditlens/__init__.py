"""AuditLens -- open, explainable bias audits for automated hiring tools."""

from .audit import AuditResult, DimensionResult, GroupResult, audit, load_csv
from .report import to_html, to_json, to_markdown

__all__ = [
    "AuditResult",
    "DimensionResult",
    "GroupResult",
    "audit",
    "load_csv",
    "to_html",
    "to_json",
    "to_markdown",
]
__version__ = "0.1.0"
