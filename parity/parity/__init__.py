"""Parity — a zero-dependency bias audit toolkit for automated decision systems."""

from .data import load_csv
from .metrics import GroupResult, audit_attribute, intersect
from .proxies import cramers_v, find_proxies

__all__ = ["load_csv", "GroupResult", "audit_attribute", "intersect", "cramers_v", "find_proxies"]
__version__ = "0.1.0"
