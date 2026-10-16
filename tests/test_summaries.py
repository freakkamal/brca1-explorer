"""Tests for manually imported AI summaries."""

import hashlib
import json

import pytest

from app import report, storage, summaries


@pytest.fixture
def summary_inputs(tmp_path, monkeypatch):
    """Create temporary evidence and a summary draft."""
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(report, "PROJECT_ROOT", tmp_path)

    raw = storage.save_raw_response(
        "uniprot", b'{"example": "test evidence"}'
    )

    bundle = {
        "target": "BRCA1",
        "bundle_id": "summary-test-bundle",
        "literature": {
            "articles": [{"pmid": "123456"}],
        },
        "raw_files": [{"source": "uniprot", **raw}],
    }

    bundle_path = tmp_path / "data/bundles/brca1-test.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()

    draft = tmp_path / "summary.md"
    draft.write_text(
        "Example research finding. PMID: 123456",
        encoding="utf-8",
    )

    return bundle_path, draft, digest, tmp_path / raw["path"]


def test_import_saves_linked_unreviewed_summary(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs
    original_bundle = bundle_path.read_bytes()

    destination = summaries.import_summary(
        bundle_path, draft, digest
    )
    saved = json.loads(destination.read_text(encoding="utf-8"))

    assert saved["bundle_sha256"] == digest
    assert saved["bundle_id"] == "summary-test-bundle"
    assert saved["review_status"] == "not_yet_reviewed"
    assert saved["origin"] == "ChatGPT — manually imported"
    assert saved["cited_pmids"] == ["123456"]
    assert saved["summary_markdown"] == draft.read_text(
        encoding="utf-8"
    )
    assert saved["summary_sha256"] == hashlib.sha256(
        saved["summary_markdown"].encode("utf-8")
    ).hexdigest()
    assert bundle_path.read_bytes() == original_bundle


def test_import_rejects_wrong_bundle_checksum(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs

    with pytest.raises(ValueError, match="checksum does not match"):
        summaries.import_summary(bundle_path, draft, "0" * 64)

    assert not (storage.PROJECT_ROOT / "data/summaries").exists()


def test_import_rejects_unknown_pmid(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs
    draft.write_text("Unsupported reference. PMID: 999999", encoding="utf-8")

    with pytest.raises(ValueError, match="absent from the bundle"):
        summaries.import_summary(bundle_path, draft, digest)


def test_import_rejects_missing_citations(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs
    draft.write_text("A summary without citations.", encoding="utf-8")

    with pytest.raises(ValueError, match="No citations found"):
        summaries.import_summary(bundle_path, draft, digest)


def test_import_rejects_empty_summary(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs
    draft.write_text("   \n", encoding="utf-8")

    with pytest.raises(ValueError, match="summary file is empty"):
        summaries.import_summary(bundle_path, draft, digest)


def test_import_rejects_corrupted_evidence(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs
    raw_path.write_bytes(b"changed evidence")

    with pytest.raises(ValueError, match="Checksum mismatch"):
        summaries.import_summary(bundle_path, draft, digest)


def test_import_preserves_previous_summary(summary_inputs):
    bundle_path, draft, digest, raw_path = summary_inputs

    first = summaries.import_summary(bundle_path, draft, digest)
    original = first.read_bytes()

    draft.write_text(
        "A revised research summary. PMID: 123456",
        encoding="utf-8",
    )
    second = summaries.import_summary(bundle_path, draft, digest)

    assert first != second
    assert first.read_bytes() == original
    assert second.is_file()


def test_extract_pmids_recognizes_labels_and_links():
    text = (
        "PMID: 123456; PMID 123456; "
        "https://pubmed.ncbi.nlm.nih.gov/234567/"
    )

    assert summaries.extract_pmids(text) == ["123456", "234567"]