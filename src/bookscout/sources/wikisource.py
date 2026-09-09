"""Wikisource adapter — MediaWiki search API on zh + en Wikisource.

Wikisource hosts CC BY-SA licensed full texts that are read online; we only
return page links (no file downloads), hence ONLINE_FULLTEXT + download_url
= None.
"""
from __future__ import annotations

from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source
from bookscout.sources._http import http_get_json

#: language code -> API endpoint
_SITES = {
    "zh": "https://zh.wikisource.org/w/api.php",
    "en": "https://en.wikisource.org/w/api.php",
}
_PER_SITE_LIMIT = 5
_LICENSE = "CC BY-SA"


class WikisourceSource(Source):
    """Multilingual Wikisource (zh/en) full-text library."""

    id = "wikisource"
    label = "Wikisource"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        sites = _target_sites(language)
        hits: list[Hit] = []
        for lang, api in sites.items():
            url = (
                f"{api}?action=query&list=search&format=json"
                f"&srlimit={_PER_SITE_LIMIT}"
                f"&srsearch=intitle:{quote(title)}"
            )
            data = http_get_json(url, self.timeout, self.max_retries)
            for result in (data.get("query") or {}).get("search", []):
                page_title = result.get("title", "")
                if not page_title:
                    continue
                slug = quote(page_title.replace(" ", "_"), safe="")
                hits.append(
                    Hit(
                        title=page_title,
                        url=f"https://{lang}.wikisource.org/wiki/{slug}",
                        source=self.id,
                        source_label=self.label,
                        language=lang,
                        formats=[],
                        hit_type=HitType.ONLINE_FULLTEXT,
                        availability=Availability.FREE,
                        license=_LICENSE,
                        download_url=None,
                        extra={"pageid": result.get("pageid")},
                    )
                )
        return hits


def _target_sites(language: str) -> dict[str, str]:
    """Pick which Wikisource instances to query from the language hint."""
    language = (language or "").strip().lower()
    if language in _SITES:
        return {language: _SITES[language]}
    # "auto" / unknown / empty: search both and merge.
    return dict(_SITES)
