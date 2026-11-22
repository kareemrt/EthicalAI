"""plainspeak: check that official notices can be understood and acted on."""
from .analyze import Report, analyze, fix

__version__ = "0.1.0"
__all__ = ["Report", "analyze", "fix", "__version__"]
