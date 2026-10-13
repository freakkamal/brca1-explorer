"""Simulated NCBI responses for software testing only."""

import hashlib
from datetime import datetime

import httpx
import pytest

from app import ncbi


@pytest.fixture
def payload():
    return {
        "result": {
            "672": {
                "uid": "672",
                "name": "BRCA1",
                "organism": {
                    "scientificname": "Homo sapiens",
                    "taxid": 9606,
                },
            }
        }
    }


def mock_response(monkeypatch, payload, status=200):
    def fake_get(url, **kwargs):
        request = httpx.Request(
            "GET", url, params=kwargs.get("params")
        )
        return httpx.Response(status, json=payload, request=request)

    monkeypatch.setattr(ncbi.httpx, "get", fake_get)


def test_valid_record_and_provenance(monkeypatch, payload):
    mock_response(monkeypatch, payload)
    result = ncbi.fetch_brca1_gene()

    assert result["gene_id"] == "672"
    assert result["gene"] == "BRCA1"
    assert result["taxonomy_id"] == 9606
    assert result["source"] == "NCBI Gene"
    assert result["evidence_type"] == "retrieved"
    assert result["record_url"] == ncbi.RECORD_URL

    query = httpx.URL(result["api_url"]).params
    assert query["db"] == "gene"
    assert query["id"] == "672"
    assert query["retmode"] == "json"

    timestamp = datetime.fromisoformat(result["retrieved_at_utc"])
    assert timestamp.utcoffset().total_seconds() == 0

    expected_bytes = httpx.Response(200, json=payload).content
    assert result["response_sha256"] == hashlib.sha256(
        expected_bytes
    ).hexdigest()


@pytest.mark.parametrize(
    "problem",
    ["missing", "species", "gene", "id", "api_error", "record_error"],
)
def test_rejects_invalid_record(monkeypatch, payload, problem):
    record = payload["result"]["672"]

    if problem == "missing":
        del record["uid"]
    elif problem == "species":
        record["organism"]["taxid"] = 10090
    elif problem == "gene":
        record["name"] = "OTHER"
    elif problem == "id":
        record["uid"] = "0"
    elif problem == "api_error":
        payload["error"] = "Simulated API error"
    else:
        record["error"] = "Simulated record error"

    mock_response(monkeypatch, payload)

    with pytest.raises(RuntimeError, match="invalid or unexpected"):
        ncbi.fetch_brca1_gene()


def test_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("Simulated timeout")

    monkeypatch.setattr(ncbi.httpx, "get", timeout)

    with pytest.raises(RuntimeError, match="timed out"):
        ncbi.fetch_brca1_gene()


@pytest.mark.parametrize("status", [429, 503])
def test_http_failure(monkeypatch, status):
    mock_response(monkeypatch, {}, status=status)

    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        ncbi.fetch_brca1_gene()