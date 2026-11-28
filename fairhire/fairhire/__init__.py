"""fairhire — a zero-dependency bias audit toolkit for automated hiring decisions."""

from .data import Record, load_csv
from .metrics import Audit, DimensionResult, GroupStat, run_audit

__all__ = ["Record", "load_csv", "Audit", "DimensionResult", "GroupStat", "run_audit"]
__version__ = "0.1.0"
