"""Equitas — a zero-dependency bias audit for automated decision systems."""
__version__ = "0.1.0"

from .data import Record, load  # noqa: E402
from .metrics import Config, Report, run  # noqa: E402

__all__ = ["Record", "load", "Config", "Report", "run", "__version__"]
