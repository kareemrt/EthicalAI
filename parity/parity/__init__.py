"""Parity: a zero-dependency bias audit for automated decision systems."""

__version__ = "0.1.0"

from .data import Record, load  # noqa: E402
from .metrics import Audit, Policy, audit, run  # noqa: E402

__all__ = ["Audit", "Policy", "Record", "audit", "load", "run", "__version__"]
