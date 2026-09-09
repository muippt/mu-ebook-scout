"""Adapter unit tests — all network seams mocked, no real requests."""

from urllib.parse import quote

from bookscout.core.model import Availability, HitType, SourceError
from bookscout.sources import cbeta, gutenberg, openlibrary, standard_ebooks, wikisource
from bookscout.sources import github_books


class TestGutenberg:
    def _patch(self, monkeypatch, payload):
        urls = []

        def fake(url, timeout, max_retries):
            urls.append(url)
            return payload

        monkeypatch.setattr(gutenberg, "http_get_json", fake)
        return urls

    def test_field_mapping_and_download_preference(self, monkeypatch):
        payload = {
            "results": [
                {
                    "id": 1342,
                    "title": "Pride and Prejudice",
                    "authors": [{"name": "Austen, Jane"}],
                    "languages": ["en"],
                    "formats": {
                        "text/html": "https://www.gutenberg.org/ebooks/1342",
                        "application/epub+zip": "https://www.gutenberg.org/ebooks/1342.epub3.images",
                        "application/x-mobipocket-ebook": "https://www.gutenberg.org/ebooks/1342.kindle.images",
                    },
                }
            ]
        }
        self._patch(monkeypatch, payload)
        hits = gutenberg.GutenbergSource().search("pride")
        assert len(hits) == 1
        h = hits[0]
        assert h.title == "Pride and Prejudice"
        assert h.author == "Austen, Jane"
        assert h.language == "en"
        assert h.formats == ["EPUB", "MOBI"]
        assert h.url == "https://www.gutenberg.org/ebooks/1342"
        assert h.download_url.endswith(".epub3.images")  # epub preferred
        assert h.availability == Availability.FREE
        assert h.license == "Public domain"

    def test_pdf_fallback_when_no_epub(self, monkeypatch):
        payload = {
            "results": [
                {
                    "id": 1,
                    "title": "Only PDF",
                    "formats": {
                        "text/html": "https://www.gutenberg.org/ebooks/1",
                        "application/pdf": "https://www.gutenberg.org/files/1/1-pdf.pdf",
                    },
                }
            ]
        }
        self._patch(monkeypatch, payload)
        hits = gutenberg.GutenbergSource().search("only pdf")
        assert hits[0].download_url.endswith(".pdf")
        assert hits[0].formats == ["PDF"]

    def test_zh_language_filter_added(self, monkeypatch):
        urls = self._patch(monkeypatch, {"results": []})
        gutenberg.GutenbergSource().search("論語", language="zh")
        assert "languages=zh" in urls[0]
        assert "%E8%AB%96%E8%AA%9E" in urls[0]

    def test_no_language_filter_for_auto(self, monkeypatch):
        urls = self._patch(monkeypatch, {"results": []})
        gutenberg.GutenbergSource().search("dream", language="auto")
        assert "languages=" not in urls[0]

    def test_empty_title_no_request(self, monkeypatch):
        def boom(*a, **kw):
            raise AssertionError("no request expected")

        monkeypatch.setattr(gutenberg, "http_get_json", boom)
        assert gutenberg.GutenbergSource().search("") == []

    def test_http_failure_raises_source_error(self, monkeypatch):
        def boom(url, timeout, max_retries):
            raise SourceError("network down")

        monkeypatch.setattr(gutenberg, "http_get_json", boom)
        import pytest

        with pytest.raises(SourceError):
            gutenberg.GutenbergSource().search("pride")


