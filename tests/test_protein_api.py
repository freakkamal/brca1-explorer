"""API tests using simulated data, not live research evidence."""

from fastapi.testclient import TestClient

from app import main


def test_protein_endpoint_success(monkeypatch):
    simulated_result = {
        "evidence_type": "retrieved",
        "source": "UniProt",
        "accession": "P38398",
        "gene": "BRCA1",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "record_url": "https://www.uniprot.org/uniprotkb/P38398/entry",
        "api_url": "https://rest.uniprot.org/uniprotkb/P38398.json",
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
        "response_sha256": "0" * 64,  # Placeholder for this test only.
    }

    monkeypatch.setattr(
        main.uniprot,
        "fetch_brca1_protein",
        lambda: simulated_result,
    )

    with TestClient(main.app) as client:
        response = client.get("/proteins/brca1")

    assert response.status_code == 200
    assert response.json() == simulated_result


def test_protein_endpoint_failure(monkeypatch):
    def failed_retrieval():
        raise RuntimeError("UniProt returned HTTP 503.")

    monkeypatch.setattr(
        main.uniprot,
        "fetch_brca1_protein",
        failed_retrieval,
    )

    with TestClient(main.app) as client:
        response = client.get("/proteins/brca1")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "UniProt returned HTTP 503."
    }