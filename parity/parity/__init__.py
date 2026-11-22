"""Parity — a zero-dependency bias audit toolkit for automated decision systems."""

from .audit import Audit, Dimension, GroupStat, run_audit
from .io import load_csv

__all__ = ["Audit", "Dimension", "GroupStat", "run_audit", "load_csv"]
__version__ = "0.1.0"
