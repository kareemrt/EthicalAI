"""Candor — find manipulative design (dark patterns) in web pages."""
__version__ = "0.1.0"

from .scanner import Report, scan_html  # noqa: E402

__all__ = ["scan_html", "Report", "__version__"]
