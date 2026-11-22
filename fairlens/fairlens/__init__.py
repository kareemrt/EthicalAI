"""FairLens — audit automated decisions for adverse impact, in one command."""

from .data import Dataset, load
from .metrics import Audit, run_audit

__all__ = ["Dataset", "Audit", "load", "run_audit"]
__version__ = "0.1.0"
