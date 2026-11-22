"""Uniform read access to a live website or a local build folder.

Both sources answer get(path) -> Page, so the audit never cares which one
it is talking to. Local folders let you check a site in CI before deploy.
"""

import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

USER_AGENT = "optout/1.0 (+https://github.com/kareemrt/EthicalAI)"
MAX_BYTES = 512 * 1024  # RFC 9309 asks parsers to read at least 500 KiB


@dataclass
class Page:
    status: int  # HTTP-style: 200 found, 404 missing, 5xx unreachable
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)  # lower-cased keys

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class WebSite:
    def __init__(self, url: str, timeout: float = 10.0):
        if "://" not in url:
            url = "https://" + url
        parts = urlparse(url)
        self.root = f"{parts.scheme}://{parts.netloc}/"
        self.label = parts.netloc
        self.timeout = timeout

    def get(self, path: str) -> Page:
        req = urllib.request.Request(urljoin(self.root, path), headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return _page(r.status, r.read(MAX_BYTES), r.headers)
        except urllib.error.HTTPError as e:
            return _page(e.code, e.read(MAX_BYTES), e.headers)
        except (urllib.error.URLError, TimeoutError, OSError):
            return Page(599)


class LocalSite:
    """A static build folder. Headers come from a Netlify/Cloudflare `_headers` file."""

    def __init__(self, folder: str | Path):
        self.root = Path(folder)
        self.label = str(self.root)
        self._headers = _parse_headers_file(self.root / "_headers")

    def get(self, path: str) -> Page:
        rel = path.lstrip("/")
        file = self.root / rel
        if file.is_dir() or not rel:
            file = file / "index.html"
        if not file.is_file():
            return Page(404)
        headers = {k: v for pat, hs in self._headers if _glob(pat, path) for k, v in hs.items()}
        return Page(200, file.read_text("utf-8", errors="replace")[:MAX_BYTES], headers)


def open_site(target: str):
    return LocalSite(target) if Path(target).is_dir() else WebSite(target)


def _page(status, raw: bytes, headers) -> Page:
    return Page(status, raw.decode("utf-8", errors="replace"),
                {k.lower(): v for k, v in headers.items()} if headers else {})


def _parse_headers_file(file: Path) -> list[tuple[str, dict[str, str]]]:
    rules: list[tuple[str, dict[str, str]]] = []
    if not file.is_file():
        return rules
    for line in file.read_text("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            rules.append((line.strip(), {}))
        elif rules and ":" in line:
            k, v = line.split(":", 1)
            rules[-1][1][k.strip().lower()] = v.strip()
    return rules


def _glob(pattern: str, path: str) -> bool:
    return path.startswith(pattern[:-1]) if pattern.endswith("*") else path == pattern
