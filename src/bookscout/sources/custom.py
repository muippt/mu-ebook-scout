"""User-configured custom sources (~/.bookscout/custom_sources.json).

A custom source is a pure pass-through: we render a search URL template
and extract result links with a user-supplied regex. We never attempt to
download from custom sources — every Hit is LINK_ONLY with download_url
forced to None (the core rule: only curated public-domain sources may
provide download URLs).

Config format::

    [
      {
        "name": "My Source",
        "search_url": "https://example.com/search?q={title}",
        "link_pattern": "<a href=\\"(https://example.com/book/[^\\"]+)\\">([^<]+)</a>"
      }
    ]

`{title}` / `{author}` in search_url are replaced with URL-encoded values.
In link_pattern, capture group 1 is the result URL and optional group 2 is
the display title; with no groups the whole match is used as the URL.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source
from bookscout.sources._http import http_get_text

DEFAULT_CONFIG_PATH = Path.home() / ".bookscout" / "custom_sources.json"
_MAX_HITS = 10


class CustomSource(Source):
    """A single user-configured, link-pass-through source."""

    def __init__(self, name: str, search_url: str, link_pattern: str):
        self.name = name
        self.search_url = search_url
        self.link_pattern = link_pattern
        self.id = "custom-" + _slug(name)
        self.label = name

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        url = (
            self.search_url.replace("{title}", quote(title))
            .replace("{author}", quote((author or "").strip()))
            .replace("{language}", quote((language or "").strip()))
        )
        try:
            pattern = re.compile(self.link_pattern)
        except re.error:
            return []
        text = http_get_text(url, self.timeout, self.max_retries)

        hits: list[Hit] = []
        for m in pattern.finditer(text):
            if m.lastindex:  # at least one capture group
                link = (m.group(1) or "").strip()
                label = m.group(2).strip() if m.lastindex >= 2 and m.group(2) else ""
            else:
                link, label = m.group(0).strip(), ""
            if not link.startswith(("http://", "https://")):
                continue
            hits.append(
                Hit(
                    title=label or title,
                    url=link,
                    source=self.id,
                    source_label=self.label,
                    formats=[],
                    hit_type=HitType.METADATA,
                    availability=Availability.LINK_ONLY,
                    license="User-configured source",
                    download_url=None,  # pass-through only, never auto-get
                )
            )
            if len(hits) >= _MAX_HITS:
                break
        return hits


def get_custom_sources(config_path: str | Path | None = None) -> list[Source]:
    """Load custom sources from a JSON config file.

    Returns an empty list when the file is missing, unreadable, or holds
    no valid entries — custom sources are strictly optional.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        entries = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []

    sources: list[Source] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        search_url = str(entry.get("search_url") or "").strip()
        link_pattern = str(entry.get("link_pattern") or "").strip()
        if not (name and search_url and link_pattern):
            continue
        sources.append(CustomSource(name, search_url, link_pattern))
    return sources


def _slug(name: str) -> str:
    """Derive a stable lowercase id fragment from a source name."""
    slug = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", name.lower()).strip("-")
    return slug or "source"