class TestOpenLibrary:
    def _patch(self, monkeypatch, search_payload, archive_payload=None, archive_error=False):
        def fake(url, timeout, max_retries):
            if "archive.org" in url:
                if archive_error:
                    raise SourceError("archive.org unreachable")
                return archive_payload
            return search_payload

        monkeypatch.setattr(openlibrary, "http_get_json", fake)

    def test_no_ia_is_metadata_with_openlibrary_url(self, monkeypatch):
        self._patch(monkeypatch, {"docs": [{"key": "/works/OL1M", "title": "Dream Book"}]})
        hits = openlibrary.OpenLibrarySource().search("dream")
        assert len(hits) == 1
        h = hits[0]
        assert h.url == "https://openlibrary.org/works/OL1M"
        assert h.availability == Availability.LINK_ONLY
        assert h.hit_type == HitType.METADATA

    def test_ia_with_epub_is_free_download(self, monkeypatch):
        self._patch(
            monkeypatch,
            {"docs": [{"key": "/works/OL2M", "title": "Dream", "ia": ["dream0000drea"]}]},
            archive_payload={
                "metadata": {},
                "files": [
                    {"name": "dream_djvu.txt"},
                    {"name": "dream.pdf"},
                    {"name": "dream.epub"},
                ],
            },
        )
        hits = openlibrary.OpenLibrarySource().search("dream")
        h = hits[0]
        assert h.availability == Availability.FREE
        assert h.hit_type == HitType.EBOOK
        assert h.formats == ["EPUB", "PDF"]
        assert h.download_url == "https://archive.org/download/dream0000drea/dream.epub"
        assert h.url == "https://archive.org/details/dream0000drea"

    def test_ia_restricted_is_borrow(self, monkeypatch):
        self._patch(
            monkeypatch,
            {"docs": [{"key": "/works/OL3M", "title": "Locked", "ia": "locked"}]},
            archive_payload={"metadata": {"access-restricted-item": "true"}, "files": []},
        )
        h = openlibrary.OpenLibrarySource().search("locked")[0]
        assert h.availability == Availability.BORROW
        assert h.download_url is None

    def test_archive_failure_degrades_to_metadata(self, monkeypatch):
        self._patch(
            monkeypatch,
            {"docs": [{"key": "/works/OL4M", "title": "Flaky", "ia": "flaky"}]},
            archive_error=True,
        )
        h = openlibrary.OpenLibrarySource().search("flaky")[0]
        assert h.availability == Availability.LINK_ONLY
        assert h.download_url is None

    def test_ia_without_ebook_files_is_online_fulltext(self, monkeypatch):
        self._patch(
            monkeypatch,
            {"docs": [{"key": "/works/OL5M", "title": "Scanned", "ia": "scan1"}]},
            archive_payload={"metadata": {}, "files": [{"name": "scan1_djvu.txt"}]},
        )
        h = openlibrary.OpenLibrarySource().search("scanned")[0]
        assert h.hit_type == HitType.ONLINE_FULLTEXT
        assert h.availability == Availability.FREE
        assert h.download_url is None


class TestWikisource:
    def _patch(self, monkeypatch, results_by_lang):
        urls = []

        def fake(url, timeout, max_retries):
            urls.append(url)
            for lang, results in results_by_lang.items():
                if f"{lang}.wikisource.org" in url:
                    return {"query": {"search": results}}
            return {"query": {"search": []}}

        monkeypatch.setattr(wikisource, "http_get_json", fake)
        return urls

    def test_zh_only_queries_zh_site(self, monkeypatch):
        urls = self._patch(monkeypatch, {"zh": [{"title": "紅樓夢", "pageid": 1}]})
        hits = wikisource.WikisourceSource().search("紅樓夢", language="zh")
        assert len(urls) == 1
        assert "zh.wikisource.org" in urls[0]
        assert "intitle:" in urls[0]
        assert hits[0].title == "紅樓夢"
        assert hits[0].url == "https://zh.wikisource.org/wiki/%E7%B4%85%E6%A8%93%E5%A4%A2"

    def test_auto_queries_both_sites(self, monkeypatch):
        urls = self._patch(
            monkeypatch,
            {"zh": [{"title": "紅樓夢"}], "en": [{"title": "Dream of the Red Chamber"}]},
        )
        hits = wikisource.WikisourceSource().search("紅樓夢", language="auto")
        assert len(urls) == 2
        assert len(hits) == 2
        assert {h.language for h in hits} == {"zh", "en"}

    def test_en_language_queries_en_only(self, monkeypatch):
        urls = self._patch(monkeypatch, {"en": [{"title": "Pride and Prejudice"}]})
        wikisource.WikisourceSource().search("pride", language="en")
        assert len(urls) == 1
        assert "en.wikisource.org" in urls[0]

    def test_hit_contract(self, monkeypatch):
        self._patch(monkeypatch, {"zh": [{"title": "論語", "pageid": 9}]})
        h = wikisource.WikisourceSource().search("論語", language="zh")[0]
        assert h.hit_type == HitType.ONLINE_FULLTEXT
        assert h.availability == Availability.FREE
        assert h.download_url is None
        assert h.license == "CC BY-SA"


