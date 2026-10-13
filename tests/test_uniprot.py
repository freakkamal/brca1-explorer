"""Simulated responses for software testing, not research evidence."""

import httpx
import pytest

from app import uniprot


@pytest.fixture
def record():
    # Minimal test fixture matching the expected response structure.
    return {
        "primaryAccession": "P38398",
        "organism": {
            "scientificName": "Homo sapiens",
            "taxonId": 9606,
        },
        "genes": [{"geneName": {"value": "BRCA1"}}],
    }


def mock_response(monkeypatch, payload, status=200):
    response = httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", uniprot.API_URL),
    )
    monkeypatch.setattr(
        uniprot.httpx, "get", lambda *args, **kwargs: response
    )


def test_valid_record(monkeypatch, record):
    mock_response(monkeypatch, record)
    result = uniprot.fetch_brca1_protein()

    assert result["accession"] == "P38398"
    assert result["gene"] == "BRCA1"
    assert result["taxonomy_id"] == 9606
    assert result["evidence_type"] == "retrieved"
    assert result["api_url"] == uniprot.API_URL


@pytest.mark.parametrize("problem", ["missing", "species", "gene"])
def test_rejects_invalid_record(monkeypatch, record, problem):
    if problem == "missing":
        del record["primaryAccession"]
    elif problem == "species":
        record["organism"]["taxonId"] = 10090
    else:
        record["genes"] = [{"geneName": {"value": "OTHER"}}]

    mock_response(monkeypatch, record)

    with pytest.raises(RuntimeError, match="invalid or unexpected"):
        uniprot.fetch_brca1_protein()


def test_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("Simulated timeout")

    monkeypatch.setattr(uniprot.httpx, "get", timeout)

    with pytest.raises(RuntimeError, match="timed out"):
        uniprot.fetch_brca1_protein()


def test_http_failure(monkeypatch):
    mock_response(monkeypatch, {}, status=503)

    with pytest.raises(RuntimeError, match="HTTP 503"):
        uniprot.fetch_brca1_protein()