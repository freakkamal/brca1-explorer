"""Tests for the BRCA1 gene API endpoint."""
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_gene_endpoint_success(monkeypatch):
    sample = {
        "evidence_type": "retrieved",
        "source": "NCBI Gene",
        "gene_id": "672",
        "gene": "BRCA1",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "record_url": "https://www.ncbi.nlm.nih.gov/gene/672",
        "api_url": (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            "esummary.fcgi?db=gene&id=672&retmode=json"
        ),
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
        "response_sha256": "0" * 64,
    }

    monkeypatch.setattr(
        main.ncbi, "fetch_brca1_gene", lambda: sample
    )

    response = client.get("/genes/brca1")

    assert response.status_code == 200
    assert response.json() == sample


def test_gene_endpoint_source_failure(monkeypatch):
    def failed_fetch():
        raise RuntimeError("NCBI returned HTTP 503.")

    monkeypatch.setattr(
        main.ncbi, "fetch_brca1_gene", failed_fetch
    )

    response = client.get("/genes/brca1")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "NCBI returned HTTP 503."
    }