class TestStandardEbooks:
    _HTML = """
    <ol class="ebooks-list grid">
      <li typeof="schema:Book" about="/ebooks/jane-austen/pride-and-prejudice">
        <p><a href="/ebooks/jane-austen/pride-and-prejudice"><span property="schema:name">Pride and Prejudice</span></a></p>
        <p class="author"><span property="schema:name">Jane Austen</span></p>
      </li>
      <li typeof="schema:Book" about="/ebooks/a-n-afanasyev/russian-folktales/leonard-a-magnus">
        <p><span property="schema:name">Russian Folktales</span></p>
        <p class="author"><span property="schema:name">A. N. Afanasyev</span></p>
      </li>
    </ol>
    """

    def test_parse_and_epub_url(self, monkeypatch):
        monkeypatch.setattr(
            standard_ebooks, "http_get_text",
            lambda url, timeout, max_retries: self._HTML,
        )
        hits = standard_ebooks.StandardEbooksSource().search("pride")
        assert len(hits) == 2
        h = hits[0]
        assert h.title == "Pride and Prejudice"
        assert h.author == "Jane Austen"
        assert h.url == "https://standardebooks.org/ebooks/jane-austen/pride-and-prejudice"
        assert (
            h.download_url
            == "https://standardebooks.org/ebooks/jane-austen/pride-and-prejudice/downloads/jane-austen_pride-and-prejudice.epub"
        )
        assert h.hit_type == HitType.EBOOK
        assert h.availability == Availability.FREE
        assert h.license == "Public domain (Standard Ebooks edition)"

    def test_multi_segment_path_epub_url(self, monkeypatch):
        monkeypatch.setattr(
            standard_ebooks, "http_get_text",
            lambda url, timeout, max_retries: self._HTML,
        )
        hits = standard_ebooks.StandardEbooksSource().search("russian")
        assert (
            hits[1].download_url
            == "https://standardebooks.org/ebooks/a-n-afanasyev/russian-folktales/leonard-a-magnus/downloads/a-n-afanasyev_russian-folktales_leonard-a-magnus.epub"
        )

    def test_unexpected_structure_raises_source_error(self, monkeypatch):
        import pytest

        monkeypatch.setattr(
            standard_ebooks, "http_get_text",
            lambda url, timeout, max_retries: "<html><body>maintenance</body></html>",
        )
        with pytest.raises(SourceError):
            standard_ebooks.StandardEbooksSource().search("pride")


class TestCbeta:
    def _payload(self):
        return {
            "num_found": 2,
            "results": [
                {"type": "catalog", "n": "CBETA.003", "label": "T etc."},
                {
                    "type": "work",
                    "work": "T0235",
                    "title": "金剛般若波羅蜜經",
                    "byline": "姚秦 鳩摩羅什譯",
                    "juan": 1,
                    "file": "T08n0235",
                },
            ],
        }

    def test_work_results_mapped(self, monkeypatch):
        monkeypatch.setattr(
            cbeta, "http_get_json",
            lambda url, timeout, max_retries: self._payload(),
        )
        hits = cbeta.CbetaSource().search("金剛經")
        assert len(hits) == 1  # catalog entries dropped
        h = hits[0]
        assert h.title == "金剛般若波羅蜜經"
        assert h.url == "https://cbetaonline.dila.edu.tw/zh/T0235"
        assert h.author == "姚秦 鳩摩羅什譯"
        assert h.hit_type == HitType.ONLINE_FULLTEXT
        assert h.availability == Availability.FREE
        assert h.download_url is None
        assert h.license == "CC BY-NC-SA 4.0 (non-commercial)"

    def test_english_query_skipped(self, monkeypatch):
        def boom(url, timeout, max_retries):
            raise AssertionError("must not query for en")

        monkeypatch.setattr(cbeta, "http_get_json", boom)
        assert cbeta.CbetaSource().search("diamond", language="en") == []

    def test_zh_and_auto_query(self, monkeypatch):
        calls = []

        def fake(url, timeout, max_retries):
            calls.append(url)
            return self._payload()

        monkeypatch.setattr(cbeta, "http_get_json", fake)
        assert cbeta.CbetaSource().search("金剛經", language="zh")
        assert cbeta.CbetaSource().search("金剛經", language="auto")
        assert len(calls) == 2


