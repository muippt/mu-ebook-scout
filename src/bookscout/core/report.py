"""Report rendering, session persistence and fallback output.

- ``render_text`` / ``render_json`` turn hits into user-facing output;
- ``purchase_links`` builds URL-encoded links to legal channels;
- ``save_session`` / ``load_session`` persist the last search so the
  explicit ``get N`` step can resolve "N" without re-searching;
- ``fallback_output`` guarantees the "never return empty-handed" rule:
  manual search entries + legal purchase channels.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from bookscout.core.model import Availability, Hit

__all__ = [
    "render_text",
    "render_json",
    "purchase_links",
    "extended_links",
    "fallback_output",
    "order_for_display",
    "save_session",
    "load_session",
    "hits_from_session",
    "SESSION_PATH",
]

#: Where the last search session is persisted (explicit-get contract).
SESSION_DIR = Path.home() / ".bookscout"
SESSION_PATH = SESSION_DIR / "last_search.json"

#: (label, url template) for legal purchase / reading channels.
_PURCHASE_CHANNELS = (
    ("微信读书 WeRead", "https://weread.qq.com/web/search/global?keyword={q}"),
    ("豆瓣读书 Douban", "https://book.douban.com/subject_search?search_text={q}"),
    ("京东图书 JD", "https://search.jd.com/Search?keyword={q}"),
)

#: (label, url template) for extended resource entries. These are pure
#: search-entry links: the tool never queries, parses or downloads from
#: these sites — it only builds the URL locally and hands it to the user,
#: who completes any search/download in their own browser.
_EXTENDED_CHANNELS = (
    (
        "Anna's Archive",
        "https://annas-archive.org/search?q={q}",
    ),
    (
        "LibGen",
        "https://libgen.is/search.php?req={q}",
    ),
)

#: Manual search entries shown when nothing was found.
_MANUAL_ENTRIES = (
    ("Wikisource 中文文库", "https://zh.wikisource.org/w/index.php?search={q}"),
    ("Project Gutenberg", "https://www.gutenberg.org/ebooks/search/?query={q}"),
    ("Open Library", "https://openlibrary.org/search?q={q}"),
    ("Internet Archive", "https://archive.org/search?query={q}"),
    ("文硕阁公版书", "https://github.com/search?q=repo%3Azhpelo%2Fwenshuoge+{q}"),
)

_AVAILABILITY_LABEL = {
    Availability.FREE: "free download",
    Availability.BORROW: "borrow (free account)",
    Availability.PURCHASE: "purchase",
    Availability.LINK_ONLY: "link only",
}


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

def order_for_display(hits: list[Hit]) -> list[Hit]:
    """Return hits in display order.

    ``search_all`` already sorts by score; display order additionally
    keeps custom/link-only sources after builtin free hits with equal
    scores (stable sort, no re-scoring).
    """
    return sorted(hits, key=lambda h: (-h.score, h.availability != Availability.FREE))


# ---------------------------------------------------------------------------
# Text / JSON rendering
# ---------------------------------------------------------------------------

def render_text(
    hits: list[Hit],
    query_title: str = "",
    query_author: str = "",
    failed_sources: Optional[list[str]] = None,
) -> str:
    """Render hits grouped by source; always returns a non-empty string."""
    lines: list[str] = []

    if query_title:
        header = f"Results for: {query_title}"
        if query_author:
            header += f" — {query_author}"
        lines.extend([header, ""])

    if failed_sources:
        lines.append(
            "⚠ temporarily unavailable sources: " + ", ".join(failed_sources)
        )
        lines.append("")

    if not hits:
        lines.append(f"No public-domain results for: {query_title or '(no title)'}")
        lines.append("")
        lines.append("Extended resource entries (download in your browser):")
        lines.extend(
            f"  - {label}: {url}"
            for label, url in extended_links(query_title, query_author)
        )
        lines.append("")
        lines.append("Manual search entries:")
        lines.extend(
            f"  - {label}: {url}" for label, url in _manual_links(query_title)
        )
        lines.append("")
        lines.append("Legal reading / purchase channels:")
        lines.extend(
            f"  - {label}: {url}"
            for label, url in purchase_links(query_title, query_author)
        )
        return "\n".join(lines)

    # Group hits by source, keeping first-seen order of the sources.
    groups: dict[str, list[Hit]] = {}
    for hit in hits:
        groups.setdefault(hit.source_label, []).append(hit)

    counter = 0
    for source_label, group in groups.items():
        lines.append(f"[{source_label}]")
        for hit in group:
            counter += 1
            parts = [f"{counter}.", hit.title]
            if hit.author:
                parts.append(hit.author)
            meta = []
            if hit.formats:
                meta.append("/".join(hit.formats))
            meta.append(_AVAILABILITY_LABEL.get(hit.availability, hit.availability))
            if hit.license:
                meta.append(hit.license)
            if hit.size_hint:
                meta.append(hit.size_hint)
            lines.append(f"  {' '.join(parts[:2])} — {hit.author or ''}".rstrip(" —"))
            lines.append(f"     ({'; '.join(meta)})")
            lines.append(f"     {hit.url}")
            if hit.download_url:
                lines.append(f"     download: {hit.download_url}")
            lines.append("")
    lines.append("Extended resource entries (download in your browser):")
    lines.extend(
        f"  - {label}: {url}"
        for label, url in extended_links(query_title, query_author)
    )
    lines.append("")
    lines.append("Tip: download explicitly with  bookscout get <N>")
    return "\n".join(lines).rstrip()


def render_json(
    hits: list[Hit],
    failed_sources: Optional[list[str]] = None,
    query_title: str = "",
    query_author: str = "",
) -> str:
    """Render the result as a JSON document (for scripts / agents)."""
    payload = {
        "query": {"title": query_title, "author": query_author},
        "failed_sources": list(failed_sources or []),
        "count": len(hits),
        "results": [_hit_to_dict(h) for h in hits],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _hit_to_dict(hit: Hit) -> dict[str, Any]:
    return {
        "title": hit.title,
        "author": hit.author,
        "url": hit.url,
        "download_url": hit.download_url,
        "source": hit.source,
        "source_label": hit.source_label,
        "language": hit.language,
        "formats": list(hit.formats),
        "hit_type": hit.hit_type,
        "availability": hit.availability,
        "license": hit.license,
        "size_hint": hit.size_hint,
        "score": hit.score,
    }


# ---------------------------------------------------------------------------
# Purchase / manual links
# ---------------------------------------------------------------------------

def purchase_links(title: str, author: str = "") -> list[tuple[str, str]]:
    """URL-encoded links to legal purchase channels for a query."""
    query = _query_string(title, author)
    encoded = quote(query)
    return [(label, tpl.format(q=encoded)) for label, tpl in _PURCHASE_CHANNELS]


def extended_links(title: str, author: str = "") -> list[tuple[str, str]]:
    """URL-encoded search-entry links to extended resource sites.

    The tool itself never contacts these sites — the URLs are built
    locally from the query and opened by the user in their own browser,
    where any search and download happens entirely on their side.
    """
    query = _query_string(title, author)
    if not query:
        return []
    encoded = quote(query)
    return [(label, tpl.format(q=encoded)) for label, tpl in _EXTENDED_CHANNELS]


def _query_string(title: str, author: str) -> str:
    return " ".join(
        x for x in ((title or "").strip(), (author or "").strip()) if x
    )


def _manual_links(title: str) -> list[tuple[str, str]]:
    encoded = quote((title or "").strip())
    return [(label, tpl.format(q=encoded)) for label, tpl in _MANUAL_ENTRIES]


def fallback_output(title: str, author: str = "") -> str:
    """Never return empty-handed: manual entries + legal channels."""
    return render_text([], title, author)


# ---------------------------------------------------------------------------
# Session persistence (for the explicit `get N` step)
# ---------------------------------------------------------------------------

_HIT_FIELDS = {
    "title", "url", "source", "source_label", "author", "language",
    "formats", "hit_type", "availability", "license", "size_hint",
    "score", "download_url", "extra",
}


def save_session(hits: list[Hit], title: str = "", author: str = "") -> None:
    """Persist the last search so ``get N`` can resolve the index."""
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": {"title": title, "author": author},
            "hits": [_hit_to_dict(h) for h in hits],
        }
        SESSION_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        # Session persistence is best-effort; search must not fail on it.
        pass


def load_session() -> Optional[dict[str, Any]]:
    """Load the last search session, or None if absent/corrupt."""
    try:
        data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("hits"), list):
        return None
    return data


def hits_from_session(session: dict[str, Any]) -> list[Hit]:
    """Rebuild Hit objects from a session loaded via ``load_session``."""
    hits: list[Hit] = []
    for item in session.get("hits", []):
        if not isinstance(item, dict):
            continue
        kwargs = {k: v for k, v in item.items() if k in _HIT_FIELDS}
        try:
            hits.append(Hit(**kwargs))
        except TypeError:
            continue
    return hits
