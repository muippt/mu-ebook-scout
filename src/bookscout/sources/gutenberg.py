"""Project Gutenberg adapter via the public Gutendex JSON API.

Docs: https://gutendex.com — anonymous, no key required.
"""
from __future__ import annotations

from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source
from bookscout.sources._http import http_get_json

_BASE = "https://gutendex.com/books/"
_MAX_HITS = 10

#: Gutendex format MIME -> display format.
_FORMAT_MAP = {
    "application/epub+zip": "EPUB",
    "application/pdf": "PDF",
    "application/x-mobipocket-ebook": "MOBI",
}


class GutenbergSource(Source):
    """Project Gutenberg — 70k+ public-domain books."""

    id = "gutenberg"
    label = "Project Gutenberg"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        query = " ".join(x for x in (title.strip(), author.strip()) if x)
        if not query:
            return []
        url = _BASE + "?search=" + quote(query)
        # Optional language narrowing (e.g. languages=zh).
        if language and language != "auto":
            url += "&languages=" + quote(language)
        data = http_get_json(url, self.timeout, self.max_retries)

        hits: list[Hit] = []
        for item in data.get("results", [])[:_MAX_HITS]:
            formats = item.get("formats") or {}
            fmts = [
                label
                for mime, label in _FORMAT_MAP.items()
                if formats.get(mime)
            ]
            download_url = (
                formats.get("application/epub+zip")
                or formats.get("application/pdf")
            )
            hits.append(
                Hit(
                    title=item.get("title", ""),
                    url=formats.get("text/html")
                    or f"https://www.gutenberg.org/ebooks/{item.get('id', '')}",
                    source=self.id,
                    source_label=self.label,
                    author=", ".join(
                        a.get("name", "") for a in item.get("authors", [])
                    ),
                    language=(item.get("languages") or [""])[0],
                    formats=fmts,
                    hit_type=HitType.EBOOK if download_url else HitType.METADATA,
                    availability=(
                        Availability.FREE if download_url else Availability.LINK_ONLY
                    ),
                    license="Public domain",
                    download_url=download_url,
                    extra={"gutenberg_id": item.get("id")},
                )
            )
        return hits
