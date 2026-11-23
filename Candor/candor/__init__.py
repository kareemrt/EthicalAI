"""Candor: find deceptive design patterns ("dark patterns") in web pages."""
__version__ = "0.1.0"

from .scanner import Report, scan  # noqa: E402

__all__ = ["scan", "Report", "__version__"]
