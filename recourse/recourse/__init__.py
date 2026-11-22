"""recourse — tell people what they can change after an automated 'no',
and check whether that burden falls evenly."""

from .audit import audit
from .model import Feature, Model
from .solver import best_plan, single_changes

__version__ = "0.1.0"
__all__ = ["Model", "Feature", "best_plan", "single_changes", "audit", "__version__"]
