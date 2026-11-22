"""RedFlag - explainable, offline scam-message detection."""

from .model import Model, Report
from .signals import SIGNALS, scan

__all__ = ["Model", "Report", "SIGNALS", "scan", "check"]
__version__ = "0.1.0"


def check(text: str) -> Report:
    """One-liner API: ``redflag.check("...").verdict``."""
    return Model.load().score(text)
