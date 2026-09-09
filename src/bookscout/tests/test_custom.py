"""Custom source tests: config parsing + LINK_ONLY pass-through contract."""
import json

from bookscout.core.model import Availability, HitType
from bookscout.sources.custom import CustomSource, get_custom_sources

_CONFIG = [
    {
        "name": "My Source",
        "search_url": "https://example.com/search?q={title}&a={author}",
        "link_pattern": r'href="(https://example\.com/book/[^"]+)">([^<]+)</a>',
    }
]

_HTML = (
    '<html><body>'
    '<a href="https://example.com/book/1">First Book</a>'
    '<a href="https://example.com/book/2">Second Book</a>'
    '<a href="/relative/link">Relative</a>'
    '<a href="https://other.example.com/x">Not This Domain</a>'
    "</body></html>"
)


class TestGetCustomSources:
    def test_missing_config_returns_empty(self, tmp_path):
        assert get_custom_sources(tmp_path / "nope.json") == []

    def test_valid_config_parsed(self, tmp_path):
        cfg = tmp_path / "custom_sources.json"
        cfg.write_text(json.dumps(_CONFIG), encoding="utf-8")
        sources = get_custom_sources(cfg)
        assert len(sources) == 1
        assert sources[0].label == "My Source"
        assert sources[0].id == "custom-my-source"

    def test_invalid_json_returns_empty(self, tmp_path):
        cfg = tmp_path / "custom_sources.json"
        cfg.write_text("{not json", encoding="utf-8")
        assert get_custom_sources(cfg) == []

    def test_entries_missing_fields_skipped(self, tmp_path):
        cfg = tmp_path / "custom_sources.json"
        cfg.write_text(
            json.dumps(
                [
                    {"name": "no url", "link_pattern": "x"},
                    {"name": "no pattern", "search_url": "https://x"},
                    _CONFIG[0],
                ]
            ),
            encoding="utf-8",
        )
        sources = get_custom_sources(cfg)
        assert len(sources) == 1
        assert sources[0].label == "My Source"

    def test_non_list_config_returns_empty(self, tmp_path):
        cfg = tmp_path / "custom_sources.json"
        cfg.write_text(json.dumps({"name": "x"}), encoding="utf-8")
        assert get_custom_sources(cfg) == []


class TestCustomSourceSearch:
    def _source(self) -> CustomSource:
        return CustomSource(
            "My Source", _CONFIG[0]["search_url"], _CONFIG[0]["link_pattern"]
        )

    def test_search_template_substitution_and_hits(self, monkeypatch):
        seen = {}

        def fake_get(url, timeout, max_retries):
            seen["url"] = url
            return _HTML

        monkeypatch.setattr("bookscout.sources.custom.http_get_text", fake_get)
        hits = self._source().search("紅樓夢", "曹雪芹")
        # {title}/{author} replaced with URL-encoded values
        assert seen["url"].startswith("https://example.com/search?q=")
        assert "%E7%B4%85%E6%A8%93%E5%A4%A2" in seen["url"]  # quoted 紅樓夢
        assert "&a=" in seen["url"]
        # both absolute links captured, relative + foreign dropped
        assert [h.url for h in hits] == [
            "https://example.com/book/1",
            "https://example.com/book/2",
        ]
        assert hits[0].title == "First Book"

    def test_availability_always_link_only(self, monkeypatch):
        monkeypatch.setattr(
            "bookscout.sources.custom.http_get_text",
            lambda url, timeout, max_retries: _HTML,
        )
        hits = self._source().search("anything")
        assert hits
        for h in hits:
            assert h.availability == Availability.LINK_ONLY

    def test_download_url_always_none(self, monkeypatch):
        monkeypatch.setattr(
            "bookscout.sources.custom.http_get_text",
            lambda url, timeout, max_retries: _HTML,
        )
        hits = self._source().search("anything")
        for h in hits:
            assert h.download_url is None

    def test_hit_type_is_metadata(self, monkeypatch):
        monkeypatch.setattr(
            "bookscout.sources.custom.http_get_text",
            lambda url, timeout, max_retries: _HTML,
        )
        hits = self._source().search("anything")
        assert all(h.hit_type == HitType.METADATA for h in hits)

    def test_no_groups_pattern_uses_whole_match(self, monkeypatch):
        monkeypatch.setattr(
            "bookscout.sources.custom.http_get_text",
            lambda url, timeout, max_retries: "see https://example.com/book/9 here",
        )
        src = CustomSource("Plain", "https://example.com/s?q={title}", r"https://example\.com/book/\d+")
        hits = src.search("x")
        assert [h.url for h in hits] == ["https://example.com/book/9"]
        assert hits[0].title == "x"  # falls back to the query title

    def test_empty_title_returns_no_hits_without_network(self, monkeypatch):
        def boom(*a, **kw):
            raise AssertionError("must not touch the network")

        monkeypatch.setattr("bookscout.sources.custom.http_get_text", boom)
        assert self._source().search("   ") == []
