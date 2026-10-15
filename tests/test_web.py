"""Tests for the local BRCA1 browser viewer."""

import json

import pytest
from fastapi.testclient import TestClient

from app import report, storage
from app.main import app


@pytest.fixture
def viewer_data(tmp_path, monkeypatch):
    """Create isolated evidence for the browser tests."""
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(report, "PROJECT_ROOT", tmp_path)

    raw = storage.save_raw_response(
        "uniprot", b'{"example": "test evidence"}'
    )
    timestamp = "2026-01-01T00:00:00+00:00"
    provenance = {
        "api_url": "https://example.org/api",
        "retrieved_at_utc": timestamp,
        "response_sha256": raw["sha256"],
    }

    bundle = {
        "target": "BRCA1",
        "protein": {
            "evidence_type": "retrieved",
            "source": "UniProt",
            "accession": "P38398",
            "gene": "BRCA1",
            "organism": "Homo sapiens",
            "taxonomy_id": 9606,
            "record_url": (
                "https://www.uniprot.org/uniprotkb/P38398/entry"
            ),
            **provenance,
        },
        "gene": {
            "evidence_type": "retrieved",
            "source": "NCBI Gene",
            "gene_id": "672",
            "gene": "BRCA1",
            "organism": "Homo sapiens",
            "taxonomy_id": 9606,
            "record_url": "https://www.ncbi.nlm.nih.gov/gene/672",
            **provenance,
        },
        "literature": {
            "evidence_type": "retrieved",
            "source": "PubMed",
            "query": "BRCA1[Title/Abstract]",
            "sort": "relevance",
            "total_matching_records": 1,
            "returned_count": 1,
            "articles": [
                {
                    "evidence_type": "retrieved",
                    "source": "PubMed",
                    "pmid": "123456",
                    "title": "Example BRCA1 study",
                    "abstract": "Example research abstract.",
                    "abstract_available": True,
                    "record_url": (
                        "https://pubmed.ncbi.nlm.nih.gov/123456/"
                    ),
                }
            ],
            "search_provenance": dict(provenance),
            "fetch_provenance": dict(provenance),
        },
        "raw_files": [{"source": "uniprot", **raw}],
    }

    bundle_path = tmp_path / "data/bundles/brca1-test.json"
    bundle_path.parent.mkdir(parents=True)

    def save():
        bundle_path.write_text(
            json.dumps(bundle), encoding="utf-8"
        )

    save()
    return bundle, bundle_path, tmp_path / raw["path"], save


def test_viewer_displays_saved_evidence(viewer_data):
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "BRCA1 Evidence Explorer" in response.text
    assert "P38398" in response.text
    assert "1 raw files verified" in response.text
    assert "Example BRCA1 study" in response.text
    assert "Example research abstract." in response.text
    assert (
        'href="https://pubmed.ncbi.nlm.nih.gov/123456/"'
        in response.text
    )


def test_viewer_handles_no_bundle(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    bundle_path.unlink()

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "No saved bundles yet" in response.text
    assert "python.exe -m app.evidence" in response.text


def test_viewer_blocks_corrupted_evidence(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    raw_path.write_bytes(b"corrupted evidence")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 500
    assert "Checksum mismatch" in response.text
    assert "Example BRCA1 study" not in response.text


def test_viewer_escapes_article_html(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    article = bundle["literature"]["articles"][0]
    article["title"] = "<script>alert('test')</script>"
    article["abstract"] = '<img src=x onerror="alert(1)">'
    save()

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "<img src=x" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "&lt;img src=x" in response.text