class TestGithubBooks:
    def _tree(self):
        return {
            "truncated": False,
            "tree": [
                {"type": "tree", "path": "子部", "sha": "x"},
                {"type": "blob", "path": "紅樓夢.epub", "sha": "a", "size": 1048576},
                {"type": "blob", "path": "《紅樓夢》.pdf", "sha": "b", "size": 2048},
                {"type": "blob", "path": "論語.txt", "sha": "c", "size": 100},
                {"type": "blob", "path": "README.md", "sha": "d", "size": 50},
            ],
        }

    def _patch(self, monkeypatch, payloads):
        urls = []

        def fake(url, timeout, max_retries):
            urls.append(url)
            return payloads[url.split("/repos/")[1].split("/git")[0]]

        monkeypatch.setattr(github_books, "http_get_json", fake)
        return urls

    def test_matching_and_raw_download_url(self, monkeypatch):
        payloads = {"zhpelo/wenshuoge": self._tree(), "garychowcmu/daizhigev20": {"tree": []}}
        self._patch(monkeypatch, payloads)
        hits = github_books.GithubBooksSource().search("紅樓夢")
        # Title marks are stripped from the displayed title; extension split off.
        assert {h.title for h in hits} == {"紅樓夢"}
        by_fmt = {tuple(h.formats): h for h in hits}
        epub = by_fmt[("EPUB",)]
        quoted = quote("紅樓夢")  # CJK path segments are URL-encoded
        assert epub.download_url == f"https://raw.githubusercontent.com/zhpelo/wenshuoge/HEAD/{quoted}.epub"
        assert epub.url == f"https://github.com/zhpelo/wenshuoge/blob/HEAD/{quoted}.epub"
        assert epub.size_hint == "1.0MB"
        assert epub.hit_type == HitType.EBOOK
        assert epub.availability == Availability.FREE

    def test_one_tree_request_per_repo(self, monkeypatch):
        payloads = {"zhpelo/wenshuoge": self._tree(), "garychowcmu/daizhigev20": {"tree": []}}
        urls = self._patch(monkeypatch, payloads)
        github_books.GithubBooksSource().search("紅樓夢")
        tree_urls = [u for u in urls if "/git/trees/HEAD" in u]
        assert len(tree_urls) == 2
        assert all("recursive=1" in u for u in tree_urls)

    def test_english_query_skipped(self, monkeypatch):
        def boom(url, timeout, max_retries):
            raise AssertionError("must not query for en")

        monkeypatch.setattr(github_books, "http_get_json", boom)
        assert github_books.GithubBooksSource().search("pride", language="en") == []

    def test_rate_limit_raises_source_error(self, monkeypatch):
        import pytest

        def boom(url, timeout, max_retries):
            raise SourceError("HTTP 403 for ...")

        monkeypatch.setattr(github_books, "http_get_json", boom)
        with pytest.raises(SourceError):
            github_books.GithubBooksSource().search("紅樓夢")

    def test_truncated_tree_still_matches(self, monkeypatch):
        payloads = {
            "zhpelo/wenshuoge": {"truncated": True, "tree": [{"type": "blob", "path": "紅樓夢.epub", "size": 1}]},
            "garychowcmu/daizhigev20": {"truncated": True, "tree": []},
        }
        self._patch(monkeypatch, payloads)
        hits = github_books.GithubBooksSource().search("紅樓夢")
        assert len(hits) == 1


