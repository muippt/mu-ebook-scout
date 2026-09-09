"""Shared contract for mu-ebook-scout: Hit data model + Source interface.

Every source adapter implements `Source`. The fallback engine and report
layer only depend on this module — keep it stable and dependency-free.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Sequence

__all__ = ["HitType", "Availability", "Hit", "Source", "SourceError"]


class HitType:
    """Kind of resource a Hit points to."""

    EBOOK = "ebook"          # downloadable EPUB/PDF/MOBI file
    AUDIOBOOK = "audiobook"  # audio files (roadmap, not v1.0)
    ONLINE_FULLTEXT = "online_fulltext"  # read on page, no single file
    METADATA = "metadata"    # catalog record only (borrow/purchase info)


class Availability:
    """How a user can actually obtain the item."""

    FREE = "free"            # direct public-domain download
    BORROW = "borrow"        # free account + lending (e.g. archive.org)
    PURCHASE = "purchase"    # paid channel
    LINK_ONLY = "link_only"  # custom/user-configured source, pass-through


@dataclass
class Hit:
    """One search result from one source."""

    title: str
    url: str                       # human-facing page (NOT a raw download URL)
    source: str                    # source id, e.g. "gutenberg"
    source_label: str              # display name, e.g. "Project Gutenberg"
    author: str = ""
    language: str = ""             # ISO 639-1, e.g. "zh", "en"
    formats: Sequence[str] = field(default_factory=list)  # ["EPUB","PDF"]
    hit_type: str = HitType.EBOOK
    availability: str = Availability.FREE
    license: str = "Public domain"  # short license note, shown to user
    size_hint: str = ""            # e.g. "2.4MB" — display only
    score: float = 0.0             # 0-100 relevance, filled by engine
    download_url: Optional[str] = None  # direct file URL; None = no auto get
    extra: dict = field(default_factory=dict)

    def compute_score(self, query_title: str, query_author: str = "") -> float:
        """0-100 confidence score (librarr-style). Engine calls this."""
        q = _norm(query_title)
        t = _norm(self.title)
        s = 0.0
        if q and (q == t or q in t or t in q):
            s += 60.0
        elif q and _shared_tokens(q, t) >= 0.5:
            s += 35.0
        if query_author and self.author:
            qa, a = _norm(query_author), _norm(self.author)
            if qa and (qa in a or a in qa):
                s += 20.0
        if self.availability == Availability.FREE:
            s += 10.0
        if self.hit_type == HitType.EBOOK:
            s += 5.0
        if "EPUB" in self.formats:
            s += 5.0
        return min(100.0, s)


class SourceError(Exception):
    """A source failed (network, parse, rate-limit). Engine degrades."""


class Source:
    """Base class for every book source adapter.

    Subclasses set `id`, `label`, and implement `search()`.
    Raise SourceError on failure; return [] when nothing found.
    """

    id: str = "base"
    label: str = "Base Source"
    #: max seconds for one HTTP request
    timeout: float = 15.0
    #: per-request retry budget inside the adapter (engine adds layer retry)
    max_retries: int = 2

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        raise NotImplementedError


def _norm(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _shared_tokens(a: str, b: str) -> float:
    ta = {x for x in a.split() if x}
    tb = {x for x in b.split() if x}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def hits_hash(hits: list[Hit]) -> str:
    """Stable short hash of a result list, used for `get` session files."""
    raw = "|".join(f"{h.source}:{h.url}" for h in hits)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
