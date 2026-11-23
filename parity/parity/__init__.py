"""Parity — a zero-dependency disparate-impact audit for automated decisions."""
from .metrics import Audit, Dimension, Group, audit
from .report import data_notes, findings, to_html, to_json, to_markdown, to_svg, to_text

__version__ = "0.1.0"
__all__ = ["audit", "Audit", "Dimension", "Group", "findings", "data_notes",
           "to_text", "to_markdown", "to_html", "to_json", "to_svg"]
