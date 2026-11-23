"""handoff: find out when your AI should hand a decision to a human.

Calibration + selective-prediction audits for any classifier, from a CSV of
predictions. Standard library only.
"""

from .data import Prediction, load_csv
from .audit import Audit, run_audit

__all__ = ["Prediction", "load_csv", "Audit", "run_audit"]
__version__ = "0.1.0"
