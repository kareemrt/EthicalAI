"""Each detector is a module exposing `detect(src: Source) -> Iterable[Finding]`.

To add a detector: write a module with a `detect` function and list it below.
"""
from . import exfil, html, phrases, unicode

ALL = (unicode, html, phrases, exfil)
