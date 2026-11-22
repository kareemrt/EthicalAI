"""equitas — a tiny, dependency-free bias audit for automated decisions."""
__version__ = "0.1.0"

from .data import Record, load
from .metrics import Audit, audit

__all__ = ["Audit", "Record", "audit", "load", "__version__"]
