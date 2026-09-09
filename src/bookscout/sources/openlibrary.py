"""Open Library adapter (search API + archive.org lending check).

Flow:
  1. https://openlibrary.org/search.json — anonymous catalog search.
  2. For records with an Internet Archive id (`ia`), consult
     https://archive.org/metadata/{ia} to decide FREE / BORROW.
     An archive.org failure degrades the hit to METADATA instead of
     failing the whole source.
  3. If openlibrary.org itself is unreachable, fall back to searching
     archive.org's own advancedsearch endpoint directly (the two are
     separately operated and can have different reachability in some
     networks). The fallback reports catalog/borrow info — downloads
     for verified-free items still go through the normal path.
"""
from __future__ import annotations

from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source, SourceError
from bookscout.sources._http import http_get_json

_SEARCH = "https://openlibrary.org/search.json"
_FIELDS = "key,title,author_name,language,ia,has_fulltext"
_MAX_HITS = 10

#: archive.org fallback search (used when openlibrary.org is unreachable).
_IA_SEARCH = "https://archive.org/advancedsearch.php"


class OpenLibrarySource(Source):
    """Open Library — catalog records with archive.org borrow/free status."""

    id = "openlibrary"
    label = "Open Library"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        query = " ".join(x for x in (title.strip(), author.strip()) if x)
        if not query:
            return []
        url = (
            f"{_SEARCH}?q={quote(query)}"
            f"&fields={_FIELDS}&limit={_MAX_HITS}"
        )
        try:
            data = http_get_json(url, self.timeout, self.max_retries)
        except SourceError:
            # openlibrary.org unreachable: try archive.org's own search
            # endpoint (separately operated, different reachability).
            return self._search_archive_org(query)

        hits: list[Hit] = []
        for doc in data.get("docs", [])[:_MAX_HITS]:
            hits.append(self._to_hit(doc))
        return hits

    # ------------------------------------------------------------------
    def _search_archive_org(self, query: str) -> list[Hit]:
        """Fallback path: search archive.org texts directly."""
        url = (
            f"{_IA_SEARCH}?q=title%3A%28{quote(query)}%29+AND+mediatype%3Atexts"
            "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=creator"
            f"&rows={_MAX_HITS}&output=json"
        )
        data = http_get_json(url, self.timeout, self.max_retries)
        hits: list[Hit] = []
        for doc in data.get("response", {}).get("docs", [])[:_MAX_HITS]:
            identifier = doc.get("identifier")
            if not identifier:
                continue
            creator = doc.get("creator")
            author = (
                ", ".join(creator)[:120] if isinstance(creator, list) else str(creator or "")[:120]
            )
            meta = self._archive_metadata(identifier)
            restricted = (
                meta is None
                or (meta.get("metadata") or {}).get("access-restricted-item") == "true"
            )
            files = (meta or {}).get("files") or []
            fmts = sorted(
                {
                    label
                    for want_ext, label in ((".epub", "EPUB"), (".pdf", "PDF"))
                    if any(str(f.get("name", "")).lower().endswith(want_ext) for f in files)
                }
            )
            hits.append(
                Hit(
                    title=doc.get("title", ""),
                    url=f"https://archive.org/details/{quote(identifier)}",
                    source=self.id,
                    source_label=self.label,
                    author=author,
                    formats=fmts,
                    hit_type=HitType.METADATA,
                    availability=Availability.BORROW if restricted else Availability.FREE,
                    download_url=None,  # borrow/download flow stays in-browser
                    extra={"ia_id": identifier},
                )
            )
        return hits

    # ------------------------------------------------------------------
    def _to_hit(self, doc: dict) -> Hit:
        key = doc.get("key", "")
        base = {
            "title": doc.get("title", ""),
            "source": self.id,
            "source_label": self.label,
            "author": ", ".join((doc.get("author_name") or [])[:3]),
            "language": (doc.get("language") or [""])[0],
            "extra": {"openlibrary_key": key},
        }
        page_url = f"https://openlibrary.org{key}"
        ia = doc.get("ia")
        if not ia:
            return Hit(
                **base,
                url=page_url,
                formats=[],
                hit_type=HitType.METADATA,
                availability=Availability.LINK_ONLY,
                download_url=None,
            )

        ia_id = ia[0] if isinstance(ia, list) else str(ia)
        details_url = f"https://archive.org/details/{ia_id}"
        meta = self._archive_metadata(ia_id)
        if meta is None:
            # archive.org unreachable: degrade to catalog metadata, no error.
            return Hit(
                **base,
                url=details_url,
                formats=[],
                hit_type=HitType.METADATA,
                availability=Availability.LINK_ONLY,
                download_url=None,
            )

        if (meta.get("metadata") or {}).get("access-restricted-item") == "true":
            return Hit(
                **base,
                url=details_url,
                formats=[],
                hit_type=HitType.METADATA,
                availability=Availability.BORROW,
                download_url=None,
            )

        files = meta.get("files") or []
        download_url = None
        fmts: list[str] = []
        for want_ext, label in ((".epub", "EPUB"), (".pdf", "PDF")):
            match = next(
                (f for f in files if str(f.get("name", "")).lower().endswith(want_ext)),
                None,
            )
            if match:
                fmts.append(label)
                if download_url is None:
                    download_url = (
                        f"https://archive.org/download/{ia_id}/{quote(match['name'])}"
                    )
        if download_url:
            return Hit(
                **base,
                url=details_url,
                formats=fmts,
                hit_type=HitType.EBOOK,
                availability=Availability.FREE,
                download_url=download_url,
            )
        # Scanned item without epub/pdf derivates: readable online only.
        return Hit(
            **base,
            url=details_url,
            formats=[],
            hit_type=HitType.ONLINE_FULLTEXT,
            availability=Availability.FREE,
            download_url=None,
        )

    def _archive_metadata(self, ia_id: str) -> dict | None:
        """Fetch archive.org metadata; return None on any failure."""
        try:
            return http_get_json(
                f"https://archive.org/metadata/{quote(ia_id)}",
                self.timeout,
                self.max_retries,
            )
        except SourceError:
            return None