class TestOpenLibraryArchiveFallback:
    """When openlibrary.org is unreachable, degrade to archive.org search."""

    def _mock(self, monkeypatch):
        def fake_json(url, timeout=15.0, max_retries=2):
            if "openlibrary.org" in url:
                raise SourceError("simulated unreachable")
            if "advancedsearch" in url:
                return {
                    "response": {
                        "docs": [
                            {
                                "identifier": "askingrightquest00brow",
                                "title": "Asking the right questions",
                                "creator": ["Browne, M. Neil"],
                            }
                        ]
                    }
                }
            if "/metadata/" in url:
                return {
                    "metadata": {"access-restricted-item": "true"},
                    "files": [{"name": "x.epub"}, {"name": "x.pdf"}],
                }
            raise AssertionError("unexpected url: " + url)

        monkeypatch.setattr(openlibrary, "http_get_json", fake_json)

    def test_fallback_returns_borrow_hit_for_restricted_item(self, monkeypatch):
        self._mock(monkeypatch)
        hits = openlibrary.OpenLibrarySource().search("asking the right questions")
        assert len(hits) == 1
        h = hits[0]
        assert h.availability == Availability.BORROW
        assert h.url == "https://archive.org/details/askingrightquest00brow"
        assert h.download_url is None  # borrow flow stays in-browser
        assert h.extra["ia_id"] == "askingrightquest00brow"
        assert set(h.formats) == {"EPUB", "PDF"}

    def test_fallback_unreachable_metadata_treated_as_restricted(self, monkeypatch):
        def fake_json(url, timeout=15.0, max_retries=2):
            if "openlibrary.org" in url:
                raise SourceError("simulated unreachable")
            if "advancedsearch" in url:
                return {
                    "response": {
                        "docs": [{"identifier": "free-item", "title": "A Book"}]
                    }
                }
            if "/metadata/" in url:
                raise SourceError("archive.org metadata unreachable")
            raise AssertionError("unexpected url: " + url)

        monkeypatch.setattr(openlibrary, "http_get_json", fake_json)
        hits = openlibrary.OpenLibrarySource().search("a book")
        assert len(hits) == 1
        assert hits[0].availability == Availability.BORROW


class TestCbetaSimplifiedQuery:
    """CBETA only matches traditional titles; simplified must auto-retry."""

    def _patch(self, monkeypatch, payloads):
        """payloads: list returned per call, in order."""
        calls = {"n": 0}

        def fake(url, timeout, max_retries):
            i = min(calls["n"], len(payloads) - 1)
            calls["n"] += 1
            return payloads[i]

        monkeypatch.setattr(cbeta, "http_get_json", fake)
        return calls

    def test_simplified_zero_hits_triggers_traditional_retry(self, monkeypatch):
        # first call (simplified 金刚经) -> empty; second (金剛經) -> results
        empty = {"results": []}
        works = {"results": [{
            "type": "work", "work": "T0235", "title": "金剛般若波羅蜜經",
            "byline": "姚秦 鳩摩羅什譯",
        }]}
        calls = self._patch(monkeypatch, [empty, works])
        hits = cbeta.CbetaSource().search("金刚经")
        assert len(hits) == 1
        assert hits[0].title == "金剛般若波羅蜜經"
        assert calls["n"] == 2  # retry really happened

    def test_traditional_no_retry(self, monkeypatch):
        works = {"results": [{
            "type": "work", "work": "T0235", "title": "金剛般若波羅蜜經",
        }]}
        calls = self._patch(monkeypatch, [works])
        hits = cbeta.CbetaSource().search("金剛般若波羅蜜經")
        assert len(hits) == 1
        assert calls["n"] == 1  # no retry when direct hit

    def test_english_query_no_retry(self, monkeypatch):
        calls = self._patch(monkeypatch, [{"results": []}])
        assert cbeta.CbetaSource().search("diamond") == []
        assert calls["n"] == 1  # no CJK, no retry


class TestCtext:
    def test_hit_mapping(self, monkeypatch):
        from bookscout.sources import ctext

        payload = {"books": [
            {"title": "論語", "urn": "ctp:analects"},
            {"title": "論語注疏", "urn": "ctp:lunyu-zhushu"},
            {"title": "", "urn": "ctp:missing-title"},   # skipped
            {"title": "no urn", "urn": ""},              # skipped
        ]}
        monkeypatch.setattr(ctext, "http_get_json", lambda *a: payload)
        hits = ctext.CtextViewSource().search("论语")
        assert len(hits) == 2
        assert hits[0].title == "論語"
        assert hits[0].url == "https://ctext.org/analects"
        assert hits[0].hit_type == HitType.ONLINE_FULLTEXT
        assert hits[0].availability == Availability.FREE
        assert hits[0].extra["urn"] == "ctp:analects"

    def test_english_language_skipped(self, monkeypatch):
        from bookscout.sources import ctext

        def boom(*a):
            raise AssertionError("should not be called")

        monkeypatch.setattr(ctext, "http_get_json", boom)
        assert ctext.CtextViewSource().search("analects", language="en") == []


