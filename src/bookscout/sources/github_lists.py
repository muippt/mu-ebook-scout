"""GitHub 全量书单检索 — community book-list index files on GitHub.

Many high-quality Chinese ebook "treasure chest" repositories do NOT commit
the book files themselves; they commit Markdown index files whose table rows
point to netdisk downloads (ctfile / lanzou / baidu pan / ...). A git-tree
adapter like ``github_books`` can never see those, because the links live in
file CONTENT, not in file names.

Two complementary strategies share one parser:

  Strategy A — full GitHub code search (token recommended):
      ``GET /search/code?q="<title>" extension:md ctfile`` (plus lanzou /
      pan.baidu.com variants). This searches ALL of GitHub, so it also finds
      lists we have never heard of. The REST code-search endpoint requires
      authentication; without a token this strategy is skipped.

  Strategy B — curated seed repositories (anonymous-friendly):
      Scan well-known index repositories directly (git tree + raw files).
      Raw markdown responses are cached under ``~/.bookscout/cache/`` for
      ``_CACHE_TTL`` seconds, so repeated searches cost no extra requests.

Parser contract: a line is a hit when it (1) contains a netdisk or direct
ebook-file URL and (2) the normalized query title appears in the normalized
line text. Hits are emitted as ``EBOOK`` + ``LINK_ONLY`` — the link leads to
the user's download, the tool itself never touches the netdisk.
"""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source, SourceError
from bookscout.sources._http import github_token, http_get_json, http_get_text
from bookscout.sources.github_books import _normalize

_SEARCH_CODE = "https://api.github.com/search/code"

#: Netdisk hosts / URL shapes that mean "a downloadable book lives here".
_NETDISK_HINTS = (
    "ctfile.", "z701.com", "u062.com", "545c.com",
    "lanzou", "lanzn", "wenshishu",
    "pan.baidu.", "aliyundrive", "alipan",
    "123pan", "123684", "189.cn", "pan.quark", "weiyun", "pikpak",
)

#: Direct ebook file extensions embedded in Markdown links.
_FILE_EXTS = (".epub", ".pdf", ".mobi", ".azw3", ".zip", ".txt")

#: Code-search terms that keep results to actual download-list files.
#: One search request per hint (REST code search has no OR operator).
_SEARCH_HOST_HINTS = ("ctfile", "lanzou", "pan.baidu.com")

#: Curated index repositories scanned without a token (and cached).
_SEED_REPOS: tuple[tuple[str, str, str], ...] = (
    # (owner, repo, markdown subdir — "" for whole tree)
    ("jbiaojerry", "ebook-treasure-chest", "md"),
)

_MAX_FILES_PER_QUERY = 3      # raw files fetched per search hint
_MAX_FILES_PER_SEED = 30      # raw files scanned per seed repository
_MAX_HITS = 8                 # total hits emitted by one search()
_CACHE_TTL = 7 * 24 * 3600    # one week: netdisk links die slowly
_CACHE_DIR = Path.home() / ".bookscout" / "cache"

