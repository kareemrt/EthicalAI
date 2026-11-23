"""fairaudit — a zero-dependency bias audit for automated decisions."""

__version__ = "0.1.0"

from .metrics import Audit, AttributeResult, GroupResult, audit, load_csv  # noqa: E402

__all__ = ["Audit", "AttributeResult", "GroupResult", "audit", "load_csv", "__version__"]
