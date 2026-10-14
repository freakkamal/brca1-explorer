"""Offline tests for PubMed search."""
import hashlib

import httpx
import pytest

from app import pubmed


def mock_search(monkeypatch, payload, status=200):
    def fake_get(url, *, params, timeout):
        assert params["db"] == "pubmed"
        assert params["term"] == "BRCA1[Title/Abstract]"
        assert params["retmax"] == 10
        assert params["sort"] == "relevance"

        return httpx.Response(
            status,
            json=payload,
            request=httpx.Request("GET", url, params=params),
        )

    monkeypatch.setattr(pubmed.httpx, "get", fake_get)


def test_search_success(monkeypatch):
    payload = {
        "esearchresult": {
            "count": "25",
            "idlist": ["123456", "234567"],
        }
    }
    mock_search(monkeypatch, payload)

    result = pubmed.search_brca1_articles()

    assert result["source"] == "PubMed"
    assert result["total_matching_records"] == 25
    assert result["returned_count"] == 2
    assert result["pmids"] == ["123456", "234567"]
    assert result["response_sha256"] == hashlib.sha256(
        httpx.Response(200, json=payload).content
    ).hexdigest()


def test_duplicate_pmids_removed(monkeypatch):
    mock_search(monkeypatch, {
        "esearchresult": {
            "count": "3",
            "idlist": ["123456", "123456", "234567"],
        }
    })

    result = pubmed.search_brca1_articles()

    assert result["pmids"] == ["123456", "234567"]
    assert result["returned_count"] == 2


def test_empty_search(monkeypatch):
    mock_search(monkeypatch, {
        "esearchresult": {"count": "0", "idlist": []}
    })

    result = pubmed.search_brca1_articles()

    assert result["total_matching_records"] == 0
    assert result["returned_count"] == 0
    assert result["pmids"] == []


@pytest.mark.parametrize("payload", [
    {"esearchresult": {"count": "1", "idlist": ["invalid"]}},
    {"error": "Search failed"},
])
def test_invalid_response(monkeypatch, payload):
    mock_search(monkeypatch, payload)

    with pytest.raises(RuntimeError, match="invalid or unexpected"):
        pubmed.search_brca1_articles()


def test_search_timeout(monkeypatch):
    def timed_out(*args, **kwargs):
        raise httpx.ReadTimeout("Simulated timeout")

    monkeypatch.setattr(pubmed.httpx, "get", timed_out)

    with pytest.raises(RuntimeError, match="timed out"):
        pubmed.search_brca1_articles()


def test_search_http_failure(monkeypatch):
    mock_search(monkeypatch, {}, status=503)

    with pytest.raises(RuntimeError, match="HTTP 503"):
        pubmed.search_brca1_articles()