"""MCP server for mu-ebook-scout (optional dependency).

Exposes the bookscout aggregation engine to any MCP-capable client or
agent. Distributed as an optional extra:

    pip install mu-ebook-scout[mcp]

Design notes
------------
- ``search`` is read-only: it fans out to the built-in public-domain /
  open-license sources plus the user's custom (link-only) sources and
  returns a text report. It never downloads anything.
- ``get`` downloads exactly ONE file, and only from hosts on a hardcoded
  allowlist of built-in public-domain sources. Custom/user-configured
  sources are pass-through by design: the tool surfaces their links but
  refuses to fetch them, so it can never proxy arbitrary user URLs.
"""

from __future__ import annotations

import posixpath
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .core.fallback import search_all
from .core.report import render_text
from .sources import SOURCE_REGISTRY, get_custom_sources

try:  # magic-number verification lives in core; optional at this layer
    from .core import validate as _validate
except ImportError:  # pragma: no cover - core is developed in parallel
    _validate = None

mcp = FastMCP("mu-ebook-scout")

#: Hardcoded download allowlist: only built-in public-domain source hosts.
#: Anything else (custom sources included) is rejected by ``get``.
_ALLOWED_HOSTS = (
    "gutenberg.org",
    "gutendex.com",
    "standardebooks.org",
    "openlibrary.org",
    "archive.org",
    "raw.githubusercontent.com",
)

#: On raw.githubusercontent.com, only these two public-domain
#: classical-Chinese repositories may be fetched.
_ALLOWED_GH_REPOS = ("zhpelo/wenshuoge", "garychowcmu/daizhigev20")

#: Hard cap for a single download.
_MAX_BYTES = 100 * 1024 * 1024  # 100 MB

_USER_AGENT = "mu-ebook-scout/1.0 (+https://github.com/muippt/mu-ebook-scout)"


def _collect_sources():
    """Built-in registry sources + user custom sources as Source objects.

    Accepts SOURCE_REGISTRY being either a dict (id -> Source) or an
    iterable of Source instances, so this module stays agnostic to the
    exact registry shape owned by the sources package.
    """
    registry = SOURCE_REGISTRY
    if hasattr(registry, "values"):
        builtin = list(registry.values())
    else:
        builtin = list(registry)
    custom = get_custom_sources() or []
    return builtin + list(custom)


def _check_url(url: str) -> str | None:
    """Return an error message if `url` may not be fetched, else None."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "invalid URL"
    if parts.scheme not in ("http", "https"):
        return "only http/https URLs are supported"
    host = (parts.hostname or "").lower()
    if not host:
        return "URL has no host"
    allowed = any(host == a or host.endswith("." + a) for a in _ALLOWED_HOSTS)
    if not allowed:
        return (
            f"host '{host}' is not in the built-in public-domain source "
            "allowlist; custom sources are link-only by design - open the "
            "link in a browser instead"
        )
    if host == "raw.githubusercontent.com" or host.endswith(".raw.githubusercontent.com"):
        path = "/" + (parts.path or "").lstrip("/")
        if not any(path.startswith("/" + repo + "/") for repo in _ALLOWED_GH_REPOS):
            return (
                "raw.githubusercontent.com URLs are limited to the "
                "wenshuoge and daizhigev20 public-domain repositories"
            )
    return None


def _download(url: str, dest: Path) -> None:
    """Stream `url` to `dest` with a hard 100 MB size cap."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response, open(dest, "wb") as fh:
        total = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_BYTES:
                raise ValueError("download exceeds the 100 MB size cap")
            fh.write(chunk)


@mcp.tool()
def search(title: str, author: str = "", language: str = "auto") -> str:
    """Search public-domain and open-license ebook sources.

    Fans out across all built-in sources (Project Gutenberg, Open
    Library / archive.org, Wikisource zh/en, Standard Ebooks, CBETA,
    wenshuoge, daizhigev20) plus the user's custom link-only sources,
    degrades gracefully when individual sources fail, and returns a
    ranked text report grouped by how the item can be obtained.

    Args:
        title: Book title to search for (Chinese or English).
        author: Optional author name to narrow results.
        language: "zh", "en", or "auto" (detect from query).

    Returns:
        A text report; when nothing is found it also lists manual
        entry points and legitimate borrow/purchase channels.
    """
    sources = _collect_sources()
    hits, failed_sources = search_all(
        title=title, author=author, language=language, sources=sources
    )
    return render_text(hits, failed_sources)


@mcp.tool()
def get(url: str, filename: str = "", out_dir: str = "") -> str:
    """Download one ebook file from a built-in public-domain source.

    Only URLs from the built-in sources are accepted: gutenberg.org,
    gutendex.com, standardebooks.org, openlibrary.org, archive.org,
    and raw.githubusercontent.com paths inside the wenshuoge or
    daizhigev20 public-domain repositories. Custom-source URLs are
    rejected - this tool never proxies user-configured sources.

    The downloaded file is verified by magic number before it is
    reported as success; failed files are deleted. 100 MB cap.

    Args:
        url: Direct download URL previously surfaced by ``search``.
        filename: Optional output filename (defaults to the URL basename).
        out_dir: Optional output directory (defaults to cwd).

    Returns:
        A short status message with the saved path, or an ERROR line.
    """
    error = _check_url(url)
    if error:
        return f"ERROR: {error}"

    if not filename:
        filename = (
            posixpath.basename(urllib.parse.urlsplit(url).path)
            or "bookscout_download"
        )
    # Never let a filename escape the output directory.
    filename = Path(filename).name

    out_path = Path(out_dir).expanduser() if out_dir else Path.cwd()
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return f"ERROR: cannot create output directory: {exc}"
    dest = out_path / filename

    try:
        _download(url, dest)
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        return f"ERROR: {exc}"
    except (OSError, urllib.error.URLError) as exc:
        dest.unlink(missing_ok=True)
        return f"ERROR: download failed: {exc}"

    if _validate is not None:
        try:
            verified = bool(_validate.verify(str(dest)))
        except Exception:
            verified = False
        if not verified:
            dest.unlink(missing_ok=True)
            return "ERROR: downloaded file failed magic-number verification; file removed"

    return f"Downloaded to {dest}"


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
