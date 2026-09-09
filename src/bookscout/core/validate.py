"""Magic-number validation for downloaded files.

The `get` command refuses to report success when a downloaded file's
content does not match the advertised format, so a misleading link can
never silently leave garbage on disk. Pure stdlib; only the first bytes
of each file are read.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

__all__ = ["sniff_format", "verify", "SUPPORTED_FORMATS"]

#: display format -> (human label) as used in Hit.formats
SUPPORTED_FORMATS = ("EPUB", "PDF", "MOBI")

_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_PDF_MAGIC = b"%PDF-"
_MOBI_MAGIC = b"BOOKMOBI"
_MOBI_OFFSET = 60


def sniff_format(path: str | Path) -> str | None:
    """Return "EPUB" | "PDF" | "MOBI" from magic bytes, or None.

    EPUB files are ZIP containers (PK...); MOBI marks the PalmDOC header
    at offset 60; PDF starts with %PDF-. Unknown content yields None.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(_MOBI_OFFSET + len(_MOBI_MAGIC))
    except OSError:
        return None
    if not head:
        return None
    if head.startswith(_PDF_MAGIC):
        return "PDF"
    if any(head.startswith(m) for m in _ZIP_MAGICS):
        return "EPUB"
    if head[_MOBI_OFFSET:_MOBI_OFFSET + len(_MOBI_MAGIC)] == _MOBI_MAGIC:
        return "MOBI"
    return None


def verify(path: str | Path, expected_format: str = "") -> tuple[bool, str]:
    """Verify a downloaded file against its advertised format.

    Args:
        path: file on disk.
        expected_format: one of ``SUPPORTED_FORMATS`` (case-insensitive),
            or an extension like ``"epub"``/``"pdf"``/``"txt"``. Unknown
            or empty values fall back to sniff-only mode (still detects
            HTML error pages masquerading as ebooks).

    Returns:
        ``(ok, detail)`` where ``detail`` is a human-readable sentence.
    """
    expected = (expected_format or "").strip().upper().lstrip(".")
    actual = sniff_format(path)
    size = _size_of(path)

    if actual == "EPUB":
        # additionally confirm the ZIP container has entries (a real book)
        try:
            with ZipFile(path) as zf:
                names = zf.namelist()
            if not names:
                return False, f"EPUB container is empty ({size})"
            return True, f"EPUB verified: ZIP container with {len(names)} entries ({size})"
        except BadZipFile:
            return False, f"magic bytes say EPUB but the ZIP container is broken ({size})"

    if actual == "PDF":
        return True, f"PDF verified: %PDF header present ({size})"
    if actual == "MOBI":
        return True, f"MOBI verified: BOOKMOBI header present ({size})"

    # Not a recognized ebook format.
    if expected in SUPPORTED_FORMATS:
        return (
            False,
            f"expected {expected} but the file is not a valid ebook format "
            f"(first bytes: {_head_hex(path)}) — likely an HTML error page",
        )
    # Sniff-only mode (e.g. plain .txt): just reject obvious HTML.
    head = _head_bytes(path)
    if head.lstrip().lower().startswith((b"<!doctype", b"<html")):
        return False, f"file looks like an HTML page, not a book ({size})"
    return True, f"format not verifiable by magic number ({size}); content check passed"


def _size_of(path: str | Path) -> str:
    try:
        n = Path(path).stat().st_size
    except OSError:
        return "unknown size"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.0f}KB"
    return f"{n}B"


def _head_bytes(path: str | Path, n: int = 16) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read(n)
    except OSError:
        return b""


def _head_hex(path: str | Path) -> str:
    return _head_bytes(path).hex()
