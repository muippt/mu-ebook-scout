"""Standard Ebooks adapter — public-domain books, carefully produced.

The OPDS feed requires an access key, so this adapter parses the public
HTML search page (https://standardebooks.org/ebooks?query=...). Result
markup is schema.org annotated, which keeps parsing robust:

    <li typeof="schema:Book" about="/ebooks/jane-austen/pride-and-prejudice">
      ... <span property="schema:name">Pride and Prejudice</span>
      ... <p class="author" ...><span property="schema:name">Jane Austen</span>

EPUB download URLs follow the stable pattern:
    https://standardebooks.org/ebooks/{path}/downloads/{path with / -> _}.epub
"""
from __future__ import annotations

import re
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source, SourceError
from bookscout.sources._http import http_get_text

_SEARCH = "https://standardebooks.org/ebooks?query="
_MAX_HITS = 10
_LICENSE = "Public domain (Standard Ebooks edition)"

_ITEM_RE = re.compile(
    r'<li\s+typeof="schema:Book"\s+about="(?P<about>/ebooks/[^"]+)"\s*>'
    r".*?<span\s+property=\"schema:name\">(?P<title>[^<]+)</span>",
    re.S,
)
_AUTHOR_RE = re.compile(r'class="author".*?<span\s+property="schema:name">([^<]+)</span>', re.S)


class StandardEbooksSource(Source):
    """Standard Ebooks — free, liberated, carefully produced ebooks."""

    id = "standard_ebooks"
    label = "Standard Ebooks"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        query = " ".join(x for x in (title.strip(), author.strip()) if x)
        if not query:
            return []
        url = _SEARCH + quote(query)
        html = http_get_text(url, self.timeout, self.max_retries)
        if "ebooks-list" not in html:
            # A no-results page still renders the search form (name="query")
            # but no result list — that is an empty result, not a parse error.
            # Anything else means the page structure changed: raise so the
            # engine degrades this source instead of silently hiding books.
            if 'name="query"' in html or "No results" in html or "no results" in html:
                return []
            raise SourceError("unexpected page structure from standardebooks.org")

        hits: list[Hit] = []
        for m in _ITEM_RE.finditer(html):
            about = m.group("about")
            title_text = m.group("title").strip()
            if not title_text:
                continue
            author_m = _AUTHOR_RE.search(html, m.end())
            author_text = author_m.group(1).strip() if author_m else ""
            hits.append(self._to_hit(title_text, author_text, about))
            if len(hits) >= _MAX_HITS:
                break
        return hits

    # ------------------------------------------------------------------
    def _to_hit(self, title: str, author: str, about: str) -> Hit:
        # about: /ebooks/jane-austen/pride-and-prejudice
        segments = about[len("/ebooks/"):].strip("/")
        epub_url = (
            f"https://standardebooks.org/ebooks/{segments}"
            f"/downloads/{segments.replace('/', '_')}.epub"
        )
        return Hit(
            title=title,
            url=f"https://standardebooks.org{about}",
            source=self.id,
            source_label=self.label,
            author=author,
            language="en",
            formats=["EPUB"],
            hit_type=HitType.EBOOK,
            availability=Availability.FREE,
            license=_LICENSE,
            download_url=epub_url,
        )
