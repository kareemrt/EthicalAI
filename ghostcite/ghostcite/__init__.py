"""ghostcite — catch fabricated citations in AI-generated text."""
from .core import check_citation, check_text
from .extract import extract
from .models import Citation, Finding, Record

__version__ = "0.1.0"
__all__ = ["check_text", "check_citation", "extract", "Citation", "Finding", "Record"]
