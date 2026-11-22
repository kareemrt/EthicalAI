"""fairaudit — a zero-dependency bias audit for automated decision tools.

Computes selection rates and impact ratios per demographic category
(the metrics required by NYC Local Law 144 and the EEOC four-fifths rule),
plus significance tests and equal-opportunity gaps, and renders a
human-readable Markdown report with SVG charts.
"""

from .metrics import GroupStat, audit, two_proportion_p

__all__ = ["GroupStat", "audit", "two_proportion_p"]
__version__ = "0.1.0"
