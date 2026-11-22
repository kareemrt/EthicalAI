"""FairCheck — a lightweight bias audit for automated decision systems."""

__version__ = "0.1.0"

from .audit import Audit, Dimension, GroupStat, load_csv, run_audit  # noqa: E402

__all__ = ["Audit", "Dimension", "GroupStat", "load_csv", "run_audit", "__version__"]
