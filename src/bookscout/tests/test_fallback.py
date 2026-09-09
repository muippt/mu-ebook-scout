"""Fallback engine tests: graceful degradation + result ordering.

Runs against ``bookscout.core.fallback.search_all`` — the single engine
implementation (CLI and MCP both consume it).
"""
import pytest

from bookscout.core.fallback import search_all
from bookscout.core.model import Availability, Hit, HitType, Source, SourceError


class GoodSource(Source):
    id = "good"
    label = "Good Source"

    def __init__(self, hits=None, fail=False):
        self.hits = hits or []
        self.fail = fail
        self.calls: list[tuple] = []

    def search(self, title, author="", language=""):
        self.calls.append((title, author, language))
        if self.fail:
            raise SourceError("planned failure")
        return list(self.hits)


def _hit(title, **kw):
    defaults = dict(
        title=title,
        url=f"https://example.com/{title}",
        source="good",
        source_label="Good Source",
    )
    defaults.update(kw)
    return Hit(**defaults)


class TestDegradation:
    def test_failing_source_does_not_break_query(self):
        good = GoodSource([_hit("Alpha")])
        bad = GoodSource(fail=True)
        hits, failed = search_all("alpha", sources=[bad, good])
        assert [h.title for h in hits] == ["Alpha"]
        assert failed == ["Good Source"]

    def test_all_sources_failing_returns_empty(self):
        hits, failed = search_all("x", sources=[GoodSource(fail=True), GoodSource(fail=True)])
        assert hits == []
        assert len(failed) == 2

    def test_unexpected_crash_marks_source_failed(self):
        class Exploding(Source):
            id = "boom"
            label = "Boom Source"

            def search(self, title, author="", language=""):
                raise ValueError("bug, not a source failure")

        hits, failed = search_all("x", sources=[GoodSource([_hit("Alpha")]), Exploding()])
        assert [h.title for h in hits] == ["Alpha"]
        assert "Boom Source" in failed

    def test_query_arguments_forwarded(self):
        good = GoodSource([_hit("Alpha")])
        search_all("alpha", author="an author", language="zh", sources=[good])
        assert good.calls == [("alpha", "an author", "zh")]

    def test_blank_title_returns_empty_without_calling_sources(self):
        good = GoodSource([_hit("Alpha")])
        hits, failed = search_all("   ", sources=[good])
        assert hits == [] and failed == []
        assert good.calls == []


class TestScoringAndOrder:
    def test_results_sorted_by_descending_score(self):
        low = _hit("The Omega Chronicles")  # no title match, bonuses only
        high = _hit("Alpha", formats=["EPUB"])  # exact match + EPUB bonus
        hits, _ = search_all("alpha", sources=[GoodSource([low, high])])
        assert [h.title for h in hits] == ["Alpha", "The Omega Chronicles"]
        assert hits[0].score > hits[1].score

    def test_scores_are_computed(self):
        h = _hit("Alpha", formats=["EPUB"])
        assert h.score == 0.0
        hits, _ = search_all("alpha", sources=[GoodSource([h])])
        assert hits[0].score == 80.0  # 60 exact + 10 free + 5 ebook + 5 epub

    def test_stable_order_for_equal_scores(self):
        a = _hit("Alpha One")
        b = _hit("Alpha Two")
        hits, _ = search_all("alpha", sources=[GoodSource([a, b])])
        assert [h.title for h in hits] == ["Alpha One", "Alpha Two"]
        assert hits[0].score == hits[1].score


class TestMixedSources:
    def test_hits_from_multiple_sources_merged(self):
        class Other(GoodSource):
            id = "other"
            label = "Other Source"

        g1 = GoodSource([_hit("Alpha")])
        g2 = Other([_hit("Alpha Revised", source="other", source_label="Other Source")])
        hits, _ = search_all("alpha", sources=[g1, g2])
        assert len(hits) == 2
        assert {h.source for h in hits} == {"good", "other"}

    def test_borrow_hits_rank_below_free_for_same_title(self):
        free = _hit("Alpha", availability=Availability.FREE)
        borrow = _hit(
            "Alpha",
            availability=Availability.BORROW,
            hit_type=HitType.METADATA,
            url="https://example.com/borrow",
        )
        hits, _ = search_all("alpha", sources=[GoodSource([borrow, free])])
        assert hits[0].availability == Availability.FREE
