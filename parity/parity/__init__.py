"""Parity — a zero-dependency bias audit for automated decision systems.

    from parity import load_rows, audit
    rows = load_rows("decisions.csv")
    result = audit(rows, ["sex"], outcome="selected")
"""

from .data import load_rows
from .metrics import Audit, GroupStat, audit, fisher_exact

__all__ = ["load_rows", "audit", "Audit", "GroupStat", "fisher_exact"]
__version__ = "0.1.0"
