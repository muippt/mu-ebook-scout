"""Google Books adapter — metadata, preview links, and purchase/borrow entry.

The Google Books API shares an anonymous quota across all keyless callers
from one IP, which is frequently exhausted (HTTP 429). Users can get a free
API key from Google Cloud Console and export it as
``BOOKSCOUT_GOOGLE_BOOKS_KEY`` — the source is inactive without a key
(it would only burn the already-exhausted shared quota).

Hits are catalog records: the books.google.com volume page is the hit URL;
free Google ebooks get a direct download link, everything else is metadata
with preview/purchase options. This is a metadata channel, not a file
repository.
"""
from __future__ import annotations

import os
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source, SourceError
from bookscout.sources._http import http_get_json

_SEARCH = "https://www.googleapis.com/books/v1/volumes"
_MAX_HITS = 8


def google_books_key() -> str:
    """Return the configured Google Books API key, or an empty string."""
    return (os.environ.get("BOOKSCOUT_GOOGLE_BOOKS_KEY") or "").strip()


class GoogleBooksSource(Source):
    """Google Books — catalog metadata with preview / free-ebook links."""

    id = "google_books"
    label = "Google Books"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        key = google_books_key()
        if not key:
            # Keyless access rides an exhausted shared quota — stay silent
            # instead of failing every search with 429 noise.
            return []

        query = " ".join(x for x in (title, author.strip()) if x)
        url = (
            f"{_SEARCH}?q={quote(query)}"
            f"&maxResults={_MAX_HITS}&country=US&key={key}"
        )
        data = http_get_json(url, self.timeout, self.max_retries)

        hits: list[Hit] = []
        for item in data.get("items", []):
            hit = self._to_hit(item)
            if hit:
                hits.append(hit)
            if len(hits) >= _MAX_HITS:
                break
        return hits

    # ------------------------------------------------------------------
    def _to_hit(self, item: dict) -> Hit | None:
        info = item.get("volumeInfo") or {}
        title = info.get("title", "")
        if not title:
            return None
        access = item.get("accessInfo") or {}
        free_epub = (access.get("epub") or {}).get("downloadLink")
        free_pdf = (access.get("pdf") or {}).get("downloadLink")
        web_reader = (access.get("webReaderLink") or "").strip()
        link = info.get("infoLink") or f"https://books.google.com/"

        if free_epub or free_pdf:
            return Hit(
                title=title,
                url=link,
                source=self.id,
                source_label=self.label,
                author=", ".join((info.get("authors") or [])[:3]),
                language=(info.get("language") or "")[:2],
                formats=["EPUB" if free_epub else "PDF"],
                hit_type=HitType.EBOOK,
                availability=Availability.FREE,
                license="Google Books free ebook",
                download_url=free_epub or free_pdf,
                extra={"volume_id": item.get("id")},
            )
        return Hit(
            title=title,
            url=web_reader or link,
            source=self.id,
            source_label=self.label,
            author=", ".join((info.get("authors") or [])[:3]),
            language=(info.get("language") or "")[:2],
            formats=[],
            hit_type=HitType.METADATA,
            availability=Availability.LINK_ONLY,
            license="Metadata / preview (purchase or borrow via Google Books)",
            download_url=None,
            extra={"volume_id": item.get("id"), "web_reader": web_reader},
        )
