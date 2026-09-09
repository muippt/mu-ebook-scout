"""ctext.org adapter — Chinese Text Project (pre-Qin through Han-era classics).

The public API endpoint ``https://api.ctext.org/searchtexts?title=...``
returns catalog matches (urn + title) and transparently accepts both
simplified and traditional queries. We surface works as ONLINE_FULLTEXT
links: ``urn: ctp:analects`` → ``https://ctext.org/analects``.

ctext.org covers texts Wikisource/CBETA may miss (pre-Qin philosophers,
histories, commentaries); its content is public-domain classical Chinese
with site-specific presentation terms, so hits are read-online links.
"""
from __future__ import annotations

from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source
from bookscout.sources._http import http_get_json

_SEARCH = "https://api.ctext.org/searchtexts"
_MAX_HITS = 8
_LICENSE = "Public-domain classical text (site presentation terms apply)"


class CtextViewSource(Source):
    """Chinese Text Project — classical Chinese full-text library."""

    id = "ctext"
    label = "ctext.org 中国哲学书电子化计划"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        # Classical Chinese canon: only meaningful for zh / auto queries.
        if language and language != "auto" and language != "zh":
            return []

        data = http_get_json(
            f"{_SEARCH}?title={quote(title)}", self.timeout, self.max_retries
        )

        hits: list[Hit] = []
        for book in data.get("books", []):
            urn = book.get("urn", "")
            display_title = book.get("title", "")
            if not urn or not display_title:
                continue
            hits.append(self._to_hit(display_title, urn))
            if len(hits) >= _MAX_HITS:
                break
        return hits

    # ------------------------------------------------------------------
    def _to_hit(self, title: str, urn: str) -> Hit:
        # urn "ctp:analects" -> https://ctext.org/analects
        path = urn[len("ctp:"):] if urn.startswith("ctp:") else urn
        return Hit(
            title=title,
            url=f"https://ctext.org/{path}" if path else "https://ctext.org/",
            source=self.id,
            source_label=self.label,
            language="zh",
            formats=[],
            hit_type=HitType.ONLINE_FULLTEXT,
            availability=Availability.FREE,
            license=_LICENSE,
            download_url=None,
            extra={"urn": urn},
        )
