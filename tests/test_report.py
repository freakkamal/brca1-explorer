"""Tests for readable evidence reports and raw-file verification."""

import hashlib
import json

import pytest

from app import report


@pytest.fixture
def report_bundle(tmp_path, monkeypatch):
    """Create a small evidence bundle with one real raw file."""
    monkeypatch.setattr(report, "PROJECT_ROOT", tmp_path)

    raw_content = b'{"example": "raw evidence"}'
    digest = hashlib.sha256(raw_content).hexdigest()
    relative_path = f"data/raw/uniprot/{digest}.json"

    raw_path = tmp_path / relative_path
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(raw_content)

    bundle = {
        "target": "BRCA1",
        "bundle_id": "test-bundle",
        "code_provenance": {
            "commit": "test-commit",
            "working_tree_dirty": False,
        },
        "gene": {
            "gene": "BRCA1",
            "gene_id": "672",
            "organism": "Homo sapiens",
            "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
            "record_url": "https://www.ncbi.nlm.nih.gov/gene/672",
        },
        "protein": {
            "accession": "P38398",
            "organism": "Homo sapiens",
            "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
            "record_url": (
                "https://www.uniprot.org/uniprotkb/P38398/entry"
            ),
        },
        "literature": {
            "query": "BRCA1[Title/Abstract]",
            "sort": "relevance",
            "total_matching_records": 1,
            "search_provenance": {
                "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
            },
            "articles": [
                {
                    "pmid": "123456",
                    "title": "Example BRCA1 article",
                    "abstract": "Example abstract for testing.",
                    "record_url": (
                        "https://pubmed.ncbi.nlm.nih.gov/123456/"
                    ),
                }
            ],
        },
        "raw_files": [
            {
                "source": "uniprot",
                "path": relative_path,
                "sha256": digest,
                "size_bytes": len(raw_content),
            }
        ],
    }

    bundle_path = tmp_path / "test-bundle.json"

    def save_bundle():
        bundle_path.write_text(
            json.dumps(bundle), encoding="utf-8"
        )
        return bundle_path

    save_bundle()
    return bundle, bundle_path, raw_path, save_bundle


def test_report_contains_evidence(report_bundle):
    bundle, bundle_path, raw_path, save_bundle = report_bundle

    destination = report.create_report(bundle_path)
    text = destination.read_text(encoding="utf-8")

    assert "# BRCA1 evidence report" in text
    assert "NCBI Gene ID: 672" in text
    assert "UniProt accession: P38398" in text
    assert "Raw files verified: 1" in text
    assert "Example BRCA1 article" in text
    assert "Example abstract for testing." in text
    assert "https://pubmed.ncbi.nlm.nih.gov/123456/" in text
    assert "Not for clinical decisions." in text


def test_report_handles_missing_abstract(report_bundle):
    bundle, bundle_path, raw_path, save_bundle = report_bundle
    bundle["literature"]["articles"][0]["abstract"] = None
    save_bundle()

    destination = report.create_report(bundle_path)

    assert "No abstract available." in destination.read_text(
        encoding="utf-8"
    )


def test_report_handles_no_articles(report_bundle):
    bundle, bundle_path, raw_path, save_bundle = report_bundle
    bundle["literature"]["articles"] = []
    bundle["literature"]["total_matching_records"] = 0
    save_bundle()

    destination = report.create_report(bundle_path)
    text = destination.read_text(encoding="utf-8")

    assert "Articles included: 0" in text
    assert "No articles were returned." in text


def test_missing_raw_file_blocks_report(report_bundle):
    bundle, bundle_path, raw_path, save_bundle = report_bundle
    raw_path.unlink()

    with pytest.raises(ValueError, match="Raw file is missing"):
        report.create_report(bundle_path)

    assert not (report.PROJECT_ROOT / "data/reports").exists()


def test_corrupted_raw_file_blocks_report(report_bundle):
    bundle, bundle_path, raw_path, save_bundle = report_bundle
    raw_path.write_bytes(b"changed evidence")

    with pytest.raises(ValueError, match="Checksum mismatch"):
        report.create_report(bundle_path)

    assert not (report.PROJECT_ROOT / "data/reports").exists()


def test_path_outside_raw_directory_is_rejected(report_bundle):
    bundle, bundle_path, raw_path, save_bundle = report_bundle

    outside_path = report.PROJECT_ROOT / "outside.json"
    outside_path.write_bytes(raw_path.read_bytes())
    bundle["raw_files"][0]["path"] = "data/raw/../../outside.json"
    save_bundle()

    with pytest.raises(ValueError, match="outside data/raw"):
        report.create_report(bundle_path)

    assert not (report.PROJECT_ROOT / "data/reports").exists()