"""Equitas — lightweight bias audits for automated decision systems."""

from .audit import Audit, Dimension, run_audit
from .metrics import GroupStat, audit_groups

__all__ = ["Audit", "Dimension", "GroupStat", "audit_groups", "run_audit"]
__version__ = "0.1.0"
