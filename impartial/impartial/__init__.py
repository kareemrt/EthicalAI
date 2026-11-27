"""Impartial — a zero-dependency bias audit toolkit for automated decisions."""

from .data import load_csv
from .metrics import DimensionResult, GroupResult, audit_dimension, run_audit

__version__ = "0.1.0"
__all__ = ["load_csv", "run_audit", "audit_dimension", "DimensionResult", "GroupResult", "__version__"]
