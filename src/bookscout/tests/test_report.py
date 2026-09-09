"""Report rendering tests: grouping, URL encoding, no-result fallback."""
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType
from bookscout.core.report import extended_links, purchase_links, render_text


def _hit(title, source, label, **kw):
    defaults = dict(
        title=title,
        url=f"https://example.com/{source}/{title}",
        source=source,
        source_label=label,
    )
    defaults.update(kw)
    return Hit(**defaults)


class TestRenderTextGrouping:
    def test_hits_grouped_by_source(self):
        hits = [
            _hit("Alpha", "gutenberg", "Project Gutenberg"),
            _hit("Beta", "wikisource", "Wikisource"),
            _hit("Gamma", "gutenberg", "Project Gutenberg"),
        ]
        text = render_text(hits, "alpha")
        # Both group headers present...
        assert "[Project Gutenberg]" in text
        assert "[Wikisource]" in text
        # ...and Gamma sits with its own source block, not between
        # the two wikisource entries.
        g_block = text.split("[Project Gutenberg]")[1].split("[Wikisource]")[0]
        assert "Alpha" in g_block and "Gamma" in g_block and "Beta" not in g_block

    def test_group_order_follows_first_seen_source(self):
        hits = [
            _hit("Beta", "wikisource", "Wikisource"),
            _hit("Alpha", "gutenberg", "Project Gutenberg"),
        ]
        text = render_text(hits)
        assert text.index("[Wikisource]") < text.index("[Project Gutenberg]")

    def test_download_url_rendered_when_present(self):
        h = _hit("Alpha", "gutenberg", "Project Gutenberg", download_url="https://x/y.epub")
        assert "download: https://x/y.epub" in render_text([h])

    def test_availability_and_formats_shown(self):
        h = _hit(
            "Alpha",
            "gutenberg",
            "Project Gutenberg",
            formats=["EPUB", "PDF"],
            availability=Availability.FREE,
        )
        text = render_text([h])
        assert "EPUB/PDF" in text
        assert "free download" in text

    def test_borrow_label_shown(self):
        h = _hit(
            "Alpha",
            "openlibrary",
            "Open Library",
            availability=Availability.BORROW,
            hit_type=HitType.METADATA,
        )
        assert "borrow" in render_text([h])


class TestNoResultsFallback:
    def test_empty_hits_non_empty_output(self):
        text = render_text([], "Some Obscure Book", "Nobody")
        assert text.strip()
        assert "Some Obscure Book" in text

    def test_no_results_suggests_purchase_channels(self):
        text = render_text([], "Some Obscure Book")
        assert "豆瓣读书" in text
        assert "京东图书" in text

    def test_no_results_includes_manual_search_entries(self):
        text = render_text([], "Some Obscure Book")
        assert "Wikisource" in text
        assert "Open Library" in text
        assert "Manual search entries" in text

    def test_no_results_includes_extended_resource_entries(self):
        """Copyrighted books must not leave the user empty-handed."""
        text = render_text([], "学会提问", "尼尔·布朗")
        assert "Extended resource entries" in text
        assert "Anna's Archive" in text
        assert "LibGen" in text

    def test_with_results_still_includes_extended_entries(self):
        h = _hit("Alpha", "gutenberg", "Project Gutenberg")
        text = render_text([h], "alpha")
        assert "Extended resource entries" in text


class TestExtendedLinks:
    def test_chinese_title_url_encoded(self):
        links = extended_links("学会提问", "尼尔·布朗")
        assert len(links) == 2
        for _, url in links:
            assert "学会提问" not in url  # raw CJK must not leak
            assert "%E5%AD%A6%E4%BC%9A%E6%8F%90%E9%97%AE" in url

    def test_empty_query_yields_no_links(self):
        assert extended_links("") == []

    def test_all_entries_are_https(self):
        for _, url in extended_links("anything"):
            assert url.startswith("https://")


class TestPurchaseLinks:
    def test_chinese_title_url_encoded(self):
        links = purchase_links("紅樓夢", "曹雪芹")
        for _, url in links:
            assert quote("紅樓夢 曹雪芹") in url
            assert "紅樓夢" not in url  # raw CJK must not leak into the URL

    def test_spaces_encoded(self):
        links = purchase_links("dream pool essays")
        for _, url in links:
            assert " " not in url
            assert quote("dream pool essays") in url

    def test_every_channel_has_label_and_http_url(self):
        links = purchase_links("anything")
        assert len(links) >= 2
        for label, url in links:
            assert label
            assert url.startswith("https://")

    def test_empty_title_still_yields_links(self):
        # purchase_links must never crash; empty query is a degenerate case.
        assert isinstance(purchase_links(""), list)
