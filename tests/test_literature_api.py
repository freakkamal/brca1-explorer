"""Offline tests for the literature endpoint."""
from fastapi.testclient import TestClient
import pytest

from app import main

client = TestClient(main.app)


@pytest.mark.parametrize("has_article", [True, False])
def test_literature_success(monkeypatch, has_article):
    provenance = {
        "api_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
        "response_sha256": "0" * 64,
    }
    article = {
        "evidence_type": "retrieved",
        "source": "PubMed",
        "pmid": "111",
        "title": "Fictional test article",
        "abstract": None,
        "abstract_available": False,
        "record_url": "https://pubmed.ncbi.nlm.nih.gov/111/",
    }
    fetch_provenance = {
        "api_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
        "response_sha256": "1" * 64,
    }
    sample = {
        "evidence_type": "retrieved",
        "source": "PubMed",
        "query": "BRCA1[Title/Abstract]",
        "sort": "relevance",
        "total_matching_records": 1 if has_article else 0,
        "returned_count": 1 if has_article else 0,
        "articles": [article] if has_article else [],
        "search_provenance": provenance,
        "fetch_provenance": fetch_provenance if has_article else {
            "api_url": None,
            "retrieved_at_utc": None,
            "response_sha256": None,
        },
    }
    monkeypatch.setattr(
        main.pubmed, "fetch_brca1_literature", lambda: sample
    )

    response = client.get("/literature/brca1")

    assert response.status_code == 200
    assert response.json() == sample


def test_literature_source_failure(monkeypatch):
    def failed_fetch():
        raise RuntimeError("PubMed returned HTTP 503.")

    monkeypatch.setattr(
        main.pubmed, "fetch_brca1_literature", failed_fetch
    )

    response = client.get("/literature/brca1")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "PubMed returned HTTP 503."
    }