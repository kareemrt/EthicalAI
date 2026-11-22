"""fairhire — bias audits for automated hiring decisions.

Computes selection rates, impact ratios and significance tests per
demographic category, in the style of NYC Local Law 144 bias audits and the
EEOC four-fifths rule. Pure standard library, no dependencies.
"""

from .data import load_csv
from .metrics import Audit, GroupResult, Status, audit

__all__ = ["Audit", "GroupResult", "Status", "audit", "load_csv"]
__version__ = "0.1.0"
