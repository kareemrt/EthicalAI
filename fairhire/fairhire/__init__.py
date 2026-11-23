"""FairHire — bias audits for automated hiring decisions, in pure Python."""

from .audit import Audit, Dimension, GroupStat, run_audit

__all__ = ["Audit", "Dimension", "GroupStat", "run_audit"]
__version__ = "0.1.0"
