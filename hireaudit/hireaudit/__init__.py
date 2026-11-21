"""HireAudit — open, dependency-free bias audits for automated hiring tools."""
__version__ = "0.1.0"

from .data import Dataset, load
from .metrics import Audit, Config, Group, audit, audit_all, fisher_exact

__all__ = ["Audit", "Config", "Dataset", "Group", "audit", "audit_all", "fisher_exact", "load"]
