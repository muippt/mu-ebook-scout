"""CBETA Chinese Buddhist canon adapter.

Uses the CBData web API (https://cbdata.dila.edu.tw, maintained by DILA).
The catalog search endpoint returns typed results; we keep only
`type == "work"` entries (scripture-level works) and link to the
cbetaonline reader page — read-online only, no file download.

The API only matches **traditional** Chinese titles (``金刚经`` returns
zero results while ``金剛經`` works), so a simplified query with no
hits is automatically retried converted to traditional characters.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source
from bookscout.sources._http import http_get_json
from bookscout.sources.github_books import _T2S_PLAIN, _T2S_TABLE

_SEARCH = "https://cbdata.dila.edu.tw/stable/search/toc?q="
_MAX_HITS = 8
_LICENSE = "CC BY-NC-SA 4.0 (non-commercial)"

#: simplified -> traditional, inverted from github_books' T2S pair table.
#: Query-grade approximation: for duplicate simplified characters the
#: first traditional mapping wins, which is good enough for API queries.
_S2T = str.maketrans({s: t for t, s in zip(_T2S_TABLE, _T2S_PLAIN)})
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class CbetaSource(Source):
    """CBETA — Chinese Buddhist electronic canon (read online)."""

    id = "cbeta"
    label = "CBETA 中华电子佛典"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        # Chinese canon: only meaningful for zh / auto queries.
        if language and language != "auto" and language != "zh":
            return []

        url = _SEARCH + quote(title)
        data = http_get_json(url, self.timeout, self.max_retries)

        if not data.get("results") and _CJK_RE.search(title):
            # The API only matches traditional titles — retry converted.
            traditional = title.translate(_S2T)
            if traditional != title:
                data = http_get_json(
                    _SEARCH + quote(traditional), self.timeout, self.max_retries
                )

        hits: list[Hit] = []
        for result in data.get("results", []):
            if result.get("type") != "work":
                continue
            work_id = result.get("work", "")
            if not work_id:
                continue
            hits.append(
                Hit(
                    title=result.get("title", ""),
                    url=f"https://cbetaonline.dila.edu.tw/zh/{work_id}",
                    source=self.id,
                    source_label=self.label,
                    author=result.get("byline", ""),
                    language="zh",
                    formats=[],
                    hit_type=HitType.ONLINE_FULLTEXT,
                    availability=Availability.FREE,
                    license=_LICENSE,
                    download_url=None,
                    extra={
                        "work": work_id,
                        "file": result.get("file", ""),
                        "juan": result.get("juan"),
                    },
                )
            )
            if len(hits) >= _MAX_HITS:
                break
        return hits
