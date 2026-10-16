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



def test_viewer_selects_older_bundle(viewer_data):
    import os

    bundle, bundle_path, raw_path, save = viewer_data

    # Keep the original bundle and create a newer, distinct bundle.
    newer = json.loads(json.dumps(bundle))
    newer["literature"]["articles"][0]["title"] = "Newer BRCA1 study"
    newer_path = bundle_path.parent / "brca1-newer.json"
    newer_path.write_text(json.dumps(newer), encoding="utf-8")

    os.utime(bundle_path, (1700000000, 1700000000))
    os.utime(newer_path, (1700000100, 1700000100))

    with TestClient(app) as client:
        default_response = client.get("/")
        selected_response = client.get(
            "/", params={"bundle": bundle_path.name}
        )

    assert default_response.status_code == 200
    assert "Newer BRCA1 study" in default_response.text
    assert "Example BRCA1 study" not in default_response.text

    assert selected_response.status_code == 200
    assert "Example BRCA1 study" in selected_response.text
    assert "Newer BRCA1 study" not in selected_response.text
    assert "Showing the bundle you selected." in selected_response.text
    assert (
        f'value="{bundle_path.name}" selected'
        in selected_response.text
    )
    assert f'value="{newer_path.name}"' in selected_response.text


def test_viewer_rejects_unknown_bundle(viewer_data):
    with TestClient(app) as client:
        response = client.get(
            "/", params={"bundle": "brca1-missing.json"}
        )

    assert response.status_code == 404
    assert "Bundle not found" in response.text
    assert "Example BRCA1 study" not in response.text


def test_viewer_rejects_path_outside_bundle_folder(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data

    # Create a real file outside the bundles folder.
    outside_path = storage.PROJECT_ROOT / "outside.json"
    outside_path.write_text(json.dumps(bundle), encoding="utf-8")

    with TestClient(app) as client:
        response = client.get(
            "/", params={"bundle": "../../outside.json"}
        )

    assert response.status_code == 404
    assert "Bundle not found" in response.text
    assert "Example BRCA1 study" not in response.text


def test_viewer_rejects_selection_when_no_bundles_exist(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    bundle_path.unlink()

    with TestClient(app) as client:
        response = client.get(
            "/", params={"bundle": bundle_path.name}
        )

    assert response.status_code == 404
    assert "Bundle not found" in response.text



def test_download_returns_markdown_report(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data

    # The report includes these fields in addition to viewer data.
    bundle["bundle_id"] = "download-test"
    bundle["code_provenance"] = {
        "commit": "test-commit",
        "working_tree_dirty": False,
    }
    save()

    with TestClient(app) as client:
        response = client.get(
            "/download-report",
            params={"bundle": bundle_path.name},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    disposition = response.headers["content-disposition"]
    assert "attachment" in disposition
    assert ".md" in disposition
    assert "# BRCA1 evidence report" in response.text
    assert "Bundle ID: download-test" in response.text
    assert "NCBI Gene ID: 672" in response.text
    assert "UniProt accession: P38398" in response.text
    assert "Example BRCA1 study" in response.text
    assert "Raw files verified: 1" in response.text


def test_download_rejects_unknown_bundle(viewer_data):
    with TestClient(app) as client:
        response = client.get(
            "/download-report",
            params={"bundle": "brca1-missing.json"},
        )

    assert response.status_code == 404
    assert "Bundle not found" in response.text
    assert "content-disposition" not in response.headers


def test_download_blocks_corrupted_raw_file(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    raw_path.write_bytes(b"corrupted evidence")

    with TestClient(app) as client:
        response = client.get(
            "/download-report",
            params={"bundle": bundle_path.name},
        )

    assert response.status_code == 500
    assert "Checksum mismatch" in response.text
    assert "content-disposition" not in response.headers
    assert not (storage.PROJECT_ROOT / "data/reports").exists()


def test_download_blocks_missing_raw_file(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    raw_path.unlink()

    with TestClient(app) as client:
        response = client.get(
            "/download-report",
            params={"bundle": bundle_path.name},
        )

    assert response.status_code == 500
    assert "Raw file is missing" in response.text
    assert "content-disposition" not in response.headers


def test_download_rejects_path_outside_bundle_folder(viewer_data):
    bundle, bundle_path, raw_path, save = viewer_data
    outside = storage.PROJECT_ROOT / "outside.json"
    outside.write_text(json.dumps(bundle), encoding="utf-8")

    with TestClient(app) as client:
        response = client.get(
            "/download-report",
            params={"bundle": "../../outside.json"},
        )

    assert response.status_code == 404
    assert "Bundle not found" in response.text
    assert "content-disposition" not in response.headers



@pytest.fixture
def displayed_summary(viewer_data):
    """Import a summary linked to the temporary viewer bundle."""
    import hashlib
    from app import summaries

    bundle, bundle_path, raw_path, save = viewer_data
    bundle["bundle_id"] = "viewer-summary-test"
    save()

    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    draft = storage.PROJECT_ROOT / "summary-draft.md"
    draft.write_text(
        "A test interpretation. PMID: 123456",
        encoding="utf-8",
    )

    summary_path = summaries.import_summary(
        bundle_path, draft, digest
    )
    return bundle_path, summary_path


def test_viewer_displays_imported_summary(displayed_summary):
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Imported AI summary" in response.text
    assert "Not yet reviewed" in response.text
    assert "A test interpretation." in response.text
    assert "Cited articles:" in response.text
    assert (
        'href="https://pubmed.ncbi.nlm.nih.gov/123456/"'
        in response.text
    )


def test_viewer_handles_no_imported_summary(viewer_data):
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "No imported summary is saved for this bundle." in response.text
    assert "Example BRCA1 study" in response.text


def test_viewer_blocks_changed_summary_text(displayed_summary):
    bundle_path, summary_path = displayed_summary
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    saved["summary_markdown"] = "Changed text. PMID: 123456"
    summary_path.write_text(json.dumps(saved), encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "AI summary unavailable" in response.text
    assert "Summary text checksum mismatch." in response.text
    assert "Changed text." not in response.text
    assert "Example BRCA1 study" in response.text


def test_viewer_does_not_attach_summary_to_changed_bundle(displayed_summary):
    bundle_path, summary_path = displayed_summary
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["bundle_id"] = "different-bundle"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "No imported summary is saved for this bundle." in response.text
    assert "A test interpretation." not in response.text


def test_viewer_escapes_imported_summary_html(displayed_summary):
    import hashlib

    bundle_path, summary_path = displayed_summary
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_text = "<script>alert('test')</script> PMID: 123456"
    saved["summary_markdown"] = summary_text
    saved["summary_sha256"] = hashlib.sha256(
        summary_text.encode("utf-8")
    ).hexdigest()
    summary_path.write_text(json.dumps(saved), encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text