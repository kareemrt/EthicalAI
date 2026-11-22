"""Candor: a linter for deceptive design (dark patterns) in UI markup and copy."""
from .patterns import PATTERNS, Pattern
from .scanner import FileResult, Finding, Report, scan_paths, scan_text

__all__ = ["PATTERNS", "Pattern", "Finding", "FileResult", "Report", "scan_paths", "scan_text"]
__version__ = "0.1.0"
