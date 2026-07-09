"""Tests for the built-in content filters and their composition."""

from onecrawler.filters import (
    by_cosine_similarity,
    by_date,
    by_extension,
    by_files,
    by_keywords,
)
from onecrawler.filters.chain import AND, NOT, OR


class TestByCosineSimilarity:
    def test_scores_against_body_text_not_title(self):
        # Regression: previously `content`/`title` preceded `text`, so a short
        # title (present in JSON output) was scored instead of the body.
        body = "machine learning models train on large datasets " * 20
        item = {"title": "cats and dogs", "text": body, "url": "http://x/a.html"}
        f = by_cosine_similarity("machine learning datasets models", threshold=0.2)
        assert f(item) is True

    def test_falls_back_to_title_when_no_body(self):
        f = by_cosine_similarity("cats dogs", threshold=0.2)
        assert f({"title": "cats and dogs"}) is True

    def test_missing_all_fields_excluded(self):
        f = by_cosine_similarity("anything")
        assert f({"url": "http://x"}) is False


class TestByDate:
    def test_prefers_publication_date_over_filedate(self):
        # `filedate` is the crawl/extraction date; publication `date` must win.
        rec = {"date": "2020-05-01", "filedate": "2026-07-09"}
        assert by_date("2020-01-01", "2021-01-01")(rec) is True
        assert by_date("2026-01-01", "2026-12-31")(rec) is False

    def test_missing_date_excluded(self):
        assert by_date("2020-01-01")({"text": "no date"}) is False

    def test_invalid_date_excluded(self):
        assert by_date("2020-01-01")({"date": "not-a-date"}) is False

    def test_field_override(self):
        f = by_date("2020-01-01", "2021-01-01", fields=("published",))
        assert f({"published": "2020-06-01"}) is True


class TestByKeywords:
    def test_matches_any_case_insensitive(self):
        assert by_keywords(["hello"])({"text": "well HELLO there"}) is True

    def test_no_match(self):
        assert by_keywords(["absent"])({"text": "nothing here"}) is False

    def test_missing_field_excluded(self):
        assert by_keywords(["x"])({"url": "http://x"}) is False

    def test_field_override(self):
        assert by_keywords(["hi"], field="body")({"body": "say hi"}) is True


class TestByFiles:
    def test_by_files_logical_type(self):
        assert by_files(["pdf"])({"url": "http://x/doc.PDF"}) is True

    def test_by_extension_miss(self):
        assert by_extension([".pdf"])({"url": "http://x/page.html"}) is False

    def test_missing_url_excluded(self):
        assert by_extension([".pdf"])({}) is False

    def test_field_override(self):
        assert by_files(["pdf"], field="link")({"link": "http://x/a.pdf"}) is True


class TestComposition:
    def test_and_or_not(self):
        chain = AND(
            by_keywords(["python"]),
            OR(by_files(["pdf"]), NOT(by_files(["docx"]))),
        )
        assert chain({"text": "python rocks", "url": "http://x/a.txt"}) is True
        assert chain({"text": "java rocks", "url": "http://x/a.txt"}) is False

    def test_empty_and_chain_accepts(self):
        assert AND()({"text": "anything"}) is True

    def test_empty_or_chain_accepts(self):
        # Empty OR must accept (regression: any([]) would reject everything).
        assert OR()({"text": "anything"}) is True
