"""FairHire — zero-dependency bias audits for automated hiring decisions."""

from .metrics import GroupResult, audit, two_proportion_p_value

__all__ = ["GroupResult", "audit", "two_proportion_p_value"]
__version__ = "0.1.0"
