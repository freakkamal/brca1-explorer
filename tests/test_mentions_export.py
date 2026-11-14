import pytest
from fastapi.testclient import TestClient

from app import mentions_export
from app.main import app


@pytest.mark.parametrize(
    "query, expected_count",
    [("GPX4", 1), ("no-such-term", 0)],
)
def test_download_literature_mentions(monkeypatch, query, expected_count):
    bundle = "brca1-example.json"
    digest = "a" * 64
    article = {
        "pmid": "39265497",
        "title": "Example article mentioning GPX4",
        "title_match": True,
        "passages": ["The example abstract mentions GPX4."],
    }
    matches = [article] if expected_count else []

    # Supply a known search result without using personal files or the internet.
    def fake_find_mentions(filename, term):
        assert filename == bundle
        assert term == query
        return {
            "filename": filename,
            "sha256": digest,
            "article_count": 10,
            "matches": matches,
        }

    monkeypatch.setattr(mentions_export, "find_mentions", fake_find_mentions)

    with TestClient(app) as client:
        response = client.get(
            "/download-literature-mentions",
            params={"bundle": bundle, "q": query},
        )

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.json() == {
        "query": query,
        "bundle_filename": bundle,
        "bundle_sha256": digest,
        "articles_searched": 10,
        "articles_matched": expected_count,
        "matches": matches,
    }