class TestLibrivox:
    PAYLOAD = {"books": [{
        "id": "253", "title": "Pride and Prejudice",
        "language": "English", "totaltime": "13:06:44",
        "url_librivox": "https://librivox.org/pride-and-prejudice-by-jane-austen/",
        "url_zip_file": "https://archive.org/compress/pride_and_prejudice_librivox",
        "authors": [{"first_name": "Jane", "last_name": "Austen"}],
    }]}

    def test_hit_mapping(self, monkeypatch):
        from bookscout.sources import librivox

        seen = {}

        def fake(url, timeout, max_retries, user_agent=""):
            seen["url"], seen["ua"] = url, user_agent
            return self.PAYLOAD

        monkeypatch.setattr(librivox, "http_get_json", fake)
        hits = librivox.LibrivoxSource().search("pride and prejudice")
        assert len(hits) == 1
        h = hits[0]
        assert h.hit_type == HitType.AUDIOBOOK
        assert h.availability == Availability.FREE
        assert h.author == "Jane Austen"
        assert h.formats == ["MP3", "M4B"]
        assert h.download_url == "https://archive.org/compress/pride_and_prejudice_librivox"
        assert "Mozilla/5.0" in seen["ua"]  # browser UA is mandatory
        assert "title=pride%20and%20prejudice" in seen["url"]

    def test_author_added_to_query(self, monkeypatch):
        from bookscout.sources import librivox

        seen = {}

        def fake(url, timeout, max_retries, user_agent=""):
            seen["url"] = url
            return {"books": []}

        monkeypatch.setattr(librivox, "http_get_json", fake)
        librivox.LibrivoxSource().search("pride", "austen")
        assert "author=austen" in seen["url"]

    def test_zh_language_skipped(self):
        from bookscout.sources import librivox

        assert librivox.LibrivoxSource().search("红楼梦", language="zh") == []


class TestGoogleBooks:
    def test_no_key_returns_empty_without_request(self, monkeypatch):
        from bookscout.sources import google_books

        monkeypatch.delenv("BOOKSCOUT_GOOGLE_BOOKS_KEY", raising=False)

        def boom(*a, **kw):
            raise AssertionError("network must not be touched without a key")

        monkeypatch.setattr(google_books, "http_get_json", boom)
        assert google_books.GoogleBooksSource().search("pride") == []

    def test_hit_mapping_free_epub(self, monkeypatch):
        from bookscout.sources import google_books

        payload = {"items": [{
            "id": "v1",
            "volumeInfo": {"title": "Pride and Prejudice",
                           "authors": ["Jane Austen"], "language": "en",
                           "infoLink": "https://books.google.com/books?id=v1"},
            "accessInfo": {"epub": {"downloadLink": "https://dl.example/x.epub"}},
        }, {
            "id": "v2",
            "volumeInfo": {"title": "No download", "language": "en"},
            "accessInfo": {"webReaderLink": "https://books.google.com/books?id=v2&reader"},
        }, {
            "id": "v3",
            "volumeInfo": {},  # no title -> skipped
        }]}
        monkeypatch.setenv("BOOKSCOUT_GOOGLE_BOOKS_KEY", "AIza_test")
        monkeypatch.setattr(google_books, "http_get_json", lambda *a: payload)
        hits = google_books.GoogleBooksSource().search("pride")
        assert len(hits) == 2
        free, meta = hits
        assert free.hit_type == HitType.EBOOK and free.availability == Availability.FREE
        assert free.download_url == "https://dl.example/x.epub"
        assert meta.hit_type == HitType.METADATA and meta.download_url is None
        assert meta.url.startswith("https://books.google.com/books?id=v2&reader")
