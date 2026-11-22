"""tether — check that AI-generated answers stay tied to their sources."""
from .core import check, Report, Claim, Source, SUPPORTED, WEAK, UNSUPPORTED, SKIPPED

__version__ = "0.1.0"
__all__ = ["check", "Report", "Claim", "Source", "SUPPORTED", "WEAK", "UNSUPPORTED", "SKIPPED"]
