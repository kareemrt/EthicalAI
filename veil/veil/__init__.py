"""veil — redact sensitive data before it reaches an AI model, restore it after."""

from .core import Finding, Vault, Veil, find
from .detectors import DETECTORS, LABELS, Detector

__all__ = ["Veil", "Vault", "Finding", "find", "Detector", "DETECTORS", "LABELS"]
__version__ = "0.1.0"
