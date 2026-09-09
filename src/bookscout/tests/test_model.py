"""Boundary tests for Hit.compute_score (core scoring contract)."""
from bookscout.core.model import Availability, Hit, HitType, hits_hash


def _hit(**kw) -> Hit:
    defaults = dict(
        title="Pride and Prejudice",
        url="https://example.com/1",
        source="test",
        source_label="Test",
    )
    defaults.update(kw)
    return Hit(**defaults)


class TestExactMatch:
    def test_exact_title_full_bonus_stack(self):
        # 60 exact + 10 FREE + 5 EBOOK + 5 EPUB = 80
        h = _hit(formats=["EPUB"])
        assert h.compute_score("Pride and Prejudice") == 80.0

    def test_exact_match_case_and_whitespace_insensitive(self):
        h = _hit()
        assert h.compute_score("  PRIDE   AND PREJUDICE ") == 75.0  # 60+10+5

    def test_query_contains_title(self):
        # t in q also counts as a match
        h = _hit()
        assert h.compute_score("The Pride and Prejudice Illustrated") >= 60.0


class TestPartialMatch:
    def test_shared_tokens_above_half(self):
        # Not a substring match either way, but token overlap ratio >= 0.5 -> +35
        h = _hit(title="Pool Dream Essays", formats=[])
        s = h.compute_score("dream pool")
        assert s == 50.0  # 35 + 10 FREE + 5 EBOOK

    def test_no_overlap_scores_only_bonuses(self):
        h = _hit(title="Totally Unrelated Book", formats=[])
        assert h.compute_score("dream pool") == 15.0  # 10 FREE + 5 EBOOK

    def test_shared_tokens_below_half(self):
        # overlap {one}/min(3,3) = 1/3 < 0.5 -> no title points
        h = _hit(title="one two three", formats=[])
        assert h.compute_score("one four five") == 15.0


class TestEmptyQuery:
    def test_empty_title_query_keeps_bonuses(self):
        h = _hit(formats=["EPUB"])
        assert h.compute_score("") == 20.0  # 10 FREE + 5 EBOOK + 5 EPUB

    def test_unrelated_hit_title_no_title_points(self):
        h = _hit(title="Omega")
        assert h.compute_score("pride") == 15.0  # 10 FREE + 5 EBOOK


class TestAuthorBonus:
    def test_author_containment_adds_20(self):
        h = _hit(author="Austen, Jane")
        assert h.compute_score("pride and prejudice", "austen") == 95.0  # 60+10+5+20

    def test_missing_author_on_hit_no_bonus(self):
        h = _hit(author="")
        assert h.compute_score("pride and prejudice", "austen") == 75.0

    def test_non_matching_author_no_bonus(self):
        h = _hit(author="Dickens, Charles")
        assert h.compute_score("pride and prejudice", "austen") == 75.0


class TestCapAndClamp:
    def test_score_capped_at_100(self):
        h = _hit(author="Jane Austen", formats=["EPUB"])
        # 60 + 20 + 10 + 5 + 5 = 100 exactly
        assert h.compute_score("pride and prejudice", "jane austen") == 100.0

    def test_score_never_exceeds_100(self):
        h = _hit(
            title="pride and prejudice",
            author="jane austen austen",
            formats=["EPUB"],
            availability=Availability.FREE,
            hit_type=HitType.EBOOK,
        )
        assert h.compute_score("pride and prejudice", "austen") <= 100.0


class TestHitsHash:
    def test_hash_stable_and_order_sensitive(self):
        a, b = _hit(), _hit(url="https://example.com/2")
        assert hits_hash([a, b]) == hits_hash([a, b])
        assert hits_hash([a, b]) != hits_hash([b, a])
