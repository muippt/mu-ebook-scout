"""Unit tests for the GitHub book-lists adapter (github_lists).

All network seams are mocked: cache is redirected to tmp_path and HTTP
helpers are monkeypatched, so no real request is ever made.
"""
from __future__ import annotations

import pytest

from urllib.parse import quote, unquote

from bookscout.core.model import Availability, HitType
from bookscout.sources import github_lists
from bookscout.sources.github_lists import (
    GithubBookListsSource,
    _is_useful_url,
    _match_key,
    _split_cells,
)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Point the on-disk cache at a temp dir for every test."""
    monkeypatch.setattr(github_lists, "_CACHE_DIR", tmp_path / "cache")


class TestHelpers:
    def test_match_key_strips_punctuation_and_width(self):
        a = _match_key("高效能人士的七个习惯（20周年纪念版）")
        b = _match_key("高效能人士的七个习惯 20周年纪念版")
        assert a == b
        assert "高效能人士的七个习惯" in _match_key(
            "| 高效能人士的七个习惯（20周年纪念版） | 史蒂芬・柯维 |"
        )

    def test_match_key_traditional_simplified(self):
        assert _match_key("紅樓夢") == _match_key("红楼梦")

    def test_is_useful_url_netdisks(self):
        for url in (
            "https://url89.ctfile.com/f/31084289-1357006063-39c12e?p=8866",
            "https://z701.com/d/31084289",
            "https://wws.lanzouq.com/iabc123",
            "https://pan.baidu.com/s/xyz",
            "https://www.alipan.com/s/xyz",
        ):
            assert _is_useful_url(url), url

    def test_is_useful_url_direct_files(self):
        for url in (
            "https://example.com/book.epub",
            "https://example.com/book.PDF",
            "https://example.com/book.azw3",
        ):
            assert _is_useful_url(url), url

    def test_is_useful_url_rejects_ordinary_pages(self):
        for url in (
            "https://example.com/page.html",
            "https://github.com/owner/repo",
            "https://example.com/about",
        ):
            assert not _is_useful_url(url), url

    def test_split_cells_table_row(self):
        line = (
            "| 高效能人士的七个习惯（20周年纪念版） | 史蒂芬・柯维 | "
            "[下载](https://url89.ctfile.com/f/1-2-3?p=8866) |"
        )
        title, author = _split_cells(line)
        assert title == "高效能人士的七个习惯（20周年纪念版）"
        assert author == "史蒂芬・柯维"

    def test_split_cells_list_row(self):
        line = "2. 学会提问 - 尼尔・布朗 https://wws.lanzouq.com/iabc123"
        title, author = _split_cells(line)
        assert title == "学会提问 - 尼尔・布朗"
        assert author == ""

    def test_split_cells_empty(self):
        assert _split_cells("https://only.a/url") == ("", "")


class TestParsing:
    def _source(self):
        return GithubBookListsSource()

    def _parse(self, text, needle="高效能人士的七个习惯"):
        hits, seen = [], set()
        self._source()._parse_markdown(
            text, _match_key(needle), "作者甲", "owner/repo", "md/x.md", hits, seen
        )
        return hits

    def test_table_row_hit(self):
        text = (
            "| 书名 | 作者 | 链接 |\n"
            "| --- | --- | --- |\n"
            "| 高效能人士的七个习惯（20周年纪念版） | 史蒂芬・柯维 | "
            "[下载](https://url89.ctfile.com/f/31084289-1-abc?p=8866) |\n"
            "| 无关书籍 | 某某 | [下载](https://url89.ctfile.com/f/2-2-abc?p=8866) |\n"
        )
        hits = self._parse(text)
        assert len(hits) == 1
        h = hits[0]
        assert h.title == "高效能人士的七个习惯（20周年纪念版）"
        assert h.author == "史蒂芬・柯维"
        assert h.hit_type == HitType.EBOOK
        assert h.availability == Availability.LINK_ONLY
        assert h.download_url is None
        assert h.url.startswith("https://url89.ctfile.com/")
        assert h.extra["repo"] == "owner/repo"

    def test_dedup_same_url(self):
        text = (
            "| 高效能人士的七个习惯 | 甲 | [下载](https://url89.ctfile.com/f/1-1-1?p=8866) |\n"
            "| 高效能人士的七个习惯 | 甲 | [下载](https://url89.ctfile.com/f/1-1-1?p=8866) |\n"
        )
        hits = self._parse(text)
        assert len(hits) == 1

    def test_line_without_url_is_ignored(self):
        hits = self._parse("高效能人士的七个习惯 只是一句没有链接的话")
        assert hits == []

    def test_line_with_useless_url_is_ignored(self):
        hits = self._parse("高效能人士的七个习惯 https://example.com/no-file")
        assert hits == []

    def test_max_hits_cap(self):
        line = "| 高效能人士的七个习惯 | 甲 | [下载](https://u{0}.ctfile.com/f/{0}) |\n"
        hits = self._parse("".join(line.format(i) for i in range(20)))
        assert len(hits) == github_lists._MAX_HITS


class TestSearch:
    def _patch_http(self, monkeypatch, *, code_search=None, tree=None, raw=None):
        """code_search: dict query-fragment -> payload; tree/raw: payloads."""
        calls = {"json": [], "text": []}

        def fake_json(url, timeout, max_retries):
            calls["json"].append(url)
            if code_search is not None and "/search/code" in url:
                for frag, payload in code_search.items():
                    if quote(frag) in url or frag in url:
                        return payload
                return {"items": []}
            if tree is not None and "/git/trees/" in url:
                return tree
            raise AssertionError(f"unexpected json url: {url}")

        def fake_text(url, timeout, max_retries):
            calls["text"].append(url)
            if raw is not None:
                decoded = unquote(url)
                for frag, payload in raw.items():
                    if frag in url or frag in decoded:
                        return payload
            return ""

        monkeypatch.setattr(github_lists, "http_get_json", fake_json)
        monkeypatch.setattr(github_lists, "http_get_text", fake_text)
        return calls

    def test_seed_repo_path_without_token(self, monkeypatch):
        monkeypatch.delenv("BOOKSCOUT_GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        table = (
            "| 高效能人士的七个习惯（20周年纪念版） | 史蒂芬・柯维 | "
            "[下载](https://url89.ctfile.com/f/1-2-3?p=8866) |"
        )
        calls = self._patch_http(
            monkeypatch,
            tree={"tree": [
                {"path": "md/励志.md", "type": "blob"},
                {"path": "md/心理.md", "type": "blob"},
                {"path": "README.md", "type": "blob"},
                {"path": "src/main.py", "type": "blob"},
            ]},
            raw={"励志": table},
        )
        hits = GithubBookListsSource().search("高效能人士的七个习惯")
        assert len(hits) == 1
        assert hits[0].title == "高效能人士的七个习惯（20周年纪念版）"
        # no /search/code call happened (no token)
        assert not any("/search/code" in u for u in calls["json"])
        # README excluded by the md/ subdir filter
        assert not any("README" in u for u in calls["text"])

    def test_code_search_path_with_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        table = (
            "| 高效能人士的七个习惯（20周年纪念版） | 史蒂芬・柯维 | "
            "[下载](https://url89.ctfile.com/f/9-8-7?p=8866) |"
        )
        calls = self._patch_http(
            monkeypatch,
            code_search={"高效能人士的七个习惯": {
                "items": [{
                    "repository": {"full_name": "someone/ebook-list"},
                    "path": "lists/self-help.md",
                }]
            }},
            tree={"tree": []},
            raw={"lists/self-help.md": table},
        )
        hits = GithubBookListsSource().search("高效能人士的七个习惯")
        assert len(hits) == 1
        assert hits[0].extra["repo"] == "someone/ebook-list"
        assert any("/search/code" in u for u in calls["json"])

    def test_code_search_error_degrades_to_seed(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

        def failing_json(url, timeout, max_retries):
            if "/search/code" in url:
                raise github_lists.SourceError("HTTP 403")
            if "/git/trees/" in url:
                return {"tree": []}
            raise AssertionError(f"unexpected url: {url}")

        monkeypatch.setattr(github_lists, "http_get_json", failing_json)
        monkeypatch.setattr(github_lists, "http_get_text", lambda *a: "")
        hits = GithubBookListsSource().search("高效能人士的七个习惯")
        assert hits == []

    def test_cache_hit_avoids_second_fetch(self, monkeypatch):
        monkeypatch.delenv("BOOKSCOUT_GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fetches = {"n": 0}

        def fake_text(url, timeout, max_retries):
            fetches["n"] += 1
            return "# empty list\n"

        monkeypatch.setattr(github_lists, "http_get_json",
                            lambda url, t, r: {"tree": []})
        monkeypatch.setattr(github_lists, "http_get_text", fake_text)
        src = GithubBookListsSource()
        src.search("高效能人士的七个习惯")
        src.search("高效能人士的七个习惯")
        # tree fetched twice but no raw file fetched more than once
        assert fetches["n"] == 0

    def test_empty_title_returns_no_hits(self):
        assert GithubBookListsSource().search("") == []
        assert GithubBookListsSource().search("   ") == []


class TestSplitCellsMarkdownSyntax:
    """Regression cases found in live testing against real repositories."""

    def test_truncated_link_label_becomes_title(self):
        # lllhhh/BooksKeeper README: "- [高效能人士的七个习惯.epub](https://pan.baidu..."
        line = "- [高效能人士的七个习惯.epub](https://pan.baidu.com/s/1CYo9"
        title, author = _split_cells(line)
        assert title == "高效能人士的七个习惯.epub"
        assert author == ""

    def test_bare_image_prefix_is_dropped(self):
        # lazyvip list: "![](...cover.jpg)[高效能...]" — image cell must not
        # become the title.
        line = "![](https://h.example/img.png) 高效能人士的七个习惯"
        title, _ = _split_cells(line)
        assert title == "高效能人士的七个习惯"

    def test_image_only_line_yields_no_title(self):
        line = "![](https://h.example/img.png"
        assert _split_cells(line) == ("", "")
