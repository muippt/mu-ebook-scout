"""LibriVox adapter — free public-domain audiobooks.

API: ``https://librivox.org/api/feed/audiobooks?title=...&format=json``.
The endpoint rejects non-browser user agents with a 404, so this adapter
sends a desktop-browser UA — LibriVox's own web catalog sends the same.

Hits are AUDIOBOOK records: the catalog page is the hit URL; the whole-book
zip (hosted on archive.org) is the download URL. All recordings are of
public-domain texts, read by volunteers (public domain dedication).
"""
from __future__ import annotations

from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source
from bookscout.sources._http import http_get_json

_SEARCH = "https://librivox.org/api/feed/audiobooks"
_MAX_HITS = 8
_LICENSE = "Public domain (volunteer recording)"

#: librivox.org 404s requests carrying tool-style user agents.
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class LibrivoxSource(Source):
    """LibriVox — free public-domain audiobooks (MP3/M4B)."""

    id = "librivox"
    label = "LibriVox"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        if language and language not in ("auto", "en"):
            return []

        url = f"{_SEARCH}?title={quote(title)}&format=json&limit={_MAX_HITS}"
        if author.strip():
            url = f"{_SEARCH}?title={quote(title)}&author={quote(author.strip())}" \
                  f"&format=json&limit={_MAX_HITS}"
        data = http_get_json(url, self.timeout, self.max_retries, user_agent=_BROWSER_UA)

        hits: list[Hit] = []
        for book in data.get("books", []):
            hits.append(self._to_hit(book))
            if len(hits) >= _MAX_HITS:
                break
        return hits

    # ------------------------------------------------------------------
    def _to_hit(self, book: dict) -> Hit:
        authors = book.get("authors") or []
        author_names = ", ".join(
            f"{a.get('first_name', '')} {a.get('last_name', '')}".strip()
            for a in authors[:3]
        )
        return Hit(
            title=book.get("title", ""),
            url=book.get("url_librivox", "") or "https://librivox.org/",
            source=self.id,
            source_label=self.label,
            author=author_names,
            language=(book.get("language") or "").lower()[:2] or "en",
            formats=["MP3", "M4B"],
            hit_type=HitType.AUDIOBOOK,
            availability=Availability.FREE,
            license=_LICENSE,
            download_url=book.get("url_zip_file") or None,
            extra={
                "librivox_id": book.get("id"),
                "totaltime": book.get("totaltime"),
                "rss": book.get("url_rss"),
            },
        )
