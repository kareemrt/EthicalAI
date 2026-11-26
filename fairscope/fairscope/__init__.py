"""fairscope — a zero-dependency bias auditor for automated decisions."""

from .metrics import Audit, GroupStats, audit

__all__ = ["Audit", "GroupStats", "audit"]
__version__ = "0.1.0"