_LINE_URL_RE = re.compile(r"https?://[^\s|)\]\"'<>\u3000]+")

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class GithubBookListsSource(Source):
    """Community book-list indexes on GitHub (netdisk link directories)."""

    id = "github_lists"
    label = "GitHub 书单索引"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        needle = _match_key(title)
        if not needle:
            return []

        hits: list[Hit] = []
        seen_urls: set[str] = set()
        if github_token():
            self._search_code(title, needle, author, hits, seen_urls)
        # Seed repositories always run: anonymous-friendly and cached, they
        # back up the code search (and replace it when no token is set).
        self._search_seed_repos(needle, author, hits, seen_urls)
        return hits[:_MAX_HITS]

    # ------------------------------------------------------------------
    # Strategy A: full GitHub code search
    # ------------------------------------------------------------------
    def _search_code(
        self,
        title: str,
        needle: str,
        author: str,
        hits: list[Hit],
        seen_urls: set[str],
    ) -> None:
        for hint in _SEARCH_HOST_HINTS:
            query = f"{title} extension:md {hint}"
            url = f"{_SEARCH_CODE}?q={quote(query)}&per_page=10"
            try:
                data = http_get_json(url, self.timeout, self.max_retries)
            except SourceError:
                continue  # one bad hint must not kill the others
            files = data.get("items") or []
            fetched = 0
            for item in files:
                if fetched >= _MAX_FILES_PER_QUERY:
                    break
                repo = item.get("repository") or {}
                full_name = repo.get("full_name", "")
                path = item.get("path", "")
                if not full_name or not path.lower().endswith(".md"):
                    continue
                raw_url = (
                    f"https://raw.githubusercontent.com/{full_name}"
                    f"/HEAD/{quote(path, safe='/')}"
                )
                text = self._fetch_text(raw_url)
                fetched += 1
                if text is None:
                    continue
                self._parse_markdown(text, needle, author, full_name, path, hits, seen_urls)
            if len(hits) >= _MAX_HITS:
                return

    # ------------------------------------------------------------------
    # Strategy B: curated seed repositories
    # ------------------------------------------------------------------
    def _search_seed_repos(
        self,
        needle: str,
        author: str,
        hits: list[Hit],
        seen_urls: set[str],
    ) -> None:
        for owner, repo, subdir in _SEED_REPOS:
            for path in self._seed_markdown_files(owner, repo, subdir):
                raw_url = (
                    f"https://raw.githubusercontent.com/{owner}/{repo}"
                    f"/HEAD/{quote(path, safe='/')}"
                )
                text = self._fetch_text(raw_url)
                if text is None:
                    continue
                self._parse_markdown(
                    text, needle, author, f"{owner}/{repo}", path, hits, seen_urls
                )
                if len(hits) >= _MAX_HITS:
                    return

    def _seed_markdown_files(self, owner: str, repo: str, subdir: str) -> list[str]:
        url = (
            f"https://api.github.com/repos/{owner}/{repo}"
            f"/git/trees/HEAD?recursive=1"
        )
        try:
            data = http_get_json(url, self.timeout, self.max_retries)
        except SourceError:
            return []
        paths: list[str] = []
        for entry in data.get("tree") or []:
            path = entry.get("path", "")
            if entry.get("type") != "blob":
                continue
            if not path.lower().endswith(".md"):
                continue
            if subdir and not path.startswith(subdir.rstrip("/") + "/"):
                continue
            paths.append(path)
            if len(paths) >= _MAX_FILES_PER_SEED:
                break
        return paths

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _fetch_text(self, url: str) -> str | None:
        """Fetch a raw markdown file through the on-disk cache."""
        cache_file = _CACHE_DIR / hashlib.sha1(url.encode()).hexdigest()[:20]
        try:
            if (
                cache_file.exists()
                and time.time() - cache_file.stat().st_mtime < _CACHE_TTL
            ):
                return cache_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        try:
            text = http_get_text(url, self.timeout, self.max_retries)
        except SourceError:
            return None
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(text, encoding="utf-8")
        except OSError:
            pass  # cache write failure is never fatal
        return text

    def _parse_markdown(
        self,
        text: str,
        needle: str,
        author_hint: str,
        repo_full: str,
        path: str,
        hits: list[Hit],
        seen_urls: set[str],
    ) -> None:
        for line in text.splitlines():
            if len(hits) >= _MAX_HITS:
                return
            if "http" not in line:
                continue
            if needle not in _match_key(line):
                continue
            url = next(
                (u for u in _LINE_URL_RE.findall(line) if _is_useful_url(u)),
                None,
            )
            if not url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title_cell, author_cell = _split_cells(line)
            if not title_cell:
                continue
            hits.append(
                Hit(
                    title=title_cell,
                    url=url,
                    source=self.id,
                    source_label=self.label,
                    author=author_cell or author_hint,
                    language="zh" if _CJK_RE.search(title_cell) else "en",
                    formats=[],
                    hit_type=HitType.EBOOK,
                    availability=Availability.LINK_ONLY,
                    license="Community netdisk upload (copyright status varies)",
                    download_url=None,
                    extra={"repo": repo_full, "list_file": path},
                )
            )


# ----------------------------------------------------------------------
# Line parsing helpers (module-level so tests can import them directly)
# ----------------------------------------------------------------------
def _match_key(value: str) -> str:
    """Aggressive match key: normalize, T2S, drop every non-word character.

    ``高效能人士的七个习惯 20周年纪念版`` and ``高效能人士的七个习惯（20周年
    纪念版）| 史蒂芬・柯维 | [下载](...)`` collapse to the same key space so a
    plain substring test survives punctuation and separator differences.
    """
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", _normalize(value or ""))


def _is_useful_url(url: str) -> bool:
    """True when the URL points at a netdisk page or a direct ebook file."""
    low = url.lower()
    if any(hint in low for hint in _NETDISK_HINTS):
        return True
    return low.endswith(_FILE_EXTS)


def _split_cells(line: str) -> tuple[str, str]:
    """Extract (title, author) from a Markdown table/list row before the URL.

    ``| 高效能人士的七个习惯 | 史蒂芬・柯维 | [下载](http..) |`` →
    ``("高效能人士的七个习惯", "史蒂芬・柯维")``. Falls back to the text
    before the first URL for non-table layouts. Markdown link/image syntax
    is stripped first: ``[书名.epub](http..`` (the URL was cut off) must
    yield ``书名.epub``, not ``[书名.epub](``.
    """
    # Strip URLs from the WHOLE line (a title may follow an image link).
    before_url = _LINE_URL_RE.sub(" ", line)
    cells = [c.strip() for c in before_url.strip().strip("|").split("|")]
    cleaned: list[str] = []
    for cell in cells:
        # drop list numbering like "3." / "1)" and bullet markers
        cell = re.sub(r"^\s*(?:\d+\s*[.)、]|[-*•·])\s*", "", cell)
        # complete and truncated Markdown links / images -> keep the text
        cell = re.sub(r"!\[[^\]]*\]\([^)]*\)?", "", cell)
        cell = re.sub(r"\[([^\]]*)\]\([^)]*\)?", r"\1", cell)
        cell = cell.strip(" []!()《》\u3000\t")
        if cell:
            cleaned.append(cell)
    if not cleaned:
        return "", ""
    return cleaned[0], (cleaned[1] if len(cleaned) > 1 else "")
