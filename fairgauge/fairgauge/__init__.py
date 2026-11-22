"""fairgauge — audit automated decisions for adverse impact."""

from .data import Record, load
from .metrics import Audit, GroupStat, audit, run

__all__ = ["Record", "load", "Audit", "GroupStat", "audit", "run"]
__version__ = "0.1.0"
