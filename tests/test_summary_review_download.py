"""Check summary downloads and their evidence integrity checks."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app import report, storage
from app.main import app


@pytest.fixture
def download_data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(report, "PROJECT_ROOT", tmp_path)

    raw = tmp_path / "data/raw/uniprot/example.json"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b'{"example": true}')

    bundle = {
        "target": "BRCA1",
        "literature": {"articles": [{"pmid": "123456"}]},
        "raw_files": [{
            "path": "data/raw/uniprot/example.json",
            "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        }],
    }
    bundle_path = tmp_path / "data/bundles/brca1-test.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    summary_text = "Example interpretation. PMID: 123456\n<script>alert(1)</script>"
    saved = {
        "target": "BRCA1",
        "summary_id": "test-summary",
        "origin": "ChatGPT - manually imported",
        "imported_at_utc": "2026-10-18T12:00:00+00:00",
        "bundle_filename": bundle_path.name,
        "bundle_sha256": hashlib.sha256(
            bundle_path.read_bytes()
        ).hexdigest(),
        "summary_markdown": summary_text,
        "summary_sha256": hashlib.sha256(
            summary_text.encode("utf-8")
        ).hexdigest(),
    }
    summary_path = tmp_path / "data/summaries/brca1-test.json"
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text(json.dumps(saved), encoding="utf-8")

    params = {
        "summary": summary_path.name,
        "digest": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    }
    return tmp_path, summary_path, raw, saved, params


def test_download_without_reviews(download_data):
    _, _, _, _, params = download_data
    with TestClient(app) as client:
        response = client.get("/download-summary-review", params=params)

    assert response.status_code == 200
    assert "attachment;" in response.headers["content-disposition"]
    assert "Not yet reviewed" in response.text
    assert "https://pubmed.ncbi.nlm.nih.gov/123456/" in response.text
    assert "&lt;script&gt;" in response.text
    assert "<script>" not in response.text
    assert '<form action="/save-review"' not in response.text


def test_download_contains_partial_review(download_data):
    root, _, _, saved, params = download_data
    directory = root / "data/reviews"
    directory.mkdir(parents=True)
    record = {
        "summary_file_sha256": params["digest"],
        "summary_id": saved["summary_id"],
        "summary_sha256": saved["summary_sha256"],
        "bundle_sha256": saved["bundle_sha256"],
        "decision": "in_progress",
        "scope": "selected_claims",
        "reviewer": "Test reviewer",
        "notes": "Checked the saved abstract only.",
        "checked_pmids": ["123456"],
        "reviewed_at_utc": "2026-10-18T13:00:00+00:00",
    }
    (directory / "review-test.json").write_text(
        json.dumps(record), encoding="utf-8"
    )

    with TestClient(app) as client:
        response = client.get("/download-summary-review", params=params)

    assert response.status_code == 200
    assert "Review in progress" in response.text
    assert "Selected claims only" in response.text
    assert "Test reviewer" in response.text
    assert "Checked the saved abstract only." in response.text
    assert "Review history (1 records)" in response.text


def test_download_rejects_changed_summary(download_data):
    _, path, _, _, params = download_data
    path.write_bytes(path.read_bytes() + b"\n")

    with TestClient(app) as client:
        response = client.get("/download-summary-review", params=params)

    assert response.status_code == 409


def test_download_rejects_corrupt_raw_file(download_data):
    _, _, raw, _, params = download_data
    raw.write_bytes(b"changed")

    with TestClient(app) as client:
        response = client.get("/download-summary-review", params=params)

    assert response.status_code == 500
    assert "Checksum mismatch" in response.text
    assert "content-disposition" not in response.headers


def test_download_rejects_path_traversal(download_data):
    _, _, _, _, params = download_data
    params = dict(params, summary="../outside.json")

    with TestClient(app) as client:
        response = client.get("/download-summary-review", params=params)

    assert response.status_code